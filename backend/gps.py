"""Reads GPS coordinates stored inside phone photos (EXIF)."""
from PIL import Image

GPS_TAG = 34853


def _to_deg(v):
    d, m, s = (float(x) for x in v)
    return d + m / 60 + s / 3600


def exif_gps(path):
    """Returns (lat, lng) or (None, None) if the photo has no GPS."""
    try:
        exif = Image.open(path).getexif()
        g = exif.get_ifd(GPS_TAG)
        if not g or 2 not in g or 4 not in g:
            return None, None
        lat, lng = _to_deg(g[2]), _to_deg(g[4])
        if g.get(1) == "S":
            lat = -lat
        if g.get(3) == "W":
            lng = -lng
        return round(lat, 7), round(lng, 7)
    except Exception:
        return None, None
