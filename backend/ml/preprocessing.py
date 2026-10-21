# -*- coding: utf-8 -*-
"""
特征工程与预处理（训练与推理共用）

放在 backend/ml/ 下的原因：
    sklearn Pipeline 会被 joblib 序列化，序列化对象记录的是类的「模块路径」。
   若把自定义 Transformer 定义在训练脚本里（__main__），Django 加载模型时会
   因为找不到 __main__.HousingPreprocessor 而失败。
   因此统一放在可导入的包 backend/ml/ 下，训练脚本与 Django 推理端共用同一份代码。

导入方式（训练脚本与 Django 均从 backend/ 作为包根导入）：
    from ml.preprocessing import HousingPreprocessor, NUM_COLS, CAT_COLS, GROUP_KEY
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

# ---- 特征定义（对应项目计划书 4.7）----
GROUP_KEY = "cid"
GROUP_IMPUTE_COLS = ["house_age", "total_floors"]      # 用同小区中位数填充
NUM_COLS = ["square", "rooms", "halls", "kitchen", "bathrooms",
            "total_floors", "house_age", "ladder_ratio", "dist_to_center"]
CAT_COLS = ["district_name", "floor_position", "renovation",
            "building_type", "building_structure",
            "elevator", "subway", "five_years"]
EXCLUDED = ["community_average", "lng", "lat", "url", "id", "cid",
            "trade_date", "total_price", "unit_price"]

# 天安门坐标（距市中心距离的基准点）
CENTER_LNG, CENTER_LAT = 116.3975, 39.9087


def haversine_km(lng: pd.Series, lat: pd.Series) -> pd.Series:
    """房源到市中心（天安门）的球面距离，单位 km"""
    r = 6371.0
    p1, p2 = np.radians(lat), np.radians(CENTER_LAT)
    dphi = p2 - p1
    dlambda = np.radians(CENTER_LNG - lng)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlambda / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


class HousingPreprocessor(BaseEstimator, TransformerMixin):
    """数值 + 类别预处理。

    model_kind='tree'   : 类别用序数编码，数值不标准化（树模型不需要）
    model_kind='linear' : 类别用独热编码，数值标准化（线性回归 / MLP 需要）

    防泄漏：所有填充统计量（同小区中位数、全局中位数、众数）与编码器
    均只在 fit 时用训练集计算，transform 阶段直接复用。
    """

    def __init__(self, model_kind: str = "tree"):
        self.model_kind = model_kind

    # ---------- fit ----------
    def fit(self, X: pd.DataFrame, y=None):
        X = X[[GROUP_KEY] + NUM_COLS + CAT_COLS].copy()

        # 1) 同小区中位数（仅训练集）
        self.group_median_ = X.groupby(GROUP_KEY)[GROUP_IMPUTE_COLS].median()
        # 2) 全局中位数（仅训练集）
        self.global_median_ = X[NUM_COLS].median(numeric_only=True)
        # 3) 类别众数（仅训练集）
        self.mode_ = {}
        for c in CAT_COLS:
            m = X[c].mode(dropna=True)
            self.mode_[c] = m.iloc[0] if len(m) else "未知"

        filled = self._fill(X)

        if self.model_kind == "linear":
            self.encoder_ = OneHotEncoder(handle_unknown="ignore", sparse_output=False,
                                          min_frequency=50)
            self.encoder_.fit(filled[CAT_COLS])
            self.scaler_ = StandardScaler().fit(filled[NUM_COLS])
        else:
            self.encoder_ = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
            self.encoder_.fit(filled[CAT_COLS])
        return self

    # ---------- 内部填充（统计量全部来自训练集）----------
    def _fill(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        for c in GROUP_IMPUTE_COLS:
            mapped = X[GROUP_KEY].map(self.group_median_[c])
            X[c] = X[c].fillna(mapped)
        for c in NUM_COLS:
            X[c] = X[c].fillna(self.global_median_.get(c, np.nan))
        for c in CAT_COLS:
            X[c] = X[c].fillna(self.mode_[c])
        return X

    # ---------- transform ----------
    def transform(self, X: pd.DataFrame) -> np.ndarray:
        filled = self._fill(X[[GROUP_KEY] + NUM_COLS + CAT_COLS].copy())
        enc = self.encoder_.transform(filled[CAT_COLS])
        if self.model_kind == "linear":
            num = self.scaler_.transform(filled[NUM_COLS])
        else:
            num = filled[NUM_COLS].to_numpy(dtype=float)
        return np.hstack([num, enc])

    def get_feature_names_out(self, input_features=None):
        cats = (list(self.encoder_.get_feature_names_out(CAT_COLS))
                if self.model_kind == "linear" else list(CAT_COLS))
        return np.array(list(NUM_COLS) + cats, dtype=object)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """在 clean.parquet 基础上补充派生特征（训练与推理共用）。"""
    out = df.copy()
    out["dist_to_center"] = haversine_km(out["lng"], out["lat"])
    for c in ["district_name", "floor_position", "renovation",
              "building_type", "building_structure"]:
        out[c] = out[c].astype("object")
    return out
