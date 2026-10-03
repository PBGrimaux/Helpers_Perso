"""Page 5 — plain-language methodology and data caveats."""

import streamlit as st

from ui.components import page_header

page_header("Methodology", "What every number means, how it is computed, and the limits of the data.")

st.markdown(
    """
### Data
- **Source.** Yahoo Finance, full available history, *adjusted* closing prices: dividends and splits are
  reinvested, so performance is total return.
- **Identifiers.** A ticker is used as is. An ISIN is looked up on Yahoo; when it matches several listings
  (exchanges / currencies) you can choose the one to use on the Portfolio page. The trading currency of a
  listing is not its currency exposure: a currency-hedged share class has its own ISIN.
- **Currency.** Daily prices are converted into the base currency with daily Yahoo FX rates (crossed through USD
  when no direct pair exists). Prices quoted in pence or cents (GBp, ZAc, ILA) are divided by 100.
  Yahoo FX history starts around 2003: older history of a foreign-currency instrument is dropped.
- **Frequency.** Daily base-currency prices are resampled to weekly Friday closes (W-FRI). An unfinished
  current week is left out.
- **Benchmarks.** Many Yahoo indices (^GSPC, ^STOXX50E, ^SSMI…) are *price* indices without dividends; they
  understate the benchmark by roughly the dividend yield. A total-return index or an ETF is a fairer benchmark.

### Performance
- **Annualised return** = (final price / first price)^(365 / number of days) − 1. Windows shorter than one
  year show the cumulative return instead, and return-based ratios are left blank.
- **Horizons.** YTD, 1, 3, 5 and 10 years, and since inception. A horizon is shown only if the instrument
  covers it entirely.

### Risk
- **Volatility** — standard deviation of weekly returns × √52.
- **Bootstrap volatility** — the weekly returns are resampled 1,000 times in blocks of about 4 weeks
  (stationary bootstrap, which keeps calm and stressed periods together). The spread of the 1,000 volatilities
  shows how precisely volatility is known: the median and a 90% interval are reported.
- **Maximum drawdown** — the largest fall from a previous peak, with the trough date and the number of
  weeks needed to recover.
- **Historical VaR / ES** — on past weekly returns: VaR is the loss not exceeded in 95% (or the chosen level)
  of weeks; Expected Shortfall (ES) is the average loss in the remaining worst weeks.
- **Forward-looking VaR / ES (GARCH Monte Carlo)** — a GARCH(1,1) model with Student-t shocks is fitted to the
  weekly log returns. It captures volatility clustering (stress follows stress) and fat tails. Starting from
  today's estimated volatility, 10,000 future paths are simulated by drawing Student-t shocks, and VaR / ES are
  read for 1 week, 1 month and 1 year. With less than two years of data the model falls back to resampling
  past returns.

### Ratios and relative statistics
- **Sharpe** = (annualised return − risk-free rate) / volatility. **Sortino** uses downside deviation
  instead of volatility. **Calmar** = annualised return / maximum drawdown.
- **Tracking error** = volatility of the weekly return difference with the benchmark.
  **Information ratio** = annualised excess return / tracking error.
- **Beta** — sensitivity to the benchmark. **Alpha (Jensen)** — return not explained by beta.
- **Up / down capture** — average return of the instrument in weeks when the benchmark rises / falls,
  relative to the benchmark's average in those weeks.

### Backtest
- **Weights.** The portfolio starts at your target weights.
  - **Drift**: holdings are never traded, weights follow prices.
  - **Weekly / monthly / quarterly / semi-annual / annual**: weights are reset to target on the last
    weekly date of each period.
- **Instruments without data yet.** Before an instrument's first price it is *not included*: the other
  target weights are scaled up to 100%. When it starts it is bought — in drift mode by selling the other
  holdings in proportion (their relative drift is kept), in rebalancing modes by a rebalance.
- **Composite benchmark.** Same weights, same rebalancing rule and same inclusion dates, with each
  instrument replaced by its benchmark. An instrument without benchmark (or before its benchmark has data)
  keeps its own return, so it adds no active return. No fees on the benchmark.
- **Fees.** Management fee: annual %, charged weekly on the portfolio value (fund and ETF fees are already
  inside Yahoo prices). Transaction cost: bps × Σ|change in weight| at each rebalance and entry.
- **Attribution.** Each line's gains and losses, in % of the starting value. Lines plus fees add up exactly to
  the cumulative return.

### Correlation and diversification
- **Ledoit-Wolf covariance.** A plain sample covariance is noisy with many instruments and few weeks;
  Ledoit-Wolf shrinks it towards a simple structure by the statistically optimal amount (the shrinkage
  intensity shown). Correlations are derived from it. It uses weeks where every line has a price.
- **Diversification ratio** = weighted average of individual volatilities / portfolio volatility (1 = none).
- **Risk contribution** — the share of portfolio volatility that comes from each line (Euler decomposition;
  the shares add up to 100%).
- **Effective number of bets** — how many independent sources of risk the portfolio really holds
  (Meucci, based on principal components). **Effective number of holdings** = 1 / Σ weight².

### Forecast
- **Model.** Weekly log returns are drawn from a multivariate Student-t distribution: fat tails, with the
  Ledoit-Wolf volatilities and correlations. The degrees of freedom ν are estimated from history
  (adjustable under *Advanced*).
- **Expected returns.** Your inputs set each instrument's *median* annual growth. The average outcome is a
  little higher than the median because of compounding.
- **Cash flows.** One-off, monthly, quarterly or annual amounts, optionally growing each year. Contributions
  are invested at target weights (current weights when drifting); withdrawals are taken pro rata. If wealth
  reaches zero the simulation counts it as depleted.
- **Outputs.** Percentile fan (5–95%, 25–75%, median), distribution of final wealth, chance of reaching a
  target, of ending below the amount invested, of running out, and the drawdown distribution.

### Limits
Past data do not predict the future. Yahoo data can contain gaps or errors, especially for funds. The models
assume the past structure of risk (volatility, correlation) remains representative. This tool is for
education and discussion, not investment advice.
"""
)
