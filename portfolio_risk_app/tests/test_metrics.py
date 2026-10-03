import numpy as np
import pandas as pd
import pytest

from core import metrics as m
from core.identifiers import is_isin, Listing
from tests.conftest import constant_growth


def test_constant_growth_metrics(weekly_dates):
    p = constant_growth(weekly_dates, 0.05)
    out = m.compute_metrics(p)
    days = (weekly_dates[-1] - weekly_dates[0]).days
    expected = (p.iloc[-1] / p.iloc[0]) ** (365 / days) - 1
    assert out["Annualised return"] == pytest.approx(expected)
    assert out["Volatility (ann.)"] == pytest.approx(0.0, abs=1e-12)
    assert out["Max drawdown"] == 0.0


def test_max_drawdown_details():
    idx = pd.date_range("2020-01-03", periods=6, freq="W-FRI")
    p = pd.Series([100, 120, 90, 60, 110, 125], idx)
    d = m.max_drawdown_details(p)
    assert d["mdd"] == pytest.approx(0.5)
    assert d["peak"] == idx[1] and d["trough"] == idx[3] and d["recovery"] == idx[5]


def test_historical_es_above_var():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.standard_t(4, 5000) * 0.02)
    var, es = m.historical_var_es(r, 0.95)
    assert es > var > 0


def test_short_window_not_annualised(weekly_dates):
    p = constant_growth(weekly_dates[:20], 0.05)
    out = m.compute_metrics(p)
    assert np.isnan(out["Annualised return"]) and np.isnan(out["Sharpe ratio"])


def test_horizons(weekly_dates):
    p = constant_growth(weekly_dates, 0.05)  # ~10 years minus a few days
    hs = m.available_horizons(p)
    assert "YTD" in hs and "5Y" in hs and "Since inception" in hs
    w = m.slice_horizon(p, "1Y")
    assert (w.index[-1] - w.index[0]).days >= 365 - 6


def test_relative_stats_identical_series(weekly_dates):
    rng = np.random.default_rng(1)
    p = pd.Series(100 * np.cumprod(1 + rng.normal(0.001, 0.02, len(weekly_dates))), weekly_dates)
    rel = m.relative_stats(p, p)
    assert rel["Beta"] == pytest.approx(1.0)
    assert rel["Tracking error"] == pytest.approx(0.0, abs=1e-12)
    assert rel["Correlation"] == pytest.approx(1.0)


def test_calendar_year_returns():
    idx = pd.to_datetime(["2020-06-05", "2020-12-25", "2021-06-04", "2021-12-31"])
    p = pd.Series([100, 110, 99, 121], idx)
    cy = m.calendar_year_returns(p)
    assert cy[2020] == pytest.approx(0.10) and cy[2021] == pytest.approx(0.10)


def test_isin_checksum():
    assert is_isin("IE00B4L5Y983")
    assert is_isin("US0378331005")
    assert not is_isin("IE00B4L5Y984")
    assert not is_isin("SPY")


def test_price_index_flag():
    assert Listing("^GSPC", "S&P 500", quote_type="INDEX").is_price_index
    assert not Listing("^SP500TR", "S&P 500 (TR)", quote_type="INDEX").is_price_index
    assert not Listing("SPY", "SPDR", quote_type="ETF").is_price_index
    assert not Listing("^GDAXI", "DAX P", quote_type="INDEX").is_price_index
    assert Listing("^SSMI", "SMI PR", quote_type="INDEX").is_price_index
