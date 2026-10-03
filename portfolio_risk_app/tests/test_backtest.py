import numpy as np
import pandas as pd
import pytest

from core import backtest as bt


@pytest.fixture
def two_assets():
    idx = pd.date_range("2020-01-03", periods=4, freq="W-FRI")
    prices = pd.DataFrame({"A": [100, 110, 99, 108.9], "B": [100, 100, 100, 100]}, idx, dtype=float)
    return prices


def test_weekly_rebalance_matches_hand_calc(two_assets):
    res = bt.run_backtest(two_assets, pd.Series({"A": 0.5, "B": 0.5}), rule="weekly")
    # week returns of A: +10%, -10%, +10% ; B flat ; 50/50 each week
    expected = 100 * 1.05 * 0.95 * 1.05
    assert res.nav.iloc[-1] == pytest.approx(expected)
    assert np.allclose(res.weights.iloc[1:].sum(axis=1), 1.0)


def test_drift_weights_follow_prices(two_assets):
    res = bt.run_backtest(two_assets, pd.Series({"A": 0.5, "B": 0.5}), rule="drift")
    a = two_assets["A"].iloc[-1] / 100
    assert res.weights["A"].iloc[-1] == pytest.approx(0.5 * a / (0.5 * a + 0.5))
    assert res.nav.iloc[-1] == pytest.approx(100 * (0.5 * a + 0.5))
    assert res.turnover.iloc[1:].sum() == 0


def test_late_entry_drift_is_pro_rata():
    idx = pd.date_range("2020-01-03", periods=5, freq="W-FRI")
    prices = pd.DataFrame(
        {"A": [100, 120, 120, 120, 120], "B": [100, 100, 100, 100, 100], "C": [np.nan, np.nan, 50, 50, 50]},
        idx, dtype=float,
    )
    w = pd.Series({"A": 0.4, "B": 0.4, "C": 0.2})
    res = bt.run_backtest(prices, w, rule="drift")
    # t0: A,B 50/50 ; after week 1 A=120/220, B=100/220 ; C enters at t2 with 20%
    w2 = res.weights.iloc[2]
    assert w2["C"] == pytest.approx(0.2)
    assert w2["A"] / w2["B"] == pytest.approx(1.2)
    assert w2.sum() == pytest.approx(1.0)
    assert res.entries["C"] == idx[2]
    late = bt.late_starters(prices, idx[0])
    assert list(late) == ["C"]


def test_late_entry_rebalance_mode():
    idx = pd.date_range("2020-01-03", periods=4, freq="W-FRI")
    prices = pd.DataFrame({"A": [100, 120, 120, 120], "B": [np.nan, 10, 10, 10]}, idx, dtype=float)
    res = bt.run_backtest(prices, pd.Series({"A": 0.7, "B": 0.3}), rule="annual")
    assert res.weights.iloc[0]["A"] == pytest.approx(1.0)
    assert res.weights.iloc[1]["B"] == pytest.approx(0.3)


def test_fees_reduce_nav_and_attribution_is_exact(two_assets):
    w = pd.Series({"A": 0.5, "B": 0.5})
    gross = bt.run_backtest(two_assets, w, rule="weekly")
    net = bt.run_backtest(two_assets, w, rule="weekly", mgmt_fee=0.01, tc_bps=10)
    assert net.nav.iloc[-1] < gross.nav.iloc[-1]
    attrib = bt.return_attribution(net)
    assert attrib.sum() == pytest.approx(net.nav.iloc[-1] / 100 - 1)
    # pure management fee: NAV ratio = (1 - weekly fee)^3 on a flat asset
    flat = pd.DataFrame({"B": two_assets["B"]})
    res = bt.run_backtest(flat, pd.Series({"B": 1.0}), mgmt_fee=0.0520)
    fee_w = 1.052 ** (1 / 52) - 1
    assert res.nav.iloc[-1] == pytest.approx(100 * (1 - fee_w) ** 3)


def test_composite_benchmark_fallback_and_mask():
    idx = pd.date_range("2020-01-03", periods=4, freq="W-FRI")
    inst = pd.DataFrame({"A": [100, 110, 121, 133.1], "C": [np.nan, 10, 11, 12.1]}, idx)
    bench = pd.DataFrame({"BA": [np.nan, np.nan, 50, 55]}, idx)
    legs = bt.composite_benchmark_returns(inst, bench, {"A": "BA", "C": None})
    assert legs["A"].iloc[1] == pytest.approx(0.10)  # bench missing → own return
    assert legs["A"].iloc[3] == pytest.approx(0.10)  # bench return 55/50-1
    assert np.isnan(legs["C"].iloc[0])  # instrument not available → masked
    assert legs["C"].iloc[2] == pytest.approx(0.10)  # no benchmark → own return


def test_calendar_flags():
    dates = pd.date_range("2020-01-03", "2020-04-24", freq="W-FRI")
    flags = bt.calendar_rebalance_flags(dates, "monthly")
    flagged = dates[flags]
    assert list(flagged.month) == [1, 2, 3]
    assert all(d.month != (d + pd.Timedelta(days=7)).month for d in flagged)
