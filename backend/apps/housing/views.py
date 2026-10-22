# -*- coding: utf-8 -*-
from django.db.models import Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from .models import House
from .serializers import HouseSerializer


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
