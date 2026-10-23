# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    BatchPredictView,
    BatchTemplateView,
    CurrentModelView,
    PredictExplanationView,
    PredictionExportView,
    PredictionHistoryDetailView,
    PredictionHistoryView,
    PredictView,
    ScenarioPredictView,
)

urlpatterns = [
    path("predict/", PredictView.as_view(), name="predict"),
    path("predict/explain/", PredictExplanationView.as_view(), name="predict-explain"),
    path("predict/scenarios/", ScenarioPredictView.as_view(), name="predict-scenarios"),
    path("predict/batch/", BatchPredictView.as_view(), name="predict-batch"),
    path("predict/batch/template/", BatchTemplateView.as_view(), name="predict-batch-template"),
    path("predictions/", PredictionHistoryView.as_view(), name="prediction-history"),
    path("predictions/export/", PredictionExportView.as_view(), name="prediction-export"),
    path("predictions/<int:pk>/", PredictionHistoryDetailView.as_view(), name="prediction-detail"),
    path("models/current/", CurrentModelView.as_view(), name="current-model"),
]
