# -*- coding: utf-8 -*-
from rest_framework import serializers

from .models import House


class HouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = House
        fields = "__all__"


class SimilarHouseQuerySerializer(serializers.Serializer):
    district_name = serializers.CharField(max_length=32)
    square = serializers.FloatField(min_value=10, max_value=500)
    rooms = serializers.IntegerField(min_value=0, max_value=20, required=False)
    floor_position = serializers.ChoiceField(
        choices=["低", "中", "高", "顶", "底", "未知"], required=False)
    subway = serializers.BooleanField(required=False)
    elevator = serializers.BooleanField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=20, required=False, default=10)
