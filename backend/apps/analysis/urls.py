# -*- coding: utf-8 -*-
from django.urls import path
from .views import (CorrelationView, DistributionView, DistrictStatsView, HeatmapView,
                    ImportanceView, MetaOptionsView, ModelMetricsView, OverviewView,
                    YearlyStatsView)

urlpatterns = [
    path("stats/overview/", OverviewView.as_view(), name="stats-overview"),
    path("stats/district/", DistrictStatsView.as_view(), name="stats-district"),
    path("stats/correlation/", CorrelationView.as_view(), name="stats-correlation"),
    path("stats/importance/", ImportanceView.as_view(), name="stats-importance"),
    path("stats/heatmap/", HeatmapView.as_view(), name="stats-heatmap"),
    path("stats/yearly/", YearlyStatsView.as_view(), name="stats-yearly"),
    path("stats/distribution/", DistributionView.as_view(), name="stats-distribution"),
    path("meta/options/", MetaOptionsView.as_view(), name="meta-options"),
    path("models/metrics/", ModelMetricsView.as_view(), name="model-metrics"),
]
