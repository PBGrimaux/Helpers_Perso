"""
Session state schema.

Editable tables use a "base + editor version" pattern: the data editor is fed
an immutable base DataFrame and returns the edited copy, which is stored
separately. When the user arrives on a page (or loads a file) the base is
replaced by the latest edited copy and the editor key is bumped, so edits
survive page changes without being applied twice.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.export import portfolio_from_json

APP_DIR = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = APP_DIR / "assets" / "example_portfolio.json"

LINE_COLUMNS = ["Instrument", "Benchmark", "Weight %"]
CASH_FLOW_COLUMNS = ["Start", "End", "Amount", "Frequency", "Indexation"]
BASE_CURRENCIES = ["CHF", "EUR", "USD", "GBP", "JPY"]
MAX_INSTRUMENTS = 20


def empty_lines() -> pd.DataFrame:
    return pd.DataFrame(
        [{"Instrument": "", "Benchmark": "", "Weight %": 0.0}], columns=LINE_COLUMNS
    )


def empty_cash_flows() -> pd.DataFrame:
    df = pd.DataFrame(columns=CASH_FLOW_COLUMNS)
    df["Amount"] = df["Amount"].astype(float)
    df["Indexation"] = df["Indexation"].astype(float)
    return df


DEFAULTS = {
    "lines": empty_lines,
    "lines_base": empty_lines,
    "cash_flows": empty_cash_flows,
    "cash_flows_base": empty_cash_flows,
    "settings": lambda: {"base_currency": "CHF", "risk_free": 0.0},
    "listings": dict,          # identifier → chosen Listing dict
    "candidates": dict,        # identifier → list of Listing dicts
    "expected_returns": dict,  # symbol → decimal
    "market": lambda: None,
    "portfolio": lambda: None,
    "loaded_signature": lambda: None,
    "editor_version": lambda: 0,
    "forecast_result": lambda: None,
}


def init_state() -> None:
    for k, factory in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = factory()


def bump_editors() -> None:
    st.session_state.editor_version += 1


def apply_portfolio_file(payload: dict) -> None:
    """Load a parsed portfolio file into the session (data must be reloaded)."""
    lines = payload["lines"].reindex(columns=LINE_COLUMNS)
    lines["Benchmark"] = lines["Benchmark"].fillna("")
    lines["Weight %"] = pd.to_numeric(lines["Weight %"], errors="coerce").fillna(0.0)
    st.session_state.lines = lines
    st.session_state.lines_base = lines.copy()
    settings = st.session_state.settings | payload.get("settings", {})
    st.session_state.settings = settings
    st.session_state.listings = payload.get("listings", {})
    st.session_state.expected_returns = payload.get("expected_returns", {})
    cf = payload.get("cash_flows")
    if cf is not None and len(cf):
        cf = cf.reindex(columns=CASH_FLOW_COLUMNS)
    else:
        cf = empty_cash_flows()
    st.session_state.cash_flows = cf
    st.session_state.cash_flows_base = cf.copy()
    st.session_state.market = None
    st.session_state.portfolio = None
    st.session_state.forecast_result = None
    bump_editors()


def load_example() -> None:
    apply_portfolio_file(portfolio_from_json(EXAMPLE_FILE.read_text(encoding="utf-8")))


def clean_lines(lines: pd.DataFrame) -> pd.DataFrame:
    df = lines.copy()
    df["Instrument"] = df["Instrument"].fillna("").astype(str).str.strip()
    df["Benchmark"] = df["Benchmark"].fillna("").astype(str).str.strip()
    df["Weight %"] = pd.to_numeric(df["Weight %"], errors="coerce").fillna(0.0)
    return df[df["Instrument"] != ""].reset_index(drop=True)


def lines_signature(lines: pd.DataFrame, base: str, listings: dict) -> str:
    df = clean_lines(lines)
    picks = {k: v.get("symbol") for k, v in listings.items()}
    return f"{base}|{df.to_json()}|{sorted(picks.items())}"
