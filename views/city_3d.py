import numpy as np
import pandas as pd
import streamlit as st

from config import SEQ
from modules import data_loader as L
from visualizations import maps, ui

ui.header("3D Mumbai", "The city as built",
          "Every block below is a real footprint from BMC's property register, raised by the number of storeys BMC records for it. "
          "Choose a monitoring station or a ward, then drag to orbit (right-drag or Ctrl-drag to tilt).")
st4, wards = L.table("stations.csv"), L.table("ward_indicators.csv")
if st4.empty or wards.empty:
    ui.missing("3D building data")
    st.stop()

c1, c2, c3 = st.columns([1.5, 1, 1])
with c1:
    mode = st.radio("View", ["Around a monitoring station (1.5 km)", "A whole ward", "Citywide built-form grid"], horizontal=False)
with c2:
    if mode.startswith("Around"):
        pick = st.selectbox("Station", sorted(st4.station))
    elif mode.startswith("A whole"):
        pick = st.selectbox("Ward", wards.sort_values("ward_name").ward_name, index=4)
    else:
        pick = st.selectbox("Column height shows", ["Built floor area ratio", "Mean storeys", "Building footprint cover"])
    colour = st.radio("Colour buildings by", ["Use", "Storeys"], horizontal=True, disabled=mode.startswith("City"))
with c3:
    ov = st.multiselect("Overlays", ["Streets", "Rail", "Parks", "Water", "Monitoring stations"], default=["Streets", "Rail", "Parks", "Water", "Monitoring stations"])
    pitch = st.slider("Tilt", 0, 60, 50, 5)

layers = []
if "Water" in ov:
    layers.append(maps.water_layer(L.geojson("water.geojson")))
if mode.startswith("City"):
    grid = L.table("grid_500m.parquet")
    col, unit, scale = {"Built floor area ratio": ("far", "floor m² per land m²", 900), "Mean storeys": ("mean_storeys", "storeys", 110), "Building footprint cover": ("cover_pct", "% of land", 45)}[pick]
    gl, hi = maps.grid_layer(grid, col, pick, unit, extruded=True, elevation_scale=scale)
    layers.append(gl)
    vs = maps.view(zoom=10.3, pitch=pitch, bearing=-15)
    b = pd.DataFrame()
else:
    if mode.startswith("Around"):
        r = st4.set_index("station").loc[pick]
        b = L.buildings_3d(f"station_{r.sid}")
        vs = maps.view(r.latitude, r.longitude, 14.4, pitch, -20)
    else:
        code = wards.set_index("ward_name").loc[pick].ward
        b = L.buildings_3d(f"ward_{code}")
        if not b.empty:
            c = np.array([p[0] for p in b.polygon])
            vs = maps.view(float(np.median(c[:, 1])), float(np.median(c[:, 0])), 13.2, pitch, -20)
    if b.empty:
        ui.missing("Building footprints for this selection")
        st.stop()
    layers.append(maps.buildings_layer(b, "storeys" if colour == "Storeys" else "usage"))
if "Streets" in ov:
    layers.append(maps.paths_layer(L.table("streets_wide.parquet"), "roads", [60, 60, 68, 200], width_col="width", min_px=1))
if "Rail" in ov:
    layers.append(maps.paths_layer(L.table("rail_suburban.parquet"), "rail", [31, 35, 40, 240], width=3))
    layers.append(maps.points_layer(L.table("rail_stations.csv"), "rail_st", [31, 35, 40, 255], radius=45, prefix="Suburban station", min_px=2, max_px=6, stroke=True))
if "Parks" in ov:
    layers.append(maps.points_layer(L.table("parks.csv"), "parks", [47, 93, 80, 235], radius=25, prefix="Park / garden", min_px=2, max_px=6))
if "Monitoring stations" in ov:
    d = L.pm25()
    med = d[d.valid].groupby("station")["pm25"].median()
    s = st4.assign(value=st4.station.map(med))
    layers.append(maps.station_layers(s, "value", "st_target", radius=60, period="Full record"))
    layers.append(maps.station_labels(s))

st.pydeck_chart(maps.deck(layers, vs), height=680)

if not b.empty:
    known = b.floors.notna()
    c = st.columns(4)
    with c[0]:
        ui.figure(f"{len(b):,}", "building footprints drawn")
    with c[1]:
        ui.figure(f"{100 * known.mean():.0f}%", "have a storey count in BMC's record; the rest are drawn flat in grey")
    with c[2]:
        ui.figure(f"{b.floors.median():.0f}", "median storeys (half of all buildings are this height or lower)")
    with c[3]:
        ui.figure(f"{int((b.floors >= 15).sum()):,}", "buildings of 15 storeys or more")
    if colour == "Storeys":
        ui.ramp_legend("Storeys", "1", "20+", SEQ)
    else:
        ui.legend([(k, f"rgb({v[0]},{v[1]},{v[2]})") for k, v in maps.USAGE_RGB.items()], "sq")
else:
    ui.ramp_legend(pick, "low", "high", SEQ)
ui.note("Heights are storeys × 3 m, a nominal storey height used only to draw the model; BMC records storeys, not metres. "
        "Buildings whose storey field is blank or unreadable are not given a guessed height. Building height is a measure of urban form - "
        "it is not a measurement of pollution, and tall does not mean dirty. Source: BMC SAC building footprints (ClimateVerse doi:10.71646/NVQWMN), last edited 18 Dec 2025.")
