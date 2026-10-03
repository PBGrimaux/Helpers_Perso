"""Page 2 — each instrument against its benchmark."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from core import metrics as m
from ui import cache, charts, theme
from ui.components import (
    excel_button, explain, format_metric_table, kpi_row, note, page_header, price_index_notice, require_portfolio,
    section, show_metric_table, show_table,
)

page_header(
    "Instruments vs benchmarks",
    "How each line behaved against its benchmark: growth, relative performance, risk and ratios over several horizons.",
)
pf = require_portfolio()
md = st.session_state.market
rf = pf["rf"]
weekly = md.weekly

instruments = pf["instruments"]
labels = {i["symbol"]: f"{i['symbol']} — {i['name']}" for i in instruments}

c1, c2, c3 = st.columns([2.2, 2.6, 1])
sym = c1.selectbox("Instrument", list(labels), format_func=labels.get)
ins = next(i for i in instruments if i["symbol"] == sym)
bsym = ins["benchmark"]

p_full = weekly[sym].dropna()
b_full = weekly[bsym].dropna() if bsym else None
# Compare on the instrument's life; the benchmark is rebased at the same start.
horizons = m.available_horizons(p_full)
horizon = c2.segmented_control("Horizon", horizons, default=horizons[-1], required=True)
level = c3.selectbox("ES level", [0.95, 0.975, 0.99], format_func=lambda x: f"{x:.1%}")

if not pf.get("use_benchmarks", True):
    note("Benchmarks are switched off on the Portfolio page: the instrument is analysed on its own.")
elif not bsym:
    st.info("This instrument has no benchmark: only absolute metrics are shown.", icon=":material/info:")
price_index_notice(instruments, [sym])

p = m.slice_horizon(p_full, horizon)
b = None
if b_full is not None:
    b = b_full.reindex(p.index).dropna()
    if len(b) < 2:
        b = None
# When the benchmark starts later, every comparison uses the common period only.
late_bench = b is not None and b.index[0] > p.index[0]
p_cmp = p.loc[b.index[0]:] if late_bench else p
if late_bench:
    note(f"The benchmark only has data from {b.index[0]:%d.%m.%Y}: the tiles and every comparison with it cover "
         f"{b.index[0]:%d.%m.%Y} – {p.index[-1]:%d.%m.%Y}; the {sym} column covers its full window.")

# ── KPIs ─────────────────────────────────────────────────────────────────
mp = m.compute_metrics(p, rf, level, cache.bootstrap_vol(p))
mpc = m.compute_metrics(p_cmp, rf, level, cache.bootstrap_vol(p_cmp)) if late_bench else mp
mb = m.compute_metrics(b, rf, level, cache.bootstrap_vol(b)) if b is not None else {}
long_enough = not np.isnan(mpc.get("Annualised return", np.nan))
ret_key = "Annualised return" if long_enough else "Cumulative return"
kpi_row([
    ("Return p.a." if long_enough else "Return (cumulative)", mpc[ret_key], "pct", mb.get(ret_key), "normal"),
    ("Volatility", mpc["Volatility (ann.)"], "pct", mb.get("Volatility (ann.)"), "inverse"),
    ("Max drawdown", mpc["Max drawdown"], "pct", mb.get("Max drawdown"), "inverse"),
    ("Sharpe ratio", mpc["Sharpe ratio"], "ratio", mb.get("Sharpe ratio"), "normal"),
])

# ── charts ───────────────────────────────────────────────────────────────
colors = {sym: theme.PORTFOLIO}
series = {sym: m.rebase(p)}
rel = None
if b is not None:
    colors[bsym] = theme.BENCHMARK
    b_aligned = b_full.loc[b.index[0]:p.index[-1]]
    # start the benchmark line at the instrument's level on the benchmark's first date
    series[bsym] = m.rebase(b_aligned, float(series[sym].loc[b_aligned.index[0]]))
    common = pd.concat([p, b_aligned], axis=1, keys=["p", "b"]).dropna()
    rel = m.rebase(common["p"] / common["b"])
st.plotly_chart(charts.growth_chart(series, colors, rel, f"Relative performance ({sym} / {bsym}, rebased)"),
                width="stretch", config=charts.CONFIG)
if rel is not None:
    explain("relative-performance", "How to read the relative performance line ↗")

t1, t2, t3, t4 = st.tabs(["Drawdown", "Rolling return", "Rolling volatility", "Calendar years"])
with t1:
    st.plotly_chart(charts.drawdown_chart({k: m.drawdown_series(v) for k, v in series.items()}, colors),
                    width="stretch", config=charts.CONFIG)
    explain("max-drawdown")
with t2:
    rr = {k: m.rolling_return(v).dropna() for k, v in series.items()}
    st.plotly_chart(charts.lines_chart(rr, colors, "Rolling 52-week return"), width="stretch", config=charts.CONFIG)
    explain("rolling-return")
with t3:
    rv = {k: m.rolling_volatility(v).dropna() for k, v in series.items()}
    st.plotly_chart(charts.lines_chart(rv, colors, "Rolling 52-week volatility"), width="stretch", config=charts.CONFIG)
    explain("volatility")
with t4:
    cy = pd.DataFrame({k: m.calendar_year_returns(v) for k, v in series.items()})
    st.plotly_chart(charts.calendar_bars(cy, colors), width="stretch", config=charts.CONFIG)
    note("First and last years are partial.")
    explain("calendar-years")

# ── returns across horizons ──────────────────────────────────────────────
section("Returns across horizons", "weekly-data")
rows = {}
for h in horizons:
    ph = m.slice_horizon(p_full, h)
    annualise = (ph.index[-1] - ph.index[0]).days >= 364
    f = m.annualized_return_from_prices if annualise else m.cumulative_return
    rows.setdefault(sym, {})[h] = f(ph)
    if b_full is not None:
        bh = b_full.reindex(ph.index).dropna()
        if len(bh) >= 2 and bh.index[0] == ph.index[0]:
            rows.setdefault(bsym, {})[h] = f(bh)
            rows.setdefault("Difference", {})[h] = rows[sym][h] - rows[bsym][h]
ret_table = pd.DataFrame(rows).T.reindex(columns=horizons)
show_table(ret_table.map(lambda v: "–" if pd.isna(v) else f"{v:.1%}"))
note("YTD and horizons under one year: cumulative return. Longer horizons: annualised, (S_T/S_0)^(365/days) − 1.")

# ── risk & ratios ────────────────────────────────────────────────────────
section(f"Risk and ratios — {horizon}", "risk")
abs_keys = [k for k in mp if m.METRIC_FORMATS[k][0] != "Relative"]
abs_df = pd.DataFrame({sym: pd.Series(mp)}).reindex(abs_keys)
if late_bench:
    abs_df[f"{sym} from {b.index[0]:%d.%m.%Y}"] = pd.Series(mpc)
if mb:
    abs_df[bsym] = pd.Series(mb)
left, right = st.columns([1.5, 1])
with left:
    show_metric_table(format_metric_table(abs_df), height=36 * (len(abs_df) + 1) + 4)
with right:
    if b is not None:
        rel_stats = m.relative_stats(p, b, rf)
        rel_df = pd.DataFrame({f"{sym} vs {bsym}": pd.Series(rel_stats)})
        show_metric_table(format_metric_table(rel_df))
    else:
        note("No benchmark: relative statistics not available.")
note(f"Weekly data. Volatility annualised with √52. Bootstrap vol: stationary block bootstrap "
     f"(4-week blocks, 1,000 resamples), median and 90% interval. Historical VaR/ES at {level:.1%} on weekly returns.")

# ── forward-looking risk ─────────────────────────────────────────────────
section("Forward-looking risk (GARCH Monte Carlo, drift removed)", "var-es-garch")
with st.spinner("Fitting GARCH(1,1)-t and simulating 10,000 paths…"):
    g_p = cache.garch_es(p_full, level)
    g_b = cache.garch_es(b_full, level) if b_full is not None else None
cols = st.columns(2 if g_b else 1)
for col, name, g in zip(cols, [sym, bsym], [g_p, g_b]):
    if g is None:
        continue
    with col:
        st.markdown(f"**{name}** · {g['method']}")
        if len(g["table"]):
            tbl = g["table"].rename(columns={"VaR": f"VaR {level:.1%}", "ES": f"ES {level:.1%}",
                                             "Volatility": "Volatility over horizon"})
            show_table(tbl.map(lambda v: f"{v:.1%}"))
        prm = g.get("params") or {}
        parts = []
        if "drift_removed_ann" in prm:
            parts.append(f"average trend removed: {prm['drift_removed_ann']:+.1%} p.a.")
        if "nu" in prm:
            parts.append(f"today's volatility {prm['current_vol_ann']:.1%} p.a. vs long-run {prm['long_run_vol_ann']:.1%}")
            parts.append(f"persistence {prm['persistence']:.3f} · Student-t ν = {prm['nu']:.1f}")
        if parts:
            note(" · ".join(parts).capitalize())
note(f"VaR = loss not exceeded with {level:.1%} probability; ES = average loss beyond the VaR, both as a % loss. "
     "The average trend is removed so that the risk is not offset by past gains; the simulation starts from "
     "today's volatility, so these numbers move with market stress.")

excel_button(
    {"Prices (rebased)": pd.DataFrame(series), "Returns by horizon": ret_table, "Metrics": abs_df,
     "Relative": pd.DataFrame({"value": pd.Series(m.relative_stats(p, b, rf))}) if b is not None else None,
     f"GARCH {sym}": g_p["table"], f"GARCH {bsym}" if bsym else "GARCH bench": g_b["table"] if g_b else None},
    f"instrument_{sym}.xlsx", key="xl_instr",
)
