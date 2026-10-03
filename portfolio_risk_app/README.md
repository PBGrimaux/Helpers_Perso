# Portfolio Risk Explorer

A web app that shows the risk behind a real allocation, for users who do not code.
Enter tickers or ISINs, benchmarks and weights; the app downloads the full price
history from Yahoo Finance, converts everything into one currency, and shows:

| Page | What it answers |
|---|---|
| **Portfolio** | Inputs, ISIN/ticker lookup, data check (currency, history, warnings). Save / open a portfolio file. |
| **Instruments** | Each instrument vs its benchmark: growth, relative performance, drawdown, rolling and calendar returns, risk and ratios per horizon, forward-looking VaR/ES (GARCH-t Monte Carlo). |
| **Backtest** | The allocation vs the same allocation in benchmarks: drift or rebalancing, management and transaction fees, late-starting instruments, weights over time, Ledoit-Wolf correlations, diversification, risk and return attribution. |
| **Forecast** | Monte Carlo (multivariate Student-t, Ledoit-Wolf covariance) with your expected returns, fees, rebalancing and a cash-flow plan. |
| **Methodology** | Plain-language explanation of every metric and model. |

**Live app:** _add the `*.streamlit.app` link here after deployment._

## Run locally
From the repository root (Streamlit Community Cloud uses the same working directory):
```bash
pip install -r portfolio_risk_app/requirements.txt
streamlit run portfolio_risk_app/app.py
```
Tests (synthetic data, no network):
```bash
pytest portfolio_risk_app
```

## Deploy (free, no server to manage)
1. Push the repository to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), sign in with GitHub → **Create app** →
   repository `PBGrimaux/Helpers_Perso`, branch `main`,
   main file path `portfolio_risk_app/app.py`, Python 3.12, choose a custom subdomain.
3. Every push to `main` redeploys automatically. Share the link.

Only this folder is used: dependencies come from `portfolio_risk_app/requirements.txt` and the
theme from `portfolio_risk_app/.streamlit/config.toml` (script-level config, Streamlit ≥ 1.65).
A free app sleeps after a period without visitors; the next visitor wakes it up in ~30 s.

## Structure
```
app.py            entrypoint, top navigation
pages/            one file per page
core/             analytics (no Streamlit): data, metrics, risk models, backtest, diversification, forecast, export
ui/               theme, charts, components, session state, caching
assets/           example portfolio
tests/            pytest suite
```

## Notes
- Prices are Yahoo *adjusted* closes (dividends reinvested). Many Yahoo indices are price-only: prefer
  total-return indices or ETFs as benchmarks.
- Nothing is stored on the server; users save their portfolio as a JSON file.
- For education and discussion, not investment advice.
