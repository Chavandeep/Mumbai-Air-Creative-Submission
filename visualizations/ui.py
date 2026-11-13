"""Small typographic building blocks so every page shares one editorial voice."""
from __future__ import annotations

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="st-"], .stMarkdown, button, input, textarea { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; }
[data-testid="stIconMaterial"], span.material-symbols-rounded, [class*="material-symbols"] { font-family: 'Material Symbols Rounded' !important; }
.block-container { padding-top: 3.4rem; padding-bottom: 4rem; max-width: 1240px; }
h1, h2, h3 { letter-spacing: -0.02em; color: #1F2328; }
.kicker { font-size: .74rem !important; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #2F5D50; margin: 0 0 .5rem 0; }
.hero { font-size: clamp(2.1rem, 4.6vw, 3.7rem) !important; font-weight: 800; line-height: 1.03 !important; max-width: 60rem; letter-spacing: -0.035em; margin: 0 0 .9rem 0; }
.h2 { font-size: clamp(1.45rem, 2.4vw, 2rem) !important; font-weight: 750; line-height: 1.12 !important; max-width: 52rem; letter-spacing: -0.025em; margin: 0 0 .5rem 0; }
.h3 { font-size: 1.08rem !important; font-weight: 700; margin: 0 0 .3rem 0; letter-spacing: -0.01em; }
.dek { font-size: 1.08rem !important; line-height: 1.55; color: #3A3F45; max-width: 46rem; margin: 0 0 1rem 0; }
.body { font-size: .97rem !important; line-height: 1.6; color: #2B3036; max-width: 44rem; }
.note { font-size: .82rem !important; line-height: 1.5; color: #6B6F76; max-width: 48rem; }
.rule { border: 0; border-top: 1px solid #D9D4C7; margin: 2.2rem 0 1.6rem 0; }
.rule-ink { border: 0; border-top: 2px solid #1F2328; margin: 0 0 .7rem 0; width: 2.6rem; }
.fig { font-size: 2.1rem; font-weight: 750; letter-spacing: -0.03em; line-height: 1; font-variant-numeric: tabular-nums; }
.fig small { font-size: .95rem; font-weight: 500; color: #6B6F76; letter-spacing: 0; }
.figlab { font-size: .8rem; color: #6B6F76; line-height: 1.35; margin: .35rem 0 1rem 0; }
.tag { display: inline-block; font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; padding: .12rem .4rem; border: 1px solid; margin-right: .3rem; vertical-align: middle; }
.tag.measured { color: #1F2328; border-color: #1F2328; }
.tag.derived { color: #2A5E9E; border-color: #2A5E9E; }
.tag.research { color: #8A5A0B; border-color: #C98A1B; }
.tag.hypo { color: #2F5D50; border-color: #2F5D50; border-style: dashed; }
.legend-dot { display: inline-block; width: .7rem; height: .7rem; border-radius: 50%; margin-right: .35rem; vertical-align: -1px; }
.legend-sq { display: inline-block; width: .8rem; height: .5rem; margin-right: .35rem; vertical-align: 1px; }
.lg { font-size: .8rem; color: #3A3F45; margin-right: 1rem; white-space: nowrap; display: inline-block; }
.ramp { height: .55rem; width: 11rem; display: inline-block; vertical-align: middle; margin: 0 .4rem; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
div[data-testid="stExpander"] { border: 0; border-top: 1px solid #D9D4C7; border-radius: 0; background: transparent; }
div[data-testid="stExpander"] details { border: 0; }
.stTabs [data-baseweb="tab-list"] { gap: 1.4rem; border-bottom: 1px solid #D9D4C7; }
.stTabs [data-baseweb="tab"] { padding: .4rem 0; font-weight: 600; }
.rec { border-top: 1px solid #D9D4C7; padding: 1.1rem 0 .4rem 0; }
.rec dt { font-size: .7rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #6B6F76; margin-top: .7rem; }
.rec dd { margin: .15rem 0 0 0; font-size: .93rem; line-height: 1.55; color: #2B3036; max-width: 46rem; }
.rank { font-size: 2.6rem; font-weight: 800; color: #C9C3B4; line-height: 1; letter-spacing: -0.04em; }
a { color: #2F5D50; }
</style>
"""

TAGS = {"measured": "Measured", "derived": "Derived indicator", "research": "Research estimate", "hypo": "Hypothetical"}


def css():
    st.markdown(CSS, unsafe_allow_html=True)


def tag(kind: str) -> str:
    return f"<span class='tag {kind}'>{TAGS[kind]}</span>"


def header(kicker: str, title: str, dek: str = "", hero=False):
    st.markdown(f"<p class='kicker'>{kicker}</p><p class='{'hero' if hero else 'h2'}'>{title}</p>" + (f"<p class='dek'>{dek}</p>" if dek else ""), unsafe_allow_html=True)


def section(title: str, dek: str = "", kinds=()):
    tags = "".join(tag(k) for k in kinds)
    st.markdown(f"<hr class='rule'><p class='h2'>{title}</p>" + (f"<p class='body'>{dek}</p>" if dek else "") + (f"<p style='margin:.4rem 0 .6rem 0'>{tags}</p>" if tags else ""), unsafe_allow_html=True)


def sub(title: str, text: str = "", kinds=()):
    tags = "".join(tag(k) for k in kinds)
    st.markdown(f"<p class='h3'>{title}</p>" + (f"<p class='body'>{text}</p>" if text else "") + (f"<p style='margin:.2rem 0 .4rem 0'>{tags}</p>" if tags else ""), unsafe_allow_html=True)


def body(text: str):
    st.markdown(f"<p class='body'>{text}</p>", unsafe_allow_html=True)


def note(text: str):
    st.markdown(f"<p class='note'>{text}</p>", unsafe_allow_html=True)


def figure(value: str, label: str, unit: str = ""):
    st.markdown(f"<hr class='rule-ink'><div class='fig'>{value}<small> {unit}</small></div><div class='figlab'>{label}</div>", unsafe_allow_html=True)


def legend(items, shape="dot"):
    """items: [(label, css colour)]"""
    cls = "legend-dot" if shape == "dot" else "legend-sq"
    st.markdown("".join(f"<span class='lg'><span class='{cls}' style='background:{c}'></span>{l}</span>" for l, c in items), unsafe_allow_html=True)


def ramp_legend(label: str, lo: str, hi: str, colors):
    grad = ",".join(colors)
    st.markdown(f"<span class='lg'>{label}: {lo}<span class='ramp' style='background:linear-gradient(90deg,{grad})'></span>{hi}</span>", unsafe_allow_html=True)


def missing(what: str):
    st.info(f"{what} is not available in this deployment. Run `python scripts/build_processed.py` after placing the source files in `data/raw/` (see README).")
