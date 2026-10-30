"""Kolhapur operational zones (approximate centre points).
An incident belongs to the zone whose centre is nearest.
Replace with official ward boundaries (GeoJSON) if the municipal corporation provides them."""
import math

ZONES = {
    "Kasaba Bawada":  (16.7300, 74.2370),
    "Tarabai Park":   (16.7145, 74.2380),
    "Kadamwadi":      (16.7170, 74.2560),
    "Shahupuri":      (16.7040, 74.2420),
    "Rajarampuri":    (16.6967, 74.2510),
    "Mangalwar Peth": (16.6960, 74.2300),
    "Shivaji Peth":   (16.6930, 74.2240),
    "Jawahar Nagar":  (16.6890, 74.2390),
    "Ruikar Colony":  (16.6900, 74.2600),
    "Ujalaiwadi":     (16.6600, 74.2700),
}
CITY_CENTER = (16.7050, 74.2433)


def haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def zone_for(lat, lng):
    if lat is None or lng is None:
        return "Unknown"
    name, (zl, zg) = min(ZONES.items(), key=lambda kv: haversine_m(lat, lng, *kv[1]))
    # further than 6 km from every centre = outside city limits
    return name if haversine_m(lat, lng, zl, zg) < 6000 else "Outside City"
