"""
Performance, risk and relative metrics on weekly price series.

Conventions (aligned with the Trend Following backtest/metrics.py):
- annualised return = (S_T / S_0) ^ (365 / nb_calendar_days) - 1
- volatility annualised with sqrt(52) on simple weekly returns
- drawdowns and ES are reported as positive numbers (0.15 = 15% loss)
- windows shorter than one year: no annualised return and no return-based ratios
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pandas as pd

PERIODS_PER_YEAR = 52
MIN_WEEKS_ANNUALISE = 52

HORIZONS = ["YTD", "1Y", "3Y", "5Y", "10Y", "Since inception"]


# ── basic building blocks ────────────────────────────────────────────────

def simple_returns(prices: pd.Series | pd.DataFrame):
    return prices / prices.shift(1) - 1


def cumulative_return(prices: pd.Series) -> float:
    prices = prices.dropna()
    assert len(prices) >= 2, "Need at least 2 price points"
    return prices.iloc[-1] / prices.iloc[0] - 1


def annualized_return_from_prices(prices: pd.Series) -> float:
    """(S_T / S_0) ^ (365 / nb_days) - 1, nb_days = calendar days between first and last date."""
    prices = prices.dropna()
    assert len(prices) >= 2, "Need at least 2 price points"
    assert prices.iloc[0] > 0 and prices.iloc[-1] > 0, "Prices must be positive"
    nb_days = (prices.index[-1] - prices.index[0]).days
    assert nb_days > 0, "Price series must span at least 1 calendar day"
    return (prices.iloc[-1] / prices.iloc[0]) ** (365 / nb_days) - 1


def annualized_volatility(returns: pd.Series, periods_per_year: float = PERIODS_PER_YEAR) -> float:
    return returns.dropna().std() * np.sqrt(periods_per_year)


def downside_deviation(returns: pd.Series, mar_per_period: float = 0.0,
                       periods_per_year: float = PERIODS_PER_YEAR) -> float:
    """Annualised root-mean-square of returns below the minimum acceptable return."""
    r = returns.dropna()
    shortfall = np.minimum(r - mar_per_period, 0.0)
    return float(np.sqrt((shortfall**2).mean()) * np.sqrt(periods_per_year))


def drawdown_series(prices: pd.Series) -> pd.Series:
    prices = prices.dropna()
    return prices / prices.cummax() - 1


def max_drawdown_details(prices: pd.Series) -> dict:
    """
    Maximum drawdown (positive), peak date, trough date, recovery date
    (None if not recovered) and the number of weeks from trough to recovery.
    """
    prices = prices.dropna()
    dd = drawdown_series(prices)
    trough = dd.idxmin()
    mdd = -dd.min()
    if mdd <= 0:
        return {"mdd": 0.0, "peak": None, "trough": None, "recovery": None, "recovery_weeks": None}
    peak = prices.loc[:trough].idxmax()
    after = prices.loc[trough:]
    recovered = after[after >= prices.loc[peak]]
    recovery = recovered.index[0] if len(recovered) else None
    rec_weeks = int(round((recovery - trough).days / 7)) if recovery is not None else None
    return {"mdd": float(mdd), "peak": peak, "trough": trough, "recovery": recovery, "recovery_weeks": rec_weeks}


def historical_var_es(returns: pd.Series, level: float = 0.95) -> tuple[float, float]:
    """Historical VaR and expected shortfall of weekly returns, as positive losses."""
    r = returns.dropna().to_numpy()
    assert len(r) > 0, "No returns"
    q = np.quantile(r, 1 - level)
    tail = r[r <= q]
    return float(-q), float(-tail.mean())


def rf_per_period(rf_annual: float, periods_per_year: float = PERIODS_PER_YEAR) -> float:
    return (1 + rf_annual) ** (1 / periods_per_year) - 1


# ── relative statistics ──────────────────────────────────────────────────

def relative_stats(p: pd.Series, b: pd.Series, rf_annual: float = 0.0) -> OrderedDict:
    """
    Statistics of instrument prices `p` against benchmark prices `b`
    (aligned on common dates).
    """
    df = pd.concat([p, b], axis=1, keys=["p", "b"]).dropna()
    out = OrderedDict()
    if len(df) < 3:
        return out
    r = simple_returns(df).dropna()
    rp, rb = r["p"], r["b"]
    active = rp - rb
    long_enough = len(r) >= MIN_WEEKS_ANNUALISE

    te = active.std() * np.sqrt(PERIODS_PER_YEAR)
    var_b = rb.var()
    beta = rp.cov(rb) / var_b if var_b > 0 else np.nan

    if long_enough:
        ann_p = annualized_return_from_prices(df["p"])
        ann_b = annualized_return_from_prices(df["b"])
        out["Excess return (ann.)"] = ann_p - ann_b
        out["Tracking error"] = te
        out["Information ratio"] = (ann_p - ann_b) / te if te > 0 else np.nan
        out["Beta"] = beta
        out["Alpha (Jensen, ann.)"] = (ann_p - rf_annual) - beta * (ann_b - rf_annual)
    else:
        out["Excess return (cum.)"] = cumulative_return(df["p"]) - cumulative_return(df["b"])
        out["Tracking error"] = te
        out["Information ratio"] = np.nan
        out["Beta"] = beta
        out["Alpha (Jensen, ann.)"] = np.nan

    out["Correlation"] = rp.corr(rb)
    up, down = rb > 0, rb < 0
    out["Up capture"] = rp[up].mean() / rb[up].mean() if up.any() else np.nan
    out["Down capture"] = rp[down].mean() / rb[down].mean() if down.any() else np.nan
    out["Weeks outperforming"] = float((active > 0).mean())
    return out


# ── full metric set ──────────────────────────────────────────────────────

# key → (section, format) ; format ∈ pct, ratio, num, date, int
METRIC_FORMATS = OrderedDict(
    [
        ("Cumulative return", ("Performance", "pct")),
        ("Annualised return", ("Performance", "pct")),
        ("Best week", ("Performance", "pct")),
        ("Worst week", ("Performance", "pct")),
        ("Positive weeks", ("Performance", "pct")),
        ("Volatility (ann.)", ("Risk", "pct")),
        ("Bootstrap vol (median)", ("Risk", "pct")),
        ("Bootstrap vol 5%", ("Risk", "pct")),
        ("Bootstrap vol 95%", ("Risk", "pct")),
        ("Downside deviation", ("Risk", "pct")),
        ("Max drawdown", ("Risk", "pct")),
        ("Max drawdown trough", ("Risk", "date")),
        ("Recovery (weeks)", ("Risk", "int")),
        ("VaR (1w, hist.)", ("Risk", "pct")),
        ("ES (1w, hist.)", ("Risk", "pct")),
        ("Skewness", ("Risk", "num")),
        ("Excess kurtosis", ("Risk", "num")),
        ("Sharpe ratio", ("Ratios", "ratio")),
        ("Sortino ratio", ("Ratios", "ratio")),
        ("Calmar ratio", ("Ratios", "ratio")),
        ("Excess return (ann.)", ("Relative", "pct")),
        ("Excess return (cum.)", ("Relative", "pct")),
        ("Tracking error", ("Relative", "pct")),
        ("Information ratio", ("Relative", "ratio")),
        ("Beta", ("Relative", "ratio")),
        ("Alpha (Jensen, ann.)", ("Relative", "pct")),
        ("Correlation", ("Relative", "ratio")),
        ("Up capture", ("Relative", "pct")),
        ("Down capture", ("Relative", "pct")),
        ("Weeks outperforming", ("Relative", "pct")),
    ]
)


def compute_metrics(
    prices: pd.Series,
    rf_annual: float = 0.0,
    level: float = 0.95,
    bootstrap: dict | None = None,
) -> OrderedDict:
    """
    Absolute metrics for one weekly price series.

    `bootstrap` is the output of risk_models.bootstrap_volatility (optional).
    """
    prices = prices.dropna()
    out = OrderedDict()
    if len(prices) < 3:
        return out
    r = simple_returns(prices).dropna()
    long_enough = len(r) >= MIN_WEEKS_ANNUALISE

    ann_ret = annualized_return_from_prices(prices) if long_enough else np.nan
    vol = annualized_volatility(r)
    dd = max_drawdown_details(prices)
    rf_w = rf_per_period(rf_annual)
    var, es = historical_var_es(r, level)
    dsd = downside_deviation(r, rf_w)

    out["Cumulative return"] = cumulative_return(prices)
    out["Annualised return"] = ann_ret
    out["Best week"] = r.max()
    out["Worst week"] = r.min()
    out["Positive weeks"] = float((r > 0).mean())
    out["Volatility (ann.)"] = vol
    if bootstrap:
        out["Bootstrap vol (median)"] = bootstrap["median"]
        out["Bootstrap vol 5%"] = bootstrap["low"]
        out["Bootstrap vol 95%"] = bootstrap["high"]
    out["Downside deviation"] = dsd
    out["Max drawdown"] = dd["mdd"]
    out["Max drawdown trough"] = dd["trough"]
    out["Recovery (weeks)"] = dd["recovery_weeks"] if dd["trough"] is not None else None
    out["VaR (1w, hist.)"] = var
    out["ES (1w, hist.)"] = es
    out["Skewness"] = float(r.skew())
    out["Excess kurtosis"] = float(r.kurt())
    if long_enough:
        out["Sharpe ratio"] = (ann_ret - rf_annual) / vol if vol > 0 else np.nan
        out["Sortino ratio"] = (ann_ret - rf_annual) / dsd if dsd > 0 else np.nan
        out["Calmar ratio"] = ann_ret / dd["mdd"] if dd["mdd"] > 0 else np.nan
    else:
        out["Sharpe ratio"] = out["Sortino ratio"] = out["Calmar ratio"] = np.nan
    return out


# ── horizons ─────────────────────────────────────────────────────────────

def horizon_start(label: str, end: pd.Timestamp, inception: pd.Timestamp) -> pd.Timestamp | None:
    """
    Start date of a horizon ending at `end`. None if the series does not
    cover the full horizon (except 'Since inception').
    """
    if label == "Since inception":
        return inception
    if label == "YTD":
        start = pd.Timestamp(year=end.year - 1, month=12, day=31)
    else:
        years = int(label[:-1])
        start = end - pd.DateOffset(years=years)
    return start if start >= inception - pd.Timedelta(days=6) else None


def slice_horizon(prices: pd.Series, label: str, end: pd.Timestamp | None = None) -> pd.Series | None:
    """
    Price window for a horizon. The window starts at the last observation on
    or before the theoretical start date, so returns cover the full period.
    """
    prices = prices.dropna()
    if len(prices) < 2:
        return None
    end = end or prices.index[-1]
    prices = prices.loc[:end]
    start = horizon_start(label, end, prices.index[0])
    if start is None:
        return None
    before = prices.loc[:start]
    first = before.index[-1] if len(before) else prices.index[0]
    window = prices.loc[first:]
    return window if len(window) >= 2 else None


def available_horizons(prices: pd.Series) -> list[str]:
    return [h for h in HORIZONS if slice_horizon(prices, h) is not None]


# ── tables ───────────────────────────────────────────────────────────────

def calendar_year_returns(prices: pd.Series) -> pd.Series:
    """Return per calendar year (first and last years may be partial)."""
    prices = prices.dropna()
    year_end = prices.groupby(prices.index.year).last()
    first_year = prices.index[0].year
    prev = year_end.shift(1)
    prev.loc[first_year] = prices.iloc[0]
    return year_end / prev - 1


def rolling_return(prices: pd.Series, window: int = 52) -> pd.Series:
    prices = prices.dropna()
    return prices / prices.shift(window) - 1


def rolling_volatility(prices: pd.Series, window: int = 52) -> pd.Series:
    r = simple_returns(prices.dropna())
    return r.rolling(window).std() * np.sqrt(PERIODS_PER_YEAR)


def rebase(prices: pd.Series | pd.DataFrame, base: float = 100.0):
    """Rebase to `base` at the first valid observation."""
    if isinstance(prices, pd.DataFrame):
        return prices.apply(lambda s: rebase(s, base))
    first = prices.dropna()
    if first.empty:
        return prices
    return prices / first.iloc[0] * base
