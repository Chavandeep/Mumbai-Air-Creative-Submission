"""MUMBAI: THE AIR WE BUILD - interactive urban intelligence and air quality platform.
Run with:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Mumbai: The Air We Build", page_icon=":material/apartment:", layout="wide", initial_sidebar_state="collapsed")

from visualizations import ui  # noqa: E402

ui.css()

PAGES = [
    st.Page("views/home.py", title="Overview", default=True),
    st.Page("views/explore_city.py", title="Explore the city", url_path="explore"),
    st.Page("views/city_3d.py", title="3D Mumbai", url_path="3d"),
    st.Page("views/understand_pollution.py", title="Understand the pollution", url_path="understand"),
    st.Page("views/equity_explorer.py", title="Urban equity", url_path="equity"),
    st.Page("views/reimagine_mumbai.py", title="Reimagine Mumbai", url_path="reimagine"),
    st.Page("views/recommendations.py", title="What next?", url_path="next"),
    st.Page("views/data_methods.py", title="Data & methods", url_path="data"),
]
st.navigation(PAGES, position="top").run()

st.markdown(
    "<hr class='rule'><p class='note'>MUMBAI: THE AIR WE BUILD · Built for the Google Mumbai Data Challenge 2026. "
    "PM2.5 observations: CPCB / CAAQMS via the challenge dataset (CC BY-SA 4.0). City layers: Brihanmumbai Municipal Corporation and "
    "OpenCity, as catalogued by ClimateVerse India. Measured values, derived indicators, research estimates and hypothetical "
    "scenarios are labelled wherever they appear. Nothing here is a pollution forecast.</p>", unsafe_allow_html=True)
