# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import include, path
from apps.analysis.views import HealthView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/", include("apps.housing.urls")),
    path("api/v1/", include("apps.analysis.urls")),
    path("api/v1/", include("apps.prediction.urls")),
]
