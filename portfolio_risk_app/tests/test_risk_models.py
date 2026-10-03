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
    assert out["table"].loc["1 week", "ES"] == pytest.approx(-theo, rel=0.2)
    assert (out["table"]["ES"] < out["table"]["VaR"]).all()


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


def test_garch_es_ignores_drift_and_exceeds_volatility():
    """A strong upward trend must not shrink the 1-year tail risk (the old bug)."""
    rng = np.random.default_rng(8)
    nu, sigma_w = 5, 0.16 / np.sqrt(52)
    r = 0.20 / 52 + rng.standard_t(nu, 1200) * sigma_w * np.sqrt((nu - 2) / nu)
    idx = pd.date_range("2000-01-07", periods=len(r), freq="W-FRI")
    p = pd.Series(100 * np.exp(np.cumsum(r)), idx)
    out = rm.garch_t_es(p, level=0.95)
    t = out["table"]
    assert out["params"]["drift_removed_ann"] == pytest.approx(0.20, abs=0.04)
    vol_1y = t.loc["1 year", "Volatility"]
    assert vol_1y == pytest.approx(0.16, rel=0.25)
    assert t.loc["1 year", "ES"] < -1.5 * vol_1y         # loss of ~2σ in log terms, less once in % loss
    assert (t["ES"] <= t["VaR"]).all() and (t["VaR"] < 0).all()
    assert t["ES"].is_monotonic_decreasing                # longer horizon, larger tail loss


def test_simulate_garch_without_arch_terms_is_iid():
    sims = rm.simulate_garch_t(omega=0.0004, alpha=0.0, beta=0.0, nu=6, sigma2_0=0.0004,
                               horizon=10, n_sims=50_000, rng=np.random.default_rng(1))
    assert sims.std() == pytest.approx(0.02, rel=0.03)


def test_simulate_garch_propagates_shocks():
    """With alpha > 0 a big first-week shock raises the next week's volatility."""
    sims = rm.simulate_garch_t(omega=1e-5, alpha=0.3, beta=0.6, nu=8, sigma2_0=4e-4,
                               horizon=2, n_sims=50_000, rng=np.random.default_rng(2))
    big = np.abs(sims[:, 0]) > np.quantile(np.abs(sims[:, 0]), 0.9)
    assert sims[big, 1].std() > 1.3 * sims[~big, 1].std()


def test_ledoit_wolf_single_column_and_read_only_input():
    rng = np.random.default_rng(3)
    X = pd.DataFrame({"A": rng.normal(0, 0.02, 200)})
    X.values.setflags(write=False)
    lw = rm.ledoit_wolf(X)
    assert lw["corr"].iloc[0, 0] == 1.0
    assert lw["cov"].iloc[0, 0] == pytest.approx(X["A"].var(ddof=0) * 52, rel=0.05)
