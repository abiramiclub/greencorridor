import json
import logging
import os
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import Point, shape
from shapely.ops import transform
from pyproj import Transformer

logger = logging.getLogger(__name__)

CORRIDOR_ZONES_PATH = Path(__file__).parent.parent / "data" / "corridor_zones.geojson"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"

WEIGHTS = {
    "corridor_overlap": 0.35,
    "wetland_presence": 0.15,
    "stream_adjacency": 0.15,
    "protected_proximity": 0.15,
    "core_area": 0.20,
}


def _bbox(lat: float, lon: float, deg: float = 0.02) -> dict:
    return {
        "xmin": lon - deg,
        "ymin": lat - deg,
        "xmax": lon + deg,
        "ymax": lat + deg,
    }


def _fetch_geojson(url: str, params: dict, cache_path: Path) -> gpd.GeoDataFrame | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        try:
            return gpd.read_file(cache_path)
        except Exception:
            pass

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        if not features:
            return None
        cache_path.write_text(json.dumps(data))
        return gpd.read_file(cache_path)
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _to_utm(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf.to_crs("EPSG:32618")


def _point_utm(lat: float, lon: float):
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True)
    x, y = transformer.transform(lon, lat)
    return Point(x, y)


def _buffer_utm(lat: float, lon: float, radius: float = 75.0):
    return _point_utm(lat, lon).buffer(radius)


def score_parcel(lat: float, lon: float) -> dict:
    warnings = []
    data_sources = []
    factors = {}

    bbox = _bbox(lat, lon)
    bbox_geom = (
        f"{bbox['xmin']},{bbox['ymin']},{bbox['xmax']},{bbox['ymax']}"
    )
    bbox_json = json.dumps({
        "xmin": bbox["xmin"], "ymin": bbox["ymin"],
        "xmax": bbox["xmax"], "ymax": bbox["ymax"],
        "spatialReference": {"wkid": 4326},
    })

    # Load corridor zones (always local)
    try:
        corridors = gpd.read_file(CORRIDOR_ZONES_PATH).to_crs("EPSG:32618")
        data_sources.append("Corridor zones")
    except Exception as e:
        warnings.append(f"Corridor zones unavailable: {e}")
        corridors = None

    # Load NWI wetlands
    nwi_cache = CACHE_DIR / f"nwi_{lat:.4f}_{lon:.4f}.geojson"
    nwi = _fetch_geojson(
        "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetlands/MapServer/0/query",
        {
            "geometry": bbox_geom,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "f": "geojson",
        },
        nwi_cache,
    )
    if nwi is not None and len(nwi) > 0:
        nwi = _to_utm(nwi)
        data_sources.append("NWI wetlands")
    else:
        warnings.append("NWI wetlands unavailable")
        nwi = None

    # Load NHD streams
    nhd_cache = CACHE_DIR / f"nhd_{lat:.4f}_{lon:.4f}.geojson"
    nhd = _fetch_geojson(
        "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query",
        {
            "geometry": bbox_geom,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "f": "geojson",
        },
        nhd_cache,
    )
    if nhd is not None and len(nhd) > 0:
        nhd = _to_utm(nhd)
        data_sources.append("NHD streams")
    else:
        warnings.append("NHD streams unavailable")
        nhd = None

    # Load NYPAD protected lands
    nypad_cache = CACHE_DIR / f"nypad_{lat:.4f}_{lon:.4f}.geojson"
    nypad = _fetch_geojson(
        "https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/NYPAD/FeatureServer/0/query",
        {
            "geometry": bbox_geom,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "f": "geojson",
        },
        nypad_cache,
    )
    if nypad is not None and len(nypad) > 0:
        nypad = _to_utm(nypad)
        data_sources.append("NYPAD protected lands")
    else:
        warnings.append("NYPAD protected lands unavailable")
        nypad = None

    buffer = _buffer_utm(lat, lon, 75.0)
    point = _point_utm(lat, lon)

    # Factor 1: corridor_overlap
    if corridors is not None and len(corridors) > 0:
        try:
            overlap = corridors.geometry.intersection(buffer).area.sum()
            pct = min(100.0, (overlap / buffer.area) * 100.0)
            factors["corridor_overlap"] = round(pct, 1)
        except Exception:
            factors["corridor_overlap"] = 0.0
    else:
        factors["corridor_overlap"] = 0.0

    # Factor 2: wetland_presence
    if nwi is not None and len(nwi) > 0:
        try:
            overlap = nwi.geometry.intersection(buffer).area.sum()
            pct = min(100.0, (overlap / buffer.area) * 100.0)
            factors["wetland_presence"] = round(pct, 1)
        except Exception:
            factors["wetland_presence"] = 0.0
    else:
        factors["wetland_presence"] = 0.0

    # Factor 3: stream_adjacency
    if nhd is not None and len(nhd) > 0:
        try:
            buffer_150 = point.buffer(150.0)
            within = nhd.geometry.intersects(buffer_150).any()
            factors["stream_adjacency"] = 100.0 if within else 0.0
        except Exception:
            factors["stream_adjacency"] = 0.0
    else:
        factors["stream_adjacency"] = 0.0

    # Factor 4: protected_proximity
    if nypad is not None and len(nypad) > 0:
        try:
            buffer_800 = point.buffer(800.0)
            within = nypad.geometry.intersects(buffer_800).any()
            factors["protected_proximity"] = 100.0 if within else 0.0
        except Exception:
            factors["protected_proximity"] = 0.0
    else:
        factors["protected_proximity"] = 0.0

    # Factor 5: core_area (fixed prototype value)
    factors["core_area"] = 50.0

    cvi = sum(factors[k] * WEIGHTS[k] for k in WEIGHTS)

    return {
        "cvi": round(cvi, 1),
        "factors": factors,
        "data_sources": data_sources,
        "warnings": warnings,
    }
