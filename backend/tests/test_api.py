# -*- coding: utf-8 -*-
"""后端 API 冒烟测试（manage.py test）"""

from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
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
        self.assertIn(data["interval_method"], {
            "time_series_cv_residual_quantile", "tree_spread", "heuristic_spread"
        })
        self.assertTrue(data["interval_note"])
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

    def test_meta_options_returns_market_median(self):
        r = self.client.get("/api/v1/meta/options/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("朝阳区", data["districts"])
        self.assertIn("朝阳区", data["market_median_unit_price"])

    def test_correlation_marks_leakage_fields(self):
        r = self.client.get("/api/v1/stats/correlation/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("leakage_fields", data)
        self.assertIn("community_average", data["leakage_fields"])
        self.assertEqual(len(data["fields"]), len(data["matrix"]))
    def test_health_returns_model_metadata(self):
        r = self.client.get("/api/v1/health/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["database"]["ready"])
        self.assertTrue(data["model"]["ready"])
        self.assertEqual(data["database"]["houses"], 120)
        self.assertTrue(data["model"]["model_sha256"])

    def test_predict_explain_returns_shap_features(self):
        r = self.client.post("/api/v1/predict/explain/", self.payload(), format="json")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["explanation"]["method"], "TreeSHAP")
        self.assertGreater(len(data["explanation"]["features"]), 0)
        self.assertIn("contribution_unit_price", data["explanation"]["features"][0])
        self.assertTrue(data["request_id"])

    def test_similar_houses_returns_ranked_candidates(self):
        r = self.client.get("/api/v1/houses/similar/", {
            "district_name": "朝阳区", "square": 89.5, "rooms": 2,
            "floor_position": "中", "subway": True, "elevator": True, "limit": 5,
        })
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreater(len(data["results"]), 0)
        self.assertLessEqual(len(data["results"]), 5)
        self.assertGreaterEqual(data["results"][0]["similarity_score"], 0)
        self.assertIn("match_reasons", data["results"][0])

    def test_prediction_history_and_export(self):
        prediction = self.client.post("/api/v1/predict/", self.payload(), format="json")
        self.assertEqual(prediction.status_code, 200)
        history = self.client.get("/api/v1/predictions/")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["count"], 1)
        export = self.client.get("/api/v1/predictions/export/")
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export["Content-Type"])
        self.assertIn("request_id", export.content.decode("utf-8-sig"))

    def test_current_model_returns_runtime_stats(self):
        r = self.client.get("/api/v1/models/current/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ready"])
        self.assertEqual(data["model"]["model_class"], "RandomForestRegressor")
        self.assertIn("prediction_count", data["runtime"])
    def test_scenario_analysis_returns_deltas(self):
        payload = {
            "base": self.payload(),
            "scenarios": [
                {"name": "有电梯", "changes": {"elevator": True}},
                {"name": "面积增加10㎡", "changes": {"square": 99.5}},
            ],
        }
        r = self.client.post("/api/v1/predict/scenarios/", payload, format="json")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["baseline"]["name"], "当前方案")
        self.assertEqual(len(data["scenarios"]), 2)
        self.assertIn("delta_total_price", data["scenarios"][1])
        self.assertTrue(data["batch_id"])

    def test_batch_predict_accepts_csv(self):
        csv_text = (
            "district_name,square,rooms,halls,bathrooms,floor_position,total_floors,house_age,"
            "renovation,building_type,building_structure,ladder_ratio,elevator,subway,five_years,"
            "market_median_unit_price\n"
            "朝阳区,89.5,2,1,1,中,18,12,3,1,2,2,true,true,true,66421\n"
            "朝阳区,70,2,1,1,中,12,10,2,1,2,2,false,true,true,66421\n"
        )
        upload = SimpleUploadedFile("houses.csv", csv_text.encode("utf-8-sig"), content_type="text/csv")
        r = self.client.post("/api/v1/predict/batch/", {"file": upload}, format="multipart")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["success"], 2)
        self.assertEqual(data["failed"], 0)
        self.assertIn("predicted_total_price", data["results"][0])
        self.assertEqual(data["results"][0]["input_json"]["district_name"], "朝阳区")

    def test_batch_template_is_csv(self):
        r = self.client.get("/api/v1/predict/batch/template/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        self.assertIn("district_name", r.content.decode("utf-8-sig"))

    def test_current_model_runtime_has_latency_and_daily(self):
        self.client.post("/api/v1/predict/", self.payload(), format="json")
        r = self.client.get("/api/v1/models/current/")
        self.assertEqual(r.status_code, 200)
        runtime = r.json()["runtime"]
        self.assertIn("latency_p50_ms", runtime)
        self.assertIn("source_counts", runtime)
        self.assertEqual(len(runtime["recent_daily"]), 7)
