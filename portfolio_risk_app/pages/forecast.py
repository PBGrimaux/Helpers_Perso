"""Page 4 — Monte Carlo forecast with expected returns, fees and cash flows."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from core import forecast as fc
from core import metrics as m
from ui import cache, charts
from ui import glossary
from ui.components import (
    excel_button, explain, fmt_value, note, page_header, price_index_notice, require_portfolio, section,
    show_metric_table,
)
from ui.state import CASH_FLOW_COLUMNS, bump_editors

RULE_LABELS = {
    "drift": "Let it drift",
    "weekly": "Rebalance every week",
    "monthly": "Rebalance monthly",
    "quarterly": "Rebalance quarterly",
    "semiannual": "Rebalance semi-annually",
    "annual": "Rebalance annually",
}

page_header(
    "Forecast",
    "Thousands of possible futures for your portfolio, based on the returns you expect and the risk observed in the past.",
)
pf = require_portfolio()
ss = st.session_state
md = ss.market
weekly = md.weekly
base = pf["base"]

ins_list = pf["instruments"]
syms = [i["symbol"] for i in ins_list]
weights = pd.Series({i["symbol"]: i["weight"] for i in ins_list})
weights = weights / weights.sum()

common_prices = weekly[syms].dropna()
lw = cache.ledoit_wolf(m.simple_returns(weekly[syms]).iloc[1:])
if lw is None:
    st.error("Not enough common history (26 weeks) across instruments to estimate risk.")
    st.stop()

# ── expected returns ─────────────────────────────────────────────────────
if ss.page_entered:
    bump_editors()

price_index_notice([i | {"benchmark": None} for i in ins_list])
section("Expected returns", "expected-return")
rows = []
for s in syms:
    p = weekly[s].dropna()
    hist_ret = m.annualized_return_from_prices(p) if len(p) > 52 else np.nan
    er = ss.expected_returns.get(s)
    rows.append({
        "Ticker": s,
        "Weight": f"{weights[s]:.1%}",
        "Past return p.a.": fmt_value(hist_ret, "pct"),
        "Past volatility": fmt_value(lw["cov"].loc[s, s] ** 0.5, "pct"),
        "Since": f"{p.index[0]:%Y}",
        "Expected return % p.a.": None if er is None else round(er * 100, 4),
    })
er_df = pd.DataFrame(rows)
edited_er = st.data_editor(
    er_df, key=f"er_editor_{ss.editor_version}", hide_index=True, width="stretch",
    disabled=["Ticker", "Weight", "Past return p.a.", "Past volatility", "Since"],
    column_config={
        "Expected return % p.a.": st.column_config.NumberColumn(
            min_value=-50.0, max_value=50.0, step=0.25, format="%.2f",
            help="Your expected annual return in the base currency (median growth rate).",
        ),
    },
)
for _, r in edited_er.iterrows():
    v = r["Expected return % p.a."]
    if pd.isna(v):
        ss.expected_returns.pop(r["Ticker"], None)
    else:
        ss.expected_returns[r["Ticker"]] = float(v) / 100
note("Past figures are for reference only. Volatility and correlations come from the Ledoit-Wolf covariance "
     f"over {lw['n_obs']} common weeks since {lw['start']:%d.%m.%Y}.")

# ── settings ─────────────────────────────────────────────────────────────
section("Simulation settings", "monte-carlo")
c1, c2, c3, c4 = st.columns(4)
initial = c1.number_input(f"Initial amount ({base})", min_value=0.0, value=100_000.0, step=10_000.0, format="%.0f")
years = c2.slider("Horizon (years)", 1, 40, 10)
if len(syms) == 1:
    rule = "drift"
    c3.selectbox("Rebalancing", ["Not applicable (single instrument)"], disabled=True,
                 help="With one instrument there is nothing to rebalance between.")
else:
    rule = c3.selectbox("Rebalancing", list(RULE_LABELS), format_func=RULE_LABELS.get, index=0,
                        help=glossary.help_text("Rebalancing"))
n_paths = c4.selectbox("Number of simulations", [1000, 2500, 5000, 10000], index=2)
c5, c6, c7, c8 = st.columns(4)
fee = c5.number_input("Management fee (% p.a.)", 0.0, 5.0, 0.0, 0.05, format="%.2f",
                      help=glossary.help_text("Management fee")) / 100
tc = c6.number_input("Transaction cost (bps)", 0.0, 200.0, 0.0, 1.0, format="%.0f",
                     help=glossary.help_text("Transaction cost"))
inflation = c7.number_input("Inflation (% p.a.)", -2.0, 15.0, 0.0, 0.25, format="%.2f",
                            help="Only used to show values in today's money. " + glossary.help_text("Inflation")) / 100
target = c8.number_input(f"Target wealth ({base}, optional)", min_value=0.0, value=0.0, step=10_000.0, format="%.0f")

with st.expander("Advanced"):
    nu_est = cache.estimate_nu(common_prices)
    nu = st.slider("Tail thickness: Student-t degrees of freedom (ν)", 3.0, 30.0, float(round(nu_est, 1)), 0.5,
                   help=f"Estimated from history: {nu_est:.1f}. Lower = fatter tails (more extreme weeks).")
    seed = st.number_input("Random seed", 0, 10_000, 42, 1)

# ── cash flows ───────────────────────────────────────────────────────────
section("Cash flow plan", "cash-flows")
start_date = weekly.index[-1]
first_month = (start_date + pd.offsets.MonthBegin(1)).date()
plan = ss.settings.get("monthly_plan") or {}

st.markdown(f"**Regular monthly investment** <a class=\"explain\" href=\"{glossary.url('cash-flows')}\" target=\"_blank\">What is this? ↗</a>", unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
monthly_amount = m1.number_input(
    f"Amount per month ({base})", value=float(plan.get("amount", 0.0)), step=100.0, format="%.0f",
    help="Invested every month, e.g. a savings plan. Use a negative amount for a monthly withdrawal (e.g. a pension).",
)
saved_start = pd.Timestamp(plan["start"]).date() if plan.get("start") else first_month
plan_start = m2.date_input(
    "First month", value=max(saved_start, first_month),
    min_value=first_month, format="DD.MM.YYYY",
)
plan_years = m3.number_input(
    "For how many years", min_value=1, max_value=40, value=int(min(plan.get("years", years), 40)), step=1,
    help="After this period the monthly amount stops (the simulation ends anyway at the horizon).",
)
plan_increase = m4.number_input(
    "Yearly increase (%)", min_value=-10.0, max_value=20.0, value=float(plan.get("increase", 0.0)) * 100,
    step=0.5, format="%.1f", help="The monthly amount grows by this % each year (e.g. with your salary).",
) / 100
ss.settings = ss.settings | {"monthly_plan": {
    "amount": monthly_amount, "start": str(plan_start), "years": int(plan_years), "increase": plan_increase,
}}
monthly_df = fc.monthly_plan(monthly_amount, pd.Timestamp(plan_start), int(plan_years), plan_increase)
if monthly_amount:
    n_months = 12 * min(int(plan_years), years)
    note(f"{fmt_value(abs(monthly_amount), 'money')} {base} "
         f"{'invested' if monthly_amount > 0 else 'withdrawn'} every month from {plan_start:%m.%Y} "
         f"(about {n_months} payments within the horizon"
         + (f", growing {plan_increase:.1%} a year" if plan_increase else "") + ").")

if ss.page_entered:
    ss.cash_flows_base = ss.cash_flows.copy()
with st.expander("Other cash flows: one-off amounts, quarterly or annual flows, withdrawals",
                 expanded=bool(len(ss.cash_flows_base))):
    cf_view = ss.cash_flows_base.copy()
    for c in ("Start", "End"):
        cf_view[c] = pd.to_datetime(cf_view[c], errors="coerce").dt.date
    cf_view["Indexation"] = pd.to_numeric(cf_view["Indexation"], errors="coerce") * 100
    edited_cf = st.data_editor(
        cf_view, key=f"cf_editor_{ss.editor_version}", num_rows="dynamic", hide_index=True, width="stretch",
        column_config={
            "Start": st.column_config.DateColumn("Start", format="DD.MM.YYYY", required=True),
            "End": st.column_config.DateColumn("End (optional)", format="DD.MM.YYYY"),
            "Amount": st.column_config.NumberColumn(f"Amount ({base})", format="%.0f", required=True,
                                                    help="Positive = contribution, negative = withdrawal."),
            "Frequency": st.column_config.SelectboxColumn("Frequency", options=list(fc.FREQUENCIES), required=True,
                                                          default="One-off"),
            "Indexation": st.column_config.NumberColumn("Indexation % p.a.", format="%.2f", default=0.0,
                                                        help="Yearly growth of the amount (e.g. salary or inflation)."),
        },
    )
    cf_store = edited_cf.copy()
    cf_store["Indexation"] = pd.to_numeric(cf_store["Indexation"], errors="coerce").fillna(0.0) / 100
    ss.cash_flows = cf_store.reindex(columns=CASH_FLOW_COLUMNS)
note("Contributions are invested at the target weights (current weights when drifting); "
     "withdrawals are taken pro rata from current holdings. Flows are booked on the first simulated Friday "
     "on or after their date.")

# ── run ──────────────────────────────────────────────────────────────────
missing = [s for s in syms if s not in ss.expected_returns]
flow_parts = [f for f in (monthly_df, ss.cash_flows.dropna(how="all")) if len(f)]
all_flows = pd.concat(flow_parts, ignore_index=True) if flow_parts else ss.cash_flows
inputs_sig = (tuple(sorted(ss.expected_returns.items())), initial, years, rule, n_paths, fee, tc, nu, seed,
              all_flows.to_json(), tuple(weights.round(8).items()))

run = st.button("Run simulation", type="primary", icon=":material/play_arrow:", disabled=bool(missing))
if missing:
    note(f"Enter an expected return for: {', '.join(missing)}.")

if run:
    dates = fc.simulation_dates(start_date, years)
    flows_df = all_flows.copy()
    for c in ("Start", "End"):
        flows_df[c] = pd.to_datetime(flows_df[c], errors="coerce")
    sched = fc.cash_flow_schedule(flows_df, dates)
    with st.spinner(f"Simulating {n_paths:,} paths over {years} years…"):
        res = fc.simulate(
            weights, pd.Series(ss.expected_returns), lw["cov"], initial, dates, rule=rule, mgmt_fee=fee,
            tc_bps=tc, flows=sched, nu=nu, n_paths=n_paths, inflation=inflation, seed=int(seed),
        )
    ss.forecast_result = {"res": res, "sig": inputs_sig, "target": target}

out = ss.forecast_result
if not out:
    st.stop()
res: fc.ForecastResult = out["res"]
res.inflation = inflation
if out["sig"] != inputs_sig:
    st.warning("Settings changed since the last run — click **Run simulation** to update.", icon=":material/sync_problem:")

section("Results", "forecast")
real = st.toggle("Show in today's money (inflation-adjusted)", value=False, disabled=inflation == 0)
summary = res.summary(target=target or None, real=real)
k = st.columns(4)
k[0].metric("Median final wealth", fmt_value(summary["Median terminal wealth"], "money"),
            help=f"Net amount invested: {fmt_value(summary['Net amount invested'], 'money')} {base}. "
                 + glossary.help_text("Median final wealth"))
if target:
    k[1].metric("Chance of reaching target", fmt_value(summary["P(reaching target)"], "pct"),
                help=glossary.help_text("Chance of reaching target"))
else:
    k[1].metric("Chance of ending below invested", fmt_value(summary["P(ending below amount invested)"], "pct"),
                help=glossary.help_text("Chance of ending below invested"))
k[2].metric("Chance of running out", fmt_value(summary["P(depletion)"], "pct"),
            help=glossary.help_text("Chance of running out"))
k[3].metric("Median return p.a.", fmt_value(summary["Median annualised return (TWR)"], "pct"),
            help=glossary.help_text("Median return p.a."))

pct = res.percentiles(real=real)
defl = res.deflator() if real else 1.0
invested = pd.Series(res.net_invested / defl, index=res.dates)
rng = np.random.default_rng(0)
sample_idx = rng.choice(res.wealth.shape[0], size=min(20, res.wealth.shape[0]), replace=False)
samples = res.wealth[sample_idx] / defl
st.plotly_chart(charts.fan_chart(pct, invested, samples, target or None, base), width="stretch", config=charts.CONFIG)
explain("monte-carlo", "How to read this chart ↗")

final = res.wealth[:, -1] / (res.deflator()[-1] if real else 1.0)
markers = {"Invested": summary["Net amount invested"], "Median": summary["Median terminal wealth"]}
if target:
    markers["Target"] = target
st.plotly_chart(charts.histogram(final, markers, f"Final wealth after {years} years ({base})"),
                width="stretch", config=charts.CONFIG)

kinds = {k_: ("pct" if k_.startswith(("P(", "Median annualised", "Median max", "Max drawdown")) else "money") for k_ in summary}
show_metric_table(pd.DataFrame({"Value": [fmt_value(v, kinds[k_]) for k_, v in summary.items()]}, index=list(summary)))
note(f"Model: weekly log-returns from a multivariate Student-t (ν = {res.params['nu']:.1f}) with the Ledoit-Wolf "
     "covariance; each instrument's median growth equals its expected return. "
     f"{res.params['n_paths']:,} simulations, {RULE_LABELS[res.params['rule']].lower()}, "
     f"fee {res.params['mgmt_fee']:.2%} p.a., transaction cost {res.params['tc_bps']:.0f} bps.")

excel_button(
    {"Percentiles": pct, "Summary": pd.Series(summary, name="value"),
     "Cash flows (schedule)": pd.Series(res.flows, index=res.dates, name="flow"),
     "Expected returns": pd.Series(ss.expected_returns, name="expected return")},
    "forecast.xlsx", key="xl_fc",
)
