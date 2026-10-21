# -*- coding: utf-8 -*-
"""将 data/clean.parquet 导入 SQLite。

用法：cd backend && python manage.py load_data [--limit 50000]
"""
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.housing.models import House


class Command(BaseCommand):
    help = "导入清洗后的房源数据（data/clean.parquet）"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="仅导入前 N 行（0=全部）")
        parser.add_argument("--batch", type=int, default=2000)

    def handle(self, *args, **options):
        path = Path(settings.DATA_DIR) / "clean.parquet"
        if not path.exists():
            self.stderr.write(f"找不到 {path}，请先运行 scripts/01_clean_data.py")
            return

        df = pd.read_parquet(path)
        if options["limit"]:
            df = df.head(options["limit"])

        # 幂等：清空后重建
        House.objects.all().delete()
        self.stdout.write(f"导入 {len(df):,} 行 -> {House._meta.db_table}")

        cols = ["id", "url", "trade_date", "district", "district_name", "lng", "lat",
                "square", "rooms", "halls", "kitchen", "bathrooms", "floor_position",
                "total_floors", "construction_year", "house_age", "renovation",
                "building_type", "building_structure", "ladder_ratio", "elevator",
                "subway", "five_years", "community_average", "total_price", "unit_price", "cid"]
        df = df[[c for c in cols if c in df.columns]].copy()
        df = df.rename(columns={"id": "source_id", "district": "district_code"})
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        df = df.where(pd.notna(df), None)

        batch_size = options["batch"]
        objs = [House(**row) for row in df.to_dict("records")]
        with transaction.atomic():
            for i in range(0, len(objs), batch_size):
                House.objects.bulk_create(objs[i:i + batch_size])
        self.stdout.write(self.style.SUCCESS(f"完成：{House.objects.count():,} 行"))
