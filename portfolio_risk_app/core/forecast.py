"""
Monte Carlo forecast of a portfolio with user expected returns.

Return model (weekly, per instrument i):
    log-return = μ_i + x_i,   μ_i = ln(1 + ER_i) / 52
    x ~ multivariate Student-t(ν) with covariance Σ_LW / 52 (zero mean)
so each instrument's *median* growth equals its expected return ER_i
(geometric). Σ_LW is the annualised Ledoit-Wolf covariance from history.

The simulation advances one week at a time and keeps only holdings
(paths × instruments) plus wealth and a time-weighted index (paths × weeks).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from core.backtest import calendar_rebalance_flags

PERIODS_PER_YEAR = 52
FREQUENCIES = {"One-off": 0, "Monthly": 1, "Quarterly": 3, "Annual": 12}
NU_BOUNDS = (3.0, 30.0)


def estimate_nu(prices: pd.DataFrame) -> float:
    """
    Degrees of freedom of a Student-t fitted on pooled, standardised weekly
    log returns (each instrument z-scored), clipped to NU_BOUNDS.
    """
    logret = np.log(prices).diff()
    z = ((logret - logret.mean()) / logret.std()).stack().dropna().to_numpy()
    if len(z) < 50:
        return 5.0
    nu, _, _ = stats.t.fit(z, floc=0)
    return float(np.clip(nu, *NU_BOUNDS))


def simulation_dates(start: pd.Timestamp, years: float) -> pd.DatetimeIndex:
    """t_0 = start followed by weekly Fridays over the horizon."""
    n = int(round(years * PERIODS_PER_YEAR))
    first_friday = start + pd.offsets.Week(weekday=4)
    return pd.DatetimeIndex([start]).append(pd.date_range(first_friday, periods=n, freq="W-FRI"))


def cash_flow_schedule(flows: pd.DataFrame | None, dates: pd.DatetimeIndex) -> np.ndarray:
    """
    Amount added (+) or withdrawn (−) at each simulation step.

    flows columns: Start, End, Amount, Frequency, Indexation (decimal p.a.).
    Each occurrence is booked at the first simulation date on/after it
    (never before step 1). Amounts grow with indexation from the start date.
    """
    out = np.zeros(len(dates))
    if flows is None or len(flows) == 0:
        return out
    last = dates[-1]
    for _, row in flows.iterrows():
        if pd.isna(row.get("Amount")) or pd.isna(row.get("Start")) or row["Amount"] == 0:
            continue
        start = pd.Timestamp(row["Start"])
        end = pd.Timestamp(row["End"]) if not pd.isna(row.get("End")) else last
        end = min(end, last)
        step = FREQUENCIES.get(row.get("Frequency") or "One-off", 0)
        idx_rate = float(row.get("Indexation") or 0.0)
        occ = [start] if step == 0 else list(pd.date_range(start, end, freq=pd.DateOffset(months=step)))
        for d in occ:
            if d > last:
                continue
            k = max(1, int(dates.searchsorted(d, side="left")))
            if k >= len(dates):
                continue
            years = (d - start).days / 365.25
            out[k] += float(row["Amount"]) * (1 + idx_rate) ** years
    return out


def monthly_plan(amount: float, start: pd.Timestamp, years: int, yearly_increase: float = 0.0) -> pd.DataFrame:
    """
    A regular monthly contribution (or withdrawal if negative) as one row of the
    cash-flow table: `amount` every month from `start` for `years` years,
    growing by `yearly_increase` per year. Empty frame when amount is 0.
    """
    if not amount:
        return pd.DataFrame(columns=["Start", "End", "Amount", "Frequency", "Indexation"])
    start = pd.Timestamp(start)
    end = start + pd.DateOffset(years=years) - pd.Timedelta(days=1)
    return pd.DataFrame([{"Start": start, "End": end, "Amount": float(amount),
                          "Frequency": "Monthly", "Indexation": float(yearly_increase)}])


@dataclass
class ForecastResult:
    dates: pd.DatetimeIndex
    wealth: np.ndarray            # (paths, T+1) nominal
    twr: np.ndarray               # (paths, T+1) time-weighted index (flows excluded), base 1
    flows: np.ndarray             # (T+1,) cash flow per step
    depleted: np.ndarray          # (paths,) bool
    initial: float
    inflation: float = 0.0
    params: dict = field(default_factory=dict)

    @property
    def net_invested(self) -> np.ndarray:
        return self.initial + np.cumsum(self.flows)

    def deflator(self) -> np.ndarray:
        t = np.arange(len(self.dates)) / PERIODS_PER_YEAR
        return (1 + self.inflation) ** t

    def percentiles(self, q=(5, 25, 50, 75, 95), real: bool = False) -> pd.DataFrame:
        w = self.wealth / self.deflator() if real else self.wealth
        p = np.percentile(w, q, axis=0)
        return pd.DataFrame(p.T, index=self.dates, columns=[f"P{x}" for x in q])

    def summary(self, target: float | None = None, real: bool = False) -> dict:
        T = len(self.dates) - 1
        wT = self.wealth[:, -1] / (self.deflator()[-1] if real else 1.0)
        invested = self.net_invested[-1] / (self.deflator()[-1] if real else 1.0)
        tw = self.twr
        run_max = np.maximum.accumulate(tw, axis=1)
        mdd = (tw / run_max).min(axis=1) - 1  # negative: -0.25 = fell 25% from a peak
        n_tail = max(1, int(0.05 * len(wT)))
        out = {
            "Median terminal wealth": float(np.median(wT)),
            "Mean terminal wealth": float(wT.mean()),
            "5th percentile": float(np.percentile(wT, 5)),
            "95th percentile": float(np.percentile(wT, 95)),
            "Expected shortfall (worst 5%)": float(np.sort(wT)[:n_tail].mean()),
            "Net amount invested": float(invested),
            "Median annualised return (TWR)": float(np.median(tw[:, -1]) ** (PERIODS_PER_YEAR / T) - 1),
            # meaningless when withdrawals exceed contributions (nothing left "invested")
            "P(ending below amount invested)": float((wT < invested).mean()) if invested > 0 else float("nan"),
            "P(depletion)": float(self.depleted.mean()),
            "Median max drawdown": float(np.median(mdd)),
            "Max drawdown (95th pct)": float(np.percentile(mdd, 5)),  # the 5% worst paths
        }
        if target:
            out["P(reaching target)"] = float((wT >= target).mean())
        return out


def simulate(
    weights: pd.Series,
    expected_returns: pd.Series,
    cov_annual: pd.DataFrame,
    initial: float,
    dates: pd.DatetimeIndex,
    rule: str = "drift",
    mgmt_fee: float = 0.0,
    tc_bps: float = 0.0,
    flows: np.ndarray | None = None,
    nu: float | None = 5.0,
    n_paths: int = 5000,
    inflation: float = 0.0,
    seed: int = 42,
) -> ForecastResult:
    """
    Simulate portfolio wealth.

    - drift: holdings compound freely; contributions follow current weights.
    - weekly / calendar rules: holdings reset to target weights (transaction
      cost on Σ|Δw|); contributions go in at target weights.
    - withdrawals are always taken pro rata of current holdings.
    - wealth is floored at 0 (path flagged as depleted).
    """
    cols = list(weights.index)
    w = weights.to_numpy(dtype=float)
    assert np.all(w >= 0) and w.sum() > 0
    w = w / w.sum()
    er = expected_returns.reindex(cols).to_numpy(dtype=float)
    assert not np.isnan(er).any(), "Every instrument needs an expected return"
    S = cov_annual.loc[cols, cols].to_numpy(dtype=float) / PERIODS_PER_YEAR
    L = np.linalg.cholesky(S + 1e-12 * np.eye(len(cols)))
    mu = np.log1p(er) / PERIODS_PER_YEAR

    T = len(dates) - 1
    assert T >= 1
    flows = np.zeros(T + 1) if flows is None else np.asarray(flows, dtype=float)
    rebal = calendar_rebalance_flags(dates, rule) if rule != "drift" else np.zeros(T + 1, bool)
    fee_w = (1 + mgmt_fee) ** (1 / PERIODS_PER_YEAR) - 1
    tc = tc_bps / 1e4
    t_scale = np.sqrt((nu - 2) / nu) if nu else 1.0

    rng = np.random.default_rng(seed)
    P, N = n_paths, len(cols)
    V = np.tile(initial * w, (P, 1))
    wealth = np.empty((P, T + 1), dtype=np.float32)
    twr = np.empty((P, T + 1), dtype=np.float32)
    wealth[:, 0] = initial
    twr[:, 0] = 1.0
    depleted = np.zeros(P, dtype=bool)

    for k in range(1, T + 1):
        x = rng.standard_normal((P, N)) @ L.T
        if nu:
            x *= t_scale / np.sqrt(rng.chisquare(nu, P) / nu)[:, None]
        V *= np.exp(mu + x)
        V *= 1 - fee_w

        prev = wealth[:, k - 1].astype(float)
        now = V.sum(axis=1)
        growth = np.divide(now, prev, out=np.ones(P), where=prev > 0)
        twr[:, k] = twr[:, k - 1] * growth

        cf = flows[k]
        if cf != 0:
            tot = V.sum(axis=1, keepdims=True)
            current = np.divide(V, tot, out=np.tile(w, (P, 1)), where=tot > 0)
            alloc = current if (cf < 0 or rule == "drift") else np.tile(w, (P, 1))
            V = V + cf * alloc
            gone = V.sum(axis=1) <= 0
            V[gone] = 0.0
            depleted |= gone

        if rebal[k]:
            tot = V.sum(axis=1, keepdims=True)
            tgt = tot * w
            traded = np.divide(np.abs(tgt - V).sum(axis=1, keepdims=True), tot, out=np.zeros_like(tot), where=tot > 0)
            V = tgt * (1 - tc * traded)

        wealth[:, k] = V.sum(axis=1)

    return ForecastResult(
        dates=dates, wealth=wealth, twr=twr, flows=flows, depleted=depleted,
        initial=initial, inflation=inflation,
        params={"nu": nu, "n_paths": P, "rule": rule, "mgmt_fee": mgmt_fee, "tc_bps": tc_bps},
    )
