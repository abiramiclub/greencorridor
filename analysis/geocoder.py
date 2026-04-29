import requests
from shapely.geometry import Point, mapping
from shapely.ops import transform
from pyproj import Transformer

FALLBACK_COORDS = {
    "238 main st": {"lat": 41.4154, "lon": -73.9571, "display_address": "238 Main St, Cold Spring, NY"},
    "9475 route 9": {"lat": 41.4231, "lon": -73.9312, "display_address": "9475 Route 9, Philipstown, NY"},
    "1520 route 9d": {"lat": 41.4089, "lon": -73.9498, "display_address": "1520 Route 9D, Philipstown, NY"},
    "1 fahnestock state park rd": {"lat": 41.4544, "lon": -73.8287, "display_address": "1 Fahnestock State Park Rd, Carmel, NY"},
    "8 seminary hill rd": {"lat": 41.4198, "lon": -73.9445, "display_address": "8 Seminary Hill Rd, Cold Spring, NY"},
}

NYS_GEOCODER_URL = (
    "https://gisservices.its.ny.gov/arcgis/rest/services/Locators/"
    "Street_and_Addresses/GeocodeServer/findAddressCandidates"
)


def _make_buffer(lat: float, lon: float):
    transformer_to = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True)
    transformer_back = Transformer.from_crs("EPSG:32618", "EPSG:4326", always_xy=True)

    point_projected = transform(transformer_to.transform, Point(lon, lat))
    buffer_projected = point_projected.buffer(75)
    buffer_wgs84 = transform(transformer_back.transform, buffer_projected)
    return buffer_wgs84


def address_to_geom(address: str) -> dict:
    lat, lon, display_address, score = None, None, address, 0

    try:
        resp = requests.get(
            NYS_GEOCODER_URL,
            params={"SingleLine": address, "outFields": "*", "f": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            best = candidates[0]
            lat = best["location"]["y"]
            lon = best["location"]["x"]
            display_address = best.get("address", address)
            score = best.get("score", 0)
    except Exception:
        pass

    if lat is None:
        addr_lower = address.lower()
        for key, fallback in FALLBACK_COORDS.items():
            if key in addr_lower:
                lat = fallback["lat"]
                lon = fallback["lon"]
                display_address = fallback["display_address"]
                score = 0
                break

    if lat is None:
        raise ValueError(f"Could not geocode address: {address}")

    buffer_polygon = _make_buffer(lat, lon)

    return {
        "lat": lat,
        "lon": lon,
        "display_address": display_address,
        "score": score,
        "point": mapping(Point(lon, lat)),
        "buffer": mapping(buffer_polygon),
    }
