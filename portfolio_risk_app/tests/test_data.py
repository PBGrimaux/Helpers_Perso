import numpy as np
import pandas as pd
import pytest

from core import data as d


def test_minor_units():
    assert d.normalize_currency("GBp") == ("GBP", 0.01)
    assert d.normalize_currency("ZAc") == ("ZAR", 0.01)
    assert d.normalize_currency("usd") == ("USD", 1.0)


def test_convert_to_base_with_pence_and_fx():
    idx = pd.date_range("2024-01-01", periods=5, freq="B")
    prices = pd.DataFrame({"A.L": [1000.0] * 5, "B": [10.0] * 5, "C.SW": [50.0] * 5}, idx)
    fx_idx = idx.delete(2)  # missing FX quote on day 3 → carried forward
    fx = pd.DataFrame({"GBP": [1.10, 1.10, 1.20, 1.20], "USD": [0.9] * 4}, fx_idx)
    out = d.convert_to_base(prices, {"A.L": "GBp", "B": "USD", "C.SW": "CHF"}, fx, "CHF")
    assert out["A.L"].iloc[0] == pytest.approx(10.0 * 1.10)
    assert out["A.L"].iloc[2] == pytest.approx(10.0 * 1.10)  # ffilled
    assert out["B"].iloc[-1] == pytest.approx(9.0)
    assert (out["C.SW"] == 50.0).all()


def test_to_weekly_keeps_inception_and_drops_partial_week():
    idx = pd.date_range("2024-01-01", "2024-02-07", freq="B")  # ends Wednesday
    a = pd.Series(np.arange(len(idx), dtype=float) + 1, idx)
    b = a.copy()
    b[b.index < "2024-01-15"] = np.nan  # late starter
    w = d.to_weekly(pd.DataFrame({"a": a, "b": b}))
    assert w.index[-1] == pd.Timestamp("2024-02-02")  # partial week (Feb 9) dropped
    assert w.index.dayofweek.unique().tolist() == [4]
    assert w["b"].first_valid_index() == pd.Timestamp("2024-01-19")
    assert w.loc["2024-01-05", "a"] == a.loc["2024-01-05"]
