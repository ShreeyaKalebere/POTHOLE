import sys
from pathlib import Path

# Force UTF-8 stdout for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend modules are on sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from zones import load_zones_geojson, resolve_zone_for_coordinates, get_zone_profiles_map
from database import insert_defects, query_defects, get_zonewise_statistics

def test_geojson_structure():
    print("\n--- Test 1: GeoJSON Zone Configuration ---")
    data = load_zones_geojson()
    assert data.get("type") == "FeatureCollection"
    features = data.get("features", [])
    assert len(features) == 5, f"Expected 5 operational zones, found {len(features)}"
    
    zone_ids = [f["properties"]["zone_id"] for f in features]
    expected_ids = ["central_kolhapur", "north_kolhapur", "south_kolhapur", "east_kolhapur", "west_kolhapur"]
    for expected in expected_ids:
        assert expected in zone_ids, f"Missing zone_id: {expected}"
    print("✓ GeoJSON structure contains all 5 project-defined operational zones.")

def test_center_coordinates_mapping():
    print("\n--- Test 2: Point-in-Polygon Resolution on Supplied Centers ---")
    centers = [
        ("Central Kolhapur", 16.7040, 74.2380, "central_kolhapur"),
        ("North Kolhapur", 16.7250, 74.2480, "north_kolhapur"),
        ("South Kolhapur", 16.6750, 74.2280, "south_kolhapur"),
        ("East Kolhapur", 16.6850, 74.2750, "east_kolhapur"),
        ("West Kolhapur", 16.6920, 74.2050, "west_kolhapur")
    ]
    
    for name, lat, lon, expected_id in centers:
        zid, zname = resolve_zone_for_coordinates(lat, lon)
        print(f"   [{name}] ({lat}, {lon}) -> Resolved: {zid} ({zname})")
        assert zid == expected_id, f"Failed for {name}: expected {expected_id}, got {zid}"
        assert zname == name, f"Failed for {name}: expected {name}, got {zname}"
    print("✓ All 5 supplied center coordinates mapped with 100% precision.")

def test_outside_study_area_coordinates():
    print("\n--- Test 3: Outside Study Area Non-Forced Assignment ---")
    outside_points = [
        ("Outer NH-48 Corridor", 16.6150, 74.3200),
        ("Mumbai Gateway", 19.0760, 72.8777),
        ("Pune Shivaji Nagar", 18.5204, 73.8567),
        ("Far South Outer Boundary", 16.5000, 74.1000)
    ]
    
    for label, lat, lon in outside_points:
        zid, zname = resolve_zone_for_coordinates(lat, lon)
        print(f"   [{label}] ({lat}, {lon}) -> Resolved: {zid} ({zname})")
        assert zid is None, f"Expected None for outside point {label}, but got {zid}"
        assert zname == "Outside Study Area", f"Expected 'Outside Study Area' for {label}, got {zname}"
    print("✓ Outside-study-area coordinates are strictly NOT forcibly assigned.")

def test_incident_ingestion_and_scoping():
    print("\n--- Test 4: Incident Ingestion with Point-in-Polygon & Role Scoping ---")
    test_incidents = [
        {
            "defect_id": 9901,
            "class_name": "pothole",
            "severity": "High",
            "confidence": 0.95,
            "gps": {"latitude": 16.7045, "longitude": 74.2385}, # Central
            "bbox_norm": [0.2, 0.4, 0.3, 0.2]
        },
        {
            "defect_id": 9902,
            "class_name": "alligator_crack",
            "severity": "Medium",
            "confidence": 0.88,
            "gps": {"latitude": 16.7260, "longitude": 74.2490}, # North
            "bbox_norm": [0.1, 0.3, 0.4, 0.3]
        },
        {
            "defect_id": 9903,
            "class_name": "pothole",
            "severity": "Low",
            "confidence": 0.82,
            "gps": {"latitude": 19.0760, "longitude": 72.8777}, # Outside
            "bbox_norm": [0.3, 0.5, 0.2, 0.1]
        }
    ]
    
    count = insert_defects(test_incidents)
    assert count == 3, f"Expected 3 ingested defects, got {count}"
    
    # Verify Central Kolhapur scoped query
    central_defects = query_defects(zone="Central Kolhapur")
    central_ids = [d["defect_id"] for d in central_defects]
    assert 9901 in central_ids, "Central Kolhapur officer must see defect 9901"
    assert 9902 not in central_ids, "Central Kolhapur officer must NOT see North Kolhapur defect 9902"
    assert 9903 not in central_ids, "Central Kolhapur officer must NOT see outside defect 9903"
    print("   -> Zone Officer query scoping: Verified.")
    
    # Verify Citywide Admin query
    all_defects = query_defects(zone="all")
    all_ids = [d["defect_id"] for d in all_defects]
    assert 9901 in all_ids and 9902 in all_ids, "Citywide Admin must see all incidents across zones"
    print("   -> Citywide Admin query scoping: Verified.")

def test_zonewise_statistics():
    print("\n--- Test 5: Zone-Wise Statistics Breakdown ---")
    stats = get_zonewise_statistics()
    assert "zones" in stats
    zones = stats["zones"]
    assert len(zones) == 5, f"Expected 5 zones in breakdown, found {len(zones)}"
    
    for zid, zstat in zones.items():
        assert "total_incidents" in zstat
        assert "potholes" in zstat
        assert "alligator_cracks" in zstat
        assert "severity" in zstat
        assert "status" in zstat
        print(f"   [{zid}] Total: {zstat['total_incidents']} | Potholes: {zstat['potholes']} | Cracks: {zstat['alligator_cracks']}")
        
    assert stats["outside_study_area_count"] >= 1, "Must detect at least 1 outside study area incident"
    print("✓ Zone-wise statistics breakdown validated successfully.")

if __name__ == "__main__":
    test_geojson_structure()
    test_center_coordinates_mapping()
    test_outside_study_area_coordinates()
    test_incident_ingestion_and_scoping()
    test_zonewise_statistics()
    print("\n========================================================")
    print(" ALL 5 KOLHAPUR OPERATIONAL ZONE TESTS PASSED!")
    print("========================================================")
