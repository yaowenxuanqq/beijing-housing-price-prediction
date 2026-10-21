# -*- coding: utf-8 -*-
"""
03_train.py —— 四格评估实验（ES-1 / ES-2 / ES-3 / ES-4）

对应项目计划书 6.7.1：
  ES-1  随机划分 8:2   + log1p(总价)    -> 同分布预测能力
  ES-2  时序划分       + log1p(总价)    -> 时间外推局限（如实报差）
  ES-3  时序划分       + 相对价格 ratio -> 相对估值能力（并还原为绝对价格评估）
  ES-4  随机划分       + 相对价格 ratio -> 2×2 因素拆解的第四格（乐观上界，仅作对照）

模型：线性回归 / 决策树 / 随机森林 / XGBoost / MLPRegressor（基线参数）
另含朴素基线：面积 × 该区训练集中位单价

输出：
  data/feature_columns_v1.json   冻结特征列清单
  data/metrics_v1.json           全部实验结果与指标
  data/models/*.joblib           全部模型（完整 Pipeline，非裸模型）

防泄漏要点：
  1. 全部预处理（含同小区中位数填充）封装在 Pipeline 内，只在训练集 fit
  2. 填充用的同小区中位数、区中位单价等统计量一律取自训练集
  3. community_average / DOM / followers / unit_price 与 total_price 交叉使用均被排除

用法：.venv/Scripts/python.exe scripts/03_train.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor

# ============================================================
# 路径与常量
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ml.metrics import reg_metrics  # noqa: E402
from ml.preprocessing import (  # noqa: E402
    CAT_COLS, EXCLUDED, GROUP_IMPUTE_COLS, GROUP_KEY, NUM_COLS,
    HousingPreprocessor, prepare,
)

DATA = ROOT / "data" / "clean.parquet"
MODEL_DIR = ROOT / "data" / "models"
FEATURE_JSON = ROOT / "data" / "feature_columns_v1.json"
METRICS_JSON = ROOT / "data" / "metrics_v1.json"

CUT_DATE = pd.Timestamp("2016-07-01")      # ES-2 / ES-3 时序切点
SEED = 42


# 目标字段（特征定义见 backend/ml/preprocessing.py，训练与推理共用）
TARGET_TOTAL = "total_price"
TARGET_UNIT = "unit_price"


# ============================================================
# 模型集合（基线参数）
# ============================================================
def build_models() -> dict:
    return {
        "linear": (LinearRegression(), "linear"),
        "tree": (DecisionTreeRegressor(random_state=SEED, max_depth=12), "tree"),
        "rf": (RandomForestRegressor(n_estimators=100, max_depth=25, min_samples_leaf=10,
                                 max_features=0.5, random_state=SEED, n_jobs=-1), "tree"),
        "xgboost": (XGBRegressor(n_estimators=300, learning_rate=0.1, max_depth=6,
                                 tree_method="hist", n_jobs=-1, random_state=SEED), "tree"),
        "mlp": (MLPRegressor(hidden_layer_sizes=(128,), max_iter=60, early_stopping=True,
                             random_state=SEED), "linear"),
    }


# ============================================================
# 实验
# ============================================================
def run_experiment(name: str, df: pd.DataFrame, split: str, target: str) -> dict:
    print(f"\n{'=' * 66}\n实验 {name}  |  划分={split}  目标={target}\n{'=' * 66}")

    if split == "random":
        rng = np.random.default_rng(SEED)
        idx = rng.permutation(len(df))
        n_tr = int(len(df) * 0.8)
        tr, te = df.iloc[idx[:n_tr]], df.iloc[idx[n_tr:]]
    else:
        tr, te = df[df["trade_date"] < CUT_DATE], df[df["trade_date"] >= CUT_DATE]

    print(f"训练 {len(tr):,} 行 / 测试 {len(te):,} 行")

    # 目标构造
    if target == "log_total":
        y_tr_raw, y_te_raw = tr[TARGET_TOTAL].to_numpy(), te[TARGET_TOTAL].to_numpy()
        y_tr, y_te = np.log1p(y_tr_raw), np.log1p(y_te_raw)
        invert = np.expm1
    else:  # ratio：单价 / 当期该区中位单价（各自用本集合的行情，模拟推理时可得信息）
        def ratio_frame(d):
            base = d.groupby([d["trade_date"].dt.year, "district_name"])[TARGET_UNIT].transform("median")
            return (d[TARGET_UNIT] / base).to_numpy(), base.to_numpy()
        y_tr, base_tr = ratio_frame(tr)
        y_te, base_te = ratio_frame(te)
        invert = None

    results = {"experiment": name, "split": split, "target": target,
               "n_train": int(len(tr)), "n_test": int(len(te)), "models": {}}

    X_tr, X_te = tr, te

    # ---- 朴素基线 ----
    t0 = time.time()
    if target == "log_total":
        dist_med = tr.groupby("district_name")[TARGET_UNIT].median()
        base_pred_unit = te["district_name"].map(dist_med).to_numpy()
        pred_total = te["square"].to_numpy() * base_pred_unit / 10000.0
        m = reg_metrics(y_te_raw, pred_total, 10.0)
        m["mae_unit_price"] = float(mean_absolute_error(
            te[TARGET_UNIT].to_numpy(), base_pred_unit))
        m["r2_unit"] = float(r2_score(te[TARGET_UNIT].to_numpy(), base_pred_unit))
        m["note"] = "朴素基线：面积 × 该区训练集中位单价"
    else:
        # ratio=1 即预测行情中位价
        pred_unit = base_te
        m = reg_metrics(te[TARGET_UNIT].to_numpy(), pred_unit, 10000.0)
        m["r2_ratio"] = 0.0
        m["r2_unit"] = m["r2"]
        m["note"] = "朴素基线：直接预测该区当期行情中位单价（ratio=1）"
    m["seconds"] = round(time.time() - t0, 1)
    results["models"]["baseline"] = m
    print(f"  [baseline] R2={m['r2']:.4f}  MAE={m['mae']:.3f}  {m['seconds']}s")

    # ---- 五个模型 ----
    for mname, (model, kind) in build_models().items():
        t0 = time.time()
        pipe = Pipeline([("prep", HousingPreprocessor(model_kind=kind)), ("model", model)])
        pipe.fit(X_tr, y_tr)
        pred = pipe.predict(X_te)

        if target == "log_total":
            unit_pred = invert(pred)                       # 总价（万元）
            m = reg_metrics(y_te_raw, unit_pred, 10.0)     # MAPE 用 y>=10 万元
            unit_price_pred = unit_pred * 10000.0 / te["square"].to_numpy()
            m["mae_unit_price"] = float(mean_absolute_error(te[TARGET_UNIT].to_numpy(), unit_price_pred))
            # 同口径 R²：三个实验统一到「单价（元/㎡）」量纲，方可横向比较
            m["r2_unit"] = float(r2_score(te[TARGET_UNIT].to_numpy(), unit_price_pred))
        else:
            unit_price_pred = pred * base_te               # 还原为绝对单价（元/㎡）
            m = reg_metrics(te[TARGET_UNIT].to_numpy(), unit_price_pred, 10000.0)
            m["r2_ratio"] = float(r2_score(y_te, pred))
            m["rmse_ratio"] = float(np.sqrt(mean_squared_error(y_te, pred)))
            m["r2_unit"] = m["r2"]      # ratio 分支的 m["r2"] 本就是还原后的单价口径
        m["seconds"] = round(time.time() - t0, 1)
        results["models"][mname] = m
        extra = f"  MAE_unit={m['mae_unit_price']:.0f}" if "mae_unit_price" in m else ""
        print(f"  [{mname:<8}] R2={m['r2']:.4f}  MAE={m['mae']:.3f}  MAPE={m['mape_pct']:.2f}%{extra}  {m['seconds']}s")

        # compress=3：压缩后模型体积可缩小数倍，便于 Django 加载
        joblib.dump(pipe, MODEL_DIR / f"{name}_{mname}.joblib", compress=3)

    # 最优模型
    best = max((k for k in results["models"] if k != "baseline"),
               key=lambda k: results["models"][k]["r2"])
    results["best_model"] = best
    print(f"  -> 最优: {best}")
    return results


def main() -> int:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 66)
    print("03_train.py —— 三层评估实验（基线参数）")
    print("=" * 66)

    df = prepare(pd.read_parquet(DATA))
    print(f"数据: {len(df):,} 行；特征 {len(NUM_COLS)} 数值 + {len(CAT_COLS)} 类别")

    FEATURE_JSON.write_text(json.dumps({
        "version": "v1",
        "group_key": GROUP_KEY,
        "group_impute_cols": GROUP_IMPUTE_COLS,
        "numeric": NUM_COLS,
        "categorical": CAT_COLS,
        "excluded": EXCLUDED,
        "target_total_price": TARGET_TOTAL,
        "target_unit_price": TARGET_UNIT,
        "note": "特征顺序即训练顺序；推理端必须按此清单组装，序列化对象为完整 Pipeline。",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    all_results = []
    all_results.append(run_experiment("ES1_random_logtotal", df, "random", "log_total"))
    all_results.append(run_experiment("ES2_time_logtotal", df, "time", "log_total"))
    all_results.append(run_experiment("ES3_time_ratio", df, "time", "ratio"))
    all_results.append(run_experiment("ES4_random_ratio", df, "random", "ratio"))

    METRICS_JSON.write_text(json.dumps({
        "version": "v1",
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cut_date": str(CUT_DATE.date()),
        "seed": SEED,
        "models_params": "基线参数（未调参），详见项目计划书 6.2 / 6.6",
        "experiments": all_results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 汇总表
    print(f"\n{'=' * 66}\n汇总（R² / MAE）\n{'=' * 66}")
    header = f"{'模型':<10}" + "".join([f"{r['experiment']:<24}" for r in all_results])
    print(header)
    for mname in ["baseline", "linear", "tree", "rf", "xgboost", "mlp"]:
        row = f"{mname:<10}"
        for r in all_results:
            mm = r["models"].get(mname)
            row += f"{mm['r2']:.4f} / {mm['mae']:<12.2f}" if mm else f"{'-':<24}"
        print(row)
    print(f"\n输出: {METRICS_JSON.name} / {FEATURE_JSON.name} / models/*.joblib")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
