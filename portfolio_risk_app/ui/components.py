"""Reusable page elements: headers, KPI tiles, formatted tables, guards."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import streamlit as st

from core.metrics import METRIC_FORMATS
from core.export import to_excel
from ui import glossary

EXPLAIN = "Explain ↗"


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.markdown(f'<p class="subtitle">{subtitle}</p>', unsafe_allow_html=True)


def _explain_link(key: str | None, text: str = "What is this? ↗") -> str:
    """HTML link to the methodology entry (opens in a new tab, so the analysis stays open)."""
    u = glossary.url(key) if key else None
    return f'<a class="explain" href="{u}" target="_blank">{text}</a>' if u else ""


def section(label: str, explain: str | None = None) -> None:
    """Section label, optionally followed by a link to its methodology entry."""
    link = _explain_link(explain or label)
    st.markdown(f'<p class="section-label">{label}{link}</p>', unsafe_allow_html=True)


def explain(key: str, text: str = "What does this show? ↗") -> None:
    """Stand-alone small link to a methodology entry (e.g. under a chart)."""
    html = _explain_link(key, text)
    if html:
        st.markdown(f'<p class="note">{html}</p>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<p class="note">{text}</p>', unsafe_allow_html=True)


def is_missing(v) -> bool:
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def fmt_value(v, kind: str) -> str:
    if is_missing(v):
        return "–"
    if kind == "pct":
        return f"{v:.1%}" if abs(v) < 10 else f"{v:.0%}"
    if kind == "pct2":
        return f"{v:.2%}"
    if kind == "ratio":
        return f"{v:.2f}"
    if kind == "num":
        return f"{v:.2f}"
    if kind == "int":
        return f"{int(v)}"
    if kind == "date":
        return pd.Timestamp(v).strftime("%d.%m.%Y")
    if kind == "money":
        return f"{v:,.0f}".replace(",", "'")
    return str(v)


def format_metric_table(df: pd.DataFrame, formats: dict[str, str] | None = None) -> pd.DataFrame:
    """Format a metrics × columns table row by row (rows named as in METRIC_FORMATS)."""
    out = df.astype(object).copy()
    for idx in df.index:
        kind = (formats or {}).get(idx) or METRIC_FORMATS.get(idx, (None, "num"))[1]
        out.loc[idx] = [fmt_value(v, kind) for v in df.loc[idx].values]
    return out


def show_table(df: pd.DataFrame, height: int | None = None) -> None:
    kwargs = {"width": "stretch"}
    if height:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)


def show_metric_table(df: pd.DataFrame, height: int | None = None) -> None:
    """
    Table whose rows are metrics: adds a last column linking each row to its
    explanation on the Methodology page.
    """
    out = df.copy()
    out[EXPLAIN] = [glossary.url(idx) for idx in out.index]
    kwargs = {"width": "stretch"}
    if height:
        kwargs["height"] = height
    st.dataframe(
        out,
        column_config={EXPLAIN: st.column_config.LinkColumn(
            "", display_text="ⓘ Explain", width="small",
            help="Opens the explanation in a new tab — your analysis stays open here.")},
        **kwargs,
    )


def kpi_row(items: list[tuple[str, float, str, float | None, str]]) -> None:
    """
    items: (label, value, kind, benchmark_value or None, delta_color)
    The delta shows value − benchmark ("normal" = higher is better,
    "inverse" = lower is better). Each tile's ⓘ explains the metric.
    """
    cols = st.columns(len(items))
    for col, (label, value, kind, bench, delta_color) in zip(cols, items):
        delta = None
        if bench is not None and not is_missing(bench) and not is_missing(value):
            diff = value - bench
            delta = f"{diff:+.1%} vs benchmark" if kind == "pct" else f"{diff:+.2f} vs benchmark"
        col.metric(label, fmt_value(value, kind), delta=delta, delta_color=delta_color,
                   help=glossary.help_text(label))


def price_index_notice(instruments: list[dict], symbols: list[str] | None = None) -> None:
    """
    Warn when an instrument or a benchmark appears to be a price index
    (dividends excluded) and explain the consequences in context.
    `symbols` restricts the check to some instruments (default: all).
    """
    sel = [i for i in instruments if symbols is None or i["symbol"] in symbols]
    inst_px = [i["symbol"] for i in sel if i.get("price_index")]
    bench_px = [(i["symbol"], i["benchmark"]) for i in sel if i.get("benchmark") and i.get("benchmark_price_index")]
    both = {s for s, _ in bench_px} & set(inst_px)
    if not inst_px and not bench_px:
        return

    lines = []
    only_inst = [s for s in inst_px if s not in both]
    only_bench = [(s, b) for s, b in bench_px if s not in both]
    if only_inst:
        lines.append(
            f"**{', '.join(only_inst)}** appear{'s' if len(only_inst) == 1 else ''} to be a **price index**: dividends "
            "are not included. Its returns are understated by roughly its dividend yield (often 1–3% a year for "
            "equities, i.e. 10–35% of performance over ten years). Sharpe, Sortino, Calmar and alpha are understated; "
            "volatility, correlation and drawdown depth are almost unaffected, but recoveries look slower. In the "
            "backtest its contribution is understated and, when drifting, its weight shrinks too fast. An index "
            "cannot be bought: a tracker earns the dividends but pays fees."
        )
    if only_bench:
        pairs = ", ".join(f"**{b}** (benchmark of {s})" for s, b in only_bench)
        lines.append(
            f"{pairs} appear{'s' if len(only_bench) == 1 else ''} to be a **price index** while the instrument "
            "includes its dividends: the instrument gets a free head start of about the dividend yield every year. "
            "Excess return, information ratio, alpha and up-capture are flattered; tracking error, beta and "
            "correlation are barely affected."
        )
    if both:
        lines.append(
            f"For **{', '.join(sorted(both))}**, both the instrument and its benchmark appear to be price indices: the "
            "comparison between them is fair, but both understate what an investor actually earns."
        )
    lines.append(
        "**Fix:** use a total-return ticker when Yahoo has one (e.g. ^SP500TR for the S&P 500) or an accumulating ETF "
        f"tracking the index. [Price vs total-return index ↗]({glossary.url('price-vs-total-return')})"
    )
    st.warning("\n\n".join(lines), icon=":material/warning:")


def require_portfolio() -> dict:
    """Stop the page with a friendly message when no data has been loaded yet."""
    pf = st.session_state.get("portfolio")
    if not pf or st.session_state.get("market") is None:
        st.info("Start on the **Portfolio** page: enter your instruments and click **Load data**.", icon=":material/info:")
        st.page_link("pages/portfolio.py", label="Go to Portfolio", icon=":material/arrow_forward:")
        st.stop()
    return pf


def excel_button(sheets: dict, filename: str, key: str) -> None:
    clean = {k: v for k, v in sheets.items() if v is not None and len(v)}
    st.download_button(
        "Download as Excel", data=to_excel(clean), file_name=filename, key=key,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
    )


def finite_or_nan(x) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return np.nan
    return x if math.isfinite(x) else np.nan
