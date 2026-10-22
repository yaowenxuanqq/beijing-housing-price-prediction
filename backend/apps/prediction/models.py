# -*- coding: utf-8 -*-
from django.db import models


class PredictionLog(models.Model):
    """预测记录（用于追溯与展示）"""

    input_json = models.JSONField()
    predicted_ratio = models.FloatField(null=True)
    predicted_unit_price = models.FloatField(null=True)
    predicted_total_price = models.FloatField(null=True)
    interval_low = models.FloatField(null=True)
    interval_high = models.FloatField(null=True)
    market_median_unit_price = models.FloatField(null=True)
    model_version = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prediction_log"
        ordering = ["-created_at"]
