import json
import os
import re
from pathlib import Path

import folium
from folium import LayerControl
import geopandas as gpd

CORRIDOR_ZONES_PATH = Path(__file__).parent.parent / "data" / "corridor_zones.geojson"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"

LEGEND_HTML = """
<div style="
    position: fixed; bottom: 30px; right: 30px; z-index: 1000;
    background: white; padding: 12px 16px; border-radius: 8px;
    border: 1px solid #ccc; font-size: 13px; font-family: sans-serif;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.2); line-height: 1.8;
">
  <b>Legend</b><br>
  <span style="color:#228B22">&#9632;</span> Green Corridor Zones<br>
  <span style="color:#1E90FF">&#9632;</span> NWI Wetlands<br>
  <span style="color:#1E90FF">&#9472;</span> NHD Streams<br>
  <span style="color:#8A2BE2">&#9632;</span> Protected Lands (NYPAD)<br>
  <span style="color:#CC0000">&#11044;</span> Assessed Location
</div>
"""

TITLE_HTML = """
<div style="
    position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
    z-index: 1000; background: rgba(255,255,255,0.92); padding: 8px 20px;
    border-radius: 6px; border: 1px solid #bbb;
    font-size: 15px; font-weight: bold; font-family: sans-serif;
    box-shadow: 1px 1px 4px rgba(0,0,0,0.2); white-space: nowrap;
">
  CorridorGuardian &mdash; Hudson Highlands Green Corridors Initiative
</div>
"""


def _cvi_color(cvi: float) -> str:
    if cvi >= 65:
        return "#2E8B57"
    if cvi >= 35:
        return "#DAA520"
    return "#CC2200"


def _bar(cvi: float) -> str:
    filled = int(round(cvi / 10))
    color = _cvi_color(cvi)
    bar = "█" * filled + "░" * (10 - filled)
    return f'<span style="color:{color};font-family:monospace">{bar}</span>'


def make_map(lat: float, lon: float, address: str, cvi_result: dict, species_list: list) -> str:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    m = folium.Map(location=[lat, lon], zoom_start=14, tiles="OpenStreetMap")

    # Title banner
    m.get_root().html.add_child(folium.Element(TITLE_HTML))
    # Legend
    m.get_root().html.add_child(folium.Element(LEGEND_HTML))

    # Layer 1: Corridor zones
    try:
        corridors = gpd.read_file(CORRIDOR_ZONES_PATH)
        corridor_group = folium.FeatureGroup(name="Green Corridor Zones")
        for _, row in corridors.iterrows():
            folium.GeoJson(
                row.geometry.__geo_interface__,
                style_function=lambda _: {
                    "fillColor": "#228B22",
                    "color": "#145214",
                    "weight": 1.5,
                    "fillOpacity": 0.35,
                },
                tooltip=folium.Tooltip(
                    f"<b>{row.get('name', '').replace('_', ' ')}</b><br>{row.get('description', '')}"
                ),
            ).add_to(corridor_group)
        corridor_group.add_to(m)
    except Exception:
        pass

    # Layer 2: NWI wetlands (from cache)
    nwi_cache = CACHE_DIR / f"nwi_{lat:.4f}_{lon:.4f}.geojson"
    if nwi_cache.exists():
        try:
            wetlands_gdf = gpd.read_file(nwi_cache)
            if len(wetlands_gdf) > 0:
                wetland_group = folium.FeatureGroup(name="NWI Wetlands")
                for _, row in wetlands_gdf.iterrows():
                    if row.geometry is None:
                        continue
                    folium.GeoJson(
                        row.geometry.__geo_interface__,
                        style_function=lambda _: {
                            "fillColor": "#1E90FF",
                            "color": "#0055CC",
                            "weight": 1,
                            "fillOpacity": 0.40,
                        },
                        tooltip=folium.Tooltip("Wetland"),
                    ).add_to(wetland_group)
                wetland_group.add_to(m)
        except Exception:
            pass

    # Layer 3: NHD streams (from cache)
    nhd_cache = CACHE_DIR / f"nhd_{lat:.4f}_{lon:.4f}.geojson"
    if nhd_cache.exists():
        try:
            streams_gdf = gpd.read_file(nhd_cache)
            if len(streams_gdf) > 0:
                stream_group = folium.FeatureGroup(name="NHD Streams")
                for _, row in streams_gdf.iterrows():
                    if row.geometry is None:
                        continue
                    folium.GeoJson(
                        row.geometry.__geo_interface__,
                        style_function=lambda _: {
                            "color": "#1E90FF",
                            "weight": 2,
                            "fillOpacity": 0,
                        },
                    ).add_to(stream_group)
                stream_group.add_to(m)
        except Exception:
            pass

    # Layer 4: NYPAD protected lands (from cache)
    nypad_cache = CACHE_DIR / f"nypad_{lat:.4f}_{lon:.4f}.geojson"
    if nypad_cache.exists():
        try:
            nypad_gdf = gpd.read_file(nypad_cache)
            if len(nypad_gdf) > 0:
                nypad_group = folium.FeatureGroup(name="Protected Lands (NYPAD)")
                for _, row in nypad_gdf.iterrows():
                    if row.geometry is None:
                        continue
                    folium.GeoJson(
                        row.geometry.__geo_interface__,
                        style_function=lambda _: {
                            "fillColor": "#8A2BE2",
                            "color": "#5500AA",
                            "weight": 1,
                            "fillOpacity": 0.20,
                        },
                    ).add_to(nypad_group)
                nypad_group.add_to(m)
        except Exception:
            pass

    # Layer 5: Assessed location marker
    cvi = cvi_result["cvi"]
    priority_species = [s for s in species_list if s.get("priority") and not s.get("not_detected")]
    species_html = ""
    if priority_species:
        species_html = "<br><b>Priority species detected:</b><br>" + "<br>".join(
            f"&bull; {s['common_name']} ({s['status']})" for s in priority_species[:5]
        )

    popup_html = f"""
    <div style="font-family:sans-serif;min-width:200px">
      <b>{address}</b><br>
      <b>CVI Score:</b> {cvi}/100 {_bar(cvi)}<br>
      {species_html}
    </div>
    """

    folium.CircleMarker(
        location=[lat, lon],
        radius=8,
        color="#CC0000",
        fill=True,
        fill_color="#CC0000",
        fill_opacity=0.9,
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{address} — CVI: {cvi}",
    ).add_to(m)

    LayerControl(collapsed=False).add_to(m)

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", address).strip("_")
    out_path = OUTPUTS_DIR / f"{slug}_map.html"
    m.save(str(out_path))
    return str(out_path)
