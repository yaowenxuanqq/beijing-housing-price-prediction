# -*- coding: utf-8 -*-
from datetime import timedelta

from django.db.models import Q, Max
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import House
from .serializers import HouseSerializer, SimilarHouseQuerySerializer


class HouseListView(generics.ListAPIView):
    """房源列表：分页 + 区域/面积/价格/楼层筛选"""

    serializer_class = HouseSerializer

    @staticmethod
    def _num(params, key):
        """解析数值参数；非法值直接 400，避免静默忽略或 500"""
        if key not in params:
            return None
        try:
            return float(params[key])
        except (TypeError, ValueError):
            raise ValidationError({key: "必须为数字"})

    @staticmethod
    def _bool01(params, key):
        if key not in params:
            return None
        if params[key] not in ("0", "1"):
            raise ValidationError({key: "只能为 0 或 1"})
        return int(params[key])

    def get_queryset(self):
        qs = House.objects.all().order_by("-trade_date", "-id")
        p = self.request.query_params
        if p.get("district"):
            qs = qs.filter(district_name=p["district"])

        v = self._num(p, "min_price")
        if v is not None:
            qs = qs.filter(total_price__gte=v)
        v = self._num(p, "max_price")
        if v is not None:
            qs = qs.filter(total_price__lte=v)
        v = self._num(p, "min_square")
        if v is not None:
            qs = qs.filter(square__gte=v)
        v = self._num(p, "max_square")
        if v is not None:
            qs = qs.filter(square__lte=v)

        if p.get("floor_position"):
            qs = qs.filter(floor_position=p["floor_position"])
        v = self._bool01(p, "subway")
        if v is not None:
            qs = qs.filter(subway=v)
        v = self._bool01(p, "elevator")
        if v is not None:
            qs = qs.filter(elevator=v)
        if p.get("q"):
            qs = qs.filter(Q(district_name__icontains=p["q"]))

        ordering = p.get("ordering")
        if ordering:
            field = ordering.lstrip("-")
            allowed = {"total_price", "unit_price", "square", "trade_date", "id"}
            if field not in allowed:
                raise ValidationError({"ordering": f"不支持的排序字段：{field}"})
            qs = qs.order_by(ordering, "-id")
        return qs


class HouseDetailView(generics.RetrieveAPIView):
    queryset = House.objects.all()
    serializer_class = HouseSerializer


class SimilarHouseListView(APIView):
    """按区域、面积、户型和配套检索相似历史成交，作为估价参照。"""

    def get(self, request):
        query = SimilarHouseQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response({"errors": query.errors}, status=status.HTTP_400_BAD_REQUEST)
        params = query.validated_data

        district = params["district_name"]
        if not House.objects.filter(district_name=district).exists():
            return Response(
                {"errors": {"district_name": "未知区域"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        latest_date = House.objects.aggregate(value=Max("trade_date"))["value"]
        window_days = 730
        base_qs = House.objects.filter(district_name=district)
        recent_qs = base_qs
        if latest_date:
            recent_qs = recent_qs.filter(trade_date__gte=latest_date - timedelta(days=window_days))

        target_square = float(params["square"])
        width = target_square * 0.30
        fields = (
            "id", "district_name", "trade_date", "lng", "lat", "square",
            "rooms", "halls", "bathrooms", "floor_position", "total_floors",
            "house_age", "renovation", "total_price", "unit_price",
            "elevator", "subway", "five_years", "url",
        )
        candidates_qs = recent_qs.filter(
            square__gte=max(1, target_square - width),
            square__lte=target_square + width,
        ).order_by("-trade_date", "-id")[:2500]
        candidates = list(candidates_qs.values(*fields))

        # 近两年无候选时放宽到全历史，仍然优先选择同区域同面积段。
        if not candidates:
            candidates = list(base_qs.filter(
                square__gte=max(1, target_square - width),
                square__lte=target_square + width,
            ).order_by("-trade_date", "-id")[:2500].values(*fields))

        target_rooms = params.get("rooms")
        target_floor = params.get("floor_position")
        target_subway = params.get("subway")
        target_elevator = params.get("elevator")
        scored = []
        for row in candidates:
            area_delta = abs(float(row["square"]) - target_square) / max(target_square, 1)
            area_similarity = max(0.0, 1.0 - area_delta / 0.30)
            room_similarity = 1.0
            if target_rooms is not None and row["rooms"] is not None:
                room_similarity = max(0.0, 1.0 - abs(float(row["rooms"]) - target_rooms) / 3)
            floor_similarity = 1.0
            if target_floor and row["floor_position"]:
                floor_similarity = 1.0 if target_floor == row["floor_position"] else 0.0
            subway_similarity = 1.0
            if target_subway is not None and row["subway"] is not None:
                subway_similarity = 1.0 if int(bool(target_subway)) == int(bool(row["subway"])) else 0.0
            elevator_similarity = 1.0
            if target_elevator is not None and row["elevator"] is not None:
                elevator_similarity = 1.0 if int(bool(target_elevator)) == int(bool(row["elevator"])) else 0.0
            recency_similarity = 1.0
            if latest_date and row["trade_date"]:
                days = max(0, (latest_date - row["trade_date"]).days)
                recency_similarity = max(0.0, 1.0 - days / window_days)

            score = (
                area_similarity * 0.40 +
                room_similarity * 0.20 +
                floor_similarity * 0.10 +
                subway_similarity * 0.10 +
                elevator_similarity * 0.10 +
                recency_similarity * 0.10
            ) * 100
            row["similarity_score"] = round(score, 1)
            row["area_delta_pct"] = round(area_delta * 100, 1)
            row["match_reasons"] = _match_reasons(
                row, target_rooms, target_floor, target_subway, target_elevator)
            scored.append(row)

        scored.sort(key=lambda row: (-row["similarity_score"], -row["trade_date"].toordinal()))
        return Response({
            "criteria": {
                "district_name": district,
                "square": target_square,
                "rooms": target_rooms,
                "floor_position": target_floor,
                "subway": target_subway,
                "elevator": target_elevator,
                "latest_trade_date": latest_date,
                "search_window_days": window_days,
                "candidate_count": len(candidates),
            },
            "results": scored[:params["limit"]],
        })


def _match_reasons(row, rooms, floor_position, subway, elevator):
    reasons = ["同区域", f"面积相差 {row['area_delta_pct']:.1f}%"]
    if rooms is not None and row["rooms"] == rooms:
        reasons.append("户型一致")
    if floor_position and row["floor_position"] == floor_position:
        reasons.append("楼层位置一致")
    if subway is not None and int(bool(subway)) == int(bool(row["subway"])):
        reasons.append("地铁条件一致")
    if elevator is not None and int(bool(elevator)) == int(bool(row["elevator"])):
        reasons.append("电梯条件一致")
    return reasons
