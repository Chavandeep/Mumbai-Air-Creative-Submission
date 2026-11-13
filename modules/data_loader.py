"""Cached loaders for the processed datasets. Every loader fails soft: a missing file returns
an empty frame and the calling view shows a notice instead of crashing."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from config import PROCESSED


def _read(name: str, **kw) -> pd.DataFrame:
    p = PROCESSED / name
    if not p.exists():
        return pd.DataFrame()
    if name.endswith(".parquet"):
        return pd.read_parquet(p, **kw)
    return pd.read_csv(p, **kw)


def _plain(d: pd.DataFrame) -> pd.DataFrame:
    """Parquet returns nested numpy arrays for coordinate lists; deck.gl needs plain lists."""
    for c in ("polygon", "path"):
        if c in d.columns:
            d[c] = [[[float(x), float(y)] for x, y in g] for g in d[c]]
    return d


@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    return _plain(_read(name))


@st.cache_data(show_spinner=False)
def pm25() -> pd.DataFrame:
    """MEASURED hourly PM2.5 at the four target stations. `valid` drops only the organiser-flagged
    readings above 1,000 ug/m3 (instrument artefacts such as 99,999); nothing is filled or smoothed."""
    d = _read("pm25_hourly.parquet")
    if d.empty:
        return d
    d["valid"] = ~d["flag_high_1000"]
    d["date"] = d["ts"].dt.normalize()
    d["hour"] = d["ts"].dt.hour
    d["dow"] = d["ts"].dt.dayofweek
    d["month"] = d["ts"].dt.to_period("M").dt.to_timestamp()
    return d


@st.cache_data(show_spinner=False)
def pm25_2024() -> pd.DataFrame:
    return _read("pm25_2024_hourly.parquet")


@st.cache_data(show_spinner=False)
def geojson(name: str) -> dict:
    p = PROCESSED / name
    return json.loads(p.read_text()) if p.exists() else {"type": "FeatureCollection", "features": []}


@st.cache_data(show_spinner=False)
def inventory() -> dict:
    p = PROCESSED / "data_inventory.json"
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data(show_spinner=False, max_entries=6)
def buildings_3d(key: str) -> pd.DataFrame:
    """Footprint polygons for one ward (`ward_KW`) or one station surrounding (`station_11611`)."""
    return _plain(_read(f"buildings/{key}.parquet"))


@st.cache_data(show_spinner=False)
def buildings_points() -> pd.DataFrame:
    d = _read("buildings_points.parquet", columns=["x", "y", "ward", "area", "floor_area", "usage"])
    if d.empty:
        return d
    res = d["usage"].isin(["Residential", "Mixed"])
    # exposure weight: residential + mixed-use floor area (footprint where storeys are unknown)
    d["w"] = d["floor_area"].fillna(d["area"]).where(res, 0.0).astype("float32")
    return d[["x", "y", "ward", "w"]]
