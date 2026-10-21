# -*- coding: utf-8 -*-
"""
04_tune.py —— P2b 超参数调优（按项目计划书 6.6.1 约束）

流程：
  1. 时序划分取出训练集（2011-01 ~ 2016-06）
  2. 从训练集内抽取 5 万条子样本（禁止用全量/测试集）
  3. RandomizedSearchCV(n_iter <= 30) + TimeSeriesSplit(5) 调参
  4. 用最优参数在**完整训练集**上重新训练
  5. 在 ES-1 / ES-2 / ES-3 三个口径上评估，与基线结果对比
  6. 保存调优后的完整 Pipeline（compress=3）

输出：
  data/metrics_tuned_v1.json
  data/models/tuned_*.joblib

用法：.venv/Scripts/python.exe scripts/04_tune.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from joblib import parallel_backend
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ml.metrics import mape, reg_metrics  # noqa: E402
from ml.preprocessing import HousingPreprocessor, prepare  # noqa: E402

DATA = ROOT / "data" / "clean.parquet"
MODEL_DIR = ROOT / "data" / "models"
OUT_JSON = ROOT / "data" / "metrics_tuned_v1.json"
BASE_JSON = ROOT / "data" / "metrics_v1.json"

CUT_DATE = pd.Timestamp("2016-07-01")
SEED = 42
TUNE_N = 50_000

# 调参预算（计划书 6.6.1）
N_ITER = {"tree": 20, "rf": 20, "xgboost": 20, "mlp": 6}


def model_and_grid(name: str):
    if name == "tree":
        return DecisionTreeRegressor(random_state=SEED), {
            "model__max_depth": [5, 8, 12, 16, 20, None],
            "model__min_samples_leaf": [1, 5, 10, 20, 50],
            "model__min_samples_split": [2, 10, 20, 50],
        }
    if name == "rf":
        return RandomForestRegressor(n_estimators=100, random_state=SEED, n_jobs=-1), {
            "model__n_estimators": [100, 150],
            # 禁止 max_depth=None：无深度限制会产出 GB 级模型，Django 无法加载
            "model__max_depth": [15, 20, 25],
            "model__min_samples_leaf": [5, 10],
            "model__max_features": [0.5, 0.7],
        }
    if name == "xgboost":
        return XGBRegressor(tree_method="hist", n_jobs=-1, random_state=SEED), {
            "model__n_estimators": [300, 600],
            "model__learning_rate": [0.03, 0.05, 0.08],
            "model__max_depth": [4, 6, 8],
            "model__subsample": [0.7, 0.9],
            "model__colsample_bytree": [0.7, 0.9],
            "model__reg_lambda": [1, 5],
        }
    if name == "mlp":
        return MLPRegressor(max_iter=100, early_stopping=True, random_state=SEED), {
            "model__hidden_layer_sizes": [(64,), (128,), (128, 64)],
            "model__alpha": [1e-4, 1e-3, 1e-2],
            "model__learning_rate_init": [0.001, 0.01],
        }
    raise ValueError(name)


def make_pipe(model, kind):
    return Pipeline([("prep", HousingPreprocessor(model_kind=kind)), ("model", model)])


def eval_log_total(pipe, tr, te):
    y_tr, y_te = np.log1p(tr.total_price.to_numpy()), np.log1p(te.total_price.to_numpy())
    pipe.fit(tr, y_tr)
    pred = np.expm1(pipe.predict(te))
    # 预测截断到训练集目标范围（生产环境同样需要该保护，防止模型外推爆炸）
    lo, hi = float(tr.total_price.min()), float(tr.total_price.max())
    pred = np.clip(pred, lo, hi)
    m = reg_metrics(te.total_price.to_numpy(), pred, 10.0)
    unit_pred = pred * 10000 / te.square.to_numpy()
    m["mae_unit_price"] = float(np.mean(np.abs(te.unit_price.to_numpy() - unit_pred)))
    m["r2_unit"] = float(r2_score(te.unit_price.to_numpy(), unit_pred))
    return m, pipe


def eval_ratio(pipe, tr, te):
    def ratio(d):
        base = d.groupby([d.trade_date.dt.year, "district_name"]).unit_price.transform("median")
        return (d.unit_price / base).to_numpy(), base.to_numpy()
    y_tr, _ = ratio(tr)
    y_te, base_te = ratio(te)
    pipe.fit(tr, y_tr)
    pred = pipe.predict(te)
    pred = np.clip(pred, float(y_tr.min()), float(y_tr.max()))   # 同上，截断到训练 ratio 范围
    unit_pred = pred * base_te
    m = reg_metrics(te.unit_price.to_numpy(), unit_pred, 10000.0)
    m["r2_ratio"] = float(1 - np.sum((y_te - pred) ** 2) / np.sum((y_te - y_te.mean()) ** 2))
    m["r2_unit"] = m["r2"]      # ratio 分支的 m["r2"] 本就是单价口径
    return m, pipe


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-only", action="store_true",
                    help="跳过调参，复用 metrics_tuned_v1.json 中已保存的最优参数重新评估")
    ap.add_argument("--target", choices=["ratio", "log_total"], default="ratio",
                    help="调参目标：ratio（部署口径，默认）或 log_total")
    args = ap.parse_args()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("04_tune.py —— P2b 超参数调优")
    print("=" * 70)

    df = prepare(pd.read_parquet(DATA))
    tr = df[df.trade_date < CUT_DATE].copy()
    te = df[df.trade_date >= CUT_DATE].copy()
    print(f"训练 {len(tr):,} / 测试 {len(te):,}")

    # 目标构造：
    #   ratio 的基准（年×区中位单价）必须先在【完整训练集】上计算，再抽样。
    #   若在子样本上算，小分组中位数噪声会污染目标（实测 R² 掉 0.03 以上）。
    if args.target == "ratio":
        base_full = tr.groupby([tr.trade_date.dt.year, "district_name"]).unit_price.transform("median")
        tr_target = tr.assign(_target=tr.unit_price / base_full)
        print("调参目标: ratio（基准在完整训练集上计算）")
    else:
        tr_target = tr.assign(_target=np.log1p(tr.total_price.to_numpy()))
        print("调参目标: log1p(总价)")

    # 调参子样本：训练集内随机抽 5 万，按日期排序以配合 TimeSeriesSplit
    sub = tr_target.sample(n=min(TUNE_N, len(tr_target)), random_state=SEED).sort_values("trade_date").reset_index(drop=True)
    print(f"调参子样本: {len(sub):,} 行（训练集内，已按日期排序）")

    y_sub = sub["_target"].to_numpy()
    cv = TimeSeriesSplit(n_splits=5)

    tuned = {}
    names = ["tree", "rf", "xgboost", "mlp"]
    if args.eval_only:
        if not OUT_JSON.exists():
            raise SystemExit("--eval-only 需要已有的 metrics_tuned_v1.json")
        tuned = json.loads(OUT_JSON.read_text(encoding="utf-8"))["tuning"]
        print("eval-only：复用已有调参结果，跳过搜索")
    else:
      for name in names:
        print(f"\n{'-' * 70}\n调参 {name}（n_iter={N_ITER[name]}）")
        model, grid = model_and_grid(name)
        pipe = make_pipe(model, "linear" if name == "mlp" else "tree")
        t0 = time.time()
        search = RandomizedSearchCV(
            pipe, grid, n_iter=N_ITER[name], cv=cv,
            scoring="neg_mean_absolute_error", n_jobs=-1,
            random_state=SEED, verbose=1, refit=True,
        )
        # Windows 下 loky 进程池会因自定义 Transformer 无法反序列化而失败，改用线程后端
        with parallel_backend("threading"):
            search.fit(sub, y_sub)
        elapsed = time.time() - t0
        print(f"  最优 CV MAE: {-search.best_score_:.4f}（log 尺度）  用时 {elapsed:.0f}s")
        print(f"  最优参数: {search.best_params_}")
        tuned[name] = {"params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in search.best_params_.items()},
                       "cv_mae_log": float(-search.best_score_), "tune_seconds": round(elapsed, 1)}

    # ---- 用最优参数在完整训练集上重训并评估 ----
    print(f"\n{'=' * 70}\n调优后评估\n{'=' * 70}")
    results = {"generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
               "tuning_target": args.target,
               "tune_sample": TUNE_N, "cv": "TimeSeriesSplit(5)", "seed": SEED,
               "tuning": tuned, "experiments": []}

    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(df))
    n_tr = int(len(df) * 0.8)
    rand_tr, rand_te = df.iloc[idx[:n_tr]], df.iloc[idx[n_tr:]]

    for name in ["tree", "rf", "xgboost", "mlp"]:
        kind = "linear" if name == "mlp" else "tree"
        model, _ = model_and_grid(name)
        best = clone(model).set_params(**{k.replace("model__", ""): v for k, v in tuned[name]["params"].items()})

        print(f"\n[{name}]")
        exp_results = {}

        # ES-2 / ES-3 公共：时序训练集
        t0 = time.time()
        m2, _ = eval_log_total(make_pipe(clone(best), kind), tr, te)
        exp_results["ES2_time_logtotal"] = m2
        print(f"  ES-2 R2={m2['r2']:.4f}  MAE={m2['mae']:.2f}  ({time.time()-t0:.0f}s)")

        t0 = time.time()
        m3, p3 = eval_ratio(make_pipe(clone(best), kind), tr, te)
        exp_results["ES3_time_ratio"] = m3
        print(f"  ES-3 R2={m3['r2']:.4f}  MAE_unit={m3['mae']:.0f}  R2_ratio={m3['r2_ratio']:.4f}  ({time.time()-t0:.0f}s)")

        t0 = time.time()
        m1, _ = eval_log_total(make_pipe(clone(best), kind), rand_tr, rand_te)
        exp_results["ES1_random_logtotal"] = m1
        print(f"  ES-1 R2={m1['r2']:.4f}  MAE={m1['mae']:.2f}  ({time.time()-t0:.0f}s)")

        # 保存 ES-3（相对价格口径）完整 Pipeline，供系统推理使用
        joblib.dump(p3, MODEL_DIR / f"tuned_{name}_es3.joblib", compress=3)
        results["experiments"].append({"model": name, "params": tuned[name]["params"], "metrics": exp_results})

    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 与基线对比 ----
    print(f"\n{'=' * 70}\n调优前后对比（R²）\n{'=' * 70}")
    base = json.loads(BASE_JSON.read_text(encoding="utf-8")) if BASE_JSON.exists() else None
    base_map = {}
    if base:
        for e in base["experiments"]:
            for k, v in e["models"].items():
                base_map[(e["experiment"], k)] = v["r2"]
    header = f"{'模型':<10}{'ES1 基线':>10}{'ES1 调优':>10}{'ES2 基线':>10}{'ES2 调优':>10}{'ES3 基线':>10}{'ES3 调优':>10}"
    print(header)
    for r in results["experiments"]:
        n = r["model"]
        row = f"{n:<10}"
        for exp in ["ES1_random_logtotal", "ES2_time_logtotal", "ES3_time_ratio"]:
            b = base_map.get((exp, n), float("nan"))
            a = r["metrics"][exp]["r2"]
            row += f"{b:>10.4f}{a:>10.4f}"
        print(row)

    print(f"\n输出: {OUT_JSON.name}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
