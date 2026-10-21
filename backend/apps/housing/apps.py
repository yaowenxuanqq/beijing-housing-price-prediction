# -*- coding: utf-8 -*-
from django.apps import AppConfig

class HousingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.housing"
    verbose_name = "房源数据"
