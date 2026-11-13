import pandas as pd
import streamlit as st

from config import AMBER, GREEN, INK, RED
from modules import air_quality_analysis as aq
from modules import data_loader as L
from modules import geospatial_analysis as geo
from modules import scenario_simulator as sim
from visualizations import charts, ui

d = L.pm25()
ui.header("Experience 2 · Understand the pollution", "Where it comes from, when it peaks, and what the city's shape can - and cannot - explain",
          "Three questions, answered with measurements where they exist and with cited research where they do not.")
if d.empty:
    ui.missing("The PM2.5 record")
    st.stop()
names = sorted(d.station.unique())
W = pd.DataFrame() if L.table("ward_indicators.csv").empty else L.table("ward_indicators.csv")

# ------------------------------------------------------------------ 1. WHEN
ui.section("1 · When is the air worst?", "Pollution in Mumbai keeps a clock and a calendar. Pick a station to see both at once: each cell is the median PM2.5 for that hour of day in that month.", kinds=["measured"])
sel = st.selectbox("Station", names, index=names.index("Shivaji Nagar - BMC") if "Shivaji Nagar - BMC" in names else 0)
m = aq.hour_month_matrix(d, sel)
st.plotly_chart(charts.heatmap(m, [c.strftime("%b %y") for c in m.columns], [f"{h:02d}" for h in m.index], "month", "hour", 420, zmax=float(min(m.max().max(), 150))), config=charts.CFG, width="stretch")
sr = aq.seasonal_ratio(d)
if {"Winter (Nov-Feb)", "Monsoon (Jun-Sep)"} <= set(sr.columns):
    ratio = (sr["Winter (Nov-Feb)"] / sr["Monsoon (Jun-Sep)"])
    ui.body(f"At {sel}, the median winter hour ({sr.loc[sel, 'Winter (Nov-Feb)']:.0f} µg/m³) carries <b>{ratio[sel]:.1f} times</b> the PM2.5 of the median monsoon hour "
            f"({sr.loc[sel, 'Monsoon (Jun-Sep)']:.0f} µg/m³). Across the four stations the ratio runs from {ratio.min():.1f} to {ratio.max():.1f}. "
            "The city's traffic, building sites and bakeries do not shut for the monsoon - rain and sea wind remove what they emit. Emissions set the supply; weather decides how much stays in the air.")

a, b = st.columns(2)
with a:
    ui.sub("The daily clock", "Median PM2.5 by hour of day, all four stations.", kinds=["measured"])
    st.plotly_chart(charts.diurnal_lines(aq.diurnal(d), names), config=charts.CFG, width="stretch")
with b:
    ui.sub("The weekly rhythm", "Median daily mean by weekday with a 90% bootstrap interval. Where intervals overlap, the data do not show a weekday effect.", kinds=["measured"])
    st.plotly_chart(charts.dow_chart(aq.dow_profile(d), names), config=charts.CFG, width="stretch")

ui.sub("Month by month", kinds=["measured"])
st.plotly_chart(charts.monthly_bars(aq.monthly(d), sel), config=charts.CFG, width="stretch")

ui.sub("Spikes and anomalies", "Each grey dot is one hourly reading. Red dots are spikes: at least three times the station's typical level for that month and hour, and above 100 µg/m³.", kinds=["measured"])
an = aq.anomalies(d)
st.plotly_chart(charts.anomaly_strip(an, sel), config=charts.CFG, width="stretch")
sp = an[an.spike].groupby("station").size().reindex(names).fillna(0).astype(int)
ep = aq.episodes(an)
c1, c2 = st.columns([1, 1.6])
with c1:
    st.plotly_chart(charts.hbar(sp.rename("hours").reset_index(), "hours", "station", color=RED, unit="spike hours", fmt=".0f", highlight=[sel]), config=charts.CFG, width="stretch")
with c2:
    e = ep[ep.station == sel].head(8)
    if e.empty:
        ui.note("No spike episodes at this station.")
    else:
        st.dataframe(e.assign(start=e.start.dt.strftime("%d %b %Y %H:00"), end=e.end.dt.strftime("%d %b %Y %H:00"))[["start", "end", "hours", "peak", "typical"]]
                     .rename(columns={"start": "Episode start", "end": "Episode end", "hours": "Spike hours", "peak": "Peak (µg/m³)", "typical": "Typical (µg/m³)"})
                     .style.format({"Peak (µg/m³)": "{:.0f}", "Typical (µg/m³)": "{:.0f}"}), hide_index=True, width="stretch")
ui.note(f"Readings above 1,000 µg/m³ ({int((~d.valid).sum())} hours, including values near 25,000 and 100,000) were flagged by the organisers as probable instrument artefacts and are excluded from every statistic. "
        "Spikes below that threshold are kept: some may be real local events such as fires, others unflagged faults. This record alone cannot tell them apart.")

# ------------------------------------------------------------------ 2. WHERE
ui.section("2 · Does the neighbourhood explain the reading?", "If built form drove PM2.5 directly, monitors in dense, road-heavy places would read consistently higher. Two tests.")
split = aq.space_time_split(d)
c = st.columns(3)
with c[0]:
    ui.figure(f"{split['time_pct']:.0f}%", "of hourly variation is <b>shared by all four stations at the same hour</b> - season, weather, city-wide load")
with c[1]:
    ui.figure(f"{split['place_pct']:.0f}%", "is a <b>persistent difference between stations</b> - the part a neighbourhood's character could explain")
with c[2]:
    ui.figure(f"{split['local_pct']:.0f}%", "is <b>local and short-lived</b> - events at one station and not the others")
ui.note(f"Two-way decomposition of log PM2.5 over the {split['hours']:,} hours when all four stations reported. Measured.")

buf, s24 = L.table("station_buffers.csv"), L.table("stations_2024.csv")
if not buf.empty and not s24.empty:
    ui.sub("Test with 25 stations: surroundings vs 2024 median PM2.5", "For each station in the 2024 archive with at least 60% of hours present, the app measures what lies within a buffer and ranks it against the station's median PM2.5. "
           "Change the radius to check whether any pattern survives.", kinds=["measured", "derived"])
    assoc = geo.station_associations(buf, s24)
    rad = st.radio("Buffer radius", sorted(assoc.radius_m.unique()), index=2, horizontal=True, format_func=lambda r: f"{r} m", key="assoc_r")
    a_, b_ = st.columns([1.25, 1])
    with a_:
        st.plotly_chart(charts.assoc_chart(assoc, rad), config=charts.CFG, width="stretch")
    with b_:
        ind = st.selectbox("Plot one indicator", list(geo.BUFFER_INDICATORS), format_func=lambda k: geo.BUFFER_INDICATORS[k][0])
        sc = geo.station_scatter(buf, s24, rad)
        st.plotly_chart(charts.scatter_xy(sc, ind, "median_2024", f"{geo.BUFFER_INDICATORS[ind][0]} ({geo.BUFFER_INDICATORS[ind][1]})", "2024 median PM2.5 (µg/m³)", "station", 320), config=charts.CFG, width="stretch")
    strongest = assoc.loc[assoc.rho.abs().idxmax()]
    crossing = int(((assoc.lo < 0) & (assoc.hi > 0)).sum())
    ui.body(f"<b>Finding: no clear spatial association.</b> The strongest rank correlation at any radius is ρ = {strongest.rho:+.2f} ({strongest.label.lower()}, {int(strongest.radius_m)} m), "
            f"and {crossing} of {len(assoc)} indicator-radius pairs have a 90% interval that includes zero. With {int(assoc.n.max())} stations, a real but modest effect could easily hide - "
            "but nothing here supports a claim such as 'more roads nearby means a dirtier monitor'. Regulatory monitors are also generally sited to represent neighbourhood background air rather than kerbsides, which mutes exactly the gradients a planner cares about.")
    ui.note("Correlation and spatial association are not causation. PM2.5 is a regional pollutant that mixes over kilometres within hours; the 2024 archive uses different averaging conventions from the 2025-26 record; "
            "surroundings are from 2023-2025 snapshots. Stations: CPCB/CAAQMS and US Embassy via the XKDR archive.")

# ------------------------------------------------------------------ 3. SOURCES
ui.section("3 · What are the sources?", "No monitor in this dataset can separate sources. For that the app relies on two published emission inventories - which disagree, instructively.", kinds=["research"])
inv = st.radio("Inventory", list(sim.INVENTORIES), horizontal=False)
I = sim.INVENTORIES[inv]
df = pd.DataFrame({"sector": list(I["shares"]), "share": list(I["shares"].values())})
a, b = st.columns([1.3, 1])
with a:
    st.plotly_chart(charts.hbar(df, "share", "sector", color=AMBER, unit="% of emitted mass", height=300), config=charts.CFG, width="stretch")
with b:
    ui.body(f"<b>What is counted:</b> {I['pollutant']}.")
    ui.note(I["detail"])
    ui.note(f"Source: {I['citation']} <a href='{I['url']}' target='_blank'>Link</a>")
ui.body("<b>Why they differ.</b> The first counts all particulate mass, which is dominated by coarse dust (PM10 and larger): by that measure road dust is nearly three-quarters of everything. "
        "The second counts only fine particles (PM2.5), which come mostly from burning fuel and waste, so exhaust and waste burning lead. Both can be true at once. "
        "A road-dust programme and a clean-fuel programme attack different particles, and neither inventory is a measurement of what people breathe: emissions are mass released, not concentration in the air.")

k = L.table("pm_2018_2020.parquet")
if not k.empty:
    r = aq.pm_ratio(k)
    ui.sub("How much of Mumbai's PM10 is PM2.5?", "The 2018-2020 archive is the only file here that records both sizes at the same stations. The ratio shows how much of the particle mass is fine.", kinds=["measured"])
    a, b = st.columns([1.3, 1])
    with a:
        st.plotly_chart(charts.hbar(r.assign(pct=100 * r.ratio), "pct", "station", color=INK, unit="PM2.5 as % of PM10 (ratio of medians)", fmt=".0f"), config=charts.CFG, width="stretch")
    with b:
        ui.figure(f"{100 * r.ratio.median():.0f}%", f"median across {len(r)} stations: fine particles are a minority of PM10 mass, the rest is coarse dust (2018-2020, {int(r.hours.sum()):,} paired hours)")
        ui.note("PM10 values are shown only in this chart. Every other measured chart in the app is PM2.5.")

# ------------------------------------------------------------------ mechanisms
ui.section("How city activity becomes particles", "Choose a theme to see the chain from activity to air, and what this app's data can say about it.")
THEMES = {
    "Transport and vehicle emissions": {
        "chain": ["Private vehicles, freight and buses in congested traffic", "Exhaust (mostly diesel soot) plus brake and tyre wear", "Fine particles, PM2.5 and smaller", "Highest at the kerb; mixes city-wide within hours"],
        "text": "Stop-start congestion raises emissions per kilometre, and a city built around private vehicles has more kilometres to begin with. Road design matters twice: wide arterials invite traffic, and continuous building walls beside them slow dispersion. "
                "Where rail and bus are within walking distance, the low-emission trip is the easy one.",
        "data": ("rail_within_1000m_pct", "Homes within 1 km of a suburban station (% of residential floor area)", GREEN),
        "gap": "No traffic counts, speeds or fleet data are in the permitted datasets, so congestion itself is not measured here."},
    "Construction and urban development": {
        "chain": ["Demolition, excavation, concrete batching, material trucks", "Mechanical dust, and soil tracked on to roads", "Mostly coarse particles (PM10), some PM2.5", "Very high next to the site, falling quickly with distance"],
        "text": "Construction dust is released close to the ground and close to homes. Uncovered trucks and unwashed wheels carry it on to streets where traffic keeps re-lifting it, so a building site quietly feeds the road-dust source too.",
        "data": ("under_construction_buildings", "Buildings recorded as under construction in BMC's property register", AMBER),
        "gap": "This is a tax-register status, not a measure of active sites, their size or their dust controls. No measured construction-activity data is available; treat this section as explanation, not measurement."},
    "Road dust": {
        "chain": ["Silt from worn surfaces, unpaved shoulders, trenches and debris", "Resuspension by tyres and vehicle wake", "Coarse particles (PM10) with a fine fraction", "Along every trafficked street, worst in dry months"],
        "text": "Road dust is recycled pollution: the same silt is lifted again and again until rain washes it away, which is one reason the monsoon months are so much cleaner. Potholes, dug-up footpaths and unpaved shoulders keep refilling the reservoir.",
        "data": ("road_km_per_km2", "Road network density (km of street per km²)", INK),
        "gap": "Silt loading and paving condition are not recorded. Carriageway width is known for about a third of street length."},
    "Industrial emissions": {
        "chain": ["Power generation, refineries, small industry, bakeries, crematoria", "Fuel combustion and process emissions", "Fine particles and gases that form particles downwind", "Tall stacks disperse regionally; small units vent at street level"],
        "text": "Large industry has shrunk inside the city and its tall stacks send emissions beyond city limits. What remains at breathing height are thousands of small combustion sources - wood-fired bakeries, eateries, crematoria - inside dense neighbourhoods.",
        "data": ("footprint_industrial_pct", "Industrial share of building footprint (%)", RED),
        "gap": "Building use shows where industrial premises are, not what or how much they burn."},
    "Green spaces and urban density": {
        "chain": ["Parks, trees and open land among dense buildings", "Leaves capture some particles; open land emits none", "Small effect on city-wide PM2.5", "Largest benefit is local: shade, space, distance from traffic"],
        "text": "Vegetation helps, but not the way it is often sold. Published reviews put city-wide particle removal by urban trees at a few percent or less, and a closed tree canopy over a narrow, busy street can trap exhaust below it. "
                "Green space matters because it is land that does not emit, it cools the city, and it puts distance between people and traffic. Density cuts both ways: it concentrates activity, but it also makes walking and transit workable. Planting cannot substitute for cutting emissions.",
        "data": ("park_within_500m_pct", "Homes within 500 m of a mapped park (% of residential floor area)", GREEN),
        "gap": "Parks are points without area or canopy cover; satellite vegetation indices were not used."},
}
t = st.radio("Theme", list(THEMES), horizontal=True, label_visibility="collapsed")
T = THEMES[t]
steps = ["Activity", "Emission process", "Particles", "Where it is felt"]
st.markdown("<div style='display:flex;gap:0;flex-wrap:wrap;margin:.6rem 0 1rem 0'>" + "".join(
    f"<div style='flex:1 1 11rem;border-top:2px solid #1F2328;padding:.55rem .9rem .2rem 0;margin-right:.9rem'><div style='font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6B6F76'>{i + 1} · {s}</div>"
    f"<div style='font-size:.95rem;line-height:1.4;margin-top:.25rem'>{txt}</div></div>" for i, (s, txt) in enumerate(zip(steps, T["chain"]))) + "</div>", unsafe_allow_html=True)
a, b = st.columns([1, 1.15])
with a:
    ui.body(T["text"])
    ui.note("<b>What the data cannot show:</b> " + T["gap"])
with b:
    col, lab, colr = T["data"]
    if not W.empty and col in W:
        ui.sub("What the city data shows, by ward", kinds=["derived"])
        st.plotly_chart(charts.hbar(W, col, "ward_name", color=colr, unit=lab, height=520), config=charts.CFG, width="stretch")
