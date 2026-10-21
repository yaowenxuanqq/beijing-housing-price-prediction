# -*- coding: utf-8 -*-
from rest_framework import serializers

FLOOR_CHOICES = ["低", "中", "高", "顶", "底", "未知"]

# 区名白名单缓存（数据静态，进程内缓存一次）
_district_cache = None


def _valid_districts():
    global _district_cache
    if _district_cache is None:
        from apps.housing.models import House
        _district_cache = set(
            House.objects.values_list("district_name", flat=True).distinct())
    return _district_cache


class PredictRequestSerializer(serializers.Serializer):
    district_name = serializers.CharField(max_length=32)
    square = serializers.FloatField(min_value=10, max_value=500)
    market_median_unit_price = serializers.FloatField(min_value=1000, max_value=300000)

    rooms = serializers.IntegerField(min_value=0, max_value=20, required=False, default=2)
    halls = serializers.IntegerField(min_value=0, max_value=20, required=False, default=1)
    kitchen = serializers.IntegerField(min_value=0, max_value=10, required=False, default=1)
    bathrooms = serializers.IntegerField(min_value=0, max_value=10, required=False, default=1)
    floor_position = serializers.ChoiceField(choices=FLOOR_CHOICES, required=False, default="中")
    total_floors = serializers.FloatField(min_value=1, max_value=100, required=False)
    house_age = serializers.FloatField(min_value=0, max_value=70, required=False)
    renovation = serializers.IntegerField(min_value=1, max_value=4, required=False)
    building_type = serializers.IntegerField(min_value=1, max_value=4, required=False)
    building_structure = serializers.IntegerField(min_value=1, max_value=7, required=False)
    ladder_ratio = serializers.FloatField(min_value=0, max_value=20, required=False)
    elevator = serializers.BooleanField(required=False, default=False)
    subway = serializers.BooleanField(required=False, default=False)
    five_years = serializers.BooleanField(required=False, default=False)
    lng = serializers.FloatField(min_value=115, max_value=118, required=False)
    lat = serializers.FloatField(min_value=39, max_value=41, required=False)
    cid = serializers.IntegerField(required=False)

    def validate_district_name(self, value):
        valid = _valid_districts()
        if valid and value not in valid:
            raise serializers.ValidationError(
                f"未知区域：{value}，可选值为 {sorted(valid)}")
        return value
