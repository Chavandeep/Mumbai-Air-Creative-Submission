import json

import pandas as pd
import streamlit as st

from config import CV, NOT_USED, SOURCES
from modules import data_loader as L
from modules import facts, gemini_explainer
from visualizations import ui

ui.header("Data & methods", "What is measured, what is derived, and what is assumed",
          "Every dataset, its source and persistent identifier, how it was cleaned, and the limits of what it can support.")
inv = L.inventory()
t1, t2, t3, t4, t5 = st.tabs(["Sources", "Data quality", "Data dictionary", "Method and limits", "Ask the data (Gemini)"])

with t1:
    df = pd.DataFrame(SOURCES, columns=["Dataset", "Publisher", "doi", "Access", "Last updated", "Licence", "Used for"])
    df["ClimateVerse record"] = [CV + x if isinstance(x, str) else None for x in df.doi]
    st.dataframe(df.drop(columns="doi"), hide_index=True, width="stretch", height=495,
                 column_config={"ClimateVerse record": st.column_config.LinkColumn(display_text=r"https://doi\.org/(.*)")})
    ui.sub("Catalogued but not used")
    st.dataframe(pd.DataFrame(NOT_USED, columns=["Dataset", "ClimateVerse DOI", "Why"]), hide_index=True, width="stretch")
    ui.note("Rules check. The challenge permits the core Zindi dataset and datasets on ClimateVerse's Google Air Quality Forecasting Challenge page. Every layer here comes from one of those two places. "
            "The BMC layers carry no stated licence; ClimateVerse catalogues them and refers to the source for terms, so they are used here with attribution for a non-commercial competition entry and are not redistributed in raw form. "
            "Two contextual research figures (emission-inventory shares) come from published reports outside ClimateVerse and are labelled as research estimates wherever they appear. "
            "The base map is CARTO Positron on OpenStreetMap data, used only as a visual backdrop. Google Earth Engine was not used: it needs authenticated project access that was not available for this build.")

with t2:
    tr = inv.get("train", {})
    if tr:
        c = st.columns(4)
        with c[0]:
            ui.figure(f"{tr['records']:,}", "station-hours in Train.csv, zero missing values, zero duplicate station-hours")
        with c[1]:
            ui.figure(f"{tr['flag_high_1000']}", "hours above 1,000 µg/m³, flagged by the organisers and excluded from statistics")
        with c[2]:
            ui.figure(f"{100 * tr['three_reading_hours'] / tr['records']:.0f}%", "of hours built from three quarter-hour readings rather than four")
        with c[3]:
            ui.figure(f"{100 * min(tr['completeness'].values()):.0f}–{100 * max(tr['completeness'].values()):.0f}%", "of hours present per station between first and last timestamp")
    rows = []
    for k, v in inv.items():
        if isinstance(v, dict) and "records" in v:
            rows.append({"Dataset": k, "Records": v["records"], "Used": v.get("used", v.get("records_used", "")), "Geometry": ", ".join(v.get("geometry", [])),
                         "Null geometry": v.get("null_geometry", ""), "Invalid geometry (repaired)": v.get("invalid_geometry", ""),
                         "Duplicates": v.get("duplicate_footprints_removed", v.get("duplicate_geometry", v.get("duplicate_coordinates", v.get("duplicate_station_hours", "")))),
                         "Outside BMC limits": v.get("outside_bmc_limits", v.get("outside_ward_polygons", ""))})
    st.dataframe(pd.DataFrame(rows).astype(str), hide_index=True, width="stretch", height=560)
    b = inv.get("bmc_buildings", {})
    s = inv.get("bmc_streets", {})
    if b and s:
        ui.note(f"Buildings: {b['records']:,} footprints downloaded; {b['demolished_excluded']:,} marked demolished and {b['duplicate_footprints_removed']:,} exact duplicate footprints removed; storeys parsed for {b['floors_parsed']:,} "
                f"and left unknown for {b['floors_unparsed']:,}. Streets: {s['total_km']:,.0f} km, of which {s['km_with_carriageway_width']:,.0f} km carry a carriageway width. "
                "Parks: 4 of 991 points fall outside the city or have no coordinates and are dropped. BEST: 684 stops lie outside BMC limits and are excluded from ward indicators.")

with t3:
    DD = [
        ("pm25_hourly", "ts", "Hour-ending timestamp, IST (UTC+05:30)", "Measured"), ("pm25_hourly", "pm25", "Hourly PM2.5 concentration, µg/m³, mean of 3-4 valid quarter-hour readings", "Measured"),
        ("pm25_hourly", "count", "Number of valid quarter-hour readings in the hour (3 or 4)", "Measured"), ("pm25_hourly", "flag_high_1000", "Organiser flag for values above 1,000 µg/m³; excluded from statistics", "Source flag"),
        ("pm25_2024_hourly", "pm25", "Hourly PM2.5 from the XKDR archive (CPCB/AirNow), calendar 2024; averaging not aligned to the 2025-26 record", "Measured"),
        ("pm_2018_2020", "pm25, pm10", "Hourly PM2.5 and PM10, µg/m³, ten stations", "Measured"),
        ("ward_indicators", "population", "Sum of prabhag populations in the ward (totals to Census 2011)", "Source"),
        ("ward_indicators", "footprint_cover_pct", "Building footprint area ÷ ward area × 100", "Derived"),
        ("ward_indicators", "floor_area_ratio", "Σ (footprint × storeys) ÷ ward area; buildings without storeys contribute nothing, so this is a lower bound", "Derived"),
        ("ward_indicators", "mean_storeys", "Footprint-weighted mean storeys of buildings with a recorded count", "Derived"),
        ("ward_indicators", "parks_per_10k", "Mapped park points ÷ population × 10,000", "Derived"),
        ("ward_indicators", "park_within_500m_pct", "Share of residential + mixed floor area whose building centroid is within 500 m (straight line) of a park point", "Derived"),
        ("ward_indicators", "best_within_400m_pct", "Same, within 400 m of a BEST stop", "Derived"), ("ward_indicators", "rail_within_1000m_pct", "Same, within 1 km of a suburban station (including stations just outside BMC limits)", "Derived"),
        ("ward_indicators", "road_km_per_km2", "Street centreline length ÷ ward area", "Derived"), ("ward_indicators", "open_space_existing_m2_pc", "Development Plan 'existing open space' designations ÷ population", "Derived"),
        ("ward_indicators", "open_space_planned_m2_pc", "Development Plan open-space reservations ÷ population", "Derived"),
        ("grid_500m", "cover_pct, far, mean_storeys, road_km_km2", "The same indicators on a 500 m grid, denominators clipped to land inside BMC limits", "Derived"),
        ("station_buffers", "*", "Indicators within 250, 500, 1,000 and 2,000 m of each monitoring station", "Derived"),
        ("buildings/*", "floors", "Storeys parsed from BMC's free-text field ('G+7' → 8). Unparseable → unknown", "Source, parsed"),
    ]
    st.dataframe(pd.DataFrame(DD, columns=["Table", "Field", "Definition", "Class"]), hide_index=True, width="stretch", height=700)

with t4:
    st.markdown("""
**Air quality.** Hourly values are used exactly as supplied. The only exclusion is the organisers' flag for readings above 1,000 µg/m³. No value is interpolated, smoothed or gap-filled; rolling medians skip gaps. Daily means need at least 18 valid hours. Medians are preferred to means because a handful of extreme hours dominate the mean. Exceedance counts compare daily means with India's 24-hour standard (60 µg/m³) and the WHO 2021 guideline (15 µg/m³).

**Anomalies.** An hour's 'typical' level is the station's median for that calendar month and hour of day. A spike is at least 3× typical and at least 100 µg/m³. Spikes within three hours are merged into episodes.

**Space and time.** The split of variance into shared-by-time, between-station and local parts is a two-way decomposition of log PM2.5 over hours when all four stations report.

**Station surroundings.** Buffers of 250 m to 2 km are clipped to land inside BMC limits. Association with 2024 median PM2.5 uses Spearman rank correlation across the archive stations with at least 60% of hours, with a 600-replicate bootstrap interval. The whole analysis is repeated at each radius as a sensitivity check.

**Access indicators.** Each residential or mixed-use building is weighted by its floor area as a proxy for residents. Distances are straight-line to the nearest point feature, not walking routes, so real access is lower than shown.

**Scenarios.** Emission scenarios scale published sector shares; urban scenarios recompute access indicators on the real geometry after a hypothetical change. Neither produces a concentration.

**Limits to keep in mind**
- Four live stations and 29 archived series cannot describe pollution in each of 24 wards; no ward-level PM2.5 is shown anywhere.
- Population is 2011 Census; buildings are 2025; streets 2023; the Development Plan layer 2021. Per-resident figures mix those dates.
- Parks are points with no area; bus stops have no routes or frequency; carriageway width is missing for two-thirds of street length.
- There is no measured traffic, construction activity, industrial fuel use or meteorology in this build, so sources are described from published research, not observed.
- Emission-inventory shares are 2019-20 estimates. One is quoted from a draft interim report, the other through a newspaper account of the original.

**References**
- CSIR-NEERI and IIT Bombay (2020), *Air Quality and Emission Source Apportionment Studies for Ten Cities of Maharashtra: Mumbai City*, draft interim report for Maharashtra Pollution Control Board.
- SAFAR, Indian Institute of Tropical Meteorology, Mumbai emission inventory 2019-20, as reported by *The Times of India*, July 2021.
- World Health Organization (2021), *WHO global air quality guidelines*. Central Pollution Control Board (2009), National Ambient Air Quality Standards; (2014) National Air Quality Index.
- Nowak, Crane and Stevens (2006), 'Air pollution removal by urban trees and shrubs in the United States', *Urban Forestry & Urban Greening*; Abhijith et al. (2017), 'Air pollution abatement performances of green infrastructure in open road and built-up street canyon environments - a review', *Atmospheric Environment*.
""")

with t5:
    F = facts.build()
    ui.body("Ask a question in plain language. Gemini writes the answer, but it is given only the fact sheet below - numbers this app has already computed - and is instructed never to add a figure or claim a cause.")
    key = gemini_explainer.api_key()
    q = st.text_input("Your question", placeholder="Which station is most polluted, and how sure can we be about why?", disabled=not key)
    ex = st.pills("Or try", ["Why is winter worse than the monsoon?", "Does living near big roads mean dirtier air here?", "Which wards have the least park access?", "What would cutting road dust do?"], disabled=not key)
    question = q or ex
    if not key:
        st.info("Gemini is switched off in this deployment because no `GEMINI_API_KEY` is set. Add one in Streamlit secrets to enable it (free key from Google AI Studio). Everything else in the app works without it.")
    elif question:
        with st.spinner("Asking Gemini…"):
            try:
                st.markdown(f"<hr class='rule-ink'><p class='body'>{gemini_explainer.ask(question, F)}</p>", unsafe_allow_html=True)
                ui.note(f"Written by Gemini ({gemini_explainer.model()}) from the fact sheet below. Check any figure against the sheet.")
            except Exception as e:  # network, quota or model errors must not break the page
                st.error(f"Gemini could not answer just now ({type(e).__name__}). The fact sheet below still has the numbers.")
    with st.expander("The fact sheet Gemini is given"):
        st.code(json.dumps(F, indent=1, default=str), language="json")
