"""
Cached wrappers around the core layer. Yahoo downloads are cached for a few
hours (shared across users of the same server, which also limits the number
of requests to Yahoo); heavy models are cached on their inputs.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import backtest as bt
from core import forecast as fc
from core import metrics as m
from core import risk_models as rm
from core.data import load_market_data
from core.identifiers import resolve_identifier


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def resolve(identifier: str) -> list[dict]:
    return [l.to_dict() for l in resolve_identifier(identifier)]


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def market_data(currency_items: tuple[tuple[str, str], ...], base: str):
    return load_market_data(dict(currency_items), base)


@st.cache_data(show_spinner=False, max_entries=256)
def bootstrap_vol(prices: pd.Series) -> dict | None:
    return rm.bootstrap_volatility(m.simple_returns(prices.dropna()).dropna())


@st.cache_data(show_spinner=False, max_entries=128)
def garch_es(prices: pd.Series, level: float) -> dict:
    return rm.garch_t_es(prices, level=level)


@st.cache_data(show_spinner=False, max_entries=32)
def ledoit_wolf(returns: pd.DataFrame) -> dict | None:
    return rm.ledoit_wolf(returns)


@st.cache_data(show_spinner=False, max_entries=32)
def backtest(prices: pd.DataFrame, weights: pd.Series, rule: str, mgmt_fee: float, tc_bps: float,
             returns_override: pd.DataFrame | None = None) -> bt.BacktestResult:
    return bt.run_backtest(prices, weights, rule, mgmt_fee, tc_bps, returns_override)


@st.cache_data(show_spinner=False, max_entries=16)
def estimate_nu(prices: pd.DataFrame) -> float:
    return fc.estimate_nu(prices)
