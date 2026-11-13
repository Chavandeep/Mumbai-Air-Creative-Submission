"""Sanity checks on data/processed. Run after build_processed.py:  python scripts/validate.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules import scenario_simulator as sim  # noqa: E402

P = Path(__file__).resolve().parents[1] / "data" / "processed"
ok = True


def check(name, cond):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


t = pd.read_parquet(P / "pm25_hourly.parquet")
check("48,400 station-hours, 4 stations", len(t) == 48400 and t.station.nunique() == 4)
check("no negative or missing PM2.5", (t.pm25 >= 0).all() and t.pm25.notna().all())
check("no duplicate station-hours", not t.duplicated(["station", "ts"]).any())
check("flagged hours are exactly those above 1,000", ((t.pm25 > 1000) == t.flag_high_1000).all())
w = pd.read_csv(P / "ward_indicators.csv")
check("24 wards", len(w) == 24)
check("ward population sums to prabhag total 12,442,373", int(w.population.sum()) == 12442373)
check("percentages within 0-100", all(w[c].between(0, 100).all() for c in w.columns if c.endswith("_pct")))
check("every ward has buildings, roads and a 3D file", (w.buildings > 0).all() and (w.road_km > 0).all() and all((P / "buildings" / f"ward_{c}.parquet").exists() for c in w.ward))
b = pd.read_parquet(P / "buildings_points.parquet")
check("building count matches ward totals", len(b) == int(w.buildings.sum()))
check("storeys between 1 and 80 where known", b.floors.dropna().between(1, 80).all())
s = pd.read_csv(P / "station_buffers.csv")
check("4 target + archive stations x 4 radii", (s.groupby("sid").size() == 4).all() and (s.network == "target_2025_2026").sum() == 16)
st = pd.read_csv(P / "stations.csv")
raw = Path(P.parent / "raw" / "Stations.csv")
if raw.exists():
    r = pd.read_csv(raw)
    check("station coordinates identical to Stations.csv", np.allclose(st.sort_values("location_id")[["latitude", "longitude"]], r.sort_values("location_id")[["latitude", "longitude"]]))
for k, v in sim.INVENTORIES.items():
    check(f"inventory shares sum to 100: {k[:28]}", abs(sum(v["shares"].values()) - 100) < 0.05)
r = sim.run_emissions(list(sim.INVENTORIES)[0], sim.PRESETS["Today (no change)"])
check("no-change scenario equals baseline", np.allclose(r.baseline, r.scenario))
r = sim.run_emissions(list(sim.INVENTORIES)[0], dict(road_dust=50))
check("50% road-dust cut halves only road dust", abs(r.set_index("sector").scenario["Road dust"] - 35.86) < 0.01 and np.allclose(r[r.sector != "Road dust"].baseline, r[r.sector != "Road dust"].scenario))
sys.exit(0 if ok else 1)
