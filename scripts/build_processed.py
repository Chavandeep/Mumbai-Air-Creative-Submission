"""Build every processed dataset the app loads, from data/raw only.

Run:  python scripts/build_processed.py
Inputs : data/raw/Train.csv, Stations.csv, additional_history/*, bmc/*.geojsonl, opencity/*.kml
Outputs: data/processed/*  (small, app-ready; committed to the repository)

Value classes used throughout the project
  MEASURED  - CPCB/CAAQMS PM2.5 observations (never altered, only flagged)
  DERIVED   - spatial indicators computed here from BMC / OpenCity geometry
Nothing in this script is simulated, interpolated or gap-filled.
"""
from __future__ import annotations

import json
import re
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Point, box
from shapely.ops import unary_union

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "buildings").mkdir(exist_ok=True)
UTM = 32643  # WGS84 / UTM 43N, metres - the CRS BMC itself publishes in
RADII = [250, 500, 1000, 2000]
WIDE_M = 12  # carriageway width (m) treated as a "wide road"
STOREY_M = 3.0  # nominal storey height used ONLY to draw 3D extrusions
INVENTORY: dict = {}


def log(*a):
    print(*a, flush=True)


def bmc(key: str) -> gpd.GeoDataFrame:
    g = gpd.read_file(RAW / "bmc" / f"{key}.geojsonl")
    INVENTORY[f"bmc_{key}"] = {
        "records": int(len(g)),
        "geometry": sorted(g.geom_type.dropna().unique().tolist()),
        "null_geometry": int(g.geometry.isna().sum()),
        "invalid_geometry": int((~g.geometry.dropna().is_valid).sum()),
        "duplicate_geometry": int(g.geometry.dropna().to_wkb().duplicated().sum()),
        "fields": [c for c in g.columns if c != "geometry"],
        "bounds": [round(float(x), 5) for x in g.total_bounds],
    }
    return g


def norm_ward(s):
    """'K/W', ' K/W', 'KW', 'K/WEST' -> 'KW';  'A' -> 'A'."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = str(s).upper().strip().replace("/", "").replace(" ", "")
    s = s.replace("WEST", "W").replace("EAST", "E").replace("NORTH", "N").replace("SOUTH", "S").replace("CENTRAL", "C")
    return s or None


# --------------------------------------------------------------------------- air quality
def build_air_quality():
    t = pd.read_csv(RAW / "Train.csv")
    t["ts"] = pd.to_datetime(t["timestamp_ist"]).dt.tz_localize(None)  # IST wall-clock, hour ending
    t["station"] = t["station_name"].str.replace(", Mumbai", "", regex=False)
    INVENTORY["train"] = {
        "records": int(len(t)), "start": str(t.ts.min()), "end": str(t.ts.max()),
        "stations": int(t.location_id.nunique()), "nulls": int(t.isna().sum().sum()),
        "duplicate_station_hours": int(t.duplicated(["location_id", "ts"]).sum()),
        "flag_high_1000": int(t.flag_high_1000.sum()),
        "three_reading_hours": int((t["count"] == 3).sum()),
        "per_station": t.groupby("station").agg(
            hours=("pm25", "size"), flagged=("flag_high_1000", "sum"), max=("pm25", "max")).reset_index().to_dict("records"),
    }
    span = (t.ts.max() - t.ts.min()) / pd.Timedelta(hours=1) + 1
    INVENTORY["train"]["completeness"] = {s: round(float(n / span), 4) for s, n in t.groupby("station").size().items()}
    t[["ts", "location_id", "station", "pm25", "count", "flag_high_1000"]].to_parquet(OUT / "pm25_hourly.parquet", index=False)

    st = pd.read_csv(RAW / "Stations.csv")
    st["station"] = st["station_name"].str.replace(", Mumbai", "", regex=False)
    st["network"] = "target_2025_2026"
    st["sid"] = st["location_id"].astype(str)

    # 2024 archive (XKDR): 29 Mumbai series with coordinates in the XKDR lookup -> spatial cross-section
    h = pd.read_csv(RAW / "additional_history" / "History_Mumbai_2024.csv.gz")
    n0 = len(h)
    h = h[(~h.flag_negative) & (~h.flag_high_1000) & h.pm25_nonnegative.notna()]
    h["ts"] = pd.to_datetime(h["collected_at"]).dt.floor("h")
    h = h.groupby(["station_id", "station_name", "source", "ts"], as_index=False)["pm25_nonnegative"].mean()
    h = h.rename(columns={"pm25_nonnegative": "pm25", "station_id": "sid"})
    h["station"] = h["station_name"].str.replace(", Mumbai", "", regex=False)
    h[["ts", "sid", "station", "source", "pm25"]].to_parquet(OUT / "pm25_2024_hourly.parquet", index=False)
    x = pd.read_csv(RAW / "additional_history" / "XKDR_All_Stations.csv")
    s24 = h.groupby(["sid", "station", "source"], as_index=False).agg(hours=("pm25", "size"), median_2024=("pm25", "median"), mean_2024=("pm25", "mean"))
    s24 = s24.merge(x[["station_id", "latitude", "longitude"]], left_on="sid", right_on="station_id", how="left").drop(columns="station_id")
    s24["coverage_2024"] = (s24.hours / 8784).round(3)
    s24["network"] = "archive_2024"
    INVENTORY["history_2024"] = {"records_raw": int(n0), "records_used": int(len(h)), "series": int(h.sid.nunique()),
                                 "series_without_coordinates": int(s24.latitude.isna().sum())}
    s24 = s24.dropna(subset=["latitude"])

    # 2018-2020 archive keeps PM10 alongside PM2.5 -> measured PM2.5/PM10 ratio
    k = pd.read_csv(RAW / "additional_history" / "History_Mumbai_2018_2020.csv.gz", usecols=["StationName", "Datetime", "PM2.5", "PM10", "flag_high_1000"])
    k = k[~k.flag_high_1000].rename(columns={"PM2.5": "pm25", "PM10": "pm10", "StationName": "station", "Datetime": "ts"})
    k["ts"] = pd.to_datetime(k["ts"])
    k["station"] = k["station"].str.replace(", Mumbai", "", regex=False)
    k[["ts", "station", "pm25", "pm10"]].to_parquet(OUT / "pm_2018_2020.parquet", index=False)
    INVENTORY["history_2018_2020"] = {"records": int(len(k)), "stations": int(k.station.nunique()),
                                      "pm25_and_pm10": int(k[["pm25", "pm10"]].notna().all(axis=1).sum())}
    for f, note in [("Legacy_Observations_2020_2022.csv.gz", "irregular samples, not hourly - inventoried, not used"),
                    ("Other_Mumbai_Stations_2025_2026.csv.gz", "no coordinates or cross-source mapping supplied - inventoried, not mapped")]:
        d = pd.read_csv(RAW / "additional_history" / f)
        INVENTORY[f.split(".")[0].lower()] = {"records": int(len(d)), "note": note}
    return st, s24


# --------------------------------------------------------------------------- KML (OpenCity)
def kml_points(path: Path) -> pd.DataFrame:
    txt = path.read_text(encoding="utf-8", errors="replace")
    txt = re.sub(r'\sxmlns="[^"]+"', "", txt, count=1)
    rows = []
    for pm in ET.fromstring(txt).iter("Placemark"):
        d = {sd.get("name"): (sd.text or "").strip() for sd in pm.iter("SimpleData")}
        d["name"] = (pm.findtext("name") or "").strip()
        d["style"] = (pm.findtext("styleUrl") or "").strip()
        c = pm.find(".//Point/coordinates")
        if c is not None and c.text and c.text.strip():
            lon, lat = c.text.strip().split(",")[:2]
            d["lon"], d["lat"] = float(lon), float(lat)
        rows.append(d)
    return pd.DataFrame(rows)


def kml_lines(path: Path) -> gpd.GeoDataFrame:
    from shapely.geometry import LineString
    txt = re.sub(r'\sxmlns="[^"]+"', "", path.read_text(encoding="utf-8", errors="replace"), count=1)
    rows = []
    for pm in ET.fromstring(txt).iter("Placemark"):
        for c in pm.iter("coordinates"):
            pts = [tuple(map(float, p.split(",")[:2])) for p in c.text.split()]
            if len(pts) > 1:
                rows.append({"name": (pm.findtext("name") or "").strip(), "geometry": LineString(pts)})
    return gpd.GeoDataFrame(rows, crs=4326)


def to_points(df, city, label):
    """Keep only points with coordinates that fall within 300 m of the BMC ward union."""
    n = len(df)
    df = df.dropna(subset=["lon", "lat"]) if "lon" in df else df.iloc[0:0]
    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(UTM)
    inside = g.within(city.buffer(300))
    INVENTORY[label] = {"records": int(n), "without_coordinates": int(n - len(df)),
                        "outside_bmc_limits": int((~inside).sum()), "used": int(inside.sum()),
                        "duplicate_coordinates": int(g[inside].geometry.to_wkb().duplicated().sum())}
    g = g[inside].copy()
    g["x"], g["y"] = g.geometry.x, g.geometry.y
    return g


# --------------------------------------------------------------------------- buildings
FLOOR_RE = re.compile(r"G(?:R|ROUND|R\.)?\.?\s*\+\s*(\d{1,2})")


def parse_floors(v):
    """Storeys above ground from BMC's free-text NO_OF_FLOO. Unparseable -> NaN (never guessed)."""
    if v is None:
        return np.nan
    s = str(v).upper().strip()
    if not s or s in {"NA", "NAN", "NONE"}:
        return np.nan
    m = FLOOR_RE.search(s)
    if m:
        return 1 + int(m.group(1))
    if re.fullmatch(r"\d{1,2}", s):
        n = int(s)
        return float(n) if 1 <= n <= 80 else np.nan
    if s.startswith("G"):  # 'G', 'GR', 'GROUND FLOOR', 'G Residential Chawl' ...
        return 1.0
    return np.nan


USAGE_MAP = {"Residential": "Residential", "Commercial": "Commercial", "Mixed": "Mixed", "Industry": "Industrial",
             "Religious": "Religious", "Industrial Estate": "Industrial"}
AGE_MAP = [("VERY", "Very old"), ("VEY", "Very old"), ("VERV", "Very old"), ("MODERATELY", "Moderately old"), ("MADERATELY", "Moderately old"),
           ("UNDER CON", "Under construction"), ("NEW", "New / recent"), ("NWE", "New / recent"), ("OLD", "Old")]
CONS_MAP = [("RCC", "RCC"), ("LOAD", "Load bearing"), ("KAC", "Kachha"), ("PAK", "Pakka"), ("PATRA", "Patra (sheet)"),
            ("SLUM", "Slum"), ("STONE", "Old stone"), ("MIXED", "Mixed")]


def first_match(v, table):
    if v is None:
        return "Not recorded"
    s = str(v).upper().strip()
    for key, lab in table:
        if key in s:
            return lab
    return "Not recorded"


def build_buildings(wards):
    log("buildings: reading")
    b = bmc("buildings")
    b = b[b.geometry.notna()].copy()
    b["geometry"] = b.geometry.buffer(0)
    b = b.to_crs(UTM)
    b["type"] = b["TYPE"].fillna("").str.strip()
    demolished = b["type"].eq("Demolished") | b["USAGE"].fillna("").str.strip().eq("Demolished")
    INVENTORY["bmc_buildings"]["demolished_excluded"] = int(demolished.sum())
    b = b[~demolished].copy()
    b["floors"] = b["NO_OF_FLOO"].map(parse_floors)
    # identical footprints are stored once per tax record (one per unit); keep one, preferring a row with storeys
    b = b.assign(_k=b.geometry.normalize().to_wkb(), _n=b.floors.isna()).sort_values(["_n", "OBJECTID"])
    INVENTORY["bmc_buildings"]["duplicate_footprints_removed"] = int(b._k.duplicated().sum())
    b = b.drop_duplicates("_k").drop(columns=["_k", "_n"]).sort_values("OBJECTID")
    INVENTORY["bmc_buildings"]["floors_parsed"] = int(b.floors.notna().sum())
    INVENTORY["bmc_buildings"]["floors_unparsed"] = int(b.floors.isna().sum())
    b["usage"] = b["USAGE"].fillna("").str.strip().map(USAGE_MAP).fillna("Other / not surveyed")
    b["age"] = b["AGE_BUILD"].map(lambda v: first_match(v, AGE_MAP))
    b["construction"] = b["CONSTRUCTI"].map(lambda v: first_match(v, CONS_MAP))
    b["under_construction"] = b["type"].eq("Under Construction") | b["age"].eq("Under construction")
    b["area"] = b.geometry.area
    b = b[b.area > 4].copy()  # slivers < 4 m2 are digitising artefacts
    c = b.geometry.centroid
    b["x"], b["y"] = c.x, c.y
    j = gpd.sjoin(gpd.GeoDataFrame(b[["OBJECTID"]], geometry=c, crs=UTM), wards[["ward", "geometry"]], predicate="within", how="left")
    b["ward"] = j.groupby(level=0)["ward"].first()
    INVENTORY["bmc_buildings"]["outside_ward_polygons"] = int(b.ward.isna().sum())
    b = b[b.ward.notna()].copy()
    b["floor_area"] = b.area * b.floors  # NaN where storeys unknown
    INVENTORY["bmc_buildings"]["used"] = int(len(b))
    pts = pd.DataFrame(b[["x", "y", "ward", "area", "floors", "floor_area", "usage", "type", "age", "construction", "under_construction"]])
    pts.to_parquet(OUT / "buildings_points.parquet", index=False)
    return b


def write_3d(b, wards, stations):
    """Per-ward and per-station polygon files for the 3D view (exterior rings, simplified to 1 m)."""
    log("buildings: writing 3D tiles")
    g = b[["ward", "floors", "usage", "type", "x", "y", "geometry"]].copy()
    g["geometry"] = g.geometry.simplify(1.0)
    g = g.explode(index_parts=False)
    g = g[g.geometry.geom_type == "Polygon"]
    ll = g.to_crs(4326)
    g["polygon"] = [np.round(np.asarray(p.exterior.coords), 6).tolist() for p in ll.geometry]
    g["floors"] = g["floors"].astype("float32")
    cols = ["polygon", "floors", "usage", "type"]
    for w, d in g.groupby("ward"):
        pd.DataFrame(d[cols]).to_parquet(OUT / "buildings" / f"ward_{w}.parquet", index=False)
    tree = cKDTree(g[["x", "y"]].values)
    for _, s in stations.iterrows():
        idx = tree.query_ball_point([s.x, s.y], 1500)
        pd.DataFrame(g.iloc[idx][cols]).to_parquet(OUT / "buildings" / f"station_{s.sid}.parquet", index=False)


# --------------------------------------------------------------------------- helpers
def nearest(src_xy, dst_xy):
    return cKDTree(dst_xy).query(src_xy)[0]


def wmedian(v, w):
    o = np.argsort(v)
    v, w = np.asarray(v)[o], np.asarray(w)[o]
    return float(v[np.searchsorted(np.cumsum(w), w.sum() / 2)]) if w.sum() > 0 else np.nan


def main():
    stations, s24 = build_air_quality()
    log("air quality done")

    # ---- wards & population
    wards = bmc("wards").to_crs(UTM)
    wards["ward"] = wards["REMARK"].map(norm_ward)
    wards["ward_name"] = wards["WARD"].str.title().str.replace("/", " / ")
    wards["geometry"] = wards.geometry.buffer(0)
    wards["area_km2"] = wards.area / 1e6
    city = unary_union(wards.geometry.values)
    pr = bmc("prabhags").to_crs(UTM)
    pr["ward"] = pr["WARD"].map(norm_ward)
    pop = pr.groupby("ward")["POPULATION"].sum()
    INVENTORY["bmc_prabhags"]["population_total"] = int(pr.POPULATION.sum())
    wi = pd.DataFrame(wards[["ward", "ward_name", "area_km2"]]).set_index("ward")
    wi["population"] = pop
    wi["prabhags"] = pr.groupby("ward").size()
    wi["pop_density_km2"] = wi.population / wi.area_km2

    # ---- monitoring stations (both networks) in UTM
    def st_utm(df):
        g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs=4326).to_crs(UTM)
        df = df.copy()
        df["x"], df["y"] = g.geometry.x.values, g.geometry.y.values
        df["ward"] = gpd.sjoin(g, wards[["ward", "geometry"]], predicate="within", how="left").groupby(level=0)["ward"].first().values
        return df
    stations, s24 = st_utm(stations), st_utm(s24)
    INVENTORY["history_2024"]["series_outside_bmc_limits"] = int(s24.ward.isna().sum())

    # ---- buildings
    b = build_buildings(wards)
    write_3d(b, wards, stations)
    bx = b[["x", "y"]].values

    # ---- streets
    st = bmc("streets")
    st = st[st.geometry.notna()].to_crs(UTM).explode(index_parts=False)
    st["len_m"] = st.length
    st = st[st.len_m > 0].copy()
    mid = st.geometry.interpolate(0.5, normalized=True)
    st["x"], st["y"] = mid.x, mid.y
    st["width"] = st["CARRIAGE_W"].where(st["CARRIAGE_W"] > 0)
    st["lanes"] = st["NO_OF_LANE"].where(st["NO_OF_LANE"] > 0)
    st["ward"] = gpd.sjoin(gpd.GeoDataFrame(st[["OBJECTID"]], geometry=mid, crs=UTM), wards[["ward", "geometry"]], predicate="within", how="left").groupby(level=0)["ward"].first().reindex(st.index).values
    INVENTORY["bmc_streets"].update({"total_km": round(float(st.len_m.sum() / 1000), 1),
                                     "km_with_carriageway_width": round(float(st.len_m[st.width.notna()].sum() / 1000), 1),
                                     "segments_with_width": int(st.width.notna().sum())})
    major = st[st.width >= 9].copy()
    major["geometry"] = major.geometry.simplify(3)
    mll = major.to_crs(4326)
    pd.DataFrame({"path": [np.round(np.asarray(g.coords), 5).tolist() for g in mll.geometry],
                  "width": major.width.values, "lanes": major.lanes.values, "name": major["NAME"].fillna("").values}
                 ).to_parquet(OUT / "streets_wide.parquet", index=False)
    pd.DataFrame(st[["x", "y", "ward", "len_m", "width", "lanes"]]).to_parquet(OUT / "streets_points.parquet", index=False)

    # ---- rail, water
    rl = bmc("railway_lines")
    rl = rl[rl.geometry.notna()].to_crs(UTM)
    rl["geometry"] = rl.geometry.simplify(5)
    rl = rl.explode(index_parts=False).to_crs(4326)
    pd.DataFrame({"path": [np.round(np.asarray(g.coords), 5).tolist() for g in rl.geometry], "name": rl["NAME"].fillna("").values}).to_parquet(OUT / "rail_bmc.parquet", index=False)
    sub = kml_lines(RAW / "opencity" / "suburban_lines.kml")
    INVENTORY["opencity_suburban_lines"] = {"records": int(len(sub)), "lines": sorted(sub.name.unique().tolist())}
    pd.DataFrame({"path": [np.round(np.asarray(g.coords), 5).tolist() for g in sub.geometry], "name": sub.name.values}).to_parquet(OUT / "rail_suburban.parquet", index=False)
    wb = bmc("waterbodies").to_crs(UTM)
    wb["geometry"] = wb.geometry.buffer(0).simplify(5)
    wb[["geometry"]].to_crs(4326).to_file(OUT / "water.geojson", driver="GeoJSON")

    # ---- points: rail stations, BEST, parks, civic
    rs = to_points(kml_points(RAW / "opencity" / "suburban_stations.kml"), city, "opencity_suburban_stations")
    rs_all = kml_points(RAW / "opencity" / "suburban_stations.kml")
    rs_all = gpd.GeoDataFrame(rs_all, geometry=gpd.points_from_xy(rs_all.lon, rs_all.lat), crs=4326).to_crs(UTM)
    rs_all["x"], rs_all["y"] = rs_all.geometry.x, rs_all.geometry.y  # stations just outside BMC still serve residents
    pd.DataFrame(rs_all[["name", "N_REGION", "lon", "lat", "x", "y"]]).rename(columns={"N_REGION": "line"}).to_csv(OUT / "rail_stations.csv", index=False)

    best = kml_points(RAW / "opencity" / "best_stops_depots.kml")
    best["kind"] = np.where(best["style"].str.contains("depot", case=False), "depot", "stop")
    best = to_points(best, city, "opencity_best")
    INVENTORY["opencity_best"]["stops_used"] = int((best.kind == "stop").sum())
    INVENTORY["opencity_best"]["depots_used"] = int((best.kind == "depot").sum())
    pd.DataFrame(best[["name", "kind", "lon", "lat", "x", "y"]]).to_csv(OUT / "best_stops.csv", index=False)
    stops = best[best.kind == "stop"]

    parks = kml_points(RAW / "opencity" / "parks_gardens.kml")
    parks["kind"] = np.select([parks["style"].str.contains("miyawaki", case=False), parks["style"].str.contains("zoo", case=False)], ["Miyawaki garden", "Zoo"], "Park / playground")
    parks = to_points(parks, city, "opencity_parks")
    parks["ward"] = gpd.sjoin(parks[["geometry"]], wards[["ward", "geometry"]], predicate="within", how="left").groupby(level=0)["ward"].first()
    pd.DataFrame(parks[["name", "kind", "ward", "lon", "lat", "x", "y"]]).to_csv(OUT / "parks.csv", index=False)

    civ = []
    for f in sorted((RAW / "bmc").glob("civic_*.geojsonl")):
        g = gpd.read_file(f)
        g = g[g.geometry.notna() & ~g.geometry.is_empty].to_crs(UTM)
        kind = f.stem.replace("civic_", "")
        grp = "School" if kind.startswith("school") else "Hospital" if kind.startswith("hospital") else {
            "polyclinic": "Clinic / dispensary", "dispensary": "Clinic / dispensary", "hbt_clinic": "Clinic / dispensary",
            "health_post": "Clinic / dispensary", "maternity_home": "Hospital", "funeral_site": "Funeral site",
            "parking_off_street": "Public parking", "public_toilet": "Public toilet"}[kind]
        inside = g.within(city.buffer(300))
        INVENTORY[f"bmc_civic_{kind}"] = {"records": int(len(g)), "used": int(inside.sum())}
        g = g[inside]
        civ.append(pd.DataFrame({"kind": kind, "group": grp, "x": g.geometry.x, "y": g.geometry.y}))
    civ = pd.concat(civ, ignore_index=True)
    cg = gpd.GeoDataFrame(civ, geometry=gpd.points_from_xy(civ.x, civ.y), crs=UTM)
    civ["ward"] = gpd.sjoin(cg[["geometry"]], wards[["ward", "geometry"]], predicate="within", how="left").groupby(level=0)["ward"].first()
    ll = cg.to_crs(4326)
    civ["lon"], civ["lat"] = ll.geometry.x.round(5), ll.geometry.y.round(5)
    civ[["kind", "group", "ward", "lon", "lat"]].to_parquet(OUT / "civic_points.parquet", index=False)

    # ---- Development Plan 2034
    ea = bmc("dp_existing_amenities").rename(columns={"NEW_DES_MAINTYPE": "code"})
    rv = bmc("dp_reservations").rename(columns={"RES_MAINTYPE": "code"})
    DP_LABEL = {"OS": "Open space", "E": "Education", "R": "Housing", "PU": "Public utilities", "SA": "Social amenities",
                "H": "Health", "T": "Transport", "MS": "Municipal services", "O": "Public offices", "AM": "Amenity plot", "P": "Primary activity"}
    dp = []
    for g, status in [(ea, "Existing (designated)"), (rv, "Planned (reserved)")]:
        g = g[g.geometry.notna()].to_crs(UTM)
        g["geometry"] = g.geometry.buffer(0)
        g["status"] = status
        g["category"] = g["code"].str[1:].map(DP_LABEL).fillna("Other")
        # ward by location (the WARD attribute is occasionally wrong); fall back to the attribute off-shore
        rp = gpd.GeoDataFrame(geometry=g.geometry.representative_point(), crs=UTM)
        g["ward"] = gpd.sjoin(rp, wards[["ward", "geometry"]], predicate="within", how="left").groupby(level=0)["ward"].first().reindex(g.index).fillna(g["WARD"].map(norm_ward))
        g["area_m2"] = g.area
        dp.append(g[["status", "category", "ward", "DISCRIPTION", "area_m2", "geometry"]].rename(columns={"DISCRIPTION": "description"}))
    dp = pd.concat(dp, ignore_index=True)
    dp = gpd.GeoDataFrame(dp, geometry="geometry", crs=UTM)
    dp["description"] = dp["description"].fillna("").str.replace(r"\s+", " ", regex=True).str.strip()
    dps = dp.groupby(["ward", "status", "category"], as_index=False).agg(plots=("area_m2", "size"), area_m2=("area_m2", "sum"))
    dps.to_csv(OUT / "dp_ward_summary.csv", index=False)
    dp.groupby(["status", "category", "description"], as_index=False).agg(plots=("area_m2", "size"), area_m2=("area_m2", "sum")).to_csv(OUT / "dp_descriptions.csv", index=False)
    keep = dp[dp.category.isin(["Open space", "Transport", "Housing", "Municipal services"]) & (dp.area_m2 > 300)].copy()
    keep["geometry"] = keep.geometry.simplify(4)
    keep = keep.explode(index_parts=False)
    keep = keep[keep.geometry.geom_type == "Polygon"]
    kll = keep.to_crs(4326)
    pd.DataFrame({"polygon": [np.round(np.asarray(p.exterior.coords), 5).tolist() for p in kll.geometry], "status": keep.status.values,
                  "category": keep.category.values, "description": keep.description.values, "area_ha": (keep.area_m2 / 1e4).round(2).values}
                 ).to_parquet(OUT / "dp_polygons.parquet", index=False)
    landfill = dp[dp.description.str.contains("Landfill", case=False)]
    INVENTORY["dp_landfill_sites"] = int(len(landfill))
    os_exist = dp[(dp.category == "Open space") & dp.status.str.startswith("Existing")]
    os_plan = dp[(dp.category == "Open space") & dp.status.str.startswith("Planned")]
    sites = os_plan[os_plan.area_m2 >= 500].copy()  # reserved open spaces large enough to act as a neighbourhood park
    sc = sites.geometry.representative_point()
    scl = gpd.GeoSeries(sc, crs=UTM).to_crs(4326)
    pd.DataFrame({"ward": sites.ward.values, "description": sites.description.values, "area_m2": sites.area_m2.round(0).values,
                  "x": sc.x.round(1).values, "y": sc.y.round(1).values, "lon": scl.x.round(5).values, "lat": scl.y.round(5).values}
                 ).sort_values("area_m2", ascending=False).to_csv(OUT / "dp_open_space_sites.csv", index=False)

    # ---- ward indicators (DERIVED)
    log("ward indicators")
    bp = pd.DataFrame(b[["ward", "area", "floors", "floor_area", "usage", "age", "construction", "under_construction", "x", "y"]])
    bp["d_park"] = nearest(bx, parks[["x", "y"]].values)
    bp["d_stop"] = nearest(bx, stops[["x", "y"]].values)
    bp["d_rail"] = nearest(bx, rs_all[["x", "y"]].values)
    # exposure weight: residential + mixed floor area (storeys unknown -> footprint x ward median storeys is NOT assumed; such buildings get footprint only)
    res = bp.usage.isin(["Residential", "Mixed"])
    bp["w"] = np.where(res, bp.floor_area.fillna(bp.area), 0.0)
    g = bp.groupby("ward")
    wi["buildings"] = g.size()
    wi["buildings_per_km2"] = wi.buildings / wi.area_km2
    wi["footprint_cover_pct"] = 100 * g["area"].sum() / (wi.area_km2 * 1e6)
    wi["floor_area_ratio"] = g["floor_area"].sum() / (wi.area_km2 * 1e6)
    wi["storeys_known_pct"] = 100 * g["floors"].apply(lambda s: s.notna().mean())
    wi["mean_storeys"] = g.apply(lambda d: np.average(d.floors.dropna(), weights=d.area[d.floors.notna()]) if d.floors.notna().any() else np.nan)
    wi["high_rise_buildings"] = g["floors"].apply(lambda s: int((s >= 15).sum()))
    wi["under_construction_buildings"] = g["under_construction"].sum()
    for u in ["Residential", "Commercial", "Mixed", "Industrial"]:
        wi[f"footprint_{u.lower()}_pct"] = 100 * bp[bp.usage == u].groupby("ward")["area"].sum().reindex(wi.index).fillna(0) / g["area"].sum()
    wi["chawl_slum_construction_pct"] = 100 * bp[bp.construction.isin(["Kachha", "Patra (sheet)", "Slum"])].groupby("ward").size().reindex(wi.index).fillna(0) / wi.buildings
    wi["parks"] = parks.groupby("ward").size().reindex(wi.index).fillna(0).astype(int)
    wi["parks_per_10k"] = wi.parks / wi.population * 1e4
    for col, d, thr in [("park", "d_park", 500), ("best", "d_stop", 400), ("rail", "d_rail", 1000)]:
        wi[f"{col}_within_{thr}m_pct"] = g.apply(lambda x: 100 * x.w[x[d] <= thr].sum() / x.w.sum() if x.w.sum() > 0 else np.nan)
        wi[f"{col}_median_dist_m"] = g.apply(lambda x: wmedian(x[d].values, x.w.values))
    stops["ward"] = gpd.sjoin(stops[["geometry"]], wards[["ward", "geometry"]], predicate="within", how="left").groupby(level=0)["ward"].first()
    wi["best_stops"] = stops.groupby("ward").size().reindex(wi.index).fillna(0).astype(int)
    wi["best_stops_per_10k"] = wi.best_stops / wi.population * 1e4
    wi["rail_stations"] = gpd.sjoin(rs[["geometry"]], wards[["ward", "geometry"]], predicate="within", how="left").groupby("ward").size().reindex(wi.index).fillna(0).astype(int)
    sg = st.groupby("ward")
    wi["road_km"] = sg["len_m"].sum() / 1000
    wi["road_km_per_km2"] = wi.road_km / wi.area_km2
    wi["road_width_known_pct"] = 100 * st[st.width.notna()].groupby("ward")["len_m"].sum() / sg["len_m"].sum()
    wi["median_carriageway_m"] = st[st.width.notna()].groupby("ward").apply(lambda d: wmedian(d.width.values, d.len_m.values))
    wi["wide_road_km"] = st[st.width >= WIDE_M].groupby("ward")["len_m"].sum().reindex(wi.index).fillna(0) / 1000
    wi["open_space_existing_m2_pc"] = os_exist.groupby("ward")["area_m2"].sum().reindex(wi.index).fillna(0) / wi.population
    wi["open_space_planned_m2_pc"] = os_plan.groupby("ward")["area_m2"].sum().reindex(wi.index).fillna(0) / wi.population
    wi["dp_reservations"] = dp[dp.status.str.startswith("Planned")].groupby("ward").size().reindex(wi.index).fillna(0).astype(int)
    for grp, col in [("School", "schools"), ("Hospital", "hospitals"), ("Clinic / dispensary", "clinics"), ("Public toilet", "public_toilets")]:
        wi[col] = civ[civ.group == grp].groupby("ward").size().reindex(wi.index).fillna(0).astype(int)
        wi[f"{col}_per_100k"] = wi[col] / wi.population * 1e5
    wi.reset_index().round(3).to_csv(OUT / "ward_indicators.csv", index=False)
    wg = wards[["ward", "ward_name", "geometry"]].copy()
    wg["geometry"] = wg.geometry.simplify(15)
    wg.to_crs(4326).to_file(OUT / "wards.geojson", driver="GeoJSON")

    # ward x building mix tables for the equity explorer
    mix = []
    for col in ["usage", "age", "construction"]:
        m = bp.groupby(["ward", col]).agg(buildings=("area", "size"), footprint_m2=("area", "sum")).reset_index().rename(columns={col: "value"})
        m["dimension"] = col
        mix.append(m)
    fl = bp.dropna(subset=["floors"]).copy()
    fl["value"] = pd.cut(fl.floors, [0, 1, 2, 4, 7, 14, 200], labels=["1 (ground only)", "2", "3-4", "5-7", "8-14", "15+"]).astype(str)
    m = fl.groupby(["ward", "value"]).agg(buildings=("area", "size"), footprint_m2=("area", "sum")).reset_index()
    m["dimension"] = "storeys"
    mix.append(m)
    pd.concat(mix, ignore_index=True).to_csv(OUT / "ward_building_mix.csv", index=False)

    # ---- 500 m grid (DERIVED) for map layers and the citywide 3D view
    log("grid")
    CELL = 500
    minx, miny, maxx, maxy = city.bounds
    x0, y0 = np.floor(minx / CELL) * CELL, np.floor(miny / CELL) * CELL
    cells = [box(x, y, x + CELL, y + CELL) for x in np.arange(x0, maxx, CELL) for y in np.arange(y0, maxy, CELL)]
    grid = gpd.GeoDataFrame(geometry=cells, crs=UTM)
    grid = grid[grid.intersects(city)].copy()
    grid["land_m2"] = grid.intersection(city).area
    grid = grid[grid.land_m2 > 0.1 * CELL * CELL].copy()
    grid["cx"], grid["cy"] = ((grid.bounds.minx - x0) // CELL).astype(int), ((grid.bounds.miny - y0) // CELL).astype(int)
    grid = grid.set_index(["cx", "cy"])

    def cell(df):
        return pd.MultiIndex.from_arrays([((df.x - x0) // CELL).astype(int), ((df.y - y0) // CELL).astype(int)])
    bp["cell"] = list(cell(bp))
    gb = bp.groupby("cell")
    idx = list(grid.index)
    grid["buildings"] = gb.size().reindex(idx).fillna(0).values
    grid["cover_pct"] = np.minimum(100, 100 * gb["area"].sum().reindex(idx).fillna(0).values / grid.land_m2)
    grid["far"] = gb["floor_area"].sum().reindex(idx).fillna(0).values / grid.land_m2
    grid["mean_storeys"] = gb.apply(lambda d: np.average(d.floors.dropna(), weights=d.area[d.floors.notna()]) if d.floors.notna().any() else np.nan).reindex(idx).values
    stc = st.assign(cell=list(cell(st)))
    grid["road_km_km2"] = stc.groupby("cell")["len_m"].sum().reindex(idx).fillna(0).values / 1000 / (grid.land_m2 / 1e6)
    cen = grid.geometry.centroid
    cxy = np.c_[cen.x, cen.y]
    grid["d_park"] = nearest(cxy, parks[["x", "y"]].values)
    grid["d_stop"] = nearest(cxy, stops[["x", "y"]].values)
    grid["d_rail"] = nearest(cxy, rs_all[["x", "y"]].values)
    gll = grid.to_crs(4326)
    cll = gpd.GeoSeries(cen, crs=UTM).to_crs(4326)
    pd.DataFrame({"polygon": [np.round(np.asarray(p.exterior.coords), 5).tolist() for p in gll.geometry],
                  "lon": cll.x.round(5).values, "lat": cll.y.round(5).values,
                  **{c: grid[c].round(2).values for c in ["buildings", "cover_pct", "far", "mean_storeys", "road_km_km2", "d_park", "d_stop", "d_rail"]}}
                 ).to_parquet(OUT / "grid_500m.parquet", index=False)

    # ---- station surroundings at several buffer radii (DERIVED) - sensitivity analysis input
    log("station buffers")
    btree, stree = cKDTree(bx), cKDTree(st[["x", "y"]].values)
    ptree, btree2 = cKDTree(parks[["x", "y"]].values), cKDTree(stops[["x", "y"]].values)
    rtree = cKDTree(rs_all[["x", "y"]].values)
    wide = st[st.width >= WIDE_M]
    wtree = cKDTree(wide[["x", "y"]].values)
    os_all = unary_union(os_exist.geometry.values)
    A, FA, IND, UC = bp.area.values, bp.floor_area.fillna(0).values, (bp.usage == "Industrial").values, bp.under_construction.values
    SL, SW = st.len_m.values, (st.width >= WIDE_M).values
    rows = []
    allst = pd.concat([stations.assign(median_2024=np.nan), s24], ignore_index=True)
    for _, s in allst.iterrows():
        p = Point(s.x, s.y)
        base = {"sid": s.sid, "station": s.station, "network": s.network, "ward": s.ward,
                "dist_park_m": ptree.query([s.x, s.y])[0], "dist_best_stop_m": btree2.query([s.x, s.y])[0],
                "dist_rail_station_m": rtree.query([s.x, s.y])[0], "dist_wide_road_m": wtree.query([s.x, s.y])[0],
                }
        for r in RADII:
            land = p.buffer(r).intersection(city).area
            if land <= 0:
                continue
            bi, si = btree.query_ball_point([s.x, s.y], r), stree.query_ball_point([s.x, s.y], r)
            rows.append({**base, "radius_m": r, "land_km2": land / 1e6,
                         "footprint_cover_pct": 100 * A[bi].sum() / land, "floor_area_ratio": FA[bi].sum() / land,
                         "industrial_footprint_pct": 100 * A[bi][IND[bi]].sum() / max(A[bi].sum(), 1),
                         "under_construction_buildings": int(UC[bi].sum()),
                         "road_km_per_km2": SL[si].sum() / 1000 / (land / 1e6),
                         "wide_road_km_per_km2": SL[si][SW[si]].sum() / 1000 / (land / 1e6),
                         "best_stops": len(btree2.query_ball_point([s.x, s.y], r)),
                         "parks": len(ptree.query_ball_point([s.x, s.y], r)),
                         "open_space_pct": 100 * p.buffer(r).intersection(os_all).area / land})
    pd.DataFrame(rows).round(3).to_csv(OUT / "station_buffers.csv", index=False)
    keep_cols = ["sid", "station", "network", "latitude", "longitude", "ward"]
    stations[keep_cols + ["location_id"]].to_csv(OUT / "stations.csv", index=False)
    s24[keep_cols + ["source", "hours", "coverage_2024", "median_2024", "mean_2024"]].to_csv(OUT / "stations_2024.csv", index=False)

    (OUT / "data_inventory.json").write_text(json.dumps(INVENTORY, indent=1, default=str))
    log("done")


if __name__ == "__main__":
    main()
