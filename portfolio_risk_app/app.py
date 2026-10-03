"""
Portfolio Risk Explorer — Streamlit entrypoint.

Run locally from the repository root (same working directory as Streamlit
Community Cloud):
    streamlit run portfolio_risk_app/app.py
"""

from __future__ import annotations

import streamlit as st

from ui.state import init_state
from ui.theme import inject_css

st.set_page_config(
    page_title="Portfolio Risk Explorer",
    page_icon=":material/donut_small:",
    layout="wide",
)
inject_css()
init_state()

pages = [
    st.Page("pages/portfolio.py", title="Portfolio", icon=":material/edit_note:", default=True),
    st.Page("pages/instruments.py", title="Instruments", icon=":material/compare_arrows:"),
    st.Page("pages/backtest.py", title="Backtest", icon=":material/history:"),
    st.Page("pages/forecast.py", title="Forecast", icon=":material/insights:"),
    st.Page("pages/methodology.py", title="Methodology", icon=":material/menu_book:"),
]
pg = st.navigation(pages, position="top")

# Flag the first run after arriving on a page (used to refresh editable tables).
st.session_state["page_entered"] = st.session_state.get("current_page") != pg.url_path
st.session_state["current_page"] = pg.url_path

pg.run()
