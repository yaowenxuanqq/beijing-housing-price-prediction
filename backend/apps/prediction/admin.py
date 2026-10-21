# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import PredictionLog


@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "predicted_total_price", "predicted_unit_price", "model_version", "created_at")
    readonly_fields = ("input_json", "created_at")
