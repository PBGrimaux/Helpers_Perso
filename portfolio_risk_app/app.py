"""
Portfolio Risk Explorer — Streamlit entrypoint.

Run locally from the repository root (same working directory as Streamlit
Community Cloud):
    streamlit run portfolio_risk_app/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
APP_PACKAGES = ("core", "ui")


def _source_fingerprint() -> tuple:
    files = sorted(p for pkg in APP_PACKAGES for p in (APP_DIR / pkg).rglob("*.py"))
    return tuple((str(p), os.path.getmtime(p)) for p in files)


def _drop_stale_app_modules() -> None:
    """
    Streamlit re-executes page scripts on every run but keeps imported modules
    in memory. After a new commit is pulled (Streamlit Cloud) a page could then
    run against an old copy of core/ or ui/ and fail with an ImportError. The
    fingerprint (file list + modification times) of core/ and ui/ is kept for
    the life of the server process; when it changes, all app modules are
    forgotten so they are imported fresh and consistently.
    """
    current = _source_fingerprint()
    previous = getattr(sys, "_portfolio_app_fingerprint", None)
    if previous is not None and previous != current:
        for name in [n for n in sys.modules if n.split(".")[0] in APP_PACKAGES]:
            del sys.modules[name]
    sys._portfolio_app_fingerprint = current


_drop_stale_app_modules()

from ui.state import init_state  # noqa: E402  (imported after the stale-module check)
from ui.theme import inject_css  # noqa: E402

st.set_page_config(
    page_title="Portfolio Risk Explorer",
    page_icon=":material/donut_small:",
    layout="wide",
)
inject_css()
init_state()

pages = [
    st.Page("views/portfolio.py", title="Portfolio", icon=":material/edit_note:", default=True),
    st.Page("views/instruments.py", title="Instruments", icon=":material/compare_arrows:"),
    st.Page("views/backtest.py", title="Backtest", icon=":material/history:"),
    st.Page("views/forecast.py", title="Forecast", icon=":material/insights:"),
    st.Page("views/methodology.py", title="Methodology", icon=":material/menu_book:"),
]
pg = st.navigation(pages, position="top")

# Flag the first run after arriving on a page (used to refresh editable tables).
st.session_state["page_entered"] = st.session_state.get("current_page") != pg.url_path
st.session_state["current_page"] = pg.url_path

pg.run()
