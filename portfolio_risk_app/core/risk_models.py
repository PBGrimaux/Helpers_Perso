"""
Statistical risk models:
- stationary block bootstrap of volatility (estimation uncertainty)
- GARCH(1,1) with Student-t innovations on de-drifted returns → Monte Carlo VaR / ES
- Ledoit-Wolf shrunk covariance → correlation matrix
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from arch import arch_model
from sklearn.covariance import LedoitWolf

PERIODS_PER_YEAR = 52
MIN_WEEKS_GARCH = 104
ES_HORIZONS = {"1 week": 1, "1 month": 4, "1 year": 52}


def stationary_bootstrap_indices(n: int, n_boot: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """
    Politis-Romano stationary bootstrap: index matrix (n_boot × n).

    Each step either starts a new block at a random position (prob 1/mean_block)
    or continues the current block (wrapping around the end).
    """
    assert n > 0 and n_boot > 0 and mean_block >= 1
    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_boot)
    p_new = 1.0 / mean_block
    for t in range(1, n):
        new_block = rng.random(n_boot) < p_new
        idx[:, t] = np.where(new_block, rng.integers(0, n, n_boot), (idx[:, t - 1] + 1) % n)
    return idx


def bootstrap_volatility(
    returns: pd.Series,
    n_boot: int = 1000,
    mean_block: float = 4.0,
    ci: float = 0.90,
    seed: int = 7,
) -> dict | None:
    """
    Annualised volatility distribution from a stationary block bootstrap.
    Returns median and the (1-ci)/2, (1+ci)/2 quantiles.
    """
    r = returns.dropna().to_numpy()
    if len(r) < 10:
        return None
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_indices(len(r), n_boot, mean_block, rng)
    vols = r[idx].std(axis=1, ddof=1) * np.sqrt(PERIODS_PER_YEAR)
    lo, hi = (1 - ci) / 2, (1 + ci) / 2
    return {
        "median": float(np.median(vols)),
        "low": float(np.quantile(vols, lo)),
        "high": float(np.quantile(vols, hi)),
    }




def _var_es_from_samples(horizon_returns: np.ndarray, level: float) -> tuple[float, float]:
    """VaR and ES of simulated returns, reported as positive losses."""
    q = np.quantile(horizon_returns, 1 - level)
    tail = horizon_returns[horizon_returns <= q]
    return float(-q), float(-tail.mean())


def fit_garch_t(demeaned_logret: np.ndarray) -> dict:
    """
    Fit a zero-mean GARCH(1,1) with standardised Student-t innovations:

        e_t = sigma_t * z_t,   z_t ~ t_nu scaled to unit variance
        sigma2_t = omega + alpha * e2_{t-1} + beta * sigma2_{t-1}

    The fit runs on returns in % (numerically stabler); parameters are
    returned in decimal units. `sigma2_next` is the variance forecast for
    the first week after the sample, the starting point of the simulation.
    """
    x = np.asarray(demeaned_logret, dtype=float) * 100
    am = arch_model(x, mean="Zero", vol="GARCH", p=1, q=1, dist="t", rescale=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = am.fit(disp="off", show_warning=False)
    prm = res.params
    omega, alpha, beta, nu = (float(prm["omega"]), float(prm["alpha[1]"]), float(prm["beta[1]"]), float(prm["nu"]))
    sigma2_last = float(np.asarray(res.conditional_volatility)[-1]) ** 2
    sigma2_next = omega + alpha * x[-1] ** 2 + beta * sigma2_last
    return {
        "omega": omega / 1e4,
        "alpha": alpha,
        "beta": beta,
        "nu": nu,
        "sigma2_next": sigma2_next / 1e4,
    }


def simulate_garch_t(
    omega: float, alpha: float, beta: float, nu: float, sigma2_0: float,
    horizon: int, n_sims: int, rng: np.random.Generator,
) -> np.ndarray:
    """
    Simulate weekly log returns (n_sims × horizon) through the GARCH recursion.

    Each week: draw z from a unit-variance Student-t(nu), set e = sigma * z,
    then update sigma2 = omega + alpha * e**2 + beta * sigma2 with that
    simulated return — so a large shock raises the volatility of the next
    weeks of the same path (volatility clustering).
    """
    assert nu > 2, "Student-t needs nu > 2 for a finite variance"
    scale = np.sqrt((nu - 2) / nu)
    out = np.empty((n_sims, horizon))
    s2 = np.full(n_sims, sigma2_0, dtype=float)
    for h in range(horizon):
        e = np.sqrt(s2) * rng.standard_t(nu, n_sims) * scale
        out[:, h] = e
        s2 = omega + alpha * e**2 + beta * s2
    return out


def garch_t_es(
    prices: pd.Series,
    level: float = 0.95,
    horizons: dict[str, int] = ES_HORIZONS,
    n_sims: int = 10_000,
    seed: int = 11,
) -> dict:
    """
    Forward-looking VaR / ES per horizon, without drift.

    1. Weekly log returns, minus their simple average (the drift): what is
       left are the fluctuations, i.e. the risk.
    2. Zero-mean GARCH(1,1)-t fitted on those de-drifted returns.
    3. Monte Carlo: `n_sims` paths simulated through the GARCH recursion from
       today's variance forecast, with Student-t shocks.
    4. Horizon return R = exp(sum of weekly log returns) − 1; VaR / ES read
       from the simulated R. The horizon volatility (std of the summed log
       returns) is reported alongside for comparison.

    Falls back to a block bootstrap of the de-drifted returns when history is
    shorter than MIN_WEEKS_GARCH, the fit fails, or the fitted process is not
    stationary (alpha + beta >= 1).
    """
    logret = np.log(prices.dropna()).diff().dropna().to_numpy()
    if len(logret) < 10:
        return {"method": "Not enough data", "table": pd.DataFrame(), "params": {}, "level": level}
    drift = float(logret.mean())
    e = logret - drift
    max_h = max(horizons.values())
    rng = np.random.default_rng(seed)

    method = "GARCH(1,1)-t, drift removed"
    params: dict = {"drift_removed_ann": drift * PERIODS_PER_YEAR}
    sims = None
    if len(e) >= MIN_WEEKS_GARCH:
        try:
            fit = fit_garch_t(e)
            persistence = fit["alpha"] + fit["beta"]
            if persistence < 1 and fit["nu"] > 2:
                sims = simulate_garch_t(fit["omega"], fit["alpha"], fit["beta"], fit["nu"],
                                        fit["sigma2_next"], max_h, n_sims, rng)
                params |= {
                    "nu": fit["nu"],
                    "persistence": persistence,
                    "current_vol_ann": float(np.sqrt(fit["sigma2_next"] * PERIODS_PER_YEAR)),
                    "long_run_vol_ann": float(np.sqrt(fit["omega"] / (1 - persistence) * PERIODS_PER_YEAR)),
                }
        except Exception:
            sims = None

    if sims is None:
        method = "Historical bootstrap, drift removed (GARCH not usable)"
        idx = stationary_bootstrap_indices(len(e), n_sims, 4.0, rng)
        sims = e[idx]
        if sims.shape[1] < max_h:  # short history: chain blocks up to the horizon
            reps = int(np.ceil(max_h / sims.shape[1]))
            sims = np.tile(sims, reps)
        sims = sims[:, :max_h]

    rows = {}
    for label, h in horizons.items():
        log_h = sims[:, :h].sum(axis=1)
        var, es = _var_es_from_samples(np.expm1(log_h), level)
        rows[label] = {"VaR": var, "ES": es, "Volatility": float(log_h.std())}
    table = pd.DataFrame(rows).T
    return {"method": method, "table": table, "params": params, "level": level}


def ledoit_wolf(returns: pd.DataFrame, min_obs: int = 26) -> dict | None:
    """
    Ledoit-Wolf covariance on the common window (rows with no NaN).

    Returns annualised covariance, correlation, shrinkage intensity and the
    window used. None if fewer than `min_obs` common weeks.
    """
    common = returns.dropna(how="any")
    if len(common) < min_obs or common.shape[1] < 1:
        return None
    lw = LedoitWolf().fit(common.to_numpy())
    cov = lw.covariance_ * PERIODS_PER_YEAR
    sd = np.sqrt(np.diag(cov))
    corr = cov / np.outer(sd, sd)
    np.fill_diagonal(corr, 1.0)  # on a numpy array we own (pandas arrays can be read-only)
    cols = common.columns
    return {
        "cov": pd.DataFrame(cov, index=cols, columns=cols),
        "corr": pd.DataFrame(corr, index=cols, columns=cols),
        "shrinkage": float(lw.shrinkage_),
        "start": common.index[0],
        "end": common.index[-1],
        "n_obs": len(common),
    }
