# -*- coding: utf-8 -*-
from django.urls import path
from .views import HouseDetailView, HouseListView

urlpatterns = [
    path("houses/", HouseListView.as_view(), name="house-list"),
    path("houses/<int:pk>/", HouseDetailView.as_view(), name="house-detail"),
]
