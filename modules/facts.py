"""One deterministic fact sheet, computed from the processed data. It feeds the recommendation
evidence strings and is the only thing Gemini is allowed to quote."""
from __future__ import annotations

import numpy as np
import streamlit as st

from modules import air_quality_analysis as aq
from modules import data_loader as L
from modules import geospatial_analysis as geo
from modules import scenario_simulator as sim


@st.cache_data(show_spinner=False)
def build() -> dict:
    d, w = L.pm25(), L.table("ward_indicators.csv")
    inv = L.inventory()
    neeri = sim.INVENTORIES["NEERI-IIT Bombay 2020 - total particulate matter (PM) load"]["shares"]
    safar = sim.INVENTORIES["SAFAR-IITM 2019-20 - PM2.5 emissions"]["shares"]
    f: dict = {"road_dust_pm": neeri["Road dust"], "construction_pm": neeri["Construction"], "bakery_pm": 3.52, "industry_pm": neeri["Industry and power"],
               "hddv_share": 100 * 3.32 / neeri["Transport exhaust"], "transport_pm25": safar["Transport exhaust"], "waste_pm25": safar["Waste burning"]}
    if not d.empty:
        s = aq.station_summary(d)
        a = aq.anomalies(d)
        sp = a[a.spike].groupby("station").size().reindex(s.station).fillna(0).astype(int)
        split = aq.space_time_split(d)
        f.update({"time_pct": split["time_pct"], "place_pct": split["place_pct"], "local_pct": split["local_pct"], "flagged": int((~d.valid).sum()),
                  "sn_spike_hours": int(sp.get("Shivaji Nagar - BMC", 0)), "other_spike_max": int(sp.drop("Shivaji Nagar - BMC", errors="ignore").max()),
                  "stations": {r.station: {"median_pm25": round(r["median"], 1), "mean_pm25": round(r["mean"], 1), "pct_days_over_india_24h_standard_60": round(r.pct_days_over_naaqs, 1),
                                           "pct_days_over_who_24h_guideline_15": round(r.pct_days_over_who, 1), "latest_pm25": round(r.latest, 1), "latest_time_ist": str(r.latest_ts),
                                           "spike_hours": int(sp[r.station])} for _, r in s.iterrows()},
                  "record": {"start": str(d.ts.min()), "end": str(d.ts.max()), "valid_station_hours": int(d.valid.sum())},
                  "seasonal_median_pm25": aq.seasonal_ratio(d).round(1).to_dict("index")})
    if not w.empty:
        pop = w.population

        def city(c):
            return float(np.average(w[c], weights=pop))

        def ext(c, lo=True):
            r = w.loc[w[c].idxmin() if lo else w[c].idxmax()]
            return float(r[c]), r.ward_name
        f.update({"road_km": float(w.road_km.sum()), "width_known": 100 * inv.get("bmc_streets", {}).get("km_with_carriageway_width", 0) / max(inv.get("bmc_streets", {}).get("total_km", 1), 1),
                  "uc_buildings": int(w.under_construction_buildings.sum()), "uc_top": ", ".join(w.nlargest(3, "under_construction_buildings").ward_name),
                  "best_city": city("best_within_400m_pct"), "rail_city": city("rail_within_1000m_pct"), "park_city": city("park_within_500m_pct"),
                  "population_census_2011": int(pop.sum()), "buildings": int(w.buildings.sum()), "parks_mapped": int(w.parks.sum())})
        for k, c in [("rail", "rail_within_1000m_pct"), ("park", "park_within_500m_pct")]:
            f[f"{k}_low"], f[f"{k}_low_ward"] = ext(c)
            f[f"{k}_high"], f[f"{k}_high_ward"] = ext(c, False)
        f["equity"] = geo.equity_table(w).round(2).drop(columns="indicator").to_dict("records")
    sites, parks, b = L.table("dp_open_space_sites.csv"), L.table("parks.csv"), L.buildings_points()
    if not sites.empty and not b.empty:
        r = sim.park_scenario(b, parks, sites, 100)
        f.update({"dp_sites": len(sites), "park_after": r["city_after"]})
    buf, s24 = L.table("station_buffers.csv"), L.table("stations_2024.csv")
    if not buf.empty and not s24.empty:
        a = geo.station_associations(buf, s24)
        f.update({"n_assoc": int(a.n.max()), "max_rho": float(a.rho.abs().max())})
    f["published_inventories"] = {k: {"pollutant": v["pollutant"], "shares_pct": v["shares"], "citation": v["citation"]} for k, v in sim.INVENTORIES.items()}
    return f
