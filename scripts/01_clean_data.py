# -*- coding: utf-8 -*-
"""
01_clean_data.py —— 北京二手房数据清洗

依据：docs/项目计划书.md 4.6 清洗阈值（唯一依据）
输出：
  data/clean.csv            清洗后数据集（UTF-8-SIG，Excel 可直接打开）
  data/clean.parquet        清洗后数据集（供建模读取，保留 dtype）
  data/cleaning_report.json 清洗质量报告（各步骤影响行数、缺失率、区域分布）

设计要点（重要）：
  本脚本只做「行级过滤 + 类型规范化 + 非法值置空」。
  任何基于统计量的填充（同小区中位数等）一律不在本脚本执行 —— 那必须放到
  训练阶段的 sklearn Pipeline 里，且只能用训练集 fit，否则会把测试期信息
  带入训练集，构成时序泄漏（见项目计划书 6.7）。

用法：
  .venv/Scripts/python.exe scripts/01_clean_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================
# 路径
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "new.csv"
OUT_CSV = ROOT / "data" / "clean.csv"
OUT_PARQUET = ROOT / "data" / "clean.parquet"
REPORT_JSON = ROOT / "data" / "cleaning_report.json"

# ============================================================
# 配置区（唯一阈值来源，改这里）
# ============================================================
CFG = {
    # 时间范围（4.6）
    "date_start": "2011-01-01",
    "date_end": "2017-12-31",
    # 数值阈值（4.6）
    "square_min": 10.0,
    "square_max": 500.0,          # ㎡
    "total_price_min": 10.0,
    "total_price_max": 5000.0,    # 万元
    "unit_price_min": 3000.0,
    "unit_price_max": 150000.0,   # 元/㎡
    "bathroom_max": 10,
    "house_age_min": 0,
    "house_age_max": 70,
    # 合法类别值域（4.6）
    "building_type_valid": [1, 2, 3, 4],
    "renovation_valid": [1, 2, 3, 4],
    "floor_positions": ["低", "中", "高", "顶", "底"],
}

# 列名规范化：原字段 -> 系统字段（与项目计划书 3.5 的 house 表一致）
RENAME = {
    "Lng": "lng", "Lat": "lat", "Cid": "cid",
    "totalPrice": "total_price", "price": "unit_price",
    "livingRoom": "rooms", "drawingRoom": "halls", "bathRoom": "bathrooms",
    "buildingType": "building_type", "constructionTime": "construction_year_raw",
    "renovationCondition": "renovation", "buildingStructure": "building_structure",
    "ladderRatio": "ladder_ratio", "fiveYearsProperty": "five_years",
    "communityAverage": "community_average",
}


def main() -> int:
    log: dict = {"steps": []}

    print("=" * 66)
    print("01_clean_data.py — 北京二手房数据清洗")
    print("=" * 66)

    # ---------- 1. 读取 ----------
    df = pd.read_csv(RAW_CSV, encoding="gbk", low_memory=False)
    n0 = len(df)
    print(f"[1] 读取原始数据: {n0:,} 行 x {df.shape[1]} 列")
    log["raw_rows"] = int(n0)
    log["raw_cols"] = int(df.shape[1])

    def record(step: str, before: int, after: int, note: str = "") -> None:
        removed = before - after
        log["steps"].append({
            "step": step, "before": int(before), "after": int(after),
            "removed": int(removed), "note": note,
        })
        pct = (removed / before * 100) if before else 0.0
        print(f"    {step}: -{removed:,} 行 ({pct:.2f}%) -> {after:,} 行  {note}")

    # ---------- 2. 时间过滤 ----------
    df["trade_date"] = pd.to_datetime(df["tradeTime"], errors="coerce")
    before = len(df)
    df = df[df["trade_date"].notna()]
    df = df[(df["trade_date"] >= CFG["date_start"]) & (df["trade_date"] <= CFG["date_end"])]
    record("时间过滤 2011-01-01 ~ 2017-12-31", before, len(df))

    # ---------- 2.5 过滤前诊断（用于论文说明规则的防御性） ----------
    _bt = pd.to_numeric(df["buildingType"], errors="coerce")
    _rc = pd.to_numeric(df["renovationCondition"], errors="coerce")
    log["prefilter_diag"] = {
        "rows_after_date_filter": int(len(df)),
        "building_type_invalid": int((_bt.notna() & ~_bt.isin(CFG["building_type_valid"])).sum()),
        "building_type_missing": int(_bt.isna().sum()),
        "renovation_zero": int((_rc == 0).sum()),
    }
    print(f"    [诊断] 时间过滤后: buildingType 非法 {log['prefilter_diag']['building_type_invalid']} 行 / "
          f"缺失 {log['prefilter_diag']['building_type_missing']} 行；renovationCondition=0 共 {log['prefilter_diag']['renovation_zero']} 行")

    # ---------- 3. 数值阈值过滤 ----------
    for col, lo_key, hi_key, label in [
        ("square", "square_min", "square_max", "面积"),
        ("totalPrice", "total_price_min", "total_price_max", "总价"),
        ("price", "unit_price_min", "unit_price_max", "单价"),
    ]:
        before = len(df)
        v = pd.to_numeric(df[col], errors="coerce")
        keep = v.between(CFG[lo_key], CFG[hi_key])
        df = df[keep]
        record(f"{label}阈值过滤 [{CFG[lo_key]}, {CFG[hi_key]}]", before, len(df))

    # ---------- 4. 户室列规范化（非数值行剔除） ----------
    before = len(df)
    for col in ["livingRoom", "drawingRoom", "bathRoom", "kitchen"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["livingRoom", "drawingRoom", "bathRoom"])
    record("户室列非数值行剔除（#NAME? / 串列）", before, len(df))

    before = len(df)
    df = df[df["bathRoom"] <= CFG["bathroom_max"]]
    record(f"卫生间数 <= {CFG['bathroom_max']}", before, len(df))

    # ---------- 5. floor 解析 ----------
    floor_raw = df["floor"].astype("string").str.strip()
    parts = floor_raw.str.split(r"\s+", n=1, expand=True)
    pos = parts[0]
    total_floors = pd.to_numeric(parts[1], errors="coerce")
    valid_pos = pos.isin(CFG["floor_positions"])
    df["floor_position"] = np.where(valid_pos, pos, "未知")
    df["total_floors"] = np.where(valid_pos, total_floors, np.nan)
    n_unknown_floor = int((df["floor_position"] == "未知").sum())
    print(f"    floor 解析: 楼层位置未知 {n_unknown_floor:,} 行（保留，单独成类）")
    log["floor_unknown"] = n_unknown_floor
    log["total_floors_missing"] = int(pd.isna(df["total_floors"]).sum())

    # ---------- 6. 建造年份 / 房龄 ----------
    cy = pd.to_numeric(df["constructionTime"], errors="coerce")   # 「未知」-> NaN
    df["construction_year"] = cy
    year = df["trade_date"].dt.year
    age = year - cy
    age = age.mask(age < CFG["house_age_min"])                    # 负值 -> 缺失
    age = age.clip(upper=CFG["house_age_max"])                    # >70 -> 70
    df["house_age"] = age
    log["construction_year_missing"] = int(cy.isna().sum())
    log["house_age_missing"] = int(age.isna().sum())
    log["house_age_clipped"] = int((year - cy > CFG["house_age_max"]).sum())
    print(f"    建造年份缺失: {log['construction_year_missing']:,} 行 -> house_age 缺失 {log['house_age_missing']:,} 行")

    # ---------- 7. 非法类别值置空 ----------
    bt = pd.to_numeric(df["buildingType"], errors="coerce")
    valid_bt = bt.isin(CFG["building_type_valid"])
    n_bad_bt = int((bt.notna() & ~valid_bt).sum())        # 非空但取值非法（串列污染）
    n_na_bt = int(bt.isna().sum())                        # 本身缺失
    df["buildingType"] = bt.where(valid_bt)

    rc = pd.to_numeric(df["renovationCondition"], errors="coerce")
    valid_rc = rc.isin(CFG["renovation_valid"])
    n_bad_rc = int((rc.notna() & ~valid_rc).sum())
    n_na_rc = int(rc.isna().sum())
    df["renovationCondition"] = rc.where(valid_rc)
    print(f"    buildingType: 非法取值 {n_bad_bt:,} 行置空，另有缺失 {n_na_bt:,} 行")
    print(f"    renovationCondition: 非法取值 {n_bad_rc:,} 行置空，另有缺失 {n_na_rc:,} 行")
    log["building_type_invalid"] = n_bad_bt
    log["building_type_missing"] = n_na_bt
    log["renovation_invalid"] = n_bad_rc
    log["renovation_missing"] = n_na_rc

    # ---------- 8. 删除 DOM（4.6：整列删除） ----------
    if "DOM" in df.columns:
        df = df.drop(columns=["DOM"])
        print("    删除 DOM 列（缺失约 50%，且属成交后信息）")

    # ---------- 9. 列名规范化 + 区名映射 ----------
    df = df.rename(columns=RENAME)
    drop_cols = [c for c in ["construction_year_raw", "floor", "tradeTime", "totalPrice", "price"] if c in df.columns]
    df = df.drop(columns=drop_cols, errors="ignore")

    import sys as _sys
    _sys.path.insert(0, str(ROOT / "scripts"))
    from config.district_mapping import map_district  # noqa: E402
    df["district_name"] = df["district"].apply(map_district)

    # 列顺序
    front = ["id", "url", "trade_date", "district", "district_name",
             "lng", "lat", "square", "rooms", "halls", "kitchen", "bathrooms",
             "floor_position", "total_floors", "construction_year", "house_age",
             "renovation", "building_type", "building_structure", "ladder_ratio",
             "elevator", "subway", "five_years", "community_average", "total_price", "unit_price"]
    rest = [c for c in df.columns if c not in front]
    df = df[front + rest]

    # ---------- 10. 写出 ----------
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    try:
        df.to_parquet(OUT_PARQUET, index=False)
        parquet_ok = True
    except Exception as exc:  # pragma: no cover
        parquet_ok = False
        print(f"    [警告] parquet 写出失败（不影响主流程）: {exc}")

    # ---------- 11. 报告 ----------
    report = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_file": str(RAW_CSV.name),
        "thresholds": CFG,
        "raw_rows": log["raw_rows"],
        "clean_rows": int(len(df)),
        "removed_rows_total": int(log["raw_rows"] - len(df)),
        "removed_ratio": round((log["raw_rows"] - len(df)) / log["raw_rows"] * 100, 2),
        "steps": log["steps"],
        "prefilter_diag": log.get("prefilter_diag", {}),
        "notes": {
            "building_type_rule": "4.6 的非法值置空规则为防御性规则：相关行已在「户室列非数值行剔除」步骤被清除，故实际影响 0 行。",
            "renovation_rule": "同上，renovationCondition=0 的行已被上游规则清除。",
            "imputation": "本脚本不做任何统计量填充；缺失值填充在建模 Pipeline 内用训练集 fit，防止时序泄漏。",
        },
        "columns": list(df.columns),
        "missing": {k: int(v) for k, v in df.isna().sum().items() if v > 0},
        "missing_ratio": {k: round(float(v) / len(df) * 100, 3)
                          for k, v in df.isna().sum().items() if v > 0},
        "district_counts": {str(k): int(v) for k, v in df["district_name"].value_counts().items()},
        "price_stats": {
            "total_price": {k: float(v) for k, v in df["total_price"].describe().items()},
            "unit_price": {k: float(v) for k, v in df["unit_price"].describe().items()},
            "skew_total_price": float(df["total_price"].skew()),
        },
        "parquet_written": bool(parquet_ok),
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"[2] 清洗完成: {len(df):,} 行 x {df.shape[1]} 列")
    print(f"    剔除 {log['raw_rows'] - len(df):,} 行，占 {report['removed_ratio']}%")
    print(f"    输出: {OUT_CSV.name} / {OUT_PARQUET.name} / {REPORT_JSON.name}")
    print("    区域分布:")
    for k, v in df["district_name"].value_counts().items():
        print(f"      {k:<6} {v:>7,}")
    print("    关键字段缺失:")
    for k, v in report["missing"].items():
        print(f"      {k:<20} {v:>7,} ({report['missing_ratio'][k]}%)")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
