import json
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

# Path to the single editable GeoJSON zone configuration file
GEOJSON_FILE = Path(__file__).resolve().parent.parent / "config" / "kolhapur_zones.geojson"

def load_zones_geojson() -> Dict[str, Any]:
    """Load the single editable GeoJSON specification for the 5 Kolhapur operational zones."""
    if not GEOJSON_FILE.exists():
        raise FileNotFoundError(f"Missing zone configuration at {GEOJSON_FILE}")
    with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def is_point_in_polygon(lon: float, lat: float, ring: List[List[float]]) -> bool:
    """
    Determines if coordinate (lon, lat) is inside a polygon ring using Ray-Casting.
    ring: List of [lon, lat] points where ring[0] == ring[-1].
    """
    inside = False
    n = len(ring)
    if n < 3:
        return False

    p1x, p1y = ring[0]
    for i in range(1, n + 1):
        p2x, p2y = ring[i % n]
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                if lon <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or lon <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside

def resolve_zone_for_coordinates(lat: float, lon: float) -> Tuple[Optional[str], str]:
    """
    Point-in-polygon resolution for incident geotagging.
    Returns:
        (zone_id, zone_name) if coordinates lie within one of the 5 operational study zones.
        (None, 'Outside Study Area') if outside the study bounds.
    """
    try:
        data = load_zones_geojson()
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])
            
            if geom.get("type") == "Polygon" and coords:
                outer_ring = coords[0]
                if is_point_in_polygon(lon, lat, outer_ring):
                    return props.get("zone_id"), props.get("zone_name")
                    
        return None, "Outside Study Area"
    except Exception as e:
        print(f"[Zones] Error resolving zone for ({lat}, {lon}): {e}")
        return None, "Outside Study Area"

def get_zone_profiles_map() -> Dict[str, Any]:
    """Build the dictionary of zone officer profiles from the GeoJSON features."""
    data = load_zones_geojson()
    profiles = {}
    
    for f in data.get("features", []):
        props = f.get("properties", {})
        z_name = props.get("zone_name")
        profiles[z_name] = {
            "zone_id": props.get("zone_id"),
            "name": props.get("role", f"Ward Officer - {z_name}"),
            "role": "Assistant Municipal Engineer",
            "zone": z_name,
            "jurisdiction_areas": props.get("localities_str", ""),
            "center_gps": props.get("center", [16.7000, 74.2400]),
            "default_zoom": 14,
            "challenges": props.get("challenges", ""),
            "color": props.get("color", "#3b82f6")
        }

    # Add Citywide Admin profile
    profiles["all"] = {
        "zone_id": "all",
        "name": "Chief Municipal Engineer",
        "role": "Executive Engineer (Civil/PWD)",
        "zone": "All Kolhapur City",
        "jurisdiction_areas": "All 5 Kolhapur Project-Defined Operational Study Zones",
        "center_gps": [16.7000, 74.2400],
        "default_zoom": 13,
        "challenges": "Citywide triage, cross-zone contractor resource allocation, capital pavement rehabilitation.",
        "color": "#6366f1"
    }
    
    return profiles
