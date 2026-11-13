import pandas as pd
import streamlit as st

from modules import facts
from modules.recommendations import CRITERIA, RECS
from visualizations import ui

F = facts.build()
ui.header("Experience 4 · What should Mumbai do next?", "Eight interventions, each tied to what the data shows - and to what it cannot",
          "Every recommendation states its evidence, its mechanism, its limits and the data needed to test it. Numbers in the evidence are computed live from this app's data or quoted from the cited inventories.")


def fill(text: str) -> str:
    try:
        return text.format(**F)
    except (KeyError, IndexError, ValueError):
        return "Evidence for this item needs data that is not loaded in this deployment."


themes = ["All"] + sorted({r["theme"] for r in RECS}, key=["Transportation", "Construction", "Road infrastructure", "Industrial emissions", "Urban greenery", "City planning"].index)
pick = st.radio("Theme", themes, horizontal=True)
for r in RECS:
    if pick not in ("All", r["theme"]):
        continue
    st.markdown(f"""<div class='rec'><p class='kicker'>{r['theme']}</p><p class='h2' style='font-size:1.45rem'>{r['title']}</p><dl>
<dt>The problem</dt><dd>{r['problem']}</dd>
<dt>Evidence</dt><dd>{fill(r['evidence'])}</dd>
<dt>Proposed intervention</dt><dd>{r['intervention']}</dd>
<dt>How it would help</dt><dd>{r['mechanism']}</dd>
<dt>Expected benefits</dt><dd>{r['benefits']}</dd>
<dt>Limits and implementation challenges</dt><dd>{r['limits']}</dd>
<dt>Data needed to measure effectiveness</dt><dd>{r['data_needed']}</dd></dl></div>""", unsafe_allow_html=True)

ui.section("If Mumbai could prioritise just five interventions…", "The order below comes from four criteria, each rated on a three-step scale. The ratings are this project's editorial judgement, stated openly; "
           "the weights are yours. No costs in rupees or tonnes abated are claimed, because the data to support them is not available.")
c = st.columns(4)
wts = {}
for col, (k, (lab, hlp)) in zip(c, CRITERIA.items()):
    with col:
        wts[k] = st.slider(lab, 0, 3, 2 if k == "mass" else 1, help=hlp)
rows = []
for r in RECS:
    sc = sum(wts[k] * r["ratings"][k] for k in CRITERIA)
    rows.append({"id": r["id"], "title": r["title"], "theme": r["theme"], "score": sc, **r["ratings"]})
rk = pd.DataFrame(rows).sort_values(["score", "mass"], ascending=False).reset_index(drop=True)
if sum(wts.values()) == 0:
    st.warning("Give at least one criterion some weight.")
else:
    WORD = {3: "High", 2: "Medium", 1: "Low"}
    COSTW = {3: "Low", 2: "Medium", 1: "High"}
    for i, r in rk.head(5).iterrows():
        a, b = st.columns([0.35, 5])
        with a:
            st.markdown(f"<div class='rank'>{i + 1}</div>", unsafe_allow_html=True)
        with b:
            st.markdown(f"<p class='h3' style='margin-top:.45rem'>{r.title}</p><p class='note'>{r.theme} · Emitted particles addressed: <b>{WORD[r.mass]}</b> · Feasibility: <b>{WORD[r.feasibility]}</b> · "
                        f"Cost: <b>{COSTW[r.cost]}</b> · Simplicity: <b>{WORD[r.complexity]}</b></p>", unsafe_allow_html=True)
    with st.expander("How the ranking is calculated"):
        st.markdown("Score = Σ (your weight × rating), ratings 1–3 where 3 is always the favourable end (large share of emissions, feasible, low cost, simple). Ties are broken by the emissions rating. All eight interventions:")
        t = rk.rename(columns={"title": "Intervention", "theme": "Theme", "score": "Score", "mass": "Emissions addressed", "feasibility": "Feasibility", "cost": "Cost (3 = low)", "complexity": "Simplicity"}).drop(columns="id")
        st.dataframe(t, hide_index=True, width="stretch")
        for k, (lab, hlp) in CRITERIA.items():
            st.markdown(f"- **{lab}** - {hlp}")
