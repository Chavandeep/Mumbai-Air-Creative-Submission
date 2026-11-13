"""Derived spatial indicators: station surroundings vs measured PM2.5, and ward equity metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from scipy.stats import spearmanr

# indicator -> (label, unit, why it might matter)
BUFFER_INDICATORS = {
    "footprint_cover_pct": ("Building footprint cover", "% of land", "Dense built form traps air and concentrates activity"),
    "floor_area_ratio": ("Built floor area ratio", "floor m2 per land m2", "More floor space means more people, trips and deliveries"),
    "road_km_per_km2": ("Road network density", "km per km2", "More road length means more traffic and resuspended dust"),
    "wide_road_km_per_km2": ("Wide roads (>= 12 m carriageway)", "km per km2", "Arterials carry the heaviest traffic"),
    "best_stops": ("BEST bus stops", "count", "A proxy for bus activity and street-level footfall"),
    "parks": ("Mapped parks", "count", "Vegetated, low-emission land"),
    "open_space_pct": ("Designated open space", "% of land", "Development Plan open-space land"),
    "industrial_footprint_pct": ("Industrial building share", "% of footprint", "Local combustion and process emissions"),
    "under_construction_buildings": ("Buildings under construction", "count", "Construction dust (as recorded in the tax register)"),
}
POINT_INDICATORS = {
    "dist_wide_road_m": ("Distance to a wide road", "m"),
    "dist_rail_station_m": ("Distance to a suburban rail station", "m"),
    "dist_park_m": ("Distance to a mapped park", "m"),
}


@st.cache_data(show_spinner=False)
def station_associations(buffers: pd.DataFrame, s24: pd.DataFrame, min_coverage: float = 0.6) -> pd.DataFrame:
    """Spearman rank correlation between each surrounding indicator and the station's 2024 median
    PM2.5, for every buffer radius, with a bootstrap 90% interval. n is small (about 25 stations):
    this is a screen for spatial association, not evidence of cause."""
    s = s24[s24.coverage_2024 >= min_coverage][["sid", "median_2024"]]
    m = buffers[buffers.network == "archive_2024"].merge(s, on="sid")
    rng = np.random.default_rng(11)
    rows = []
    for r, g in m.groupby("radius_m"):
        for col, (lab, unit, _) in BUFFER_INDICATORS.items():
            x, y = g[col].values, g["median_2024"].values
            if np.nanstd(x) == 0:
                continue
            rho, p = spearmanr(x, y)
            bs = []
            for _ in range(600):
                i = rng.integers(0, len(x), len(x))
                if np.std(x[i]) > 0 and np.std(y[i]) > 0:
                    bs.append(spearmanr(x[i], y[i])[0])
            rows.append({"radius_m": r, "indicator": col, "label": lab, "rho": rho, "p": p, "n": len(x),
                         "lo": np.quantile(bs, 0.05), "hi": np.quantile(bs, 0.95)})
    return pd.DataFrame(rows)


def station_scatter(buffers: pd.DataFrame, s24: pd.DataFrame, radius: int, min_coverage: float = 0.6) -> pd.DataFrame:
    s = s24[s24.coverage_2024 >= min_coverage][["sid", "median_2024", "coverage_2024"]]
    return buffers[(buffers.network == "archive_2024") & (buffers.radius_m == radius)].merge(s, on="sid")


# ---- ward equity ---------------------------------------------------------------------------------
# column -> (label, unit, direction: +1 higher is better access, -1 lower is better, 0 descriptive)
WARD_INDICATORS = {
    "population": ("Population (Census 2011)", "people", 0),
    "pop_density_km2": ("Population density", "people per km2", 0),
    "buildings_per_km2": ("Building density", "buildings per km2", 0),
    "footprint_cover_pct": ("Building footprint cover", "% of ward", 0),
    "floor_area_ratio": ("Built-up intensity (floor area ratio)", "floor m2 per land m2", 0),
    "mean_storeys": ("Mean storeys (footprint-weighted)", "storeys", 0),
    "parks": ("Mapped parks", "count", 1),
    "parks_per_10k": ("Parks per 10,000 residents", "per 10k", 1),
    "park_within_500m_pct": ("Homes within 500 m of a park", "% of residential floor area", 1),
    "open_space_existing_m2_pc": ("Designated open space", "m2 per resident", 1),
    "open_space_planned_m2_pc": ("Planned open space (DP 2034 reservations)", "m2 per resident", 1),
    "best_within_400m_pct": ("Homes within 400 m of a BEST stop", "% of residential floor area", 1),
    "best_stops_per_10k": ("BEST stops per 10,000 residents", "per 10k", 1),
    "rail_within_1000m_pct": ("Homes within 1 km of a suburban station", "% of residential floor area", 1),
    "road_km_per_km2": ("Road network density", "km per km2", 0),
    "schools_per_100k": ("Schools", "per 100k residents", 1),
    "clinics_per_100k": ("Clinics and dispensaries", "per 100k residents", 1),
    "public_toilets_per_100k": ("Public toilets", "per 100k residents", 1),
}
EQUITY_SET = ["parks_per_10k", "park_within_500m_pct", "open_space_existing_m2_pc", "best_within_400m_pct",
              "rail_within_1000m_pct", "schools_per_100k", "clinics_per_100k", "public_toilets_per_100k"]


def gini(x, w=None) -> float:
    """Population-weighted Gini coefficient (0 = every resident has the same, 1 = one ward has all)."""
    x = np.asarray(x, float)
    w = np.ones_like(x) if w is None else np.asarray(w, float)
    o = np.argsort(x)
    x, w = x[o], w[o]
    cw, cxw = np.cumsum(w), np.cumsum(x * w)
    if cxw[-1] == 0:
        return 0.0
    lor = np.r_[0, cxw / cxw[-1]]
    pw = np.r_[0, cw / cw[-1]]
    return float(1 - np.sum((pw[1:] - pw[:-1]) * (lor[1:] + lor[:-1])))


def equity_table(w: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in EQUITY_SET:
        lab, unit, _ = WARD_INDICATORS[c]
        lo, hi = w.loc[w[c].idxmin()], w.loc[w[c].idxmax()]
        rows.append({"indicator": c, "label": lab, "unit": unit, "gini": gini(w[c], w.population),
                     "lowest_ward": lo.ward_name, "lowest": lo[c], "highest_ward": hi.ward_name, "highest": hi[c],
                     "city": float(np.average(w[c], weights=w.population))})
    return pd.DataFrame(rows)


def percentile_ranks(w: pd.DataFrame, cols) -> pd.DataFrame:
    """Each ward's rank position (0-100) among the 24 wards for each indicator."""
    return w.set_index("ward_name")[list(cols)].rank(pct=True) * 100
