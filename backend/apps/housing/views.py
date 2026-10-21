# -*- coding: utf-8 -*-
from django.db.models import Q
from rest_framework import generics

from .models import House
from .serializers import HouseSerializer


class HouseListView(generics.ListAPIView):
    """房源列表：分页 + 区域/面积/价格/楼层筛选"""

    serializer_class = HouseSerializer

    def get_queryset(self):
        qs = House.objects.all().order_by("-trade_date", "-id")
        p = self.request.query_params
        if p.get("district"):
            qs = qs.filter(district_name=p["district"])
        if p.get("min_price"):
            qs = qs.filter(total_price__gte=float(p["min_price"]))
        if p.get("max_price"):
            qs = qs.filter(total_price__lte=float(p["max_price"]))
        if p.get("min_square"):
            qs = qs.filter(square__gte=float(p["min_square"]))
        if p.get("max_square"):
            qs = qs.filter(square__lte=float(p["max_square"]))
        if p.get("floor_position"):
            qs = qs.filter(floor_position=p["floor_position"])
        if p.get("subway") in ("0", "1"):
            qs = qs.filter(subway=int(p["subway"]))
        if p.get("elevator") in ("0", "1"):
            qs = qs.filter(elevator=int(p["elevator"]))
        if p.get("q"):
            qs = qs.filter(Q(district_name__icontains=p["q"]))
        return qs


class HouseDetailView(generics.RetrieveAPIView):
    queryset = House.objects.all()
    serializer_class = HouseSerializer
