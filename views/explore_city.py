import pandas as pd
import streamlit as st

from config import AQI_BANDS, SEQ, STATION_COLORS
from modules import air_quality_analysis as aq
from modules import data_loader as L
from visualizations import charts, maps, ui

d = L.pm25()
st4 = L.table("stations.csv")
s24 = L.table("stations_2024.csv")
buf = L.table("station_buffers.csv")
grid = L.table("grid_500m.parquet")

ui.header("Experience 1 · Explore the city", "One map, the whole urban system",
          "Switch layers on and off to see where Mumbai's infrastructure, built form and air-quality monitors overlap. "
          "Station colours are measured PM2.5; everything else is official city geometry or an indicator derived from it.")
if d.empty or st4.empty:
    ui.missing("The station record")
    st.stop()

GRID = {"None": None,
        "Building footprint cover": ("cover_pct", "% of land"),
        "Built floor area ratio": ("far", "floor m² per land m²"),
        "Mean storeys": ("mean_storeys", "storeys"),
        "Road network density": ("road_km_km2", "km per km²"),
        "Distance to nearest park": ("d_park", "m"),
        "Distance to nearest BEST stop": ("d_stop", "m"),
        "Distance to nearest suburban station": ("d_rail", "m")}

left, right = st.columns([1, 3.1], gap="large")
with left:
    ui.sub("Air quality")
    lo, hi = d.date.min().date(), d.date.max().date()
    period = st.slider("Period for station colours", lo, hi, (lo, hi), format="MMM YYYY", help="Stations are coloured by their median PM2.5 over this period.")
    show_arch = st.toggle("2024 archive stations", True, help="Smaller markers: median PM2.5 for calendar 2024 from the XKDR archive in AdditionalHistory.zip.")
    ui.sub("Transport")
    t_road = st.toggle("Streets ≥ 9 m carriageway", True)
    t_rail = st.toggle("Suburban rail and stations", True)
    t_metro = st.toggle("Metro, monorail, all rail", False, help="Every line in BMC's base-layer railway dataset, including monorail and metro alignments.")
    t_bus = st.toggle("BEST bus stops", False)
    ui.sub("Urban development")
    gsel = st.selectbox("Built-form grid (500 m cells)", list(GRID), index=1)
    t_dp = st.toggle("Plan 2034: other plots", False, help="Development Plan 2034 housing, transport and municipal-service plots: existing designations (green) and planned reservations (amber).")
    ui.sub("Natural environment")
    t_parks = st.toggle("Mapped parks and gardens", False)
    t_os = st.toggle("Open space: now vs planned", False, help="Development Plan 2034: existing designated open space (green) against reserved open-space plots that are not yet parks (amber).")
    t_water = st.toggle("Lakes and water bodies", True)
    t_wards = st.toggle("Ward boundaries", True)

v = aq.valid(d)
v = v[(v.date >= pd.Timestamp(period[0])) & (v.date <= pd.Timestamp(period[1]))]
med = v.groupby("station")["pm25"].median()
st4 = st4.assign(value=st4.station.map(med))

layers, grid_hi = [], None
if gsel != "None" and not grid.empty:
    col, unit = GRID[gsel]
    gl, grid_hi = maps.grid_layer(grid, col, gsel, unit)
    layers.append(gl)
if t_water:
    layers.append(maps.water_layer(L.geojson("water.geojson")))
dp = L.table("dp_polygons.parquet")
if t_os and not dp.empty:
    layers.append(maps.dp_layer(dp[dp.category == "Open space"], "dp_os"))
if t_dp and not dp.empty:
    layers.append(maps.dp_layer(dp[dp.category != "Open space"], "dp_other"))
if t_wards:
    layers.append(maps.wards_layer(L.geojson("wards.geojson")))
if t_road:
    r = L.table("streets_wide.parquet")
    layers.append(maps.paths_layer(r, "roads", [70, 70, 78, 130], width_col="width", min_px=1,
                                   tip=lambda x: ["<b>" + (n or "Street") + f"</b><br>Carriageway {w:.0f} m · BMC street network" for n, w in zip(x.name, x.width)]))
if t_metro:
    layers.append(maps.paths_layer(L.table("rail_bmc.parquet"), "rail_bmc", [120, 80, 150, 200], width=1.5))
if t_rail:
    layers.append(maps.paths_layer(L.table("rail_suburban.parquet"), "rail", [31, 35, 40, 230], width=2.5, tip=lambda x: ["<b>" + n.title() + "</b><br>Suburban rail" for n in x.name]))
    layers.append(maps.points_layer(L.table("rail_stations.csv"), "rail_st", [31, 35, 40, 255], radius=90, prefix="Suburban station", min_px=3, max_px=7, stroke=True))
if t_bus:
    b = L.table("best_stops.csv")
    layers.append(maps.points_layer(b[b.kind == "stop"], "bus", [42, 120, 214, 150], radius=22, prefix="BEST stop", min_px=1.5, max_px=5))
if t_parks:
    layers.append(maps.points_layer(L.table("parks.csv"), "parks", [47, 93, 80, 220], radius=45, prefix="Park / garden", min_px=2.5, max_px=8))
if show_arch and not s24.empty:
    layers.append(maps.station_layers(s24, "median_2024", "st_2024", radius=220, period="Calendar 2024 · archive"))
layers.append(maps.station_layers(st4, "value", "st_target", radius=480, period=f"{period[0]:%b %Y} – {period[1]:%b %Y}"))
layers.append(maps.station_labels(st4))

with right:
    ev = st.pydeck_chart(maps.deck(layers, maps.view()), height=640, on_select="rerun", selection_mode="single-object", key="explore_map")
    ui.legend([(f"{n} ({int(lo_)}–{int(hi_)})" if hi_ < 1e6 else f"{n} (250+)", c) for lo_, hi_, n, c in AQI_BANDS])
    ui.note("Station colours use the CPCB National AQI bands for PM2.5 (µg/m³, defined for 24-hour means; applied here to the period median). "
            "Large ringed markers: the four target stations. Small markers: 2024 archive stations.")
    if grid_hi:
        ui.ramp_legend(gsel, "0", f"{grid_hi:,.0f}+ {GRID[gsel][1]}", SEQ)
    if t_os:
        ui.legend([("Existing designated open space", "#2F5D50"), ("Planned open-space reservation (not yet a park)", "#C98A1B")], "sq")

# ---- station panel --------------------------------------------------------------------------------
picked = None
try:
    obj = ev.selection.objects.get("st_target", [])
    if obj:
        picked = obj[0].get("station")
except Exception:
    picked = None
names = sorted(d.station.unique())
if picked in names and st.session_state.get("_map_pick") != picked:  # apply a map click once, then let the selector lead
    st.session_state["_map_pick"] = picked
    st.session_state["station_pick"] = picked

ui.section("Station file", "Click one of the four ringed stations on the map, or choose it here.")
c1, c2 = st.columns([1.3, 2])
with c1:
    sel = st.selectbox("Monitoring station", names, key="station_pick")
with c2:
    comp = st.multiselect("Compare with", [n for n in names if n != sel], default=[n for n in names if n != sel])

summ = aq.station_summary(d).set_index("station")
row, meta = summ.loc[sel], st4.set_index("station").loc[sel]
c = st.columns(4)
with c[0]:
    ui.figure(f"{row.latest:.0f}", f"Latest observation, hour ending {row.latest_ts:%d %b %Y %H:%M} IST", "µg/m³")
with c[1]:
    ui.figure(f"{row['median']:.0f}", f"Median hourly PM2.5 across the record (mean {row['mean']:.0f})", "µg/m³")
with c[2]:
    ui.figure(f"{row.pct_days_over_naaqs:.0f}%", f"of {row.days} monitored days above India's 24-hour standard of 60 µg/m³")
with c[3]:
    ui.figure(f"{row.completeness_pct:.0f}%", f"of hours have a valid reading; {row.flagged_hours} flagged artefacts excluded")
ui.note(f"{sel} · {meta.latitude:.4f}° N, {meta.longitude:.4f}° E · BMC ward {meta.ward} · coordinates from Stations.csv")

tab1, tab2, tab3 = st.tabs(["Trend", "Daily and weekly rhythm", "Surroundings"])
with tab1:
    win = st.radio("Smoothing", [1, 7, 30], index=1, horizontal=True, format_func=lambda x: {1: "Daily means", 7: "7-day rolling median", 30: "30-day rolling median"}[x])
    st.plotly_chart(charts.daily_trend(aq.daily(d), [sel] + comp, win), config=charts.CFG, width="stretch")
with tab2:
    a, b = st.columns(2)
    with a:
        ui.sub("By hour of day", kinds=["measured"])
        st.plotly_chart(charts.diurnal_lines(aq.diurnal(d), [sel] + comp), config=charts.CFG, width="stretch")
    with b:
        ui.sub("By day of week", "Dots are the median daily mean; bars are a 90% bootstrap interval. Overlapping bars mean no reliable weekday difference.", kinds=["measured"])
        st.plotly_chart(charts.dow_chart(aq.dow_profile(d), [sel] + comp), config=charts.CFG, width="stretch")
with tab3:
    if buf.empty:
        ui.missing("Station surroundings")
    else:
        rad = st.radio("Buffer radius around the station", sorted(buf.radius_m.unique()), index=2, horizontal=True, format_func=lambda r: f"{r} m")
        b4 = buf[(buf.network == "target_2025_2026") & (buf.radius_m == rad)].set_index("station")
        show = {"footprint_cover_pct": "Building footprint cover (% of land)", "floor_area_ratio": "Built floor area ratio", "road_km_per_km2": "Road density (km per km²)",
                "wide_road_km_per_km2": "Roads ≥ 12 m (km per km²)", "best_stops": "BEST stops", "parks": "Mapped parks", "open_space_pct": "Designated open space (% of land)",
                "industrial_footprint_pct": "Industrial share of footprint (%)", "under_construction_buildings": "Buildings recorded under construction",
                "dist_rail_station_m": "Distance to suburban station (m)", "dist_park_m": "Distance to nearest park (m)", "dist_wide_road_m": "Distance to a ≥ 12 m road (m)"}
        t = b4[list(show)].rename(columns=show).T
        t = t[[sel] + [c_ for c_ in t.columns if c_ != sel]]
        st.dataframe(t.style.format("{:,.1f}"), width="stretch")
        ui.note("Derived from BMC building footprints, BMC street network, OpenCity parks, BEST stops and rail stations, and Development Plan 2034 open-space designations, "
                "within the buffer clipped to land inside BMC limits. Carriageway width is recorded for only about a third of street length, so wide-road figures are lower bounds. "
                "With four stations these differences describe each monitor's setting; they cannot show what causes its readings.")
