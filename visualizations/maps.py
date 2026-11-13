"""pydeck layer builders. Every layer is drawn from a processed, documented dataset."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pydeck as pdk

from config import SEQ, band

BASEMAP = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
MUMBAI = dict(latitude=19.075, longitude=72.88, zoom=10.2)
USAGE_RGB = {"Residential": [196, 178, 148], "Commercial": [201, 138, 27], "Mixed": [140, 122, 160],
             "Industrial": [178, 58, 46], "Religious": [42, 120, 214], "Other / not surveyed": [176, 172, 162]}


def hex_rgb(h, a=255):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [a]


def ramp(values: pd.Series, alpha=170, vmax=None):
    """Sequential colour for each value (one hue, light -> dark), clipped at the 97th percentile."""
    v = values.astype(float)
    hi = vmax or float(np.nanquantile(v, 0.97)) or 1.0
    t = np.clip(v / hi, 0, 1).fillna(0).values
    stops = np.array([hex_rgb(c)[:3] for c in SEQ], float)
    pos = t * (len(SEQ) - 1)
    i = np.clip(pos.astype(int), 0, len(SEQ) - 2)
    f = (pos - i)[:, None]
    rgb = stops[i] * (1 - f) + stops[i + 1] * f
    return [list(map(int, c)) + [alpha] for c in rgb], hi


def view(lat=None, lon=None, zoom=None, pitch=0, bearing=0):
    return pdk.ViewState(latitude=lat or MUMBAI["latitude"], longitude=lon or MUMBAI["longitude"], zoom=zoom or MUMBAI["zoom"], pitch=pitch, bearing=bearing)


def wards_layer(gj, filled=False):
    return pdk.Layer("GeoJsonLayer", gj, id="wards", stroked=True, filled=filled, get_fill_color=[0, 0, 0, 0], get_line_color=[90, 90, 90, 150],
                     line_width_min_pixels=1, pickable=False)


def water_layer(gj):
    return pdk.Layer("GeoJsonLayer", gj, id="water", stroked=False, filled=True, get_fill_color=[126, 170, 196, 190], pickable=False)


def grid_layer(grid: pd.DataFrame, col: str, label: str, unit: str, extruded=False, elevation_scale=1.0):
    g = grid.dropna(subset=[col]).copy()
    g["color"], hi = ramp(g[col])
    g["tip"] = [f"<b>{label}</b><br>{v:,.1f} {unit}<br><span style='opacity:.7'>500 m cell · derived indicator</span>" for v in g[col]]
    g["elev"] = g[col].astype(float)
    return pdk.Layer("PolygonLayer", g[["polygon", "color", "tip", "elev"]], id="grid", get_polygon="polygon", get_fill_color="color", stroked=False,
                     extruded=extruded, get_elevation="elev", elevation_scale=elevation_scale, pickable=True, auto_highlight=True), hi


def paths_layer(df, lid, color, width_col=None, width=2, tip=None, min_px=1):
    d = df.copy()
    d["tip"] = tip if isinstance(tip, str) else (tip(d) if tip else "")
    if width_col:
        d["w"] = d[width_col].fillna(width).astype(float)
    return pdk.Layer("PathLayer", d, id=lid, get_path="path", get_color=color, get_width="w" if width_col else width, width_units=pdk.types.String("meters" if width_col else "pixels"),
                     width_min_pixels=min_px, pickable=bool(tip), cap_rounded=True, joint_rounded=True)


def points_layer(df, lid, color, radius=40, tip_col="name", prefix="", min_px=2, max_px=10, stroke=False):
    d = df.copy()
    d["tip"] = [f"<b>{prefix}</b><br>{n}" if prefix else f"{n}" for n in d[tip_col]] if tip_col in d else prefix
    return pdk.Layer("ScatterplotLayer", d, id=lid, get_position=["lon", "lat"], get_fill_color=color, get_radius=radius, radius_min_pixels=min_px,
                     radius_max_pixels=max_px, stroked=stroke, get_line_color=[247, 244, 238], line_width_min_pixels=1, pickable=True)


def dp_layer(dp: pd.DataFrame, lid="dp"):
    d = dp.copy()
    planned = d.status.str.startswith("Planned")
    d["color"] = [[201, 138, 27, 150] if p else [47, 93, 80, 150] for p in planned]
    d["tip"] = [f"<b>{s}</b><br>{c}: {de}<br>{a:,.2f} ha · Development Plan 2034" for s, c, de, a in zip(d.status, d.category, d.description, d.area_ha)]
    return pdk.Layer("PolygonLayer", d[["polygon", "color", "tip"]], id=lid, get_polygon="polygon", get_fill_color="color", get_line_color=[60, 60, 60, 120],
                     line_width_min_pixels=0.5, stroked=True, pickable=True)


def station_layers(st: pd.DataFrame, value_col: str, lid: str, radius=420, label="PM2.5", period=""):
    """Monitoring stations coloured by the CPCB AQI band of a MEASURED median."""
    d = st.dropna(subset=[value_col]).copy()
    d["color"] = [hex_rgb(band(v)[1], 235) for v in d[value_col]]
    d["tip"] = [f"<b>{n}</b><br>Median PM2.5 <b>{v:.0f} µg/m³</b> · {band(v)[0]}<br><span style='opacity:.7'>{period} · measured</span>" for n, v in zip(d.station, d[value_col])]
    return pdk.Layer("ScatterplotLayer", d, id=lid, get_position=["longitude", "latitude"], get_fill_color="color", get_radius=radius, radius_min_pixels=7 if radius > 300 else 5,
                     radius_max_pixels=26, stroked=True, get_line_color=[31, 35, 40], line_width_min_pixels=2 if radius > 300 else 1, pickable=True, auto_highlight=True)


def station_labels(st: pd.DataFrame):
    d = st.copy()
    d["short"] = d.station.str.split(" - ").str[0]
    return pdk.Layer("TextLayer", d, id="station_labels", get_position=["longitude", "latitude"], get_text="short", get_size=13, get_color=[31, 35, 40],
                     get_pixel_offset=[0, -22], font_family="Inter, Arial, sans-serif", font_weight=600, background=True, get_background_color=[247, 244, 238, 215],
                     background_padding=[4, 2], pickable=False)


def buildings_layer(b: pd.DataFrame, colour_by="usage", storey_m=3.0):
    d = b.copy()
    known = d.floors.notna()
    d["elev"] = (d.floors.fillna(0) * storey_m).astype(float)
    if colour_by == "storeys":
        cols, _ = ramp(d.floors.fillna(0), alpha=235, vmax=20)
        d["color"] = [c if k else [205, 202, 194, 200] for c, k in zip(cols, known)]
    else:
        d["color"] = [USAGE_RGB.get(u, USAGE_RGB["Other / not surveyed"]) + [235] if k else [205, 202, 194, 200] for u, k in zip(d.usage, known)]
    d["tip"] = [f"<b>{t or 'Building'}</b> · {u}<br>" + (f"{int(f)} storey{'s' if f != 1 else ''} (BMC record)" if k else "Storeys not recorded - drawn flat")
                for t, u, f, k in zip(d.type, d.usage, d.floors.fillna(0), known)]
    return pdk.Layer("PolygonLayer", d[["polygon", "elev", "color", "tip"]], id="buildings", get_polygon="polygon", extruded=True, get_elevation="elev",
                     get_fill_color="color", stroked=False, pickable=True, auto_highlight=True, material=dict(ambient=0.55, diffuse=0.6, shininess=8))


def deck(layers, view_state, height=None):
    return pdk.Deck(layers=[l for l in layers if l is not None], initial_view_state=view_state, map_style=BASEMAP,
                    tooltip={"html": "{tip}", "style": {"backgroundColor": "#FFFFFF", "color": "#1F2328", "fontFamily": "Inter, Arial, sans-serif", "fontSize": "12px",
                                                        "border": "1px solid #D9D4C7", "borderRadius": "2px", "padding": "6px 8px"}})
