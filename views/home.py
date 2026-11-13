import streamlit as st

from modules import air_quality_analysis as aq
from modules import data_loader as L
from visualizations import charts, ui

d = L.pm25()
w = L.table("ward_indicators.csv")
inv = L.inventory()

ui.header("Mumbai · The air we build", "Understanding how the city we build shapes the air we breathe.",
          "Most air-quality tools show you a number. This one puts that number back into the city that produced it: "
          "300,000 buildings, 5,000 km of streets, every bus stop, park and planned reservation - next to 48,000 hours of measured PM2.5.", hero=True)

if d.empty:
    ui.missing("The PM2.5 record")
    st.stop()

s = aq.station_summary(d)
split = aq.space_time_split(d)
dd = aq.daily(d)

c = st.columns(4)
with c[0]:
    ui.figure(f"{len(aq.valid(d)):,}", f"valid station-hours of measured PM2.5, {d.ts.min():%b %Y} – {d.ts.max():%b %Y}, at four CPCB stations")
with c[1]:
    ui.figure(f"{s.pct_days_over_who.mean():.0f}%", "of monitored days exceeded the WHO 24-hour guideline of 15 µg/m³ (average of the four stations)")
with c[2]:
    ui.figure(f"{split['time_pct']:.0f}%", "of hour-to-hour PM2.5 variation is shared by all four stations at once - weather and season, not neighbourhood")
with c[3]:
    ui.figure(f"{inv.get('bmc_buildings', {}).get('used', 0):,}", "building footprints, with storeys and use, behind every urban-form indicator in this app")

ui.section("The record at a glance", "Seven-day rolling median of daily mean PM2.5 at the four stations. Every monsoon the air clears; "
           "every dry season it does not. Gaps are real gaps in the record - nothing is filled in.", kinds=["measured"])
st.plotly_chart(charts.daily_trend(dd, sorted(d.station.unique()), 7, 380), config=charts.CFG, width="stretch")

ui.section("Six ways in")
ROUTES = [
    ("Explore the city", "views/explore_city.py", "A layered map: stations, streets by carriageway width, rail, bus stops, parks, built form and the 2034 Development Plan. Click a station for its record and surroundings."),
    ("3D Mumbai", "views/city_3d.py", "Buildings extruded by their recorded storeys around each monitor or across any ward, with roads, rail, parks and water."),
    ("Understand the pollution", "views/understand_pollution.py", "When the air is worst, what the sources are according to published inventories, and what the surroundings of 25 stations can and cannot explain."),
    ("Urban equity", "views/equity_explorer.py", "Compare any wards on parks, transit, open space and civic amenities per resident."),
    ("Reimagine Mumbai", "views/reimagine_mumbai.py", "A scenario lab: cut emissions by source, build out planned parks, add bus stops, change development intensity - with assumptions on show."),
    ("What should Mumbai do next?", "views/recommendations.py", "Evidence-linked interventions, their limits, and the five to prioritise."),
]
cols = st.columns(3)
for i, (t, p, txt) in enumerate(ROUTES):
    with cols[i % 3]:
        st.markdown(f"<hr class='rule-ink'><p class='h3'>{t}</p><p class='body' style='min-height:5.6rem'>{txt}</p>", unsafe_allow_html=True)
        st.page_link(p, label=f"Open {t.lower().rstrip('?')} →")

ui.section("How to read this app", "Four kinds of number appear, and they are never mixed without a label.")
c = st.columns(4)
KINDS = [("measured", "A reading from a CPCB monitor. Only organiser-flagged instrument artefacts above 1,000 µg/m³ are excluded."),
         ("derived", "Computed here from official BMC or OpenCity geometry - for example, the share of homes within 500 m of a park."),
         ("research", "A figure from a published emission inventory or study, cited where it appears."),
         ("hypo", "The result of a what-if you set. It describes the scenario, not a prediction of Mumbai's air.")]
for col, (k, txt) in zip(c, KINDS):
    with col:
        st.markdown(f"{ui.tag(k)}<p class='note' style='margin-top:.5rem'>{txt}</p>", unsafe_allow_html=True)
