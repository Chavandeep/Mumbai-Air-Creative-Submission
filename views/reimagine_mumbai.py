import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
from pyproj import Transformer

from modules import data_loader as L
from modules import scenario_simulator as sim
from visualizations import charts, maps, ui

ui.header("Experience 3 · Reimagine Mumbai", "What if we made different decisions?",
          "A scenario lab with two instruments. The first changes how much the city emits, by source. The second changes the city itself - parks, bus stops, density - "
          "and recomputes access on the real map. Neither predicts PM2.5.")
st.markdown(f"<p style='margin:.2rem 0 1rem 0'>{ui.tag('research')}{ui.tag('derived')}{ui.tag('hypo')}</p>", unsafe_allow_html=True)

tab_e, tab_p, tab_b, tab_d = st.tabs(["Emissions by source", "Build the planned parks", "Extend bus coverage", "Change development intensity"])

# ============================================================ emissions
with tab_e:
    a, b = st.columns([1, 1.5], gap="large")
    with a:
        inv = st.radio("Baseline inventory (research estimate)", list(sim.INVENTORIES), help="Two published inventories that count different particles. Try the same scenario on both.")
        I = sim.INVENTORIES[inv]
        preset = st.selectbox("Start from a scenario", list(sim.PRESETS))
        if st.session_state.get("_preset") != preset:
            st.session_state["_preset"] = preset
            for k, v in sim.PRESETS[preset].items():
                st.session_state[f"cut_{k}"] = v
        cuts = {}
        for k in sim.ACTIVE_LEVERS:
            sector, mx, name, what = sim.LEVERS[k]
            present = sector in I["shares"]
            cuts[k] = st.slider(f"{name}", 0, mx, key=f"cut_{k}", step=5, format="%d%% cut", disabled=not present,
                                help=f"Reduces '{sector}' emissions. {what}" + ("" if present else " This inventory does not list the sector separately."))
        green = st.slider("Greener Mumbai: extra tree and hedge cover", 0, 30, 0, 5, format="+%d%%", help="Deliberately has no effect on emitted mass - see the note.")
    with b:
        res = sim.run_emissions(inv, cuts)
        base, scen = res.baseline.sum(), res.scenario.sum()
        c = st.columns(3)
        with c[0]:
            ui.figure(f"{scen:.0f}", "emitted particle mass in your scenario, where today's inventory total = 100", "/ 100")
        with c[1]:
            ui.figure(f"−{100 * (base - scen) / base:.0f}%" if base - scen > 0.05 else "0%", "change in <b>emissions</b> counted by this inventory - not a change in PM2.5 in the air")
        with c[2]:
            top = res.assign(saved=res.baseline - res.scenario).sort_values("saved", ascending=False).iloc[0]
            ui.figure(top.sector if top.saved > 0 else "—", "the source contributing most of the reduction" if top.saved > 0 else "move a slider to begin")
        st.plotly_chart(charts.emissions_compare(res), config=charts.CFG, width="stretch")
        ui.note(f"Baseline shares: {I['citation']} Counted pollutant: {I['pollutant']}.")
        other = [k for k in sim.INVENTORIES if k != inv][0]
        r2 = sim.run_emissions(other, cuts)
        d1, d2 = 100 * (base - scen) / base, 100 * (r2.baseline.sum() - r2.scenario.sum()) / r2.baseline.sum()
        ui.body(f"<b>Uncertainty across inventories.</b> The same sliders cut emissions by <b>{d1:.0f}%</b> on this inventory and by <b>{d2:.0f}%</b> on the other "
                f"({other.split(' - ')[0]}). The gap is the point: which particles you count changes which intervention looks biggest.")
        if green:
            ui.body(f"<b>Greener Mumbai (+{green}% cover): 0 change to emitted mass.</b> {sim.GREEN_NOTE}")
    with st.expander("Assumptions, and why this is not a PM2.5 forecast", expanded=True):
        st.markdown("""
- **Each slider scales one sector's emissions** in the chosen inventory by the percentage shown. Sectors are independent; there is no rebound, no growth in activity, no interaction.
- **Baseline shares are research estimates** from 2019-20 studies. They are not measurements, they predate current fleet and construction activity, and the two inventories count different particle sizes.
- **Emissions are not concentrations.** A 30% cut in what Mumbai emits does not produce a 30% cut in PM2.5 at a monitor, because part of the PM2.5 over the city is blown in from outside it, part forms in the air from gases, and dispersion depends on weather. In this app's own record, the monsoon months show how strongly weather alone moves PM2.5.
- **Coarse is not fine.** Road and construction dust dominate total PM but contribute less to PM2.5. A dust programme can cut PM10 sharply while PM2.5 moves little.
- **No atmospheric model is used**, because the permitted data contain no gridded emissions, traffic or chemistry to drive one. Converting these scenarios to µg/m³ would need a dispersion or chemical-transport model and receptor-based source apportionment for Mumbai.
- **Slider ranges** are bounded by the control levels discussed in the NEERI-IIT Bombay action plan (for example 50% control of construction dust, 100% control of landfill burning); they are upper bounds on ambition, not predictions of what policy will achieve.
""")

b_pts, parks, sites = L.buildings_points(), L.table("parks.csv"), L.table("dp_open_space_sites.csv")
W = L.table("ward_indicators.csv")
nm = W.set_index("ward").ward_name if not W.empty else {}

# ============================================================ parks
with tab_p:
    if b_pts.empty or sites.empty:
        ui.missing("Building and Development Plan data")
    else:
        a, b = st.columns([1, 1.6], gap="large")
        with a:
            ui.body(f"Mumbai's Development Plan 2034 reserves <b>{len(sites):,}</b> open-space plots of 500 m² or more that are not yet parks. What if the city built them, largest first?")
            share = st.slider("Share of reserved open-space plots built", 0, 100, 25, 5, format="%d%%")
            thr = st.radio("Walking distance that counts as access", [300, 500, 800], index=1, horizontal=True, format_func=lambda x: f"{x} m")
            r = sim.park_scenario(b_pts, parks, sites, share, thr)
            c = st.columns(2)
            with c[0]:
                ui.figure(f"{r['city_before']:.1f}%", f"of residential floor area within {thr} m of a mapped park today")
            with c[1]:
                ui.figure(f"{r['city_after']:.1f}%", f"in the scenario: {len(r['sites']):,} new parks, {r['area_ha']:,.0f} ha")
            ui.note("Derived: straight-line distance from each residential or mixed-use building to the nearest park point, weighted by floor area. Hypothetical: reserved plots become parks. "
                    "Many reservations are encumbered or occupied; this shows what the plan would deliver, not what is easy.")
        with b:
            wd = r["ward"].assign(ward_name=lambda x: x.ward.map(nm))
            st.plotly_chart(charts.before_after(wd, "ward_name", "before", "after", f"% of residential floor area within {thr} m of a park", top=14), config=charts.CFG, width="stretch")
        lay = [maps.wards_layer(L.geojson("wards.geojson")), maps.points_layer(parks, "parks", [47, 93, 80, 200], radius=45, prefix="Existing park", min_px=2, max_px=7)]
        if len(r["sites"]):
            s = r["sites"].assign(name=lambda x: x.description + " · " + (x.area_m2 / 1e4).round(2).astype(str) + " ha")
            lay.append(maps.points_layer(s, "new", [201, 138, 27, 235], radius=70, prefix="Hypothetical new park (DP 2034 reservation)", min_px=3, max_px=10, stroke=True))
        st.pydeck_chart(maps.deck(lay, maps.view(zoom=10)), height=460)
        ui.legend([("Existing mapped park", "#2F5D50"), ("Reservation built in this scenario", "#C98A1B")])
        ui.body("<b>Environmental implication.</b> More residents gain a nearby low-emission, cooler open space. This scenario does not estimate any change in PM2.5: parks are not an emission control.")

# ============================================================ bus
with tab_b:
    stops = L.table("best_stops.csv")
    if b_pts.empty or stops.empty:
        ui.missing("Building and bus-stop data")
    else:
        stops = stops[stops.kind == "stop"]
        a, b = st.columns([1, 1.6], gap="large")
        with a:
            ui.body("Where would new bus stops reach the most people who currently have none nearby? The app places each new stop in the 250 m cell with the most unserved residential floor area, one at a time.")
            n = st.slider("New BEST stops to place", 0, 150, 40, 10)
            thr = st.radio("Distance that counts as access", [300, 400, 500], index=1, horizontal=True, format_func=lambda x: f"{x} m", key="bus_thr")
            r = sim.bus_scenario(b_pts, stops, n, thr)
            c = st.columns(2)
            with c[0]:
                ui.figure(f"{r['city_before']:.1f}%", f"of residential floor area within {thr} m of a BEST stop today")
            with c[1]:
                ui.figure(f"{r['city_after']:.1f}%", f"with {len(r['new_xy'])} hypothetical stops")
            ui.note("A stop is not a service: the BEST layer has no routes or frequencies, so this measures proximity only. New stops are placed without checking whether a road reaches the cell.")
        with b:
            wd = r["ward"].assign(ward_name=lambda x: x.ward.map(nm))
            st.plotly_chart(charts.before_after(wd, "ward_name", "before", "after", f"% of residential floor area within {thr} m of a stop", top=14), config=charts.CFG, width="stretch")
        lay = [maps.wards_layer(L.geojson("wards.geojson")), maps.points_layer(stops, "bus", [42, 120, 214, 120], radius=22, prefix="Existing BEST stop", min_px=1.5, max_px=4)]
        if len(r["new_xy"]):
            lon, lat = Transformer.from_crs(32643, 4326, always_xy=True).transform(r["new_xy"][:, 0], r["new_xy"][:, 1])
            new = pd.DataFrame({"lon": lon, "lat": lat, "name": [f"Placement {i + 1}" for i in range(len(lon))]})
            lay.append(maps.points_layer(new, "new", [201, 138, 27, 240], radius=90, prefix="Hypothetical new stop", min_px=4, max_px=11, stroke=True))
        st.pydeck_chart(maps.deck(lay, maps.view(zoom=10)), height=460)
        ui.legend([("Existing BEST stop", "#2A78D6"), ("Hypothetical stop", "#C98A1B")])
        ui.body("<b>Environmental implication.</b> Shorter walks to a bus make low-emission trips more practical, which is the mechanism behind the 'cleaner mobility' slider. How many trips would actually shift is not known from this data.")

# ============================================================ intensity
with tab_d:
    if W.empty:
        ui.missing("Ward indicators")
    else:
        a, b = st.columns([1, 1.6], gap="large")
        with a:
            wn = st.selectbox("Ward", W.sort_values("ward_name").ward_name, index=3)
            chg = st.slider("Change in built floor area", -20, 60, 20, 5, format="%+d%%", help="For example, redevelopment at a higher floor space index.")
            ui.body("If a ward's floor area grows and each resident keeps today's floor space, more people share the same parks, streets and bus stops - unless amenities are added with the buildings.")
        with b:
            t = sim.intensity_scenario(W.set_index("ward_name").loc[wn], chg)
            t["change"] = 100 * (t.scenario / t.today - 1)
            st.dataframe(t.rename(columns={"indicator": "Indicator", "today": "Today (derived)", "scenario": "Scenario (hypothetical)", "unit": "Unit", "change": "Change"})
                         .style.format({"Today (derived)": "{:,.2f}", "Scenario (hypothetical)": "{:,.2f}", "Change": "{:+.0f}%"}), hide_index=True, width="stretch")
            ui.note("Arithmetic only. Assumes the ward keeps its present floor area per resident (2011 Census population) and that no parks, stops or roads are added. "
                    "It says nothing about emissions or PM2.5: denser wards can generate fewer vehicle trips per person if transit access is good, or more congestion if it is not.")
