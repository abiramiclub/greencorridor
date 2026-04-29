import logging
import os

import requests

logger = logging.getLogger(__name__)

TARGET_SPECIES = [
    {"common": "Bald Eagle", "scientific": "Haliaeetus leucocephalus", "status": "NYS Endangered"},
    {"common": "Spotted Salamander", "scientific": "Ambystoma maculatum", "status": "Species of Concern"},
    {"common": "American Eel", "scientific": "Anguilla rostrata", "status": "Species of Concern"},
    {"common": "Wood Turtle", "scientific": "Glyptemys insculpta", "status": "NYS Threatened"},
    {"common": "Bobcat", "scientific": "Lynx rufus", "status": "Species of Concern"},
    {"common": "Cerulean Warbler", "scientific": "Setophaga cerulea", "status": "NYS Special Concern"},
]

INAT_URL = "https://api.inaturalist.org/v1/observations"
EBIRD_URL = "https://api.ebird.org/v2/data/obs/geo/recent"


def _is_target(name: str) -> dict | None:
    if not name:
        return None
    name_lower = name.lower()
    for t in TARGET_SPECIES:
        if t["common"].lower() in name_lower or t["scientific"].lower() in name_lower:
            return t
    return None


def _inject_parcel_species(parcel: dict, detected_targets: set, results: list):
    """Add species detections from parcels.json rich data."""
    f = parcel.get("features", {})

    if f.get("bald_eagle_sightings_miles", 9) < 2.0 and f.get("eagle_sightings_count", 0) > 0:
        t = next(x for x in TARGET_SPECIES if x["common"] == "Bald Eagle")
        results.append({
            "common_name": "Bald Eagle",
            "scientific_name": t["scientific"],
            "observed_on": f.get("eagle_last_sighting", ""),
            "quality_grade": "research",
            "source": "Philipstown parcel database",
            "priority": True,
            "status": t["status"],
        })
        detected_targets.add("Bald Eagle")

    if f.get("spotted_salamander_habitat"):
        t = next(x for x in TARGET_SPECIES if x["common"] == "Spotted Salamander")
        results.append({
            "common_name": "Spotted Salamander",
            "scientific_name": t["scientific"],
            "observed_on": "",
            "quality_grade": "habitat confirmed",
            "source": "Philipstown parcel database",
            "priority": True,
            "status": t["status"],
        })
        detected_targets.add("Spotted Salamander")

    if f.get("american_eel_access"):
        t = next(x for x in TARGET_SPECIES if x["common"] == "American Eel")
        results.append({
            "common_name": "American Eel",
            "scientific_name": t["scientific"],
            "observed_on": "",
            "quality_grade": "habitat confirmed",
            "source": "Philipstown parcel database",
            "priority": True,
            "status": t["status"],
        })
        detected_targets.add("American Eel")


def get_species(lat: float, lon: float, parcel: dict | None = None) -> list:
    results = []
    detected_targets = set()

    # Inject species from parcel data first
    if parcel:
        _inject_parcel_species(parcel, detected_targets, results)

    # iNaturalist
    try:
        resp = requests.get(
            INAT_URL,
            params={
                "lat": lat,
                "lng": lon,
                "radius": 2,
                "threatened": "true",
                "per_page": 20,
                "order_by": "observed_on",
            },
            timeout=15,
        )
        resp.raise_for_status()
        for obs in resp.json().get("results", []):
            taxon = obs.get("taxon") or {}
            common = taxon.get("preferred_common_name", "")
            scientific = taxon.get("name", "")
            target = _is_target(common) or _is_target(scientific)
            entry = {
                "common_name": common or scientific,
                "scientific_name": scientific,
                "observed_on": obs.get("observed_on", ""),
                "quality_grade": obs.get("quality_grade", ""),
                "source": "iNaturalist",
                "priority": bool(target),
                "status": target["status"] if target else "",
            }
            results.append(entry)
            if target:
                detected_targets.add(target["common"])
    except Exception as e:
        logger.warning("iNaturalist lookup failed: %s", e)

    # eBird
    ebird_key = os.environ.get("EBIRD_API_KEY", "")
    if ebird_key:
        try:
            resp = requests.get(
                EBIRD_URL,
                params={"lat": lat, "lng": lon, "dist": 3, "back": 30},
                headers={"X-eBirdApiToken": ebird_key},
                timeout=15,
            )
            resp.raise_for_status()
            for obs in resp.json():
                common = obs.get("comName", "")
                scientific = obs.get("sciName", "")
                target = _is_target(common) or _is_target(scientific)
                entry = {
                    "common_name": common,
                    "scientific_name": scientific,
                    "observed_on": obs.get("obsDt", ""),
                    "quality_grade": "research",
                    "source": "eBird",
                    "priority": bool(target),
                    "status": target["status"] if target else "",
                }
                results.append(entry)
                if target:
                    detected_targets.add(target["common"])
        except Exception as e:
            logger.warning("eBird lookup failed: %s", e)
    else:
        logger.warning("EBIRD_API_KEY not set — skipping eBird lookup")

    # Add not_detected entries for target species not found
    for t in TARGET_SPECIES:
        if t["common"] not in detected_targets:
            results.append({
                "common_name": t["common"],
                "scientific_name": t["scientific"],
                "observed_on": "",
                "quality_grade": "",
                "source": "not_detected",
                "priority": True,
                "status": t["status"],
                "not_detected": True,
            })

    return results
