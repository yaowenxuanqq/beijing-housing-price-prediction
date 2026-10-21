# -*- coding: utf-8 -*-
"""
02_eda.py —— 探索性数据分析（EDA）

输入：data/clean.parquet（由 01_clean_data.py 产出）
输出：docs/figures/*.png + docs/figures/eda_summary.md

图表清单（对应项目计划书 5.2 可视化分析模块）：
  fig01 房价分布（原始 vs log1p）
  fig02 各区均价对比（含样本量；低频区标注）
  fig03 面积-总价关系散点
  fig04 数值特征相关性热力图
  fig05 房价空间热力图（经纬度 + 单价，不绘制行政边界）
  fig06 年度价格与成交量趋势
  fig07 类别特征对单价的影响（电梯/地铁/满五/楼层位置）
  fig08 房龄与单价关系

用法：.venv/Scripts/python.exe scripts/02_eda.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# ---------------- 路径与样式 ----------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "clean.parquet"
FIG_DIR = ROOT / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130
plt.rcParams["savefig.bbox"] = "tight"
sns.set_theme(style="whitegrid", font=plt.rcParams["font.sans-serif"][0])

LOW_FREQ = {"房山区", "亦庄", "门头沟区"}   # 样本量 < 3000
RNG = np.random.default_rng(42)


def save(fig, name: str) -> None:
    path = FIG_DIR / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  [fig] {name}")


def main() -> int:
    df = pd.read_parquet(DATA)
    print("=" * 66)
    print("02_eda.py —— 探索性数据分析")
    print("=" * 66)
    print(f"数据: {len(df):,} 行 x {df.shape[1]} 列")

    summary: list[str] = []
    summary.append("# 探索性数据分析（EDA）结果摘要\n")
    summary.append(f"- 数据规模：{len(df):,} 行 × {df.shape[1]} 列（clean.parquet）")
    summary.append(f"- 时间范围：{df['trade_date'].min():%Y-%m-%d} ~ {df['trade_date'].max():%Y-%m-%d}\n")

    # ---------- fig01 房价分布 ----------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(df["total_price"], bins=80, color="#4C72B0")
    axes[0].set_title("总价分布（原始，万元）")
    axes[0].set_xlabel("总价（万元）"); axes[0].set_ylabel("样本数")
    axes[1].hist(np.log1p(df["total_price"]), bins=80, color="#DD8452")
    axes[1].set_title("总价分布（log1p 变换后）")
    axes[1].set_xlabel("log1p(总价)")
    save(fig, "fig01_price_distribution.png")

    tp = df["total_price"]
    summary.append("## 1. 价格分布\n")
    summary.append(f"- 总价：中位数 {tp.median():.0f} 万，均值 {tp.mean():.1f} 万，p99 {tp.quantile(0.99):.0f} 万，最大 {tp.max():.0f} 万")
    summary.append(f"- 总价偏度 {tp.skew():.2f} → 右偏严重，**建模需做 log1p 变换**")
    up = df["unit_price"]
    summary.append(f"- 单价：中位数 {up.median():.0f} 元/㎡，均值 {up.mean():.0f} 元/㎡\n")

    # ---------- fig02 各区均价 ----------
    g = (df.groupby("district_name")
           .agg(n=("unit_price", "size"), avg=("unit_price", "mean"))
           .sort_values("avg", ascending=False))
    colors = ["#C44E52" if i in LOW_FREQ else "#4C72B0" for i in g.index]
    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(g.index, g["avg"], color=colors)
    for b, (name, row) in zip(bars, g.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 800,
                f"{row['avg']:.0f}\n(n={row['n']:,})", ha="center", va="bottom", fontsize=8)
    ax.set_title("各区二手房均价（红色 = 样本量 < 3000，结果可靠性较低）")
    ax.set_ylabel("均价（元/㎡）"); ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=30)
    ax.set_ylim(0, g["avg"].max() * 1.18)
    save(fig, "fig02_unit_price_by_district.png")

    summary.append("## 2. 区域差异\n")
    summary.append("| 区域 | 样本量 | 均价（元/㎡） |")
    summary.append("|---|---|---|")
    for name, row in g.iterrows():
        flag = " ⚠️" if name in LOW_FREQ else ""
        summary.append(f"| {name}{flag} | {row['n']:,.0f} | {row['avg']:,.0f} |")
    summary.append("")
    summary.append(f"- 最高：{g.index[0]} {g['avg'].iloc[0]:,.0f} 元/㎡；最低：{g.index[-1]} {g['avg'].iloc[-1]:,.0f} 元/㎡")
    ratio = g["avg"].iloc[0] / g["avg"].iloc[-1]
    summary.append(f"- 最高/最低比 ≈ {ratio:.2f} 倍\n")

    # ---------- fig03 面积-总价 ----------
    s = df.sample(n=min(20000, len(df)), random_state=42)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    sc = ax.scatter(s["square"], s["total_price"], c=s["unit_price"], s=5, alpha=0.45, cmap="viridis")
    ax.set_xlabel("建筑面积（㎡）"); ax.set_ylabel("总价（万元）")
    ax.set_title("面积与总价关系（抽样 2 万条，颜色 = 单价）")
    plt.colorbar(sc, label="单价（元/㎡）")
    ax.set_xlim(0, 300); ax.set_ylim(0, 2000)
    save(fig, "fig03_area_vs_price.png")

    corr_area = df["square"].corr(df["total_price"])
    summary.append("## 3. 面积与总价\n")
    summary.append(f"- 面积与总价相关系数 r = {corr_area:.3f} → 面积是总价的强预测因素")
    summary.append(f"- 面积与单价相关系数 r = {df['square'].corr(df['unit_price']):.3f} → 面积对单价影响较弱\n")

    # ---------- fig04 相关性热力图 ----------
    num_cols = ["total_price", "unit_price", "square", "rooms", "halls", "kitchen",
                "bathrooms", "total_floors", "house_age", "construction_year",
                "ladder_ratio", "community_average", "lng", "lat"]
    num_cols = [c for c in num_cols if c in df.columns]
    corr = df[num_cols].corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                square=True, linewidths=0.5, annot_kws={"size": 7}, ax=ax)
    ax.set_title("数值特征相关性热力图")
    save(fig, "fig04_correlation_heatmap.png")

    summary.append("## 4. 相关性\n")
    top = corr["total_price"].drop("total_price").sort_values(key=abs, ascending=False).head(6)
    summary.append("与总价相关性最强的字段：\n")
    for k, v in top.items():
        summary.append(f"- {k}: r = {v:.3f}")
    summary.append("")

    # ---------- fig05 空间热力图 ----------
    s2 = df.sample(n=min(60000, len(df)), random_state=1)
    fig, ax = plt.subplots(figsize=(8.5, 7))
    sc = ax.scatter(s2["lng"], s2["lat"], c=s2["unit_price"], s=3, alpha=0.5,
                    cmap="jet", vmin=df["unit_price"].quantile(0.02), vmax=df["unit_price"].quantile(0.98))
    ax.set_xlabel("经度"); ax.set_ylabel("纬度")
    ax.set_title("北京二手房单价空间分布（抽样 6 万条；不绘制行政边界）")
    plt.colorbar(sc, label="单价（元/㎡）")
    ax.set_aspect("equal", adjustable="datalim")
    save(fig, "fig05_price_heatmap.png")

    # ---------- fig06 年度趋势 ----------
    yr = df.assign(year=df["trade_date"].dt.year).groupby("year").agg(
        n=("unit_price", "size"), avg=("unit_price", "mean"))
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(yr.index, yr["n"], color="#CCCCCC", label="成交量")
    ax1.set_xlabel("年份"); ax1.set_ylabel("成交记录数")
    ax2 = ax1.twinx()
    ax2.plot(yr.index, yr["avg"], "o-", color="#C44E52", linewidth=2, label="均价")
    ax2.set_ylabel("均价（元/㎡）")
    ax1.set_title("年度成交量与均价趋势")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    save(fig, "fig06_yearly_trend.png")

    summary.append("## 5. 时间趋势\n")
    summary.append("| 年份 | 成交量 | 均价（元/㎡） |")
    summary.append("|---|---|---|")
    for y, row in yr.iterrows():
        summary.append(f"| {y} | {row['n']:,.0f} | {row['avg']:,.0f} |")
    summary.append("")

    # ---------- fig07 类别特征影响 ----------
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, col, title in zip(
        axes.ravel(),
        ["elevator", "subway", "five_years", "floor_position"],
        ["电梯", "近地铁", "满五年", "楼层位置"],
    ):
        if col not in df.columns:
            continue
        gg = df.groupby(col)["unit_price"].mean().sort_values()
        ax.bar([str(i) for i in gg.index], gg.values, color="#55A868")
        ax.set_title(f"{title} 对均价的影响")
        ax.set_ylabel("均价（元/㎡）")
        for i, v in enumerate(gg.values):
            ax.text(i, v + 500, f"{v:.0f}", ha="center", fontsize=8)
    fig.tight_layout()
    save(fig, "fig07_category_effects.png")

    summary.append("## 6. 类别特征效应\n")
    for col, name in [("elevator", "电梯"), ("subway", "近地铁"), ("five_years", "满五年")]:
        if col in df.columns:
            gg = df.groupby(col)["unit_price"].mean()
            if len(gg) >= 2:
                summary.append(f"- {name}：{gg.max():,.0f} vs {gg.min():,.0f} 元/㎡，差值 {gg.max()-gg.min():,.0f}")
    if "floor_position" in df.columns:
        gg = df.groupby("floor_position")["unit_price"].agg(["mean", "size"]).sort_values("mean", ascending=False)
        summary.append(f"- 楼层位置：最高 {gg.index[0]}（{gg['mean'].iloc[0]:,.0f}，n={gg['size'].iloc[0]:,.0f}），"
                       f"最低 {gg.index[-1]}（{gg['mean'].iloc[-1]:,.0f}，n={gg['size'].iloc[-1]:,.0f}）")
        summary.append("> ⚠️ 楼层位置的均价差异同样受**区位与楼栋类型混淆**影响（如「底」层样本多分布于老小区），不可直接作因果解读。")
    summary.append("")

    # ---------- fig08 房龄与单价 ----------
    d2 = df.dropna(subset=["house_age"]).copy()
    d2["age_bin"] = pd.cut(d2["house_age"], bins=[-1, 5, 10, 15, 20, 30, 70],
                           labels=["0-5", "6-10", "11-15", "16-20", "21-30", "31+"])
    ab = d2.groupby("age_bin", observed=True).agg(avg=("unit_price", "mean"), n=("unit_price", "size"))
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.bar(ab.index.astype(str), ab["avg"], color="#8172B3")
    for i, (idx, row) in enumerate(ab.iterrows()):
        ax.text(i, row["avg"] + 400, f"{row['avg']:.0f}\n(n={row['n']:,.0f})", ha="center", fontsize=8)
    ax.set_title("房龄与均价关系")
    ax.set_xlabel("房龄（年）"); ax.set_ylabel("均价（元/㎡）")
    ax.set_ylim(0, ab["avg"].max() * 1.2)
    save(fig, "fig08_house_age_effect.png")

    summary.append("## 7. 房龄效应\n")
    for idx, row in ab.iterrows():
        summary.append(f"- {idx} 年：{row['avg']:,.0f} 元/㎡（n={row['n']:,.0f}）")
    summary.append("")
    summary.append("> ⚠️ **因果解读警告**：上表显示房龄越大单价越高，这是**区位混淆**的结果，不是「老房更值钱」。")
    summary.append("> 北京老房集中在西城、东城、海淀等核心区，新房多在远郊，房龄与区位高度混杂。")
    summary.append("> 此表仅反映边际相关性，**不可解读为因果关系**。")
    summary.append("")
    age_by_dist = d2.groupby("district_name").house_age.median().sort_values()
    summary.append(f"- 佐证：房龄中位数最低的区域为 {age_by_dist.index[0]}（{age_by_dist.iloc[0]:.0f} 年），最高为 {age_by_dist.index[-1]}（{age_by_dist.iloc[-1]:.0f} 年）")
    summary.append("")

    # ---------- 数据质量提示 ----------
    summary.append("## 8. 建模前须注意的数据问题\n")
    for col in ["house_age", "total_floors", "construction_year", "building_type", "community_average"]:
        if col in df.columns:
            r = df[col].isna().mean() * 100
            if r > 0:
                summary.append(f"- {col} 缺失 {r:.2f}%（须在训练 Pipeline 内用**训练集**统计量填充）")
    summary.append("- 单价与总价存在数学换算关系，建模时二者互斥使用（见计划书 4.5）")
    summary.append("- community_average 与目标高度相关，建模一律排除\n")

    (FIG_DIR / "eda_summary.md").write_text("\n".join(summary), encoding="utf-8")
    print()
    print(f"完成：8 张图表 + eda_summary.md -> {FIG_DIR}")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
