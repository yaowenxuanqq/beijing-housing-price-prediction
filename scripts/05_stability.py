# -*- coding: utf-8 -*-
"""
05_stability.py —— 部署模型定稿 + 3 种子稳定性验证

背景：
  04_tune.py 的 ratio 调参在 RF 上选中 n_estimators=150（R²=0.8665）；
  实测 100 棵为 0.8664，体积 92.7 MB（150 棵为 138.6 MB）。
  按体积/收益比，定稿采用 100 棵。

流程：
  1. 读取 metrics_tuned_v1.json 的最优 RF 参数，强制 n_estimators=100
  2. 3 个随机种子分别训练，评估 ES-3，报告均值 ± 标准差
  3. 在训练集内部执行 TimeSeriesSplit(5)，用折外残差分位校准预测区间
  4. seed=42 的模型（含区间元数据）保存为 data/models/tuned_rf_es3.joblib
  5. 回写 metrics_tuned_v1.json 的 RF 条目（参数与三个实验指标）
  6. 输出 data/stability_v1.json（含区间实测覆盖率）

用法：.venv/Scripts/python.exe scripts/05_stability.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ml.metrics import reg_metrics  # noqa: E402
from ml.preprocessing import HousingPreprocessor, prepare  # noqa: E402

DATA = ROOT / "data" / "clean.parquet"
MODEL_DIR = ROOT / "data" / "models"
TUNED_JSON = ROOT / "data" / "metrics_tuned_v1.json"
OUT_JSON = ROOT / "data" / "stability_v1.json"

CUT = pd.Timestamp("2016-07-01")
N_TREES = 100          # 已确认：100 棵 vs 150 棵指标几乎相同，体积少 46 MB
SEEDS = [42, 2024, 7]
CALIBRATION_SPLITS = 5
INTERVAL_LEVEL = 0.8
RATIO_MIN, RATIO_MAX = 0.05, 9.0


def ratio_target(d: pd.DataFrame):
    base = d.groupby([d.trade_date.dt.year, "district_name"]).unit_price.transform("median")
    return (d.unit_price / base).to_numpy(), base.to_numpy()


def calibrate_interval(tr: pd.DataFrame, params: dict, seed: int) -> dict:
    """用训练集内部的时序折外残差校准 ratio 预测区间。"""
    ordered = tr.sort_values("trade_date", kind="mergesort").reset_index(drop=True)
    y, _ = ratio_target(ordered)
    residuals = []
    folds = TimeSeriesSplit(n_splits=CALIBRATION_SPLITS)

    for fit_idx, val_idx in folds.split(ordered):
        pipe = Pipeline([
            ("prep", HousingPreprocessor("tree")),
            ("model", RandomForestRegressor(random_state=seed, n_jobs=-1, **params)),
        ])
        pipe.fit(ordered.iloc[fit_idx], y[fit_idx])
        pred = np.clip(pipe.predict(ordered.iloc[val_idx]), RATIO_MIN, RATIO_MAX)
        residuals.append(y[val_idx] - pred)

    residuals = np.concatenate(residuals)
    alpha = (1.0 - INTERVAL_LEVEL) / 2.0
    q_low, q_high = np.quantile(residuals, [alpha, 1.0 - alpha])
    return {
        "method": "time_series_cv_residual_quantile",
        "level": INTERVAL_LEVEL,
        "n_splits": CALIBRATION_SPLITS,
        "calibration_rows": int(len(residuals)),
        "q_low": float(q_low),
        "q_high": float(q_high),
        "seed": seed,
        "note": "仅使用训练集内部时序折外残差；经验校准区间，不是严格置信区间。",
    }


def main() -> int:
    tuned = json.loads(TUNED_JSON.read_text(encoding="utf-8"))
    raw_params = tuned["tuning"]["rf"]["params"]
    params = {k.replace("model__", ""): v for k, v in raw_params.items()}
    params["n_estimators"] = N_TREES

    df = prepare(pd.read_parquet(DATA))
    tr, te = df[df.trade_date < CUT].copy(), df[df.trade_date >= CUT].copy()
    y_tr, _ = ratio_target(tr)
    _, base_te = ratio_target(te)

    print("=" * 66)
    print("05_stability.py —— 部署模型定稿（RF, ratio 口径）")
    print("=" * 66)
    print("参数:", params)

    runs = []
    official = None
    for seed in SEEDS:
        pipe = Pipeline([
            ("prep", HousingPreprocessor("tree")),
            ("model", RandomForestRegressor(random_state=seed, n_jobs=-1, **params)),
        ])
        pipe.fit(tr, y_tr)
        pred = np.clip(pipe.predict(te), y_tr.min(), y_tr.max())
        unit = pred * base_te
        r2 = float(r2_score(te.unit_price.to_numpy(), unit))
        mae = float(mean_absolute_error(te.unit_price.to_numpy(), unit))
        runs.append({"seed": seed, "r2_unit": r2, "mae_unit": mae})
        print(f"  seed={seed:<5} R2={r2:.4f}  MAE={mae:.0f} 元/㎡")
        if seed == 42:
            official = pipe

    calibration = calibrate_interval(tr, params, SEEDS[0])
    official.interval_calibration_ = calibration
    print(f"\n  区间校准: q10={calibration['q_low']:.6f}  q90={calibration['q_high']:.6f}")

    r2s = np.array([r["r2_unit"] for r in runs])
    maes = np.array([r["mae_unit"] for r in runs])
    summary = {
        "model": "RandomForestRegressor",
        "model_version": "tuned_rf_es3_v2",
        "target": "ratio",
        "n_estimators": N_TREES,
        "params": params,
        "seeds": SEEDS,
        "runs": runs,
        "r2_mean": float(r2s.mean()), "r2_std": float(r2s.std(ddof=1)),
        "mae_mean": float(maes.mean()), "mae_std": float(maes.std(ddof=1)),
        "interval_calibration": calibration,
    }
    print(f"\n  R2   = {summary['r2_mean']:.4f} +/- {summary['r2_std']:.4f}")
    print(f"  MAE  = {summary['mae_mean']:.0f} +/- {summary['mae_std']:.0f} 元/㎡")

    # 保存定稿模型
    path = MODEL_DIR / "tuned_rf_es3.joblib"
    joblib.dump(official, path, compress=3)
    mb = path.stat().st_size / 1024 / 1024
    print(f"\n  已保存: {path.name} ({mb:.1f} MB)")

    # 回写 metrics_tuned_v1.json 的 RF 条目（参数 + 三实验指标）
    params_out = {("model__" + k): v for k, v in params.items()}
    tuned["tuning"]["rf"]["params"] = params_out
    tuned["tuning"]["rf"]["note"] = f"n_estimators 由搜索的 150 降为 100（指标相同，体积 -46MB）"

    rng = np.random.default_rng(42)
    idx = rng.permutation(len(df)); n = int(len(df) * 0.8)
    rtr, rte = df.iloc[idx[:n]], df.iloc[idx[n:]]

    # ES-1 随机 + log 总价
    p1 = Pipeline([("prep", HousingPreprocessor("tree")),
                   ("model", RandomForestRegressor(random_state=42, n_jobs=-1, **params))])
    y1tr = np.log1p(rtr.total_price.to_numpy())
    p1.fit(rtr, y1tr)
    pred1 = np.clip(np.expm1(p1.predict(rte)), rtr.total_price.min(), rtr.total_price.max())
    unit1 = pred1 * 10000 / rte.square.to_numpy()
    m1 = reg_metrics(rte.total_price.to_numpy(), pred1, 10.0)
    m1["r2_target"] = "log1p_total_price"
    m1["mae_unit_price"] = float(mean_absolute_error(rte.unit_price.to_numpy(), unit1))
    m1["r2_unit"] = float(r2_score(rte.unit_price.to_numpy(), unit1))

    # ES-2 时序 + log 总价
    p2 = Pipeline([("prep", HousingPreprocessor("tree")),
                   ("model", RandomForestRegressor(random_state=42, n_jobs=-1, **params))])
    y2tr = np.log1p(tr.total_price.to_numpy())
    p2.fit(tr, y2tr)
    pred2 = np.clip(np.expm1(p2.predict(te)), tr.total_price.min(), tr.total_price.max())
    unit2 = pred2 * 10000 / te.square.to_numpy()
    m2 = reg_metrics(te.total_price.to_numpy(), pred2, 10.0)
    m2["r2_target"] = "log1p_total_price"
    m2["mae_unit_price"] = float(mean_absolute_error(te.unit_price.to_numpy(), unit2))
    m2["r2_unit"] = float(r2_score(te.unit_price.to_numpy(), unit2))

    # ES-3 用稳定性 seed=42 的结果（复用同一份预测，含截断）
    pred3 = np.clip(official.predict(te), y_tr.min(), y_tr.max())
    unit3 = pred3 * base_te
    y_te, _ = ratio_target(te)
    m3 = reg_metrics(te.unit_price.to_numpy(), unit3, 10000.0)
    m3["r2_target"] = "unit_price"
    m3["r2_ratio"] = float(1 - np.sum((y_te - pred3) ** 2) / np.sum((y_te - y_te.mean()) ** 2))
    m3["r2_unit"] = m3["r2"]

    interval_low = np.minimum(pred3, pred3 + calibration["q_low"])
    interval_high = np.maximum(pred3, pred3 + calibration["q_high"])
    summary["interval_calibration"]["test_coverage"] = float(np.mean((y_te >= interval_low) & (y_te <= interval_high)))
    summary["interval_calibration"]["test_rows"] = int(len(te))
    print(f"  区间实测覆盖率: {summary['interval_calibration']['test_coverage']:.2%}（测试集 {len(te):,} 行）")

    for e in tuned["experiments"]:
        if e["model"] != "rf":
            continue
        e["params"] = params_out
        e["metrics"]["ES1_random_logtotal"] = m1
        e["metrics"]["ES2_time_logtotal"] = m2
        e["metrics"]["ES3_time_ratio"] = m3

    TUNED_JSON.write_text(json.dumps(tuned, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n  已回写 {TUNED_JSON.name}；已输出 {OUT_JSON.name}")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
