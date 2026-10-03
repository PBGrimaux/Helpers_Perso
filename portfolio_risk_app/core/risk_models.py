"""
Statistical risk models:
- stationary block bootstrap of volatility (estimation uncertainty)
- GARCH(1,1) with Student-t innovations → Monte Carlo VaR / ES per horizon
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
    q = np.quantile(horizon_returns, 1 - level)
    tail = horizon_returns[horizon_returns <= q]
    return float(-q), float(-tail.mean())


def garch_t_es(
    prices: pd.Series,
    level: float = 0.95,
    horizons: dict[str, int] = ES_HORIZONS,
    n_sims: int = 10_000,
    seed: int = 11,
) -> dict:
    """
    Forward-looking VaR / ES from a GARCH(1,1)-t fitted on weekly log returns.

    The fitted model is simulated `n_sims` times over the longest horizon,
    starting from today's conditional variance. Log returns are summed over
    each horizon and converted to simple returns.

    Falls back to a historical block bootstrap when fewer than
    MIN_WEEKS_GARCH observations exist or the fit fails.
    """
    logret = np.log(prices.dropna()).diff().dropna()
    max_h = max(horizons.values())

    method = "GARCH(1,1)-t"
    params = {}
    sims = None
    if len(logret) >= MIN_WEEKS_GARCH:
        try:
            am = arch_model(logret * 100, mean="Constant", vol="GARCH", p=1, q=1, dist="t", rescale=False)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = am.fit(disp="off", show_warning=False)
            p = res.params
            nu = float(p["nu"])
            rng = np.random.default_rng(seed)

            def t_innovations(size):
                # Student-t draws scaled to unit variance (arch's standardised t)
                return rng.standard_t(nu, size) * np.sqrt((nu - 2) / nu)

            fc = res.forecast(horizon=max_h, method="simulation", simulations=n_sims, rng=t_innovations)
            sims = fc.simulations.values[-1] / 100.0  # (n_sims, max_h) log returns
            params = {
                "nu": float(p.get("nu", np.nan)),
                "persistence": float(p.get("alpha[1]", 0) + p.get("beta[1]", 0)),
                "current_vol_ann": float(np.sqrt(res.conditional_volatility.iloc[-1] ** 2 * PERIODS_PER_YEAR) / 100),
                "long_run_vol_ann": float(
                    np.sqrt(p["omega"] / max(1e-12, 1 - p.get("alpha[1]", 0) - p.get("beta[1]", 0)) * PERIODS_PER_YEAR) / 100
                ),
            }
        except Exception:
            sims = None

    if sims is None:
        method = "Historical bootstrap (not enough data for GARCH)"
        rng = np.random.default_rng(seed)
        r = logret.to_numpy()
        if len(r) < 10:
            return {"method": "Not enough data", "table": pd.DataFrame(), "params": {}}
        idx = stationary_bootstrap_indices(len(r), n_sims, 4.0, rng)[:, : min(max_h, len(r))]
        sims = r[idx]
        if sims.shape[1] < max_h:  # very short history: tile blocks
            reps = int(np.ceil(max_h / sims.shape[1]))
            sims = np.tile(sims, reps)[:, :max_h]

    rows = {}
    for label, h in horizons.items():
        horizon_ret = np.expm1(sims[:, :h].sum(axis=1))
        var, es = _var_es_from_samples(horizon_ret, level)
        rows[label] = {"VaR": var, "ES": es}
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
    cov = pd.DataFrame(lw.covariance_ * PERIODS_PER_YEAR, index=common.columns, columns=common.columns)
    sd = np.sqrt(np.diag(cov))
    corr = cov / np.outer(sd, sd)
    np.fill_diagonal(corr.values, 1.0)
    return {
        "cov": cov,
        "corr": corr,
        "shrinkage": float(lw.shrinkage_),
        "start": common.index[0],
        "end": common.index[-1],
        "n_obs": len(common),
    }
