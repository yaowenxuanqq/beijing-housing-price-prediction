# -*- coding: utf-8 -*-
"""后端 API 冒烟测试（manage.py test）"""

from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.housing.models import House


class ApiSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rows = []
        for i in range(120):
            rows.append(House(
                source_id=f"t{i}",
                trade_date=date(2016, (i % 12) + 1, 1),
                district_code=7, district_name="朝阳区",
                lng=116.47 + i * 0.0001, lat=39.94,
                square=80.0 + i, rooms=2, halls=1, kitchen=1, bathrooms=1,
                floor_position="中", total_floors=18, construction_year=2005,
                house_age=11, renovation=3, building_type=1, building_structure=2,
                ladder_ratio=2, elevator=1, subway=1, five_years=1,
                community_average=60000 + i, total_price=400 + i,
                unit_price=50000 + i, cid=1000 + i,
            ))
        House.objects.bulk_create(rows)

    def setUp(self):
        self.client = APIClient()

    def payload(self, **override):
        p = {
            "district_name": "朝阳区",
            "square": 89.5,
            "rooms": 2, "halls": 1, "bathrooms": 1,
            "floor_position": "中", "total_floors": 18,
            "house_age": 12, "renovation": 3, "building_type": 1,
            "building_structure": 2, "ladder_ratio": 2,
            "elevator": True, "subway": True, "five_years": True,
            "market_median_unit_price": 66421,
        }
        p.update(override)
        return p

    def test_predict_ok(self):
        r = self.client.post("/api/v1/predict/", self.payload(), format="json")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("predicted_total_price", data)
        self.assertIn("model_version", data)
        self.assertLessEqual(data["interval_low"], data["predicted_unit_price"])
        self.assertGreaterEqual(data["interval_high"], data["predicted_unit_price"])
        self.assertEqual(data["interval_level"], 0.8)
        # 响应三字段可互推
        self.assertAlmostEqual(
            data["ratio"] * data["market_median_unit_price"],
            data["predicted_unit_price"], delta=1.0)

    def test_predict_unknown_district_returns_400(self):
        r = self.client.post("/api/v1/predict/", self.payload(district_name="火星区"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("district_name", r.json()["errors"])

    def test_predict_missing_required_returns_400(self):
        p = self.payload()
        p.pop("square")
        r = self.client.post("/api/v1/predict/", p, format="json")
        self.assertEqual(r.status_code, 400)

    def test_houses_invalid_numeric_param_returns_400(self):
        r = self.client.get("/api/v1/houses/?min_price=abc")
        self.assertEqual(r.status_code, 400)

    def test_correlation_marks_leakage_fields(self):
        r = self.client.get("/api/v1/stats/correlation/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("leakage_fields", data)
        self.assertIn("community_average", data["leakage_fields"])
        self.assertEqual(len(data["fields"]), len(data["matrix"]))
