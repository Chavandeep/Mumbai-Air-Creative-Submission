import pandas as pd
import pydeck as pdk
import streamlit as st

from config import AMBER, GREEN, SEQ
from modules import data_loader as L
from modules import geospatial_analysis as geo
from visualizations import charts, maps, ui

W = L.table("ward_indicators.csv")
ui.header("Mumbai urban equity explorer", "Twenty-four wards, one city, unequal access",
          "Compare any wards on what their residents can reach: parks, open space, buses, trains, schools, clinics. "
          "Every figure is derived from official BMC and OpenCity layers; none is a pollution measurement.")
if W.empty:
    ui.missing("Ward indicators")
    st.stop()
LAB = {k: v[0] for k, v in geo.WARD_INDICATORS.items()}
UNIT = {k: v[1] for k, v in geo.WARD_INDICATORS.items()}
names = W.sort_values("ward_name").ward_name.tolist()

# ---- map + indicator ---------------------------------------------------------------------------
c1, c2 = st.columns([1, 2.2], gap="large")
with c1:
    ind = st.selectbox("Map indicator", list(geo.WARD_INDICATORS), index=list(geo.WARD_INDICATORS).index("park_within_500m_pct"), format_func=LAB.get)
    picks = st.multiselect("Wards to compare (two or more)", names, default=["M / East", "H / West", "R / Central"] if {"M / East", "H / West", "R / Central"} <= set(names) else names[:3], max_selections=5)
    lo, hi = W.loc[W[ind].idxmin()], W.loc[W[ind].idxmax()]
    ui.figure(f"{hi[ind] / lo[ind]:.1f}×" if lo[ind] > 0 else "n/a", f"gap between the highest ward ({hi.ward_name}, {hi[ind]:,.1f}) and the lowest ({lo.ward_name}, {lo[ind]:,.1f}) · {UNIT[ind]}")
    ui.note("Population is the sum of BMC electoral-ward (prabhag) figures, which total 12,442,373 - the 2011 Census count. Per-resident indicators therefore describe 2011 residents and today's amenities.")
with c2:
    gj = L.geojson("wards.geojson")
    vals = W.set_index("ward")[ind]
    vmin, vmax = float(vals.min()), float(vals.max())
    cols, _ = maps.ramp(vals - vmin, alpha=200, vmax=max(vmax - vmin, 1e-9))  # stretch the ramp across the observed range
    cmap = dict(zip(vals.index, cols))
    nm = W.set_index("ward").ward_name
    sel_codes = set(W[W.ward_name.isin(picks)].ward)
    feats = []
    for f in gj["features"]:
        w = f["properties"]["ward"]
        feats.append({**f, "properties": {**f["properties"], "color": cmap.get(w, [200, 200, 200, 120]), "lw": 3.5 if w in sel_codes else 0.8,
                                         "tip": f"<b>{nm.get(w, w)}</b><br>{LAB[ind]}: <b>{vals.get(w, float('nan')):,.1f}</b> {UNIT[ind]}<br><span style='opacity:.7'>derived indicator</span>"}})
    layer = pdk.Layer("GeoJsonLayer", {"type": "FeatureCollection", "features": feats}, id="wards", filled=True, stroked=True, get_fill_color="properties.color",
                      get_line_color=[31, 35, 40, 230], get_line_width="properties.lw", line_width_units=pdk.types.String("pixels"), pickable=True, auto_highlight=True)
    st.pydeck_chart(maps.deck([layer], maps.view(zoom=9.9)), height=520)
    ui.ramp_legend(LAB[ind], f"{vmin:,.1f}", f"{vmax:,.1f} {UNIT[ind]}", SEQ)

if len(picks) < 2:
    st.warning("Choose at least two wards to compare.")
    st.stop()

# ---- comparison ----------------------------------------------------------------------------------
ui.section("Side by side", "Where each selected ward stands among all 24, indicator by indicator. Far left is the lowest value in the city, far right the highest.", kinds=["derived"])
PAL = ["#2A78D6", "#C26A12", "#8A4FB0", "#12A37A", "#6B6F76"]
prof_cols = ["pop_density_km2", "floor_area_ratio", "footprint_cover_pct", "parks_per_10k", "park_within_500m_pct", "open_space_existing_m2_pc",
             "best_within_400m_pct", "rail_within_1000m_pct", "schools_per_100k", "clinics_per_100k", "public_toilets_per_100k"]
st.plotly_chart(charts.ward_profile(geo.percentile_ranks(W, prof_cols), LAB, picks, PAL), config=charts.CFG, width="stretch")

t = W[W.ward_name.isin(picks)].set_index("ward_name").loc[picks]
show = ["population", "pop_density_km2", "buildings_per_km2", "footprint_cover_pct", "floor_area_ratio", "mean_storeys", "parks", "parks_per_10k", "park_within_500m_pct",
        "open_space_existing_m2_pc", "open_space_planned_m2_pc", "best_stops", "best_within_400m_pct", "rail_stations", "rail_within_1000m_pct", "schools", "hospitals", "clinics", "public_toilets", "dp_reservations"]
extra = {"best_stops": "BEST stops", "rail_stations": "Suburban stations inside the ward", "schools": "Schools", "hospitals": "Hospitals and maternity homes", "clinics": "Clinics and dispensaries",
         "public_toilets": "Public toilets", "dp_reservations": "Development Plan 2034 reservations"}
tbl = t[show].T
tbl.index = [f"{LAB.get(c, extra.get(c, c))}" + (f" ({UNIT[c]})" if c in UNIT else "") for c in show]
city = pd.Series({c: (W[c].sum() if c in ("population", "parks", "best_stops", "rail_stations", "schools", "hospitals", "clinics", "public_toilets", "dp_reservations") else float((W[c] * W.population).sum() / W.population.sum())) for c in show})
tbl["All Mumbai"] = city.values
COUNTS = {"population", "parks", "best_stops", "rail_stations", "schools", "hospitals", "clinics", "public_toilets", "dp_reservations", "pop_density_km2", "buildings_per_km2"}
txt = tbl.copy().astype(object)
for lab_, c_ in zip(tbl.index, show):
    txt.loc[lab_] = [f"{v:,.0f}" if c_ in COUNTS else f"{v:,.1f}" for v in tbl.loc[lab_]]
txt.index.name = "Indicator"
st.dataframe(txt, width="stretch", height=735, column_config={"Indicator": st.column_config.Column(width="large")})
ui.note("'All Mumbai' is a total for counts and a population-weighted average for rates. Access shares weight each residential or mixed-use building by its floor area (footprint × recorded storeys) as a stand-in for where people live.")

a, b = st.columns(2)
mix = L.table("ward_building_mix.csv")
with a:
    ui.sub("What the buildings are used for", kinds=["derived"])
    if not mix.empty:
        m = mix[(mix.dimension == "usage")].merge(W[["ward", "ward_name"]], on="ward")
        m = m[m.ward_name.isin(picks)]
        order = ["Residential", "Mixed", "Commercial", "Industrial", "Religious", "Other / not surveyed"]
        colr = {k: f"rgb({v[0]},{v[1]},{v[2]})" for k, v in maps.USAGE_RGB.items()}
        st.plotly_chart(charts.stacked_share(m, "value", "footprint_m2", "ward_name", order, colr, 90 + 46 * len(picks)), config=charts.CFG, width="stretch")
with b:
    ui.sub("How tall they are", "Share of buildings with a recorded storey count.", kinds=["derived"])
    if not mix.empty:
        m = mix[(mix.dimension == "storeys")].merge(W[["ward", "ward_name"]], on="ward")
        m = m[m.ward_name.isin(picks)]
        order = ["1 (ground only)", "2", "3-4", "5-7", "8-14", "15+"]
        st.plotly_chart(charts.stacked_share(m, "value", "buildings", "ward_name", order, dict(zip(order, SEQ[1:])), 90 + 46 * len(picks), "% of buildings"), config=charts.CFG, width="stretch")

dps = L.table("dp_ward_summary.csv")
if not dps.empty:
    ui.sub("Existing designations vs planned reservations (Development Plan 2034)", "Land already designated for each public purpose, and land the plan reserves for it in future, per resident.", kinds=["derived"])
    code = W.set_index("ward_name").ward
    cats = ["Open space", "Education", "Health", "Housing", "Transport", "Social amenities"]
    cols_ = st.columns(len(picks))
    for col_, wn in zip(cols_, picks):
        g = dps[(dps.ward == code[wn]) & dps.category.isin(cats)]
        p = g.pivot_table(index="category", columns="status", values="area_m2", aggfunc="sum").reindex(cats).fillna(0) / W.set_index("ward_name").loc[wn, "population"]
        p.columns = [c.split(" (")[0] for c in p.columns]
        with col_:
            st.markdown(f"<p class='h3'>{wn}</p>", unsafe_allow_html=True)
            st.dataframe(p.style.format("{:.2f}"), width="stretch")
    ui.note("m² per resident. The Development Plan layer (last edited 30 Jun 2021) records designated amenities and reservations only - it is not a full existing-land-use map, and a reservation is an intention, not a built facility.")

# ---- city-wide inequality --------------------------------------------------------------------
ui.section("How unequal is access across the city?", "For each amenity: the population-weighted Gini coefficient across wards (0 = every resident's ward has the same, 1 = one ward has everything), and the wards at each end.", kinds=["derived"])
eq = geo.equity_table(W)
a, b = st.columns([1, 1.3])
with a:
    st.plotly_chart(charts.hbar(eq, "gini", "label", color=AMBER, unit="Gini coefficient across wards", fmt=".2f", height=330), config=charts.CFG, width="stretch")
with b:
    st.dataframe(eq[["label", "unit", "lowest_ward", "lowest", "highest_ward", "highest", "city"]].rename(columns={"label": "Indicator", "unit": "Unit", "lowest_ward": "Lowest ward", "lowest": "Value", "highest_ward": "Highest ward", "highest": "Value ", "city": "City average"})
                 .style.format({"Value": "{:,.1f}", "Value ": "{:,.1f}", "City average": "{:,.1f}"}), hide_index=True, width="stretch")
low = W.nsmallest(5, "park_within_500m_pct")[["ward_name", "park_within_500m_pct", "parks_per_10k", "open_space_existing_m2_pc", "open_space_planned_m2_pc"]]
ui.sub("Wards with the lowest mapped park access")
st.dataframe(low.rename(columns={"ward_name": "Ward", "park_within_500m_pct": "Homes within 500 m of a park (%)", "parks_per_10k": "Parks per 10,000 residents",
                                 "open_space_existing_m2_pc": "Designated open space (m² per resident)", "open_space_planned_m2_pc": "Planned open space (m² per resident)"})
             .style.format({c: "{:.1f}" for c in ["Homes within 500 m of a park (%)", "Parks per 10,000 residents", "Designated open space (m² per resident)", "Planned open space (m² per resident)"]}), hide_index=True, width="stretch")
ui.note("Ward-level PM2.5 is deliberately absent. Four live monitors, or 29 archived ones, cannot support a pollution value for each of 24 wards, so this app does not assign one. "
        "'Mapped parks' are points in BMC's parks layer; a ward can have large unmapped green areas (national park, mangroves, private grounds).")
