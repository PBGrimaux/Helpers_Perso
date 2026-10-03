import numpy as np
import pandas as pd
import pytest
from scipy import stats

from core import risk_models as rm
from core import diversification as dv


def _t_prices(n=1500, nu=5, sigma=0.02, seed=3):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(nu, n) * sigma * np.sqrt((nu - 2) / nu)
    idx = pd.date_range("1995-01-06", periods=n, freq="W-FRI")
    return pd.Series(100 * np.exp(np.cumsum(r)), idx)


def test_bootstrap_vol_brackets_sample_vol():
    p = _t_prices()
    r = p.pct_change().dropna()
    b = rm.bootstrap_volatility(r, n_boot=500)
    sample = r.std() * np.sqrt(52)
    assert b["low"] < sample < b["high"]
    assert b["median"] == pytest.approx(sample, rel=0.05)


def test_garch_es_close_to_theory_on_iid_t():
    nu, sigma = 5, 0.02
    p = _t_prices(nu=nu, sigma=sigma)
    out = rm.garch_t_es(p, level=0.975, n_sims=20_000)
    assert out["method"].startswith("GARCH")
    # theoretical 1-week ES of a unit-variance t scaled by sigma (log returns)
    a = 0.025
    q = stats.t.ppf(a, nu)
    es_std = (nu + q**2) / (nu - 1) * stats.t.pdf(q, nu) / a * np.sqrt((nu - 2) / nu)
    theo = -np.expm1(-es_std * sigma)
    assert out["table"].loc["1 week", "ES"] == pytest.approx(theo, rel=0.2)
    assert (out["table"]["ES"] > out["table"]["VaR"]).all()


def test_garch_falls_back_on_short_history():
    p = _t_prices(n=60)
    out = rm.garch_t_es(p)
    assert out["method"].startswith("Historical")


def test_ledoit_wolf_corr_is_valid():
    rng = np.random.default_rng(5)
    X = pd.DataFrame(rng.normal(size=(300, 4)) @ rng.normal(size=(4, 4)), columns=list("ABCD"))
    lw = rm.ledoit_wolf(X)
    c = lw["corr"].to_numpy()
    assert np.allclose(np.diag(c), 1.0)
    assert np.allclose(c, c.T)
    assert np.linalg.eigvalsh(c).min() > -1e-10
    assert 0 <= lw["shrinkage"] <= 1


def test_diversification_measures():
    cov = pd.DataFrame(np.diag([0.04, 0.04]), index=["A", "B"], columns=["A", "B"])
    corr = pd.DataFrame(np.eye(2), index=["A", "B"], columns=["A", "B"])
    w = pd.Series({"A": 0.5, "B": 0.5})
    rc = dv.risk_contributions(w, cov)
    assert rc["Risk contribution"].sum() == pytest.approx(1.0)
    assert dv.diversification_ratio(w, cov) == pytest.approx(np.sqrt(2))
    assert dv.effective_number_of_bets(w, cov) == pytest.approx(2.0)
    assert dv.effective_number_of_holdings(w) == pytest.approx(2.0)
    assert dv.average_correlation(w, corr) == pytest.approx(0.0)
