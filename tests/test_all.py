"""
RoadCare AI - Automated Test Suite
Validates dataset integrity, severity heuristics, database operations, and FastAPI endpoints.
"""

import sys
import unittest
import json
from pathlib import Path

# Add paths
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir / "backend"))
sys.path.append(str(root_dir / "downstream_prototype"))

from track_and_severity import estimate_severity
import database
import models
import main

class TestRoadDamagePipeline(unittest.TestCase):

    def test_severity_heuristics(self):
        """Verify severity decision boundaries for potholes and cracks."""
        # Pothole
        self.assertEqual(estimate_severity("pothole", 0.01), "Low")
        self.assertEqual(estimate_severity("pothole", 0.035), "Medium")
        self.assertEqual(estimate_severity("pothole", 0.08), "High")
        
        # Alligator Crack
        self.assertEqual(estimate_severity("alligator_crack", 0.02), "Low")
        self.assertEqual(estimate_severity("alligator_crack", 0.07), "Medium")
        self.assertEqual(estimate_severity("alligator_crack", 0.14), "High")

    def test_database_and_analytics(self):
        """Verify SQLite fallback and statistical aggregation."""
        stats = database.get_summary_statistics()
        self.assertIn("total_defects", stats)
        self.assertIn("total_potholes", stats)
        self.assertIn("total_alligator_cracks", stats)
        self.assertIn("repair_rate_percent", stats)
        self.assertGreaterEqual(stats["total_defects"], 0)

    def test_fastapi_health(self):
        """Verify API health endpoint."""
        res = main.health_check()
        self.assertEqual(res["status"], "online")
        self.assertIn("pothole", res["classes_supported"])
        self.assertIn("alligator_crack", res["classes_supported"])

    def test_geojson_export(self):
        """Verify GeoJSON RFC 7946 compliance."""
        geojson = main.get_defects_geojson()
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertIsInstance(geojson["features"], list)
        if geojson["features"]:
            feat = geojson["features"][0]
            self.assertEqual(feat["type"], "Feature")
            self.assertEqual(feat["geometry"]["type"], "Point")
            self.assertEqual(len(feat["geometry"]["coordinates"]), 2)
            self.assertIn("severity", feat["properties"])

    def test_dataset_config_yaml(self):
        """Verify data.yaml exists and points to the 2 target classes."""
        yaml_file = root_dir / "dataset" / "RoadDamage20K" / "data.yaml"
        self.assertTrue(yaml_file.exists())
        content = yaml_file.read_text(encoding="utf-8")
        self.assertIn("0: pothole", content)
        self.assertIn("1: alligator_crack", content)

    def test_metadata_csvs_exist(self):
        """Verify all required metadata manifests exist."""
        meta_dir = root_dir / "dataset" / "RoadDamage20K" / "metadata"
        self.assertTrue((meta_dir / "source_manifest.csv").exists())
        self.assertTrue((meta_dir / "IMAGE_PROVENANCE.csv").exists())
        self.assertTrue((meta_dir / "class_mapping.csv").exists())
        self.assertTrue((meta_dir / "split_manifest.csv").exists())
        self.assertTrue((meta_dir / "duplicate_report.csv").exists())

    def test_kolhapur_zone_profiles(self):
        """Verify that all 5 Kolhapur municipal zones are configured."""
        zones = main.list_zones()
        expected_zones = [
            "Central Kolhapur",
            "North Kolhapur",
            "South Kolhapur",
            "East Kolhapur",
            "West Kolhapur",
            "all"
        ]
        for z in expected_zones:
            self.assertIn(z, zones)
            self.assertIn("center_gps", zones[z])
            self.assertEqual(len(zones[z]["center_gps"]), 2)

    def test_kolhapur_auth_login(self):
        """Verify ward officer authentication by Kolhapur administrative zone."""
        # Test Central Kolhapur
        req = models.AuthLoginRequest(zone="Central Kolhapur", username="eng_patil")
        profile = main.login_officer(req)
        self.assertEqual(profile["zone"], "Central Kolhapur")
        self.assertIn("Shahupuri", profile["jurisdiction_areas"])

        # Test West Kolhapur
        req_west = models.AuthLoginRequest(zone="West Kolhapur")
        profile_west = main.login_officer(req_west)
        self.assertEqual(profile_west["zone"], "West Kolhapur")
        self.assertIn("Rankala", profile_west["jurisdiction_areas"])

    def test_kolhapur_zone_defect_filtering(self):
        """Verify database query filtering by Kolhapur zone."""
        # Central Kolhapur
        central_defects = database.query_defects(zone="Central Kolhapur")
        for d in central_defects:
            self.assertEqual(d["zone"], "Central Kolhapur")

        # West Kolhapur
        west_defects = database.query_defects(zone="West Kolhapur")
        for d in west_defects:
            self.assertEqual(d["zone"], "West Kolhapur")

    def test_kolhapur_zone_statistics(self):
        """Verify summary statistics calculation when filtered by zone."""
        stats = database.get_summary_statistics(zone="Central Kolhapur")
        self.assertIn("total_defects", stats)
        self.assertIn("total_potholes", stats)
        self.assertIn("total_alligator_cracks", stats)

if __name__ == "__main__":
    unittest.main()

