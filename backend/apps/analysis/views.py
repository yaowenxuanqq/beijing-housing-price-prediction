# -*- coding: utf-8 -*-
import json
from pathlib import Path

import numpy as np
import pandas as pd
from django.conf import settings
from django.db.models import Avg, Count, Max, Min
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.housing.models import House
from ml.predictor import HousingPredictor


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok", "houses": House.objects.count()})


class OverviewView(APIView):
    """概览指标"""

    def get(self, request):
        agg = House.objects.aggregate(
            count=Count("id"),
            avg_unit_price=Avg("unit_price"),
            avg_total_price=Avg("total_price"),
            min_date=Min("trade_date"),
            max_date=Max("trade_date"),
        )
        agg["districts"] = House.objects.values("district_name").distinct().count()
        return Response(agg)


class DistrictStatsView(APIView):
    """各区样本量与均价"""

    def get(self, request):
        rows = (House.objects.values("district_name")
                .annotate(count=Count("id"),
                          avg_unit_price=Avg("unit_price"),
                          avg_total_price=Avg("total_price"))
                .order_by("-avg_unit_price"))
        data = [{
            "district": r["district_name"], "count": r["count"],
            "avg_unit_price": round(r["avg_unit_price"], 0),
            "avg_total_price": round(r["avg_total_price"], 1),
        } for r in rows]
        return Response(data)


_CORR_CACHE = None
_CORR_CACHE_ROWS = None


class YearlyStatsView(APIView):
    """年度成交量与均价"""

    def get(self, request):
        rows = (House.objects.values("trade_date__year")
                .annotate(count=Count("id"),
                          avg_unit_price=Avg("unit_price"),
                          avg_total_price=Avg("total_price"))
                .order_by("trade_date__year"))
        return Response([{
            "year": r["trade_date__year"],
            "count": r["count"],
            "avg_unit_price": round(r["avg_unit_price"], 0),
            "avg_total_price": round(r["avg_total_price"], 1),
        } for r in rows])


class DistributionView(APIView):
    """总价分布直方图 + 面积-总价散点（随机抽样 3000）"""

    def get(self, request):
        rows = list(House.objects.order_by("?").values("total_price", "square", "unit_price")[:3000])
        if not rows:
            return Response({"histogram": {"bins": [], "counts": []}, "scatter": []})
        df = pd.DataFrame(rows)
        counts, bins = np.histogram(df["total_price"].to_numpy(), bins=30)
        return Response({
            "histogram": {
                "bins": [round(float(b), 1) for b in bins],
                "counts": [int(c) for c in counts],
            },
            "scatter": [{
                "square": float(r["square"]),
                "total_price": float(r["total_price"]),
                "unit_price": float(r["unit_price"]),
            } for r in rows],
        })


class CorrelationView(APIView):
    """数值特征相关性（取前 2 万行样本计算）"""

    FIELDS = ["unit_price", "total_price", "square", "rooms", "halls", "bathrooms",
              "total_floors", "house_age", "construction_year", "ladder_ratio",
              "community_average", "lng", "lat"]

    LEAKAGE_FIELDS = ["unit_price", "total_price", "community_average"]

    def get(self, request):
        global _CORR_CACHE, _CORR_CACHE_ROWS
        current_rows = House.objects.count()
        if _CORR_CACHE is None or _CORR_CACHE_ROWS != current_rows:
            # 随机取样：避免按物理顺序取前 N 行导致的时间偏倚
            qs = House.objects.order_by("?").values(*self.FIELDS)[:20000]
            df = pd.DataFrame(list(qs))
            if df.empty:
                return Response({"fields": [], "matrix": [], "sample_size": 0,
                                 "leakage_fields": self.LEAKAGE_FIELDS})
            corr = df.corr(numeric_only=True).round(4).fillna(0)
            _CORR_CACHE = {
                "fields": list(corr.columns),
                "matrix": corr.values.tolist(),
                "sample_size": int(len(df)),
                "leakage_fields": self.LEAKAGE_FIELDS,
            }
            _CORR_CACHE_ROWS = current_rows
        return Response(_CORR_CACHE)


class ImportanceView(APIView):
    """特征重要性（取自部署模型）"""

    def get(self, request):
        p = HousingPredictor.instance()
        model = p.pipe.named_steps["model"]
        if not hasattr(model, "feature_importances_"):
            return Response({"error": "部署模型不提供 feature_importances_"}, status=400)
        names = list(p.feature_names)
        pairs = sorted(zip(names, model.feature_importances_), key=lambda x: -x[1])
        return Response([{"feature": n, "importance": round(float(v), 4)} for n, v in pairs])


class HeatmapView(APIView):
    """房价空间热力图数据（抽样，不绘制行政边界）"""

    def get(self, request):
        limit = int(request.query_params.get("limit", 5000))
        rows = House.objects.raw(
            "SELECT id, lng, lat, unit_price, district_name FROM housing_house "
            "WHERE id %% 50 = 0 LIMIT %s", [limit])
        return Response([{
            "id": r.id, "lng": r.lng, "lat": r.lat,
            "unit_price": round(r.unit_price, 0), "district": r.district_name,
        } for r in rows])


class MetaOptionsView(APIView):
    """预测表单可选项 + 各区当期行情中位单价（2017 年）"""

    def get(self, request):
        districts = list(House.objects.values_list("district_name", flat=True).distinct().order_by("district_name"))
        floor_positions = list(House.objects.exclude(floor_position="")
                               .values_list("floor_position", flat=True).distinct().order_by("floor_position"))

        # 各区最后一年中位单价（作为请求中 market_median_unit_price 的默认值）
        latest_year = House.objects.aggregate(y=Max("trade_date"))["y"]
        latest_year = latest_year.year if latest_year else None
        market = {}
        if latest_year:
            qs = House.objects.filter(trade_date__year=latest_year).values_list("district_name", "unit_price")
            df = pd.DataFrame(list(qs), columns=["district_name", "unit_price"])
            if not df.empty:
                market = {k: round(float(v), 0) for k, v in
                          df.groupby("district_name").unit_price.median().items()}

        return Response({
            "districts": districts,
            "floor_positions": floor_positions,
            "renovation": [1, 2, 3, 4],
            "building_type": [1, 2, 3, 4],
            "building_structure": [1, 2, 3, 4, 5, 6, 7],
            "latest_year": latest_year,
            "market_median_unit_price": market,
        })


class ModelMetricsView(APIView):
    """模型对比与调参结果（读取实验产物）"""

    def get(self, request):
        out = {}
        for name, fname in [("baseline", "metrics_v1.json"),
                            ("tuned", "metrics_tuned_v1.json"),
                            ("stability", "stability_v1.json")]:
            p = Path(settings.DATA_DIR) / fname
            out[name] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        return Response(out)
