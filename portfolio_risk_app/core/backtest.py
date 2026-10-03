"""
Weekly portfolio backtest engine.

Timeline: prices at weekly dates t_0 … t_T. The portfolio is formed at the
close of t_0 and NAV(t_0) = 100. Weights h are set at the close of t_{k-1}
and earn the returns of week k.

Rules
- Availability: an instrument is investable at the close of t when it has a
  price at t. Before its first price its target weight is spread pro rata
  over the available instruments (targets rescaled to 100%).
- Rebalancing rule: "drift", "weekly", or a calendar rule ("monthly",
  "quarterly", "semiannual", "annual") which rebalances at the last weekly
  date of each period.
- Late entry: in drift mode the new instrument is funded by selling the
  existing holdings pro rata (their relative drift is kept); in rebalance
  modes the entry triggers a full rebalance to the rescaled targets.
- Exit (series ends): its weight is redistributed pro rata.
- Fees: management fee (annual, accrued weekly on NAV) and transaction cost
  (bps × traded notional, Σ|Δw|).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PERIODS_PER_YEAR = 52
REBALANCE_RULES = ["drift", "weekly", "monthly", "quarterly", "semiannual", "annual"]


@dataclass
class BacktestResult:
    nav: pd.Series                 # net NAV, base 100
    gross_nav: pd.Series           # NAV before any fee
    returns: pd.Series             # net weekly returns
    weights: pd.DataFrame          # end-of-week weights (after rebalancing)
    turnover: pd.Series            # Σ|Δw| traded at each date
    fees: pd.Series                # fees paid in NAV points
    contributions: pd.DataFrame    # P&L per instrument in NAV points (base 100)
    rebalance_dates: list = field(default_factory=list)
    entries: dict = field(default_factory=dict)   # instrument → first date in portfolio
    exits: dict = field(default_factory=dict)


def _period_key(date: pd.Timestamp, rule: str):
    if rule == "monthly":
        return (date.year, date.month)
    if rule == "quarterly":
        return (date.year, (date.month - 1) // 3)
    if rule == "semiannual":
        return (date.year, (date.month - 1) // 6)
    if rule == "annual":
        return date.year
    raise ValueError(rule)


def calendar_rebalance_flags(dates: pd.DatetimeIndex, rule: str) -> np.ndarray:
    """True on the last weekly date of each calendar period (never on the last date)."""
    flags = np.zeros(len(dates), dtype=bool)
    if rule in ("drift",):
        return flags
    if rule == "weekly":
        flags[:] = True
        flags[-1] = False
        return flags
    keys = [_period_key(d, rule) for d in dates]
    for k in range(len(dates) - 1):
        flags[k] = keys[k] != keys[k + 1]
    return flags


def effective_targets(target: np.ndarray, available: np.ndarray) -> np.ndarray:
    """Targets restricted to available instruments and rescaled to 1."""
    w = np.where(available, target, 0.0)
    s = w.sum()
    return w / s if s > 0 else w


def run_backtest(
    prices: pd.DataFrame,
    target_weights: pd.Series,
    rule: str = "drift",
    mgmt_fee: float = 0.0,
    tc_bps: float = 0.0,
    returns_override: pd.DataFrame | None = None,
) -> BacktestResult:
    """
    Run the backtest on weekly prices (columns = instruments, NaN = no data).

    `returns_override` (same shape) replaces the returns computed from prices
    while availability still comes from `prices`; this is how the composite
    benchmark is run with the portfolio's inclusion mask.
    """
    assert rule in REBALANCE_RULES, f"Unknown rule {rule}"
    cols = list(target_weights.index)
    prices = prices[cols]
    target = target_weights.to_numpy(dtype=float)
    assert np.all(target >= 0) and target.sum() > 0, "Weights must be non-negative and not all zero"
    target = target / target.sum()

    avail_df = prices.notna()
    # keep dates from the first date where something is available
    first_row = avail_df.any(axis=1).to_numpy().argmax()
    prices = prices.iloc[first_row:]
    avail = avail_df.iloc[first_row:].to_numpy()
    dates = prices.index
    T = len(dates)
    assert T >= 2, "Backtest needs at least 2 weekly dates"

    if returns_override is not None:
        rets = returns_override[cols].reindex(dates).to_numpy(dtype=float)
    else:
        rets = (prices / prices.shift(1) - 1).to_numpy(dtype=float)

    rebal_flags = calendar_rebalance_flags(dates, rule)
    fee_w = (1 + mgmt_fee) ** (1 / PERIODS_PER_YEAR) - 1
    tc = tc_bps / 1e4

    n = len(cols)
    W = np.zeros((T, n))
    nav = np.zeros(T)
    gross = np.zeros(T)
    turnover = np.zeros(T)
    fees = np.zeros(T)
    contrib = np.zeros((T, n))
    rebalance_dates, entries, exits = [], {}, {}

    held_mask = avail[0] & (target > 0)
    h = effective_targets(target, held_mask)
    for i in np.where(held_mask)[0]:
        entries[cols[i]] = dates[0]
    W[0] = h
    nav[0] = gross[0] = 100.0
    turnover[0] = h.sum()
    initial_tc = 100.0 * tc * turnover[0]
    nav[0] -= initial_tc
    fees[0] = initial_tc

    for k in range(1, T):
        r = np.nan_to_num(rets[k], nan=0.0)
        r = np.where(h > 0, r, 0.0)
        port_r = float(h @ r)
        contrib[k] = nav[k - 1] * h * r
        nav_before_fees = nav[k - 1] * (1 + port_r)
        gross[k] = gross[k - 1] * (1 + port_r)
        h_drift = h * (1 + r) / (1 + port_r) if (1 + port_r) != 0 else h

        now_avail = avail[k] & (target > 0)
        entering = now_avail & ~held_mask
        exiting = held_mask & ~avail[k]

        is_rebal = bool(rebal_flags[k])
        if rule != "drift" and (entering.any() or exiting.any()):
            is_rebal = True

        if is_rebal:
            new_h = effective_targets(target, now_avail)
        else:
            new_h = h_drift.copy()
            if exiting.any():
                new_h[exiting] = 0.0
                s = new_h.sum()
                new_h = new_h / s if s > 0 else effective_targets(target, now_avail)
            if entering.any():
                eff = effective_targets(target, now_avail)
                w_in = eff[entering].sum()
                new_h = new_h * (1 - w_in)
                new_h[entering] = eff[entering]

        for i in np.where(entering)[0]:
            entries[cols[i]] = dates[k]
        for i in np.where(exiting)[0]:
            exits[cols[i]] = dates[k]
        if is_rebal:
            rebalance_dates.append(dates[k])

        traded = float(np.abs(new_h - h_drift).sum())
        mgmt_cost = nav_before_fees * fee_w
        nav_after_mgmt = nav_before_fees - mgmt_cost
        trade_cost = nav_after_mgmt * tc * traded
        nav[k] = nav_after_mgmt - trade_cost

        turnover[k] = traded
        fees[k] = mgmt_cost + trade_cost
        W[k] = new_h
        h = new_h
        held_mask = now_avail

    idx = dates
    nav_s = pd.Series(nav, idx, name="NAV")
    return BacktestResult(
        nav=nav_s,
        gross_nav=pd.Series(gross, idx, name="Gross NAV"),
        returns=nav_s.pct_change().iloc[1:],
        weights=pd.DataFrame(W, idx, cols),
        turnover=pd.Series(turnover, idx, name="Turnover"),
        fees=pd.Series(fees, idx, name="Fees"),
        contributions=pd.DataFrame(contrib, idx, cols),
        rebalance_dates=rebalance_dates,
        entries=entries,
        exits=exits,
    )


def composite_benchmark_returns(
    instrument_prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    benchmark_of: dict[str, str | None],
) -> pd.DataFrame:
    """
    Weekly returns of each instrument's benchmark leg.

    - leg i = return of benchmark_of[i]
    - no benchmark, or benchmark without data that week → instrument's own return
    - NaN wherever the instrument itself has no data (same inclusion mask)
    """
    inst_ret = instrument_prices / instrument_prices.shift(1) - 1
    out = {}
    for col in instrument_prices.columns:
        own = inst_ret[col]
        b = benchmark_of.get(col)
        if b and b in benchmark_prices:
            bp = benchmark_prices[b].reindex(instrument_prices.index)
            leg = bp / bp.shift(1) - 1
            leg = leg.where(leg.notna(), own)
        else:
            leg = own.copy()
        leg[instrument_prices[col].isna()] = np.nan
        out[col] = leg
    return pd.DataFrame(out, index=instrument_prices.index)


def backtest_window(prices: pd.DataFrame, start: pd.Timestamp | None, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Prices from the last weekly date on or before `start` up to `end`."""
    p = prices
    if start is not None:
        before = p.loc[:start]
        first = before.index[-1] if len(before) else p.index[0]
        p = p.loc[first:]
    if end is not None:
        p = p.loc[:end]
    return p


def late_starters(prices: pd.DataFrame, start: pd.Timestamp) -> dict[str, pd.Timestamp]:
    """Instruments whose first price is after the backtest start."""
    out = {}
    for c in prices.columns:
        first = prices[c].first_valid_index()
        if first is not None and first > start:
            out[c] = first
    return out


def return_attribution(result: BacktestResult) -> pd.Series:
    """
    Contribution of each instrument to the cumulative net return, in % of the
    starting value. Instrument P&L (in NAV points) plus a 'Fees' line sum
    exactly to NAV_T / 100 - 1.
    """
    contrib = result.contributions.sum() / 100.0
    contrib["Fees"] = -result.fees.sum() / 100.0
    return contrib
