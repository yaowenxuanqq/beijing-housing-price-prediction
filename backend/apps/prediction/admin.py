# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import PredictionLog


@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "request_id", "predicted_total_price", "predicted_unit_price",
        "interval_method", "model_version", "duration_ms", "created_at",
    )
    list_filter = ("model_version", "interval_method", "created_at")
    search_fields = ("request_id", "input_json")
    readonly_fields = (
        "request_id", "input_json", "response_json", "duration_ms", "created_at",
    )
    date_hierarchy = "created_at"
