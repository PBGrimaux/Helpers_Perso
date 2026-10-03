# Portfolio Risk Explorer

**Live app → [appersperso-8nnw2dvizdqujyxuezfvzk.streamlit.app](https://appersperso-8nnw2dvizdqujyxuezfvzk.streamlit.app/)**
No installation, no account, no Python: open the link in a browser.

## The problem this solves

Most private investors know *what* they own — a few ETFs, a fund, some shares — but not *how much risk* the
combination carries, nor whether each line actually does better than a simple index alternative. The usual
tools either show one instrument at a time, ignore currency effects, or require a spreadsheet and some
programming to put everything together.

Typical questions this app answers:

- *"My ETF is up 60% — is that good?"* → compared with its benchmark, over 1, 3, 5, 10 years and since inception,
  with relative performance, risk and risk-adjusted ratios.
- *"How bad can it get?"* → maximum drawdown and recovery time, Value at Risk and Expected Shortfall —
  both historical and forward-looking (a GARCH model that reacts to today's market stress).
- *"How would my allocation have behaved?"* → a backtest of the whole portfolio, letting it drift or rebalancing
  it, with fees, compared with the same allocation invested in the benchmarks.
- *"Am I really diversified?"* → correlations, the share of risk coming from each line, and the *effective
  number of bets* (ten lines can still be one single risk).
- *"Where could I be in 10 or 20 years if I invest 1'000 every month?"* → thousands of simulated futures with
  your own return assumptions, fees, monthly savings or withdrawals, and the chance of reaching a target or of
  running out of money.

Every number in the app has an **ⓘ Explain** link to a plain-language page saying what it means for an investor,
how it is computed and how to read it.

## How it works

```
Tickers / ISINs ──► Yahoo Finance (full history, dividends reinvested)
                    │
                    ├─► conversion into one base currency (daily FX), weekly prices (Friday close)
                    │
                    ├─► Instruments   each line vs its benchmark: performance, risk, ratios, GARCH-t VaR/ES
                    ├─► Backtest      allocation vs composite benchmark, drift / rebalancing, fees,
                    │                 Ledoit-Wolf correlations, diversification, attribution
                    └─► Forecast      Monte Carlo (multivariate Student-t) with expected returns,
                                      monthly investment plan and other cash flows
```

| Page | What you do / see |
|---|---|
| **Portfolio** | Enter instruments (ticker or ISIN), optional benchmarks and weights — or click *Load example*. A single instrument is fine (it is analysed as a 100% portfolio). Benchmarks are optional, and a *Compare with benchmarks* switch turns them off entirely to study the time series on their own. The app checks the data: currency, history length, price-index benchmarks, stale prices. Save the portfolio to a file and reopen it later. |
| **Instruments** | One instrument at a time vs its benchmark: growth and relative performance chart, drawdown, rolling and calendar-year returns, a full table of metrics per horizon, forward-looking risk. |
| **Backtest** | Choose a start date, rebalancing rule and fees. If an instrument did not exist yet at the start, it is left out until its first price and the other weights are scaled up — the app says so explicitly. |
| **Forecast** | Enter an expected return per instrument, an initial amount, a monthly investment (or withdrawal), other cash flows and fees; get a fan chart of possible outcomes and the probabilities that matter. |
| **Methodology** | The financial explanation of every metric and model, reachable from each ⓘ link. |

### Methods in brief
- **Volatility** with a stationary block **bootstrap** (how precisely it is known).
- **Expected Shortfall** from a **GARCH(1,1) with Student-t shocks**, simulated 10'000 times.
- **Correlations** from a **Ledoit-Wolf** shrunk covariance matrix.
- **Backtest**: weekly, drift or calendar/weekly rebalancing, management and transaction fees, late-entry
  rescaling, composite benchmark with the same inclusion dates.
- **Forecast**: multivariate **Student-t** Monte Carlo; each instrument's median growth equals your expected return.

### Data caveats
- Prices are Yahoo *adjusted* closes (dividends reinvested) for ETFs, funds and shares. Many Yahoo **indices are
  price-only** (no dividends): used as an instrument they understate performance by roughly the dividend yield;
  used as a benchmark they flatter the instrument. The app detects this and explains the consequences —
  prefer a total-return index (e.g. `^SP500TR`) or an ETF.
- Yahoo FX history starts around 2003; fund data can have gaps.
- Nothing is stored on the server: save your portfolio file to keep it.
- For education and discussion, not investment advice.

## For developers

Run locally from the repository root (Streamlit Community Cloud uses the same working directory):
```bash
pip install -r portfolio_risk_app/requirements.txt
streamlit run portfolio_risk_app/app.py
pytest portfolio_risk_app          # unit tests on synthetic data, no network
```

Deployment: Streamlit Community Cloud, repository `PBGrimaux/Helpers_Perso`, branch `main`, main file
`portfolio_risk_app/app.py`, Python 3.12. Every push to `main` redeploys automatically. The app is
self-contained in this folder: dependencies from `requirements.txt`, theme from `.streamlit/config.toml`
(script-level config, Streamlit ≥ 1.65).

```
app.py            entrypoint, top navigation
pages/            one file per page
core/             analytics without Streamlit: data, metrics, risk models, backtest, diversification, forecast, export
ui/               theme, charts, components, glossary (all explanations), session state, caching
assets/           example portfolio
tests/            pytest suite
```
