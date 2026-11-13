"""Scenario engines. Two different things live here and are never mixed:

1. An EMISSIONS scenario: published emission-inventory shares (research estimates) scaled by
   user-chosen reductions. The output is an index of emitted mass, not an ambient PM2.5 forecast.
2. URBAN-INDICATOR scenarios: derived access indicators recomputed on the real building, park
   and bus-stop geometry after a hypothetical change (new parks on Development Plan
   reservations, new bus stops in under-served cells, a change in development intensity).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from scipy.spatial import cKDTree

# ---- 1. emissions ----------------------------------------------------------------------------------
# Sector shares as published. Keys are the app's sector groups; "detail" keeps the source rows.
INVENTORIES = {
    "NEERI-IIT Bombay 2020 - total particulate matter (PM) load": {
        "pollutant": "Total PM emission load (dominated by coarse particles; not PM2.5-specific)",
        "citation": "CSIR-NEERI & IIT Bombay for Maharashtra Pollution Control Board, 'Air Quality and Emission Source "
                    "Apportionment Studies for Ten Cities of Maharashtra: Mumbai City', draft interim report, January 2020.",
        "url": "https://www.mcgm.gov.in/irj/go/km/docs/documents/MCGM%20Department%20List/Environment/Docs/04%20Source%20Apportionment%20Report-MCGM.pdf",
        "shares": {"Road dust": 71.72, "Construction": 11.17, "Transport exhaust": 4.77, "Waste burning": 3.69,
                   "Commercial and domestic fuel": 7.02, "Industry and power": 1.17, "Aircraft and shipping": 0.45},
        "detail": "Road dust = unpaved 45.09 + paved 26.63. Construction = construction activity 8.01 + Metro works road dust 3.16. "
                  "Transport exhaust = heavy diesel 3.32 + three-wheelers 1.08 + two-wheelers 0.16 + cars 0.14 + taxis 0.02 + CNG buses 0.05. "
                  "Waste burning = open and landfill burning 3.69. Commercial and domestic fuel = bakeries 3.52 + domestic 1.59 + restaurants 1.28 "
                  "+ crematoria 0.61 + open eat-outs 0.02. Industry and power = Tata Power 0.89 + large 0.22 + small/medium 0.06.",
    },
    "SAFAR-IITM 2019-20 - PM2.5 emissions": {
        "pollutant": "PM2.5 emissions (fine particles)",
        "citation": "SAFAR, Indian Institute of Tropical Meteorology, Mumbai emission inventory 2019-20, sector shares as reported "
                    "by The Times of India, 'Vehicle pollution doubled in 5 years in Mumbai, shows study', July 2021 (secondary source).",
        "url": "https://timesofindia.indiatimes.com/city/mumbai/vehicle-pollution-doubled-in-5-years-in-mumbai-shows-study/articleshow/83970799.cms",
        "shares": {"Transport exhaust": 30.5, "Waste burning": 21.5, "Industry and power": 18.0,
                   "Commercial and domestic fuel": 15.0, "Road dust": 15.0},
        "detail": "As reported: transport 30.5%, municipal waste 21.5%, industries and power 18%, residential burning 15%, wind-blown dust 15%. "
                  "Wind-blown dust is mapped to 'Road dust' here; the inventory does not list construction separately.",
    },
}

# lever -> (sector it acts on, max reduction of that sector's emissions the slider allows, what it means, evidence note)
LEVERS = {
    "mobility": ("Transport exhaust", 60, "Cleaner mobility",
                 "Fewer private-vehicle kilometres, more trips on rail, metro, bus and foot, cleaner fleets."),
    "construction": ("Construction", 80, "Better construction management",
                     "Site barriers and water misting, covered materials and trucks, wheel washing, debris removal."),
    "road_dust": ("Road dust", 70, "Road dust management",
                  "Wall-to-wall paving, mechanised sweeping and washing, prompt trench reinstatement."),
    "waste": ("Waste burning", 100, "No open or landfill burning",
              "Reliable collection, landfill fire control, enforcement against roadside burning."),
    "fuel": ("Commercial and domestic fuel", 90, "Clean fuel for bakeries, eateries and homes",
             "Wood and coal replaced with piped gas, LPG or electricity."),
    "industry": ("Industry and power", 60, "Cleaner industry and power", "Fuel switching and stack controls."),
}
ACTIVE_LEVERS = ["mobility", "construction", "road_dust", "waste", "fuel", "industry"]

# NEERI-IITB's own action-plan targets, used as the "official plan" preset (report, chapter 4)
PRESETS = {
    "Today (no change)": dict(mobility=0, construction=0, road_dust=0, waste=0, fuel=0, industry=0),
    "Cleaner mobility": dict(mobility=30, construction=0, road_dust=0, waste=0, fuel=0, industry=0),
    "Better construction management": dict(mobility=0, construction=50, road_dust=0, waste=0, fuel=0, industry=0),
    "Road dust management": dict(mobility=0, construction=0, road_dust=25, waste=0, fuel=0, industry=0),
    "Combined - NEERI-IITB long-term plan targets": dict(mobility=50, construction=50, road_dust=25, waste=100, fuel=50, industry=0),
}


def run_emissions(inventory: str, cuts: dict) -> pd.DataFrame:
    """Scale each sector by its reduction. Returns baseline and scenario shares (baseline total = 100)."""
    shares = INVENTORIES[inventory]["shares"]
    rows = []
    for sector, base in shares.items():
        cut = max([cuts.get(k, 0) for k in ACTIVE_LEVERS if LEVERS[k][0] == sector] or [0])
        rows.append({"sector": sector, "baseline": base, "cut_pct": cut, "scenario": base * (1 - cut / 100)})
    return pd.DataFrame(rows)


GREEN_NOTE = ("Vegetation is not modelled as an emission cut. Published reviews find that urban trees remove only a few "
            "percent or less of city-wide PM, and dense street trees can even trap exhaust in narrow street canyons. "
            "Their role here is as low-emission land, shade and buffers between roads and people.")


# ---- 2. urban indicators -----------------------------------------------------------------------------
def _access(bxy, w, pts, thr):
    d = cKDTree(pts).query(bxy)[0]
    return d, float(100 * w[d <= thr].sum() / w.sum())


@st.cache_data(show_spinner=False)
def park_scenario(b: pd.DataFrame, parks: pd.DataFrame, sites: pd.DataFrame, share: int, thr: int = 500) -> dict:
    """Build out the largest `share`% of Development Plan 2034 open-space reservations as parks and
    recompute the share of residential floor area within `thr` m of a park, by ward."""
    bxy, w = b[["x", "y"]].values, b["w"].values
    d0 = cKDTree(parks[["x", "y"]].values).query(bxy)[0]
    n = int(round(len(sites) * share / 100))
    new = sites.head(n)
    pts = np.vstack([parks[["x", "y"]].values, new[["x", "y"]].values]) if n else parks[["x", "y"]].values
    d1 = cKDTree(pts).query(bxy)[0]
    df = pd.DataFrame({"ward": b["ward"].values, "w": w, "in0": w * (d0 <= thr), "in1": w * (d1 <= thr)})
    g = df.groupby("ward").sum()
    ward = pd.DataFrame({"before": 100 * g.in0 / g.w, "after": 100 * g.in1 / g.w, "new_sites": new.groupby("ward").size()}).fillna({"new_sites": 0})
    return {"city_before": 100 * df.in0.sum() / w.sum(), "city_after": 100 * df.in1.sum() / w.sum(), "ward": ward.reset_index(),
            "sites": new, "area_ha": float(new.area_m2.sum() / 1e4)}


@st.cache_data(show_spinner=False)
def bus_scenario(b: pd.DataFrame, stops: pd.DataFrame, n_new: int, thr: int = 400) -> dict:
    """Greedy placement: put each new stop at the centre of the 250 m cell holding the most
    residential floor area that is still farther than `thr` m from any stop."""
    bxy, w = b[["x", "y"]].values, b["w"].values
    pts = stops[["x", "y"]].values
    d0 = cKDTree(pts).query(bxy)[0]
    d = d0.copy()
    cx, cy = (bxy[:, 0] // 250).astype(int), (bxy[:, 1] // 250).astype(int)
    new = []
    for _ in range(n_new):
        un = d > thr
        if not un.any():
            break
        cell = pd.DataFrame({"cx": cx[un], "cy": cy[un], "w": w[un]}).groupby(["cx", "cy"])["w"].sum()
        if cell.max() <= 0:
            break
        (bx, by) = cell.idxmax()
        p = np.array([bx * 250 + 125, by * 250 + 125], float)
        new.append(p)
        d = np.minimum(d, np.hypot(bxy[:, 0] - p[0], bxy[:, 1] - p[1]))
    df = pd.DataFrame({"ward": b["ward"].values, "w": w, "in0": w * (d0 <= thr), "in1": w * (d <= thr)})
    g = df.groupby("ward").sum()
    ward = pd.DataFrame({"before": 100 * g.in0 / g.w, "after": 100 * g.in1 / g.w}).reset_index()
    return {"city_before": 100 * df.in0.sum() / w.sum(), "city_after": 100 * df.in1.sum() / w.sum(), "ward": ward,
            "new_xy": np.array(new) if new else np.empty((0, 2))}


def intensity_scenario(row: pd.Series, change_pct: float) -> pd.DataFrame:
    """What a change in built floor area implies for per-person amenities in one ward, assuming the
    ward keeps today's floor area per resident and no amenities are added. Pure arithmetic."""
    f = 1 + change_pct / 100
    pop0 = row.population
    pop1 = pop0 * f
    items = [("Built floor area ratio", row.floor_area_ratio, row.floor_area_ratio * f, "floor m2 per land m2"),
             ("Residents (implied)", pop0, pop1, "people"),
             ("Parks per 10,000 residents", row.parks_per_10k, row.parks / pop1 * 1e4, "per 10k"),
             ("Designated open space", row.open_space_existing_m2_pc, row.open_space_existing_m2_pc / f, "m2 per resident"),
             ("BEST stops per 10,000 residents", row.best_stops_per_10k, row.best_stops / pop1 * 1e4, "per 10k"),
             ("Road length", row.road_km / pop0 * 1e4, row.road_km / pop1 * 1e4, "km per 10k residents")]
    return pd.DataFrame(items, columns=["indicator", "today", "scenario", "unit"])
