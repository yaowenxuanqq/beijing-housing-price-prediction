# -*- coding: utf-8 -*-
from django.db import models


class House(models.Model):
    """清洗后的房源主表（对应 data/clean.parquet）"""

    source_id = models.CharField(max_length=64, blank=True, db_index=True)
    url = models.URLField(max_length=500, blank=True)
    trade_date = models.DateField(db_index=True)
    district_code = models.IntegerField(db_index=True)
    district_name = models.CharField(max_length=32, db_index=True)
    lng = models.FloatField()
    lat = models.FloatField()
    square = models.FloatField()
    rooms = models.IntegerField(null=True)
    halls = models.IntegerField(null=True)
    kitchen = models.IntegerField(null=True)
    bathrooms = models.IntegerField(null=True)
    floor_position = models.CharField(max_length=8, blank=True, db_index=True)
    total_floors = models.FloatField(null=True)
    construction_year = models.FloatField(null=True)
    house_age = models.FloatField(null=True)
    renovation = models.FloatField(null=True)
    building_type = models.FloatField(null=True)
    building_structure = models.FloatField(null=True)
    ladder_ratio = models.FloatField(null=True)
    elevator = models.FloatField(null=True)
    subway = models.FloatField(null=True)
    five_years = models.FloatField(null=True)
    community_average = models.FloatField(null=True)
    total_price = models.FloatField()
    unit_price = models.FloatField()
    cid = models.BigIntegerField(null=True, db_index=True)

    class Meta:
        db_table = "housing_house"
        indexes = [
            models.Index(fields=["district_name", "trade_date"]),
            models.Index(fields=["unit_price"]),
        ]

    def __str__(self):
        return f"{self.district_name} {self.square}㎡ {self.total_price}万"


class ModelMetric(models.Model):
    """模型评估指标留档"""

    model_name = models.CharField(max_length=32)
    version = models.CharField(max_length=64)
    experiment = models.CharField(max_length=64, blank=True)
    rmse = models.FloatField(null=True)
    mae = models.FloatField(null=True)
    r2 = models.FloatField(null=True)
    r2_unit = models.FloatField(null=True)
    mape_pct = models.FloatField(null=True)
    params_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "model_metric"
