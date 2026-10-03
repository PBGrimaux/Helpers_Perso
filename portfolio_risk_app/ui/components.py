"""Reusable page elements: headers, KPI tiles, formatted tables, guards."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import streamlit as st

from core.metrics import METRIC_FORMATS
from core.export import to_excel


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.markdown(f'<p class="subtitle">{subtitle}</p>', unsafe_allow_html=True)


def section(label: str) -> None:
    st.markdown(f'<p class="section-label">{label}</p>', unsafe_allow_html=True)


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


def kpi_row(items: list[tuple[str, float, str, float | None, str]]) -> None:
    """
    items: (label, value, kind, benchmark_value or None, delta_color)
    The delta shows value − benchmark ("normal" = higher is better,
    "inverse" = lower is better).
    """
    cols = st.columns(len(items))
    for col, (label, value, kind, bench, delta_color) in zip(cols, items):
        delta = None
        if bench is not None and not is_missing(bench) and not is_missing(value):
            diff = value - bench
            delta = f"{diff:+.1%} vs benchmark" if kind == "pct" else f"{diff:+.2f} vs benchmark"
        col.metric(label, fmt_value(value, kind), delta=delta, delta_color=delta_color)


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
