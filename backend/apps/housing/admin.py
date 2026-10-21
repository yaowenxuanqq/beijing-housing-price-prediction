# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import House, ModelMetric


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ("id", "district_name", "square", "rooms", "floor_position",
                    "total_price", "unit_price", "trade_date")
    list_filter = ("district_name", "floor_position", "renovation", "elevator", "subway")
    search_fields = ("source_id",)
    date_hierarchy = "trade_date"


@admin.register(ModelMetric)
class ModelMetricAdmin(admin.ModelAdmin):
    list_display = ("model_name", "version", "experiment", "r2", "r2_unit", "mae", "created_at")
