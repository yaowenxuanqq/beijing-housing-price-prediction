# -*- coding: utf-8 -*-
"""在线推理：加载调参后的完整 Pipeline，输出 ratio → 单价 → 总价。"""

from __future__ import annotations

import hashlib
import threading
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .preprocessing import prepare

# 训练集 ratio 的近似边界（p0.05%~p99.95%），防止外推爆炸
RATIO_MIN, RATIO_MAX = 0.05, 9.0

# 各区中心坐标（用于请求未提供经纬度时估算距市中心距离）
DISTRICT_CENTROIDS = {
    "东城区": (116.4321, 39.9230),
    "西城区": (116.3628, 39.9055),
    "朝阳区": (116.4772, 39.9391),
    "海淀区": (116.3329, 39.9806),
    "丰台区": (116.3708, 39.8581),
    "石景山区": (116.2104, 39.9152),
    "通州区": (116.6648, 39.9006),
    "昌平区": (116.3633, 40.0827),
    "大兴区": (116.3447, 39.7724),
    "亦庄": (116.5004, 39.8041),
    "顺义区": (116.6547, 40.1245),
    "房山区": (116.1728, 39.7639),
    "门头沟区": (116.1197, 39.9374),
}

DEFAULTS = {
    "cid": -1,
    "rooms": 2, "halls": 1, "kitchen": 1, "bathrooms": 1,
    "total_floors": 6.0, "house_age": 20.0, "ladder_ratio": 2.0,
    "floor_position": "中", "renovation": 3,
    "building_type": 1, "building_structure": 2,
    "elevator": 0, "subway": 0, "five_years": 0,
}

FEATURE_LABELS = {
    "square": "建筑面积",
    "rooms": "卧室数",
    "halls": "客厅数",
    "kitchen": "厨房数",
    "bathrooms": "卫生间数",
    "total_floors": "总楼层",
    "house_age": "房龄",
    "ladder_ratio": "梯户比",
    "dist_to_center": "距市中心距离",
    "district_name": "所属区域",
    "floor_position": "楼层位置",
    "renovation": "装修等级",
    "building_type": "建筑类型",
    "building_structure": "建筑结构",
    "elevator": "电梯",
    "subway": "近地铁",
    "five_years": "满五年",
}


class HousingPredictor:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                from django.conf import settings
                cls._instance = cls(settings.MODEL_PATH, settings.MODEL_VERSION)
            return cls._instance

    def __init__(self, model_path: str, version: str):
        self.model_path = str(model_path)
        self.pipe = joblib.load(self.model_path)
        self.version = getattr(self.pipe, "model_version_", version)
        self.feature_names = list(self.pipe.named_steps["prep"].get_feature_names_out())
        self.loaded_at = datetime.now().isoformat(timespec="seconds")
        self._explainer = None
        self._explainer_lock = threading.Lock()
        self._metadata = None

    def _prepare_input(self, payload: dict):
        """构造与线上预测完全一致的单行特征矩阵。"""
        district = payload["district_name"]
        # 双保险：即使绕过 serializer 直接调用，也拒绝未知区域
        # （OrdinalEncoder 的 unknown_value=-1 会与"东城区=0"落在同一分支，导致静默误判）
        if district not in DISTRICT_CENTROIDS:
            raise ValueError(f"未知区域：{district}")
        lng = payload.get("lng")
        lat = payload.get("lat")
        if lng is None or lat is None:
            lng, lat = DISTRICT_CENTROIDS[district]

        row = {**DEFAULTS}
        for k in ["cid", "rooms", "halls", "kitchen", "bathrooms", "total_floors",
                  "house_age", "ladder_ratio", "floor_position", "renovation",
                  "building_type", "building_structure"]:
            if payload.get(k) is not None:
                row[k] = payload[k]
        for k in ["elevator", "subway", "five_years"]:
            row[k] = int(bool(payload.get(k, False)))

        row.update({
            "square": float(payload["square"]),
            "district_name": district,
            "lng": float(lng),
            "lat": float(lat),
        })

        X = prepare(pd.DataFrame([row]))
        prep = self.pipe.named_steps["prep"]
        model = self.pipe.named_steps["model"]
        Xt = prep.transform(X)
        raw_ratio = float(model.predict(Xt)[0])
        ratio = float(np.clip(raw_ratio, RATIO_MIN, RATIO_MAX))
        return row, X, Xt, raw_ratio, ratio

    def _result(self, row: dict, raw_ratio: float, ratio: float, market: float) -> dict:
        """把 ratio 统一换算成接口展示的价格与区间。"""
        # 优先使用训练期时序折外残差分位；旧模型回退到树间离散度。
        calibration = getattr(self.pipe, "interval_calibration_", None)
        if calibration and "q_low" in calibration and "q_high" in calibration:
            lo_r = raw_ratio + float(calibration["q_low"])
            hi_r = raw_ratio + float(calibration["q_high"])
            interval_level = float(calibration.get("level", 0.8))
            interval_method = str(calibration.get("method", "residual_quantile"))
            interval_note = str(calibration.get(
                "note", "训练期折外残差经验校准区间，不是严格置信区间。"))
        else:
            model = self.pipe.named_steps["model"]
            if hasattr(model, "estimators_"):
                Xt = self._prepare_input({**row, "market_median_unit_price": market})[2]
                tree_preds = np.array([float(t.predict(Xt)[0]) for t in model.estimators_])
                lo_r = float(np.percentile(tree_preds, 10))
                hi_r = float(np.percentile(tree_preds, 90))
                interval_level = 0.8
                interval_method = "tree_spread"
                interval_note = "随机森林树间离散度区间，未经残差覆盖率校准。"
            else:
                lo_r, hi_r = ratio * 0.95, ratio * 1.05
                interval_level = 0.8
                interval_method = "heuristic_spread"
                interval_note = "启发式区间，未经残差覆盖率校准。"
        lo_r = float(np.clip(lo_r, RATIO_MIN, RATIO_MAX))
        hi_r = float(np.clip(hi_r, RATIO_MIN, RATIO_MAX))
        lo_r, hi_r = min(lo_r, ratio), max(hi_r, ratio)

        unit_price = round(ratio * market, 0)
        total_price = unit_price * row["square"] / 10000.0
        unit_low = round(lo_r * market, 0)
        unit_high = round(hi_r * market, 0)
        total_low = round(unit_low * row["square"] / 10000.0, 1)
        total_high = round(unit_high * row["square"] / 10000.0, 1)

        return {
            "ratio": round(unit_price / market, 6),
            "predicted_unit_price": unit_price,
            "predicted_total_price": round(total_price, 1),
            "interval_low": unit_low,
            "interval_high": unit_high,
            "interval_total_low": total_low,
            "interval_total_high": total_high,
            "interval_level": interval_level,
            "interval_method": interval_method,
            "interval_note": interval_note,
            "market_median_unit_price": round(market, 0),
            "model_version": self.version,
            "currency": "CNY",
            "unit": "万元",
            "note": "相对行情估值；绝对价格依赖输入的当期该区中位单价",
        }

    def predict(self, payload: dict) -> dict:
        row, _X, _Xt, raw_ratio, ratio = self._prepare_input(payload)
        market = float(payload["market_median_unit_price"])
        return self._result(row, raw_ratio, ratio, market)

    def explain(self, payload: dict, top_n: int = 8) -> dict:
        """使用 TreeSHAP 解释随机森林对当前输入的局部特征贡献。"""
        row, X, Xt, raw_ratio, ratio = self._prepare_input(payload)
        market = float(payload["market_median_unit_price"])
        result = self._result(row, raw_ratio, ratio, market)

        with self._explainer_lock:
            if self._explainer is None:
                import shap
                self._explainer = shap.TreeExplainer(self.pipe.named_steps["model"])
            explainer = self._explainer

        values = explainer.shap_values(Xt)
        if isinstance(values, list):
            values = values[0]
        values = np.asarray(values, dtype=float).reshape(-1)
        expected = np.asarray(explainer.expected_value, dtype=float).reshape(-1)[0]

        prepared = X.iloc[0].to_dict()
        features = []
        for name, contribution in zip(self.feature_names, values):
            features.append({
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "value": _json_scalar(prepared.get(name)),
                "contribution_ratio": round(float(contribution), 6),
                "contribution_unit_price": round(float(contribution) * market, 0),
            })
        features.sort(key=lambda item: abs(item["contribution_ratio"]), reverse=True)
        top = features[:max(1, min(int(top_n), len(features)))]
        clip_delta = ratio - raw_ratio
        return {
            "prediction": result,
            "explanation": {
                "method": "TreeSHAP",
                "method_note": "基于随机森林 TreeSHAP 的局部特征贡献，反映模型关联，不是因果推断。",
                "base_ratio": round(float(expected), 6),
                "raw_ratio": round(raw_ratio, 6),
                "predicted_ratio": round(ratio, 6),
                "base_unit_price": round(float(expected) * market, 0),
                "clip_adjustment_ratio": round(float(clip_delta), 6),
                "clip_adjustment_unit_price": round(float(clip_delta) * market, 0),
                "features": top,
                "top_positive": [x for x in top if x["contribution_ratio"] > 0][:4],
                "top_negative": [x for x in top if x["contribution_ratio"] < 0][:4],
            },
        }

    def metadata(self) -> dict:
        """返回模型文件、模型版本与校准信息，供健康检查和模型页使用。"""
        if self._metadata is None:
            path = Path(self.model_path)
            sha256 = None
            size = None
            if path.exists():
                size = path.stat().st_size
                digest = hashlib.sha256()
                with path.open("rb") as fh:
                    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                        digest.update(chunk)
                sha256 = digest.hexdigest()
            model = self.pipe.named_steps["model"]
            self._metadata = {
                "model_version": self.version,
                "model_file": path.name,
                "model_size_bytes": size,
                "model_sha256": sha256,
                "loaded_at": self.loaded_at,
                "model_class": type(model).__name__,
                "feature_count": len(self.feature_names),
                "n_estimators": getattr(model, "n_estimators", None),
                "interval_calibration": getattr(self.pipe, "interval_calibration_", None),
            }
        return dict(self._metadata)


def _json_scalar(value):
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
