"""Page 3 — portfolio backtest vs composite benchmark, allocation, correlation, diversification."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from core import backtest as bt
from core import diversification as dv
from core import metrics as m
from ui import cache, charts, theme
from ui.components import (
    excel_button, fmt_value, format_metric_table, kpi_row, note, page_header, require_portfolio, section, show_table,
)

RULE_LABELS = {
    "drift": "Let it drift (buy and hold)",
    "weekly": "Rebalance every week",
    "monthly": "Rebalance monthly",
    "quarterly": "Rebalance quarterly",
    "semiannual": "Rebalance semi-annually",
    "annual": "Rebalance annually",
}

page_header(
    "Backtest",
    "How the allocation would have behaved, compared with the same allocation invested in each instrument's benchmark.",
)
pf = require_portfolio()
md = st.session_state.market
rf = pf["rf"]
weekly = md.weekly

ins_list = pf["instruments"]
syms = [i["symbol"] for i in ins_list]
weights = pd.Series({i["symbol"]: i["weight"] for i in ins_list})
weights = weights / weights.sum()
bench_of = {i["symbol"]: i["benchmark"] for i in ins_list}
bench_syms = sorted({b for b in bench_of.values() if b})
prices = weekly[syms]

firsts = {s: prices[s].first_valid_index() for s in syms}
earliest, full_date = min(firsts.values()), max(firsts.values())
last = weekly.index[-1]
max_start = last - pd.Timedelta(weeks=26)

# ── controls ─────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([1.2, 1.6, 1, 1])
start = c1.date_input(
    "Start date", value=min(full_date, max_start).date(), min_value=earliest.date(), max_value=max_start.date(),
    format="DD.MM.YYYY",
    help="Default: first date when every instrument has data. Earlier dates are allowed; see the note below.",
)
rule = c2.selectbox("Rebalancing", list(RULE_LABELS), format_func=RULE_LABELS.get, index=0)
fee = c3.number_input("Management fee (% p.a.)", 0.0, 5.0, 0.0, 0.05, format="%.2f",
                      help="Portfolio-level fee accrued weekly. Fund and ETF TERs are already in Yahoo prices.") / 100
tc = c4.number_input("Transaction cost (bps)", 0.0, 200.0, 0.0, 1.0, format="%.0f",
                     help="Cost per unit traded: bps × Σ|change in weight| at each rebalance or entry.")

start_ts = pd.Timestamp(start)
window = bt.backtest_window(prices, start_ts)
legs = bt.composite_benchmark_returns(prices, weekly[bench_syms] if bench_syms else pd.DataFrame(index=weekly.index), bench_of)

with st.spinner("Running backtest…"):
    res_p = cache.backtest(window, weights, rule, fee, tc)
    res_b = cache.backtest(window, weights, rule, 0.0, 0.0, legs)

t0 = res_p.nav.index[0]
late = bt.late_starters(window, t0)
msgs = []
if late:
    items = ", ".join(f"**{s}** (from {d:%d.%m.%Y})" for s, d in late.items())
    msgs.append(
        f"Some instruments have no data at the start: {items}. Until each one starts, it is **not included**: "
        "the other weights are scaled up to 100%. The composite benchmark leaves out that instrument's benchmark "
        "over the same period."
    )
no_bench = [s for s in syms if not bench_of[s]]
if no_bench:
    msgs.append(f"No benchmark for {', '.join(no_bench)}: the benchmark uses the instrument itself (zero active return).")
short_bench = [s for s in syms if bench_of[s] and weekly[bench_of[s]].first_valid_index() > max(firsts[s], t0)]
if short_bench:
    msgs.append(f"Benchmark history is shorter than the instrument for {', '.join(short_bench)}: "
                "the instrument's own return fills the gap.")
for msg in msgs:
    st.info(msg, icon=":material/info:")

nav_p = res_p.nav.rename("Portfolio")
nav_b = res_b.nav.rename("Benchmark")
colors = {"Portfolio": theme.PORTFOLIO, "Benchmark": theme.BENCHMARK}

mp = m.compute_metrics(nav_p, rf, 0.95, cache.bootstrap_vol(nav_p))
mb = m.compute_metrics(nav_b, rf, 0.95, cache.bootstrap_vol(nav_b))
kpi_row([
    ("Return p.a.", mp["Annualised return"], "pct", mb["Annualised return"], "normal"),
    ("Volatility", mp["Volatility (ann.)"], "pct", mb["Volatility (ann.)"], "inverse"),
    ("Max drawdown", mp["Max drawdown"], "pct", mb["Max drawdown"], "inverse"),
    ("Sharpe ratio", mp["Sharpe ratio"], "ratio", mb["Sharpe ratio"], "normal"),
])

series = {"Portfolio": nav_p, "Benchmark": nav_b}
st.plotly_chart(charts.growth_chart(series, colors, m.rebase(nav_p / nav_b), "Relative performance (portfolio / benchmark, rebased)"),
                width="stretch", config=charts.CONFIG)

t1, t2, t3, t4, t5 = st.tabs(["Drawdown", "Rolling return", "Rolling volatility", "Calendar years", "Data availability"])
with t1:
    st.plotly_chart(charts.drawdown_chart({k: m.drawdown_series(v) for k, v in series.items()}, colors),
                    width="stretch", config=charts.CONFIG)
with t2:
    st.plotly_chart(charts.lines_chart({k: m.rolling_return(v).dropna() for k, v in series.items()}, colors,
                                       "Rolling 52-week return"), width="stretch", config=charts.CONFIG)
with t3:
    st.plotly_chart(charts.lines_chart({k: m.rolling_volatility(v).dropna() for k, v in series.items()}, colors,
                                       "Rolling 52-week volatility"), width="stretch", config=charts.CONFIG)
with t4:
    cy = pd.DataFrame({k: m.calendar_year_returns(v) for k, v in series.items()})
    cy["Difference"] = cy["Portfolio"] - cy["Benchmark"]
    st.plotly_chart(charts.calendar_bars(cy[["Portfolio", "Benchmark"]], colors), width="stretch", config=charts.CONFIG)
    show_table(cy.T.map(lambda v: "–" if pd.isna(v) else f"{v:.1%}"))
with t5:
    av = pd.DataFrame([{"name": s, "first": firsts[s]} for s in syms])
    st.plotly_chart(charts.availability_timeline(av, t0, last), width="stretch", config=charts.CONFIG)
    note("Blue: available from the start. Orange: joins the portfolio later.")

# ── metrics ──────────────────────────────────────────────────────────────
section("Returns across horizons")
rows = {}
for h in m.available_horizons(nav_p):
    ph, bh = m.slice_horizon(nav_p, h), m.slice_horizon(nav_b, h)
    f = m.annualized_return_from_prices if (ph.index[-1] - ph.index[0]).days >= 364 else m.cumulative_return
    rows[h] = {"Portfolio": f(ph), "Benchmark": f(bh)}
    rows[h]["Difference"] = rows[h]["Portfolio"] - rows[h]["Benchmark"]
ret_table = pd.DataFrame(rows)
show_table(ret_table.map(lambda v: "–" if pd.isna(v) else f"{v:.1%}"))
note("Under one year: cumulative. Longer: annualised. 'Since inception' = since the backtest start.")

section("Risk and ratios — full backtest")
abs_keys = [k for k in mp if m.METRIC_FORMATS[k][0] != "Relative"]
abs_df = pd.DataFrame({"Portfolio": pd.Series(mp), "Benchmark": pd.Series(mb)}).reindex(abs_keys)
rel_stats = m.relative_stats(nav_p, nav_b, rf)
n_years = (res_p.nav.index[-1] - t0).days / 365.25
trading = pd.Series({
    "Annualised turnover": res_p.turnover.iloc[1:].sum() / n_years,
    "Total fees paid (% of start)": res_p.fees.sum() / 100,
    "Number of rebalances": len(res_p.rebalance_dates),
})
left, right = st.columns([1.5, 1])
with left:
    show_table(format_metric_table(abs_df), height=36 * (len(abs_df) + 1) + 4)
with right:
    show_table(format_metric_table(pd.DataFrame({"Portfolio vs benchmark": pd.Series(rel_stats)})))
    show_table(pd.DataFrame({"Trading": [fmt_value(trading.iloc[0], "pct"), fmt_value(trading.iloc[1], "pct2"),
                                         fmt_value(trading.iloc[2], "int")]}, index=trading.index))

# ── allocation ───────────────────────────────────────────────────────────
section("Allocation over time")
cat_colors = charts.category_colors(syms)
st.plotly_chart(charts.stacked_weights(res_p.weights, cat_colors), width="stretch", config=charts.CONFIG)
dates = list(res_p.weights.index)
sel = st.select_slider("Weights on date", options=dates, value=dates[-1], format_func=lambda d: f"{d:%d.%m.%Y}")
w_at = res_p.weights.loc[sel]
cmp = pd.DataFrame({"Target": weights, "Actual": w_at})
st.plotly_chart(charts.paired_bars(cmp, [theme.BENCHMARK, theme.PORTFOLIO], f"Target vs actual weights on {sel:%d.%m.%Y}"),
                width="stretch", config=charts.CONFIG)

# ── correlation & diversification ────────────────────────────────────────
section("Correlation and diversification")
d1, d2, d3 = st.columns([1.6, 1.2, 1.2])
win = d1.segmented_control("Estimation window", ["All common data", "5Y", "3Y"], default="All common data", required=True)
with_bench = d2.toggle("Include benchmarks", value=False, disabled=not bench_syms)
w_choice = d3.segmented_control("Weights", ["Target", "On selected date"], default="Target", required=True)

cols_corr = syms + ([b for b in bench_syms if b not in syms] if with_bench else [])
rets = m.simple_returns(weekly[cols_corr]).iloc[1:]
if win != "All common data":
    rets = rets.loc[last - pd.DateOffset(years=int(win[0])):]
lw_all = cache.ledoit_wolf(rets)
lw_inst = cache.ledoit_wolf(rets[syms]) if with_bench else lw_all

if lw_all is None or lw_inst is None:
    st.info("Not enough common weekly data (at least 26 weeks where every line has a price).", icon=":material/info:")
    div_df, rc = None, None
else:
    st.plotly_chart(charts.corr_heatmap(lw_all["corr"]), width="stretch", config=charts.CONFIG)
    note(f"Ledoit-Wolf shrinkage on {lw_all['n_obs']} common weeks "
         f"({lw_all['start']:%d.%m.%Y} – {lw_all['end']:%d.%m.%Y}); shrinkage intensity {lw_all['shrinkage']:.2f}.")
    w_div = weights if w_choice == "Target" else w_at
    div = dv.summary(w_div, lw_inst["cov"], lw_inst["corr"])
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Portfolio volatility", fmt_value(div["Portfolio volatility"], "pct"),
              help="From the Ledoit-Wolf covariance and the selected weights.")
    k2.metric("Diversification ratio", fmt_value(div["Diversification ratio"], "ratio"),
              help="Weighted average of individual volatilities divided by portfolio volatility. "
                   f"1 = no diversification benefit. Weighted avg. vol: {div['Weighted avg. volatility']:.1%}.")
    k3.metric("Effective nb of bets", fmt_value(div["Effective nb of bets"], "ratio"),
              help="Number of independent risk sources (Meucci, principal components). "
                   f"Out of {len(syms)} lines; effective nb of holdings {div['Effective nb of holdings']:.1f}.")
    k4.metric("Avg. correlation", fmt_value(div["Avg. pairwise correlation"], "ratio"),
              help="Weight-weighted average pairwise correlation.")
    rc = dv.risk_contributions(w_div, lw_inst["cov"])
    st.plotly_chart(charts.paired_bars(rc[["Weight", "Risk contribution"]], [theme.BENCHMARK, theme.PORTFOLIO],
                                       "Weight vs share of portfolio risk"), width="stretch", config=charts.CONFIG)
    note("A line whose share of risk is much larger than its weight dominates the portfolio's ups and downs.")
    div_df = pd.Series(div)

# ── attribution ──────────────────────────────────────────────────────────
section("Return attribution")
attrib = bt.return_attribution(res_p)
total = nav_p.iloc[-1] / 100 - 1
st.plotly_chart(charts.signed_bars(attrib, f"Contribution to the cumulative return of {total:.1%}"),
                width="stretch", config=charts.CONFIG)
note("Each line's gains and losses in % of the starting value; the lines (and fees) add up exactly to the total.")

excel_button(
    {"NAV": pd.DataFrame(series), "Weights": res_p.weights, "Returns by horizon": ret_table, "Metrics": abs_df,
     "Relative": pd.Series(rel_stats, name="value"), "Trading": trading, "Calendar years": cy,
     "Correlation": lw_all["corr"] if lw_all else None, "Risk contributions": rc,
     "Diversification": div_df, "Attribution": attrib.rename("contribution")},
    "backtest.xlsx", key="xl_bt",
)
