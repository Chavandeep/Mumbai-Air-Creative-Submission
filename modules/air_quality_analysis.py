"""Deterministic analysis of the MEASURED PM2.5 record. All statistics are computed from valid
hourly observations; medians are preferred because the distribution is heavily right-skewed."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from config import NAAQS_24H, WHO_24H

MIN_HOURS_PER_DAY = 18  # a daily mean needs >= 75% of the day's hours


def valid(d: pd.DataFrame) -> pd.DataFrame:
    return d[d["valid"]]


@st.cache_data(show_spinner=False)
def daily(d: pd.DataFrame) -> pd.DataFrame:
    g = valid(d).groupby(["station", "date"])["pm25"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] >= MIN_HOURS_PER_DAY].rename(columns={"mean": "pm25", "size": "hours"})
    return g


@st.cache_data(show_spinner=False)
def station_summary(d: pd.DataFrame) -> pd.DataFrame:
    v = valid(d)
    dd = daily(d)
    span_h = (d.ts.max() - d.ts.min()) / pd.Timedelta(hours=1) + 1
    rows = []
    for s, g in v.groupby("station"):
        dg = dd[dd.station == s]
        last = g.sort_values("ts").iloc[-1]
        rows.append({
            "station": s, "hours": len(g), "completeness_pct": 100 * len(g) / span_h,
            "median": g.pm25.median(), "mean": g.pm25.mean(), "p95": g.pm25.quantile(0.95),
            "days": len(dg), "days_over_naaqs": int((dg.pm25 > NAAQS_24H).sum()),
            "days_over_who": int((dg.pm25 > WHO_24H).sum()),
            "pct_days_over_naaqs": 100 * (dg.pm25 > NAAQS_24H).mean(), "pct_days_over_who": 100 * (dg.pm25 > WHO_24H).mean(),
            "latest_ts": last.ts, "latest": last.pm25,
            "flagged_hours": int((d.station == s).sum() - len(g)),
        })
    return pd.DataFrame(rows)


def diurnal(d: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    keys = ["station", "hour"] + ([by] if by else [])
    return valid(d).groupby(keys)["pm25"].median().reset_index()


def hour_month_matrix(d: pd.DataFrame, station: str) -> pd.DataFrame:
    v = valid(d)
    v = v[v.station == station]
    return v.pivot_table(index="hour", columns="month", values="pm25", aggfunc="median")


def hour_dow_matrix(d: pd.DataFrame, station: str) -> pd.DataFrame:
    v = valid(d)
    v = v[v.station == station]
    return v.pivot_table(index="dow", columns="hour", values="pm25", aggfunc="median")


def dow_profile(d: pd.DataFrame) -> pd.DataFrame:
    """Median of daily means by weekday, with a bootstrap 90% interval of that median."""
    dd = daily(d).copy()
    dd["dow"] = dd["date"].dt.dayofweek
    rng = np.random.default_rng(7)
    rows = []
    for (s, w), g in dd.groupby(["station", "dow"]):
        x = g.pm25.values
        bs = np.median(rng.choice(x, (400, len(x))), axis=1)
        rows.append({"station": s, "dow": w, "median": np.median(x), "lo": np.quantile(bs, 0.05), "hi": np.quantile(bs, 0.95), "n": len(x)})
    return pd.DataFrame(rows)


def monthly(d: pd.DataFrame) -> pd.DataFrame:
    g = valid(d).groupby(["station", "month"])["pm25"].agg(["median", "size"]).reset_index()
    return g[g["size"] >= 240]  # at least ~10 days of hours in the month


@st.cache_data(show_spinner=False)
def anomalies(d: pd.DataFrame) -> pd.DataFrame:
    """Hourly anomaly = observed / typical, where typical is the station's median for the same
    calendar month and hour of day. A spike is an hour at least 3x typical and above 100 ug/m3."""
    v = valid(d).copy()
    v["typical"] = v.groupby(["station", "month", "hour"])["pm25"].transform("median")
    v["ratio"] = v["pm25"] / v["typical"].clip(lower=5)
    v["spike"] = (v["ratio"] >= 3) & (v["pm25"] >= 100)
    return v


def episodes(a: pd.DataFrame) -> pd.DataFrame:
    """Group spike hours that are within 3 hours of each other into episodes."""
    s = a[a.spike].sort_values(["station", "ts"]).copy()
    if s.empty:
        return s
    gap = s.groupby("station")["ts"].diff() > pd.Timedelta(hours=3)
    s["episode"] = (gap | (s.station != s.station.shift())).cumsum()
    e = s.groupby(["station", "episode"]).agg(start=("ts", "min"), end=("ts", "max"), hours=("pm25", "size"),
                                              peak=("pm25", "max"), typical=("typical", "median")).reset_index()
    return e.drop(columns="episode").sort_values("peak", ascending=False)


@st.cache_data(show_spinner=False)
def space_time_split(d: pd.DataFrame) -> dict:
    """How much of the hour-to-hour variation is shared by all stations (time) versus persistent
    differences between stations (place)? Two-way decomposition on log PM2.5 over hours with all
    four stations reporting."""
    v = valid(d)
    w = v.pivot_table(index="ts", columns="station", values="pm25").dropna()
    w = np.log(w.clip(lower=1))
    grand = w.values.mean()
    time_eff = w.mean(axis=1) - grand
    place_eff = w.mean(axis=0) - grand
    tot = ((w - grand) ** 2).values.sum()
    ss_time = (time_eff ** 2).sum() * w.shape[1]
    ss_place = (place_eff ** 2).sum() * w.shape[0]
    corr = w.corr(method="spearman")
    return {"hours": len(w), "time_pct": 100 * ss_time / tot, "place_pct": 100 * ss_place / tot,
            "local_pct": 100 * (tot - ss_time - ss_place) / tot, "corr": corr}


def seasonal_ratio(d: pd.DataFrame) -> pd.DataFrame:
    """Median PM2.5 in the dry winter months (Nov-Feb) versus the monsoon (Jun-Sep)."""
    v = valid(d).copy()
    m = v.ts.dt.month
    v["season"] = np.select([m.isin([11, 12, 1, 2]), m.isin([6, 7, 8, 9]), m.isin([3, 4, 5])], ["Winter (Nov-Feb)", "Monsoon (Jun-Sep)", "Summer (Mar-May)"], "Post-monsoon (Oct)")
    return v.groupby(["station", "season"])["pm25"].median().unstack()


@st.cache_data(show_spinner=False)
def pm_ratio(k: pd.DataFrame) -> pd.DataFrame:
    """MEASURED PM2.5 / PM10 at the 2018-2020 stations (hours where both exist and PM10 >= PM2.5 > 0)."""
    k = k.dropna(subset=["pm25", "pm10"])
    k = k[(k.pm10 > 0) & (k.pm25 > 0) & (k.pm25 <= k.pm10)]
    g = k.groupby("station").agg(hours=("pm25", "size"), pm25=("pm25", "median"), pm10=("pm10", "median")).reset_index()
    g["ratio"] = g.pm25 / g.pm10
    return g
