# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    CurrentModelView,
    PredictExplanationView,
    PredictionExportView,
    PredictionHistoryDetailView,
    PredictionHistoryView,
    PredictView,
)

urlpatterns = [
    path("predict/", PredictView.as_view(), name="predict"),
    path("predict/explain/", PredictExplanationView.as_view(), name="predict-explain"),
    path("predictions/", PredictionHistoryView.as_view(), name="prediction-history"),
    path("predictions/export/", PredictionExportView.as_view(), name="prediction-export"),
    path("predictions/<int:pk>/", PredictionHistoryDetailView.as_view(), name="prediction-detail"),
    path("models/current/", CurrentModelView.as_view(), name="current-model"),
]
