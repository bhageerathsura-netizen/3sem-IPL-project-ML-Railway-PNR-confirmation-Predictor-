"""
Unit and Integration Test Suite for Indian Railways PNR Forecast & Trip Planner Application
Tests Flask REST API endpoints, model inference integrity, probability calibration,
train searching with real-time AI probability, and ticket reservation.
"""

import unittest
import json
from app import app

class TestIRCTCPNRApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_01_index_route(self):
        """Verify the main UI page loads successfully"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"RailPredict", response.data)
        self.assertIn(b"Berth Confirmation", response.data)

    def test_02_corridors_api(self):
        """Verify corridors metadata endpoint"""
        response = self.client.get("/api/corridors")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("Delhi-Mumbai", data["corridors"])
        self.assertIn("Bangalore-Chennai", data["corridors"])
        self.assertTrue(len(data["quotas"]) >= 3)
        self.assertTrue(len(data["classes"]) >= 5)

    def test_03_metrics_api(self):
        """Verify model performance metrics endpoint"""
        response = self.client.get("/api/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        rf = data["metrics"]["random_forest"]
        self.assertGreater(rf["accuracy"], 0.75)
        self.assertGreater(rf["roc_auc"], 0.85)
        self.assertIn("true_positive", rf["confusion_matrix"])

    def test_04_predict_high_confirmation_scenario(self):
        """Test high confirmation scenario: small waitlist, large lead time, GNWL"""
        payload = {
            "corridor": "Delhi-Mumbai",
            "train_category": "Rajdhani/VB",
            "coach_class": "3A",
            "quota": "GNWL",
            "current_wl": 5,
            "lead_time_days": 35,
            "is_festive_season": 0,
            "is_weekend": 0
        }
        response = self.client.post("/api/predict", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        data = res["data"]
        
        self.assertGreaterEqual(data["probability_pct"], 65.0)
        self.assertIn(data["risk_tier"], ["HIGH", "MEDIUM"])
        self.assertTrue(len(data["trajectory"]) > 0)
        self.assertEqual(len(data["quota_comparison"]), 3)
        self.assertTrue(len(data["class_alternatives"]) > 0)

    def test_05_predict_low_confirmation_scenario(self):
        """Test low confirmation scenario: high waitlist, small lead time, PQWL"""
        payload = {
            "corridor": "Delhi-Bangalore",
            "train_category": "Superfast",
            "coach_class": "SL",
            "quota": "PQWL",
            "current_wl": 95,
            "lead_time_days": 2,
            "is_festive_season": 1,
            "is_weekend": 1
        }
        response = self.client.post("/api/predict", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        data = res["data"]
        
        self.assertLessEqual(data["probability_pct"], 35.0)
        self.assertEqual(data["risk_tier"], "LOW")
        self.assertEqual(data["recommendation"], "Immediate Alternate Strategy Required")

    def test_06_quota_clearing_dynamics(self):
        """Verify that GNWL probability is significantly higher than PQWL for identical conditions"""
        base_payload = {
            "corridor": "Delhi-Kolkata",
            "train_category": "Superfast",
            "coach_class": "3A",
            "current_wl": 30,
            "lead_time_days": 15,
            "is_festive_season": 0,
            "is_weekend": 0
        }
        
        payload_gnwl = base_payload.copy()
        payload_gnwl["quota"] = "GNWL"
        
        payload_pqwl = base_payload.copy()
        payload_pqwl["quota"] = "PQWL"
        
        res_gnwl = self.client.post("/api/predict", data=json.dumps(payload_gnwl), content_type="application/json").get_json()["data"]
        res_pqwl = self.client.post("/api/predict", data=json.dumps(payload_pqwl), content_type="application/json").get_json()["data"]
        
        self.assertGreater(res_gnwl["probability_pct"], res_pqwl["probability_pct"])

    def test_07_simulate_endpoint(self):
        """Verify What-If sensitivity matrix generation"""
        payload = {
            "corridor": "Delhi-Mumbai",
            "train_category": "Rajdhani/VB",
            "coach_class": "3A",
            "quota": "GNWL",
            "is_festive_season": 0,
            "is_weekend": 0
        }
        response = self.client.post("/api/simulate", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["days_headers"]), 6)
        self.assertEqual(len(res["matrix"]), 6)
        wl5_scores = res["matrix"][0]["scores"]
        wl100_scores = res["matrix"][-1]["scores"]
        self.assertGreater(wl5_scores[0]["probability_pct"], wl100_scores[0]["probability_pct"])

    def test_08_search_trains_api(self):
        """Verify the Trip Planner train search with dynamic AI probability badges"""
        response = self.client.get("/api/search_trains?corridor=Delhi-Mumbai&date=2026-12-01&class=3A&quota=GNWL")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        self.assertTrue(len(res["trains"]) >= 3)
        self.assertIsNotNone(res["split_journey"])
        
        first_train = res["trains"][0]
        self.assertIn("class_options", first_train)
        self.assertTrue(len(first_train["class_options"]) > 0)
        # Check that AI probability is calculated for each class
        for c in first_train["class_options"]:
            self.assertIn("ai_probability", c)
            self.assertIn("fare", c)

    def test_09_book_ticket_api(self):
        """Verify ticket booking and Electronic Reservation Slip (ERS) generation"""
        booking_payload = {
            "train_number": "12952",
            "train_name": "Mumbai Tejas Rajdhani",
            "coach_class": "3A",
            "quota": "GNWL",
            "travel_date": "2026-12-05",
            "corridor": "Delhi-Mumbai",
            "total_fare": 2040.0,
            "availability": "AVL 14",
            "passengers": [
                {"name": "Aarav Mehta", "age": 29, "gender": "Male", "berth_pref": "Lower Berth"}
            ]
        }
        response = self.client.post("/api/book_ticket", data=json.dumps(booking_payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        ticket = res["ticket"]
        self.assertTrue(len(ticket["pnr"]) == 11) # e.g. 248-1849201
        self.assertEqual(ticket["passengers"][0]["name"], "Aarav Mehta")
        self.assertIn("CONFIRMED", ticket["passengers"][0]["booking_status"])

    def test_10_tatkal_status_api(self):
        """Verify live Tatkal countdown status endpoint"""
        response = self.client.get("/api/tatkal_status")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        self.assertIn("ac_tatkal", res)
        self.assertIn("seconds_left", res["ac_tatkal"])

if __name__ == "__main__":
    unittest.main()
