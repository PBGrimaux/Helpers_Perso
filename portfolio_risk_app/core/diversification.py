"""
Diversification diagnostics for a weight vector and a covariance matrix.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pandas as pd


def _align(weights: pd.Series, cov: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list]:
    cols = [c for c in cov.columns if c in weights.index]
    w = weights.reindex(cols).fillna(0.0).to_numpy(dtype=float)
    s = w.sum()
    assert s > 0, "Weights on the covariance universe sum to zero"
    return w / s, cov.loc[cols, cols].to_numpy(dtype=float), cols


def portfolio_volatility(weights: pd.Series, cov: pd.DataFrame) -> float:
    w, S, _ = _align(weights, cov)
    return float(np.sqrt(w @ S @ w))


def effective_number_of_holdings(weights: pd.Series) -> float:
    """1 / Σ w² (inverse Herfindahl)."""
    w = weights[weights > 0]
    w = w / w.sum()
    return float(1.0 / (w**2).sum())


def diversification_ratio(weights: pd.Series, cov: pd.DataFrame) -> float:
    """Σ w_i σ_i / σ_p — 1 means no diversification benefit."""
    w, S, _ = _align(weights, cov)
    return float(w @ np.sqrt(np.diag(S)) / np.sqrt(w @ S @ w))


def risk_contributions(weights: pd.Series, cov: pd.DataFrame) -> pd.DataFrame:
    """
    Euler decomposition of portfolio volatility.
    RC_i = w_i (Σw)_i / σ_p ; percentages sum to 1.
    """
    w, S, cols = _align(weights, cov)
    sigma = np.sqrt(w @ S @ w)
    mrc = S @ w / sigma
    rc = w * mrc
    return pd.DataFrame(
        {"Weight": w, "Risk contribution": rc / sigma, "Marginal risk": mrc, "Volatility": np.sqrt(np.diag(S))},
        index=cols,
    )


def effective_number_of_bets(weights: pd.Series, cov: pd.DataFrame) -> float:
    """
    Meucci (2009) effective number of bets on principal components:
    exp(entropy of the variance shares of the uncorrelated factors).
    """
    w, S, _ = _align(weights, cov)
    eigval, eigvec = np.linalg.eigh(S)
    eigval = np.clip(eigval, 0, None)
    exposures = eigvec.T @ w
    var_contrib = exposures**2 * eigval
    total = var_contrib.sum()
    if total <= 0:
        return float("nan")
    p = var_contrib / total
    p = p[p > 1e-12]
    return float(np.exp(-(p * np.log(p)).sum()))


def average_correlation(weights: pd.Series, corr: pd.DataFrame) -> float:
    """Weight-weighted average pairwise correlation (off-diagonal)."""
    w, C, _ = _align(weights, corr)
    ww = np.outer(w, w)
    np.fill_diagonal(ww, 0.0)
    s = ww.sum()
    return float((ww * C).sum() / s) if s > 0 else float("nan")


def summary(weights: pd.Series, cov: pd.DataFrame, corr: pd.DataFrame) -> OrderedDict:
    rc = risk_contributions(weights, cov)
    out = OrderedDict()
    out["Portfolio volatility"] = portfolio_volatility(weights, cov)
    out["Weighted avg. volatility"] = float((rc["Weight"] * rc["Volatility"]).sum())
    out["Diversification ratio"] = diversification_ratio(weights, cov)
    out["Effective nb of holdings"] = effective_number_of_holdings(weights.reindex(cov.columns).fillna(0))
    out["Effective nb of bets"] = effective_number_of_bets(weights, cov)
    out["Avg. pairwise correlation"] = average_correlation(weights, corr)
    return out
