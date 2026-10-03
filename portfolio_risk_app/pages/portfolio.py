"""Page 1 — portfolio inputs, identifier lookup and data loading."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.export import portfolio_from_json, portfolio_to_json
from core.identifiers import Listing
from ui import cache
from ui.components import fmt_value, page_header, section, note
from ui.state import (
    BASE_CURRENCIES, MAX_INSTRUMENTS, apply_portfolio_file, bump_editors, clean_lines,
    lines_signature, load_example,
)

STALE_DAYS = 10

page_header(
    "Your portfolio",
    "Enter each instrument by ticker or ISIN, an optional benchmark and its weight. "
    "Prices come from Yahoo Finance, dividends reinvested, converted into one currency.",
)

ss = st.session_state
if ss.page_entered:
    ss.lines_base = ss.lines.copy()
    bump_editors()

# ── settings ─────────────────────────────────────────────────────────────
c1, c2, _ = st.columns([1, 1, 2])
base = c1.selectbox(
    "Base currency", BASE_CURRENCIES,
    index=BASE_CURRENCIES.index(ss.settings.get("base_currency", "CHF")),
    help="Every price is converted into this currency with daily Yahoo FX rates.",
)
rf = c2.number_input(
    "Risk-free rate (% per year)", value=float(ss.settings.get("risk_free", 0.0)) * 100,
    min_value=-2.0, max_value=15.0, step=0.25, format="%.2f",
    help="Used for Sharpe, Sortino and alpha. A constant rate in the base currency.",
)
ss.settings = ss.settings | {"base_currency": base, "risk_free": rf / 100}

# ── editor ───────────────────────────────────────────────────────────────
section("Instruments")
edited = st.data_editor(
    ss.lines_base,
    key=f"lines_editor_{ss.editor_version}",
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    column_config={
        "Instrument": st.column_config.TextColumn(
            "Instrument (ticker or ISIN)", required=True,
            help="Yahoo ticker such as CSSMI.SW, AGG, IWDA.AS — or an ISIN such as IE00B4L5Y983.",
        ),
        "Benchmark": st.column_config.TextColumn(
            "Benchmark (optional)",
            help="Ticker or ISIN. Prefer a total-return index or an ETF: most Yahoo indices exclude dividends.",
        ),
        "Weight %": st.column_config.NumberColumn("Weight %", min_value=0.0, max_value=100.0, step=0.5, format="%.2f"),
    },
)
ss.lines = edited
lines = clean_lines(edited)
total = lines["Weight %"].sum()

w1, w2, _ = st.columns([1.2, 1, 3])
ok_total = abs(total - 100) < 0.01
w1.markdown(f"**Total weight:** {total:.2f}%" + ("" if ok_total else "  ·  must equal 100%"))
if w2.button("Normalise to 100%", disabled=ok_total or total <= 0, icon=":material/balance:"):
    norm = lines.copy()
    norm["Weight %"] = norm["Weight %"] / total * 100
    ss.lines = norm
    ss.lines_base = norm.copy()
    bump_editors()
    st.rerun()


def _validate(df: pd.DataFrame) -> list[str]:
    errs = []
    if df.empty:
        errs.append("Add at least one instrument.")
    if len(df) > MAX_INSTRUMENTS:
        errs.append(f"At most {MAX_INSTRUMENTS} instruments.")
    if (df["Weight %"] < 0).any():
        errs.append("Weights cannot be negative.")
    if not df.empty and abs(df["Weight %"].sum() - 100) >= 0.01:
        errs.append(f"Weights sum to {df['Weight %'].sum():.2f}% — use **Normalise to 100%**.")
    dup = df["Instrument"].str.upper().duplicated()
    if dup.any():
        errs.append(f"Duplicate instrument: {', '.join(df.loc[dup, 'Instrument'])}.")
    return errs


def _default_pick(cands: list[dict], base_ccy: str) -> dict:
    for c in cands:
        if c.get("currency", "").upper() == base_ccy:
            return c
    return cands[0]


def _load(df: pd.DataFrame, base_ccy: str) -> None:
    identifiers = list(dict.fromkeys(list(df["Instrument"]) + [b for b in df["Benchmark"] if b]))
    with st.status("Loading data…", expanded=True) as status:
        unresolved = []
        for ident in identifiers:
            status.write(f"Looking up **{ident}**")
            try:
                cands = cache.resolve(ident)
            except Exception as exc:
                cands = []
                status.write(f"Lookup failed for {ident}: {exc}")
            ss.candidates[ident] = cands
            if not cands:
                unresolved.append(ident)
                continue
            current = ss.listings.get(ident)
            if not current or current["symbol"] not in [c["symbol"] for c in cands]:
                ss.listings[ident] = _default_pick(cands, base_ccy)
        if unresolved:
            status.update(label="Some identifiers were not found", state="error")
            st.error(
                "Not found on Yahoo Finance: " + ", ".join(f"**{u}**" for u in unresolved)
                + ". Check the spelling, or try the Yahoo ticker (for example with an exchange suffix like .SW, .L, .AS, .DE)."
            )
            return

        symbols = {ss.listings[i]["symbol"]: ss.listings[i]["currency"] for i in identifiers}
        if any(not ccy for ccy in symbols.values()):
            status.update(label="Missing currency information", state="error")
            st.error("Yahoo did not return a currency for: " + ", ".join(s for s, c in symbols.items() if not c))
            return

        status.write(f"Downloading full price history for {len(symbols)} lines and FX into {base_ccy}…")
        try:
            md = cache.market_data(tuple(sorted(symbols.items())), base_ccy)
        except Exception as exc:
            status.update(label="Download failed", state="error")
            st.error(f"Yahoo Finance did not answer ({exc}). Wait a minute and try again.")
            return

        instruments, problems = [], []
        seen = set()
        for _, row in df.iterrows():
            L = ss.listings[row["Instrument"]]
            sym = L["symbol"]
            if sym in seen:
                problems.append(f"{row['Instrument']} resolves to {sym}, which is already in the portfolio.")
                continue
            seen.add(sym)
            if sym not in md.info:
                problems.append(f"No usable price history for {row['Instrument']} ({sym}).")
                continue
            B = ss.listings.get(row["Benchmark"]) if row["Benchmark"] else None
            bsym = B["symbol"] if B and B["symbol"] in md.info else None
            if B and not bsym:
                md.warnings.append(f"Benchmark {row['Benchmark']} has no usable data: {sym} is shown without benchmark.")
            instruments.append({
                "symbol": sym,
                "identifier": row["Instrument"],
                "name": L.get("name") or sym,
                "currency": L.get("currency", ""),
                "quote_type": L.get("quote_type", ""),
                "weight": row["Weight %"] / 100,
                "benchmark": bsym,
                "benchmark_name": (B.get("name") or bsym) if bsym else None,
                "benchmark_price_index": Listing.from_dict(B).is_price_index if bsym else False,
            })
        if problems:
            status.update(label="Some instruments could not be used", state="error")
            for p in problems:
                st.error(p)
            return

        ss.market = md
        ss.portfolio = {"instruments": instruments, "base": base_ccy, "rf": ss.settings["risk_free"]}
        ss.loaded_signature = lines_signature(ss.lines, base_ccy, ss.listings)
        ss.forecast_result = None
        status.update(label="Data loaded", state="complete", expanded=False)


# ── actions ──────────────────────────────────────────────────────────────
a1, a2, a3, a4 = st.columns([1.1, 1.1, 1.1, 1.3])
if a1.button("Load data", type="primary", icon=":material/cloud_download:", width="stretch"):
    errs = _validate(lines)
    if errs:
        for e in errs:
            st.error(e)
    else:
        _load(lines, base)

if a2.button("Load example", icon=":material/auto_awesome:", width="stretch"):
    load_example()
    st.rerun()

with a3.popover("Open file", icon=":material/upload_file:", width="stretch"):
    up = st.file_uploader("Portfolio file (.json)", type=["json"], label_visibility="collapsed")
    if up is not None and ss.get("last_upload_id") != up.file_id:
        try:
            apply_portfolio_file(portfolio_from_json(up.getvalue().decode("utf-8")))
            ss.last_upload_id = up.file_id
            st.rerun()
        except Exception as exc:
            st.error(f"Could not read this file: {exc}")

a4.download_button(
    "Save portfolio", icon=":material/save:", width="stretch",
    data=portfolio_to_json(ss.lines, ss.settings, ss.listings, ss.expected_returns, ss.cash_flows),
    file_name="portfolio.json", mime="application/json",
    help="Saves instruments, benchmarks, weights, expected returns and cash flows. Open it later with **Open file**.",
)
note("Nothing is stored on the server: save your portfolio to a file to reuse it later.")

# ── loaded data summary ──────────────────────────────────────────────────
md, pf = ss.market, ss.portfolio
if md is None or pf is None:
    st.stop()

if lines_signature(ss.lines, base, ss.listings) != ss.loaded_signature:
    st.warning("Inputs changed since the last load — click **Load data** to refresh the analysis.", icon=":material/sync_problem:")

section("Loaded data")
today = pd.Timestamp.today().normalize()
rows = []
for ins in pf["instruments"]:
    info = md.info[ins["symbol"]]
    notes = []
    if ins["benchmark_price_index"]:
        notes.append("benchmark is a price index (no dividends)")
    if info.get("fx_truncated"):
        notes.append("history cut by FX availability")
    if (today - info["last_daily_date"]).days > STALE_DAYS:
        notes.append(f"last price {info['last_daily_date']:%d.%m.%Y}")
    if not ins["benchmark"]:
        notes.append("no benchmark")
    b_info = md.info.get(ins["benchmark"]) if ins["benchmark"] else None
    rows.append({
        "Ticker": ins["symbol"],
        "Name": ins["name"],
        "Weight": fmt_value(ins["weight"], "pct"),
        "Currency": ins["currency"],
        "Type": ins["quote_type"],
        "Data from": fmt_value(info["first_date"], "date"),
        "Benchmark": ins["benchmark"] or "–",
        "Benchmark from": fmt_value(b_info["first_date"], "date") if b_info else "–",
        "Notes": "; ".join(notes),
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
             column_config={"Name": st.column_config.TextColumn(width="medium"),
                            "Notes": st.column_config.TextColumn(width="large")})
note(f"Weekly prices (Friday close) in {pf['base']}. Latest week: {md.weekly.index[-1]:%d.%m.%Y}.")

for w in md.warnings:
    st.warning(w, icon=":material/warning:")

multi = {k: v for k, v in ss.candidates.items() if len(v) > 1}
if multi:
    with st.expander("Listings used for identifiers with several matches"):
        for ident, cands in multi.items():
            labels = [Listing.from_dict(c).label for c in cands]
            current = ss.listings.get(ident, cands[0])
            idx = next((i for i, c in enumerate(cands) if c["symbol"] == current["symbol"]), 0)
            choice = st.selectbox(ident, range(len(cands)), index=idx, format_func=lambda i, l=labels: l[i],
                                  key=f"pick_{ident}")
            ss.listings[ident] = cands[choice]

st.page_link("pages/instruments.py", label="Next: compare instruments with their benchmarks", icon=":material/arrow_forward:")
