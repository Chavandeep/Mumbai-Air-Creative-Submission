"""Plotly figures with one shared editorial style: thin marks, recessive grid, one axis per chart,
station colours fixed by entity, sequential ramps in one hue direction."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config import AMBER, GREEN, INK, MUTED, NAAQS_24H, RED, RULE, SEQ, STATION_COLORS, WHO_24H

FONT = "Inter, 'Helvetica Neue', Arial, sans-serif"
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CFG = {"displayModeBar": False, "responsive": True}
UG = "µg/m³"


def style(fig: go.Figure, height=340, legend=True, title=None) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=36 if title else 12, b=8), font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=12, color=INK), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=RULE, font=dict(family=FONT, size=12, color=INK)),
        title=dict(text=title, x=0, font=dict(size=14, color=INK)) if title else None, hovermode="closest")
    fig.update_xaxes(showgrid=False, linecolor=RULE, tickcolor=RULE, tickfont=dict(color=MUTED, size=12), title_font=dict(color=MUTED, size=12), zeroline=False)
    fig.update_yaxes(gridcolor="#E7E2D6", linecolor="rgba(0,0,0,0)", tickfont=dict(color=MUTED, size=12), title_font=dict(color=MUTED, size=12), zeroline=False)
    return fig


def _ref_lines(fig, naaqs=True, who=True):
    if naaqs:
        fig.add_hline(y=NAAQS_24H, line=dict(color=RED, width=1, dash="dot"), annotation_text="India 24-h standard 60", annotation_position="top left", annotation_font=dict(size=11, color=RED))
    if who:
        fig.add_hline(y=WHO_24H, line=dict(color=GREEN, width=1, dash="dot"), annotation_text="WHO 24-h guideline 15", annotation_position="bottom left", annotation_font=dict(size=11, color=GREEN))


def daily_trend(dd: pd.DataFrame, stations, window=7, height=360):
    """Rolling median of daily means; gaps are left as gaps (no interpolation)."""
    fig = go.Figure()
    for s in stations:
        g = dd[dd.station == s].set_index("date")["pm25"].asfreq("D")
        r = g.rolling(window, min_periods=max(2, window // 2), center=True).median() if window > 1 else g
        fig.add_trace(go.Scatter(x=r.index, y=r.values, name=s, mode="lines", line=dict(color=STATION_COLORS.get(s, MUTED), width=2), connectgaps=False,
                                 hovertemplate="%{x|%d %b %Y}<br><b>%{y:.0f}</b> " + UG + "<extra>" + s + "</extra>"))
    _ref_lines(fig)
    fig.update_yaxes(title_text=f"PM2.5, daily mean ({UG})", rangemode="tozero")
    return style(fig, height)


def diurnal_lines(di: pd.DataFrame, stations, height=320):
    fig = go.Figure()
    for s in stations:
        g = di[di.station == s].sort_values("hour")
        fig.add_trace(go.Scatter(x=g.hour, y=g.pm25, name=s, mode="lines+markers", line=dict(color=STATION_COLORS.get(s, MUTED), width=2), marker=dict(size=5),
                                 hovertemplate="Hour ending %{x}:00<br><b>%{y:.0f}</b> " + UG + "<extra>" + s + "</extra>"))
    fig.update_xaxes(title_text="Hour of day (IST, hour ending)", tickvals=list(range(0, 24, 3)))
    fig.update_yaxes(title_text=f"Median PM2.5 ({UG})", rangemode="tozero")
    return style(fig, height)


def heatmap(m: pd.DataFrame, x_labels, y_labels, xt, yt, height=360, zmax=None):
    fig = go.Figure(go.Heatmap(z=m.values, x=x_labels, y=y_labels, colorscale=[[i / (len(SEQ) - 1), c] for i, c in enumerate(SEQ)],
                               zmin=0, zmax=zmax, xgap=2, ygap=2, colorbar=dict(title=dict(text=UG, font=dict(size=11, color=MUTED)), thickness=10, len=0.8, outlinewidth=0, tickfont=dict(size=11, color=MUTED)),
                               hovertemplate=f"{yt} %{{y}} · {xt} %{{x}}<br><b>%{{z:.0f}}</b> {UG} (median)<extra></extra>", hoverongaps=False))
    fig.update_yaxes(autorange="reversed", showgrid=False, title_text=yt)
    fig.update_xaxes(title_text=xt)
    return style(fig, height, legend=False)


def dow_chart(dp: pd.DataFrame, stations, height=320):
    fig = go.Figure()
    off = np.linspace(-0.24, 0.24, len(stations)) if len(stations) > 1 else [0]
    for o, s in zip(off, stations):
        g = dp[dp.station == s].sort_values("dow")
        fig.add_trace(go.Scatter(x=g.dow + o, y=g["median"], name=s, mode="markers", marker=dict(size=9, color=STATION_COLORS.get(s, MUTED)),
                                 error_y=dict(type="data", symmetric=False, array=g.hi - g["median"], arrayminus=g["median"] - g.lo, color=STATION_COLORS.get(s, MUTED), thickness=1.5, width=0),
                                 customdata=np.c_[g.lo, g.hi, g.n, [DOW[i] for i in g.dow]],
                                 hovertemplate="%{customdata[3]}<br><b>%{y:.1f}</b> " + UG + " (90% interval %{customdata[0]:.1f}–%{customdata[1]:.1f}, %{customdata[2]} days)<extra>" + s + "</extra>"))
    fig.update_xaxes(tickvals=list(range(7)), ticktext=DOW)
    fig.update_yaxes(title_text=f"Median daily PM2.5 ({UG})", rangemode="tozero")
    return style(fig, height)


def monthly_bars(mo: pd.DataFrame, station, height=300):
    g = mo[mo.station == station]
    fig = go.Figure(go.Bar(x=g.month, y=g["median"], marker=dict(color=STATION_COLORS.get(station, MUTED), cornerradius=3), width=1000 * 3600 * 24 * 22,
                           hovertemplate="%{x|%b %Y}<br><b>%{y:.0f}</b> " + UG + " (median of hours)<extra></extra>"))
    fig.update_yaxes(title_text=f"Monthly median ({UG})", rangemode="tozero")
    fig.update_xaxes(dtick="M3", tickformat="%b\n%Y")
    return style(fig, height, legend=False)


def anomaly_strip(a: pd.DataFrame, station, height=300):
    g = a[a.station == station]
    base = g[~g.spike]
    sp = g[g.spike]
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=base.ts, y=base.pm25, mode="markers", name="Hourly reading", marker=dict(size=3, color="#B9B4A6", opacity=0.55), hoverinfo="skip"))
    fig.add_trace(go.Scattergl(x=sp.ts, y=sp.pm25, mode="markers", name="Spike (≥ 3× typical and ≥ 100)", marker=dict(size=7, color=RED, line=dict(color="#F7F4EE", width=1)),
                               customdata=sp.typical, hovertemplate="%{x|%d %b %Y, %H:00}<br><b>%{y:.0f}</b> " + UG + " vs typical %{customdata:.0f}<extra></extra>"))
    fig.update_yaxes(title_text=f"Hourly PM2.5 ({UG}), log scale", type="log")
    return style(fig, height)


def hbar(df: pd.DataFrame, value, label, color=GREEN, unit="", height=None, highlight=None, fmt=".1f", ref=None, ref_label=None):
    df = df.sort_values(value)
    cols = [color if (highlight is None or l in highlight) else "#C9C3B4" for l in df[label]]
    fig = go.Figure(go.Bar(x=df[value], y=df[label], orientation="h", marker=dict(color=cols, cornerradius=3),
                           hovertemplate="%{y}<br><b>%{x:" + fmt + "}</b> " + unit + "<extra></extra>"))
    if ref is not None:
        fig.add_vline(x=ref, line=dict(color=INK, width=1, dash="dot"), annotation_text=ref_label, annotation_position="top", annotation_font=dict(size=11, color=MUTED))
    fig.update_xaxes(title_text=unit, showgrid=True, gridcolor="#E7E2D6")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=12))
    return style(fig, height or max(220, 22 * len(df) + 60), legend=False)


def emissions_compare(res: pd.DataFrame, height=330):
    """Baseline vs scenario emitted mass by sector (baseline total = 100)."""
    r = res.sort_values("baseline")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=r.sector, x=r.baseline, name="Published baseline", orientation="h", marker=dict(color="#C9C3B4", cornerradius=3),
                         hovertemplate="%{y}<br>Baseline <b>%{x:.1f}</b> of 100<extra></extra>"))
    fig.add_trace(go.Bar(y=r.sector, x=r.scenario, name="Your scenario (hypothetical)", orientation="h", marker=dict(color=GREEN, cornerradius=3),
                         hovertemplate="%{y}<br>Scenario <b>%{x:.1f}</b> of 100<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.08)
    fig.update_xaxes(title_text="Share of baseline emitted mass (baseline total = 100)", showgrid=True, gridcolor="#E7E2D6")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK))
    return style(fig, height)


def assoc_chart(a: pd.DataFrame, radius: int, height=360):
    g = a[a.radius_m == radius].sort_values("rho")
    fig = go.Figure(go.Scatter(x=g.rho, y=g.label, mode="markers", marker=dict(size=10, color=INK),
                               error_x=dict(type="data", symmetric=False, array=g.hi - g.rho, arrayminus=g.rho - g.lo, color=MUTED, thickness=1.5, width=0),
                               customdata=np.c_[g.lo, g.hi, g.n, g.p],
                               hovertemplate="%{y}<br>Spearman ρ <b>%{x:.2f}</b> (90% interval %{customdata[0]:.2f} to %{customdata[1]:.2f})<br>n = %{customdata[2]} stations, p = %{customdata[3]:.2f}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=RULE, width=1))
    fig.update_xaxes(range=[-1, 1], title_text="Rank correlation with 2024 median PM2.5  (−1 … +1)", showgrid=True, gridcolor="#E7E2D6")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK))
    return style(fig, height, legend=False)


def scatter_xy(df, x, y, xt, yt, label, height=340, highlight=None):
    hl = df[label].isin(highlight or [])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x][~hl], y=df[y][~hl], mode="markers", marker=dict(size=9, color="#8C8778", line=dict(color="#F7F4EE", width=1.5)), text=df[label][~hl],
                             hovertemplate="%{text}<br>" + xt + ": <b>%{x:.1f}</b><br>" + yt + ": <b>%{y:.1f}</b><extra></extra>"))
    if hl.any():
        fig.add_trace(go.Scatter(x=df[x][hl], y=df[y][hl], mode="markers+text", marker=dict(size=11, color=AMBER, line=dict(color="#F7F4EE", width=1.5)), text=df[label][hl], textposition="top center", textfont=dict(size=11, color=INK),
                                 hovertemplate="%{text}<br>" + xt + ": <b>%{x:.1f}</b><br>" + yt + ": <b>%{y:.1f}</b><extra></extra>"))
    fig.update_xaxes(title_text=xt, showgrid=True, gridcolor="#E7E2D6")
    fig.update_yaxes(title_text=yt)
    return style(fig, height, legend=False)


def ward_profile(ranks: pd.DataFrame, labels: dict, wards, colors, height=None):
    """Dot plot: each selected ward's rank position among the 24 wards, per indicator."""
    fig = go.Figure()
    ys = [labels[c] for c in ranks.columns]
    for wname, col in zip(wards, colors):
        fig.add_trace(go.Scatter(x=ranks.loc[wname].values, y=ys, mode="markers", name=wname, marker=dict(size=11, color=col, line=dict(color="#F7F4EE", width=2)),
                                 hovertemplate="%{y}<br>" + wname + ": ranked above <b>%{x:.0f}%</b> of wards<extra></extra>"))
    fig.add_vline(x=50, line=dict(color=RULE, width=1), annotation_text="median ward", annotation_font=dict(size=11, color=MUTED))
    fig.update_xaxes(range=[-3, 103], title_text="Rank among the 24 wards (0 = lowest value, 100 = highest)", showgrid=True, gridcolor="#E7E2D6")
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color=INK))
    return style(fig, height or 30 * len(ys) + 90)


def stacked_share(df, cat, val, group, order, colors, height=260, xt="% of building footprint"):
    fig = go.Figure()
    tot = df.groupby(group)[val].sum()
    for c in order:
        g = df[df[cat] == c].set_index(group)[val].reindex(tot.index).fillna(0)
        fig.add_trace(go.Bar(y=tot.index, x=100 * g / tot, name=c, orientation="h", marker=dict(color=colors[c], line=dict(color="#F7F4EE", width=2)),
                             hovertemplate="%{y}<br>" + c + ": <b>%{x:.0f}%</b><extra></extra>"))
    fig.update_layout(barmode="stack", bargap=0.35)
    fig.update_xaxes(title_text=xt, range=[0, 100])
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK))
    return style(fig, height)


def before_after(df, label, before, after, unit, height=None, top=None):
    df = df.assign(gain=df[after] - df[before]).sort_values("gain", ascending=False)
    if top:
        df = df.head(top)
    df = df.iloc[::-1]
    fig = go.Figure()
    for _, r in df.iterrows():
        fig.add_trace(go.Scatter(x=[r[before], r[after]], y=[r[label], r[label]], mode="lines", line=dict(color="#C9C3B4", width=2), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=df[before], y=df[label], mode="markers", name="Today (derived)", marker=dict(size=9, color="#8C8778"), hovertemplate="%{y}<br>Today <b>%{x:.1f}</b> " + unit + "<extra></extra>"))
    fig.add_trace(go.Scatter(x=df[after], y=df[label], mode="markers", name="Scenario (hypothetical)", marker=dict(size=10, color=GREEN), hovertemplate="%{y}<br>Scenario <b>%{x:.1f}</b> " + unit + "<extra></extra>"))
    fig.update_xaxes(title_text=unit, showgrid=True, gridcolor="#E7E2D6")
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK))
    return style(fig, height or 24 * len(df) + 90)
