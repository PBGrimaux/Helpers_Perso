import numpy as np
import pandas as pd
import pytest

from core import forecast as fc
from core.export import portfolio_to_json, portfolio_from_json, to_excel


def _cov(vols, corr=0.0):
    vols = np.asarray(vols)
    C = np.full((len(vols), len(vols)), corr)
    np.fill_diagonal(C, 1.0)
    names = [f"X{i}" for i in range(len(vols))]
    return pd.DataFrame(np.outer(vols, vols) * C, index=names, columns=names)


def test_zero_vol_is_deterministic_with_flows():
    cov = _cov([1e-9])
    dates = fc.simulation_dates(pd.Timestamp("2026-10-02"), 2)
    flows = pd.DataFrame([{"Start": pd.Timestamp("2027-01-01"), "End": None, "Amount": 1000.0,
                           "Frequency": "One-off", "Indexation": 0.0}])
    sched = fc.cash_flow_schedule(flows, dates)
    assert sched.sum() == pytest.approx(1000.0)
    res = fc.simulate(pd.Series({"X0": 1.0}), pd.Series({"X0": 0.0}), cov, 10_000, dates,
                      flows=sched, nu=None, n_paths=50)
    assert np.allclose(res.wealth[:, -1], 11_000, rtol=1e-4)
    assert res.depleted.sum() == 0


def test_median_growth_matches_expected_return():
    cov = _cov([0.15, 0.05], corr=0.3)
    dates = fc.simulation_dates(pd.Timestamp("2026-10-02"), 10)
    w = pd.Series({"X0": 1.0, "X1": 0.0})
    res = fc.simulate(w, pd.Series({"X0": 0.06, "X1": 0.02}), cov, 100.0, dates, nu=6, n_paths=8000)
    T = len(dates) - 1
    med = np.median(res.wealth[:, -1]) / 100
    assert med ** (52 / T) - 1 == pytest.approx(0.06, abs=0.006)


def test_withdrawals_cause_depletion():
    cov = _cov([0.10])
    dates = fc.simulation_dates(pd.Timestamp("2026-10-02"), 5)
    flows = pd.DataFrame([{"Start": pd.Timestamp("2026-11-01"), "End": None, "Amount": -10_000.0,
                           "Frequency": "Annual", "Indexation": 0.0}])
    res = fc.simulate(pd.Series({"X0": 1.0}), pd.Series({"X0": 0.0}), cov, 20_000, dates,
                      flows=fc.cash_flow_schedule(flows, dates), n_paths=500)
    assert res.depleted.mean() > 0.5
    assert (res.wealth >= 0).all()


def test_monthly_schedule_with_indexation():
    dates = fc.simulation_dates(pd.Timestamp("2026-10-02"), 3)
    flows = pd.DataFrame([{"Start": pd.Timestamp("2026-10-15"), "End": pd.Timestamp("2027-09-30"),
                           "Amount": 100.0, "Frequency": "Monthly", "Indexation": 0.0}])
    assert fc.cash_flow_schedule(flows, dates).sum() == pytest.approx(1200.0)


def test_portfolio_json_roundtrip():
    lines = pd.DataFrame([{"Instrument": "AGG", "Benchmark": "BND", "Weight %": 100.0}])
    cf = pd.DataFrame([{"Start": pd.Timestamp("2027-01-01").date(), "End": None, "Amount": 5.0,
                        "Frequency": "Monthly", "Indexation": 0.01}])
    text = portfolio_to_json(lines, {"base_currency": "CHF"}, {"AGG": {"symbol": "AGG"}}, {"AGG": 0.04}, cf)
    back = portfolio_from_json(text)
    assert back["lines"].iloc[0]["Instrument"] == "AGG"
    assert back["expected_returns"]["AGG"] == 0.04
    assert back["cash_flows"].iloc[0]["Amount"] == 5.0
    assert len(to_excel({"a": lines, "b": cf})) > 0


def test_monthly_plan_payments():
    dates = fc.simulation_dates(pd.Timestamp("2026-10-02"), 12)
    plan = fc.monthly_plan(500.0, pd.Timestamp("2026-11-01"), 10)
    sched = fc.cash_flow_schedule(plan, dates)
    assert (sched > 0).sum() == 120
    assert sched.sum() == pytest.approx(120 * 500.0)
    assert fc.monthly_plan(0.0, pd.Timestamp("2026-11-01"), 10).empty
    grown = fc.cash_flow_schedule(fc.monthly_plan(500.0, pd.Timestamp("2026-11-01"), 2, 0.10), dates)
    assert grown[grown > 0][-1] > 500 * 1.09
