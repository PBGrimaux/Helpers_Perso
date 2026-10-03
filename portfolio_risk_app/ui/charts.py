"""
Plotly figures. One y-scale per panel (no dual axes): relative performance
gets its own panel under the growth chart.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui import theme

CONFIG = {"displayModeBar": False, "responsive": True}
MAX_CATEGORIES = 8


def _line(x, y, name, color, width=2, dash=None, showlegend=True, hover_fmt=".1f", fill=None, fillcolor=None):
    return go.Scatter(
        x=x, y=y, name=name, mode="lines", showlegend=showlegend,
        line=dict(color=color, width=width, dash=dash), fill=fill, fillcolor=fillcolor,
        hovertemplate=f"%{{y:{hover_fmt}}}<extra>{name}</extra>",
    )


def growth_chart(series: dict[str, pd.Series], colors: dict[str, str], relative: pd.Series | None = None,
                 relative_name: str = "Relative performance") -> go.Figure:
    """Rebased growth of 100 (top) and relative performance (bottom panel)."""
    rows = 2 if relative is not None else 1
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.07,
        row_heights=[0.68, 0.32] if rows == 2 else [1.0],
        subplot_titles=("", relative_name) if rows == 2 else None,
    )
    fig.update_yaxes(title_text="Growth of 100", title_font=dict(size=12, color=theme.TEXT_SECONDARY), row=1, col=1)
    for name, s in series.items():
        fig.add_trace(_line(s.index, s.values, name, colors.get(name, theme.PORTFOLIO)), row=1, col=1)
    if relative is not None:
        fig.add_trace(_line(relative.index, relative.values, relative_name, theme.RELATIVE, showlegend=False),
                      row=2, col=1)
        fig.add_hline(y=100, line=dict(color=theme.GRID, width=1), row=2, col=1)
    fig.update_layout(height=520 if rows == 2 else 400)
    for ann in fig.layout.annotations:
        ann.update(x=0, xanchor="left", font=dict(size=13, color=theme.TEXT_SECONDARY))
    return fig


def drawdown_chart(series: dict[str, pd.Series], colors: dict[str, str]) -> go.Figure:
    fig = go.Figure()
    for i, (name, dd) in enumerate(series.items()):
        c = colors.get(name, theme.PORTFOLIO)
        fig.add_trace(_line(dd.index, dd.values, name, c, hover_fmt=".1%",
                            fill="tozeroy" if i == 0 else None,
                            fillcolor="rgba(42,120,214,0.12)" if i == 0 else None))
    fig.update_layout(height=340, yaxis_tickformat=".0%", title="Drawdown from previous peak")
    return fig


def lines_chart(series: dict[str, pd.Series], colors: dict[str, str], title: str, pct: bool = True) -> go.Figure:
    fig = go.Figure()
    for name, s in series.items():
        fig.add_trace(_line(s.index, s.values, name, colors.get(name, theme.PORTFOLIO), hover_fmt=".1%" if pct else ".2f"))
    fig.update_layout(height=320, title=title, yaxis_tickformat=".0%" if pct else None)
    return fig


def calendar_bars(df: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    """Grouped bars, one group per year."""
    fig = go.Figure()
    for name in df.columns:
        fig.add_trace(go.Bar(
            x=df.index.astype(str), y=df[name], name=name, marker_color=colors.get(name, theme.PORTFOLIO),
            marker_line_width=0, hovertemplate=f"%{{y:.1%}}<extra>{name}</extra>",
        ))
    fig.update_layout(height=340, barmode="group", bargap=0.35, bargroupgap=0.08, yaxis_tickformat=".0%",
                      title="Calendar-year returns", hovermode="x")
    return fig


def availability_timeline(rows: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> go.Figure:
    """Horizontal bars from first to last available date, per instrument."""
    fig = go.Figure()
    for _, r in rows.iterrows():
        fig.add_trace(go.Scatter(
            x=[max(r["first"], start), end], y=[r["name"], r["name"]], mode="lines",
            line=dict(color=theme.PORTFOLIO if r["first"] <= start else theme.RELATIVE, width=10),
            showlegend=False, hovertemplate=f"{r['name']}: data from {r['first']:%d.%m.%Y}<extra></extra>",
        ))
    fig.add_vline(x=start, line=dict(color=theme.TEXT_SECONDARY, width=1))
    fig.update_layout(height=60 + 34 * len(rows), title="Data availability within the backtest",
                      hovermode="closest", yaxis=dict(autorange="reversed", showgrid=False))
    return fig


def _fold_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the 7 largest (by average) and fold the rest into 'Other'."""
    if df.shape[1] <= MAX_CATEGORIES:
        return df
    order = df.mean().sort_values(ascending=False).index
    keep = list(order[: MAX_CATEGORIES - 1])
    out = df[keep].copy()
    out["Other"] = df.drop(columns=keep).sum(axis=1)
    return out


def category_colors(names: list[str]) -> dict[str, str]:
    """Stable colour per entity (assigned in input order, never by rank)."""
    out = {}
    for i, n in enumerate(names):
        out[n] = theme.CATEGORICAL[i] if i < len(theme.CATEGORICAL) else theme.OTHER
    out["Other"] = theme.OTHER
    return out


def stacked_weights(weights: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    w = _fold_categories(weights)
    fig = go.Figure()
    for name in w.columns:
        fig.add_trace(go.Scatter(
            x=w.index, y=w[name], name=name, stackgroup="one", mode="lines",
            line=dict(width=0.5, color="#FFFFFF"), fillcolor=colors.get(name, theme.OTHER),
            hovertemplate=f"%{{y:.1%}}<extra>{name}</extra>",
        ))
    fig.update_layout(height=380, yaxis=dict(tickformat=".0%", range=[0, 1]), title="Weights over time")
    return fig


def paired_bars(df: pd.DataFrame, colors: list[str], title: str, fmt: str = ".1%") -> go.Figure:
    """Horizontal grouped bars, e.g. target vs actual weight, weight vs risk."""
    fig = go.Figure()
    for col, c in zip(df.columns, colors):
        fig.add_trace(go.Bar(
            y=df.index, x=df[col], name=col, orientation="h", marker_color=c, marker_line_width=0,
            hovertemplate=f"%{{x:{fmt}}}<extra>{col}</extra>",
        ))
    fig.update_layout(
        height=90 + 44 * len(df), barmode="group", bargap=0.3, bargroupgap=0.1, hovermode="y unified",
        xaxis=dict(tickformat=fmt.replace(".1", ".0"), gridcolor=theme.GRID, showgrid=True),
        yaxis=dict(autorange="reversed", showgrid=False), title=title,
    )
    return fig


def signed_bars(s: pd.Series, title: str) -> go.Figure:
    colors = [theme.POSITIVE if v >= 0 else theme.NEGATIVE for v in s.values]
    fig = go.Figure(go.Bar(
        y=s.index, x=s.values, orientation="h", marker_color=colors, marker_line_width=0,
        text=[f"{v:+.1%}" for v in s.values], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:+.2%}<extra></extra>",
    ))
    fig.update_layout(height=90 + 40 * len(s), title=title, hovermode="closest", showlegend=False,
                      xaxis=dict(tickformat=".0%", gridcolor=theme.GRID, showgrid=True, zeroline=True,
                                 zerolinecolor=theme.TEXT_SECONDARY, zerolinewidth=1),
                      yaxis=dict(autorange="reversed", showgrid=False))
    return fig


def corr_heatmap(corr: pd.DataFrame) -> go.Figure:
    n = len(corr)
    show_text = n <= 14
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index, zmin=-1, zmax=1, colorscale=theme.DIVERGING,
        xgap=2, ygap=2, colorbar=dict(thickness=10, outlinewidth=0, tickformat=".1f"),
        text=np.round(corr.values, 2) if show_text else None,
        texttemplate="%{text:.2f}" if show_text else None, textfont=dict(size=11, color=theme.TEXT),
        hovertemplate="%{y} / %{x}: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(height=max(320, 60 + 42 * n), hovermode="closest",
                      yaxis=dict(autorange="reversed", showgrid=False), xaxis=dict(showgrid=False, side="bottom"),
                      title="Correlation (Ledoit-Wolf)")
    return fig


def fan_chart(pct: pd.DataFrame, invested: pd.Series, samples: np.ndarray | None = None,
              target: float | None = None, currency: str = "") -> go.Figure:
    x = pct.index
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=pct["P95"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=pct["P5"], fill="tonexty", fillcolor="rgba(42,120,214,0.14)", line=dict(width=0),
                             name="5–95% range", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=pct["P75"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=pct["P25"], fill="tonexty", fillcolor="rgba(42,120,214,0.28)", line=dict(width=0),
                             name="25–75% range", hoverinfo="skip"))
    if samples is not None:
        for i, path in enumerate(samples):
            fig.add_trace(go.Scatter(x=x, y=path, mode="lines", line=dict(color="rgba(110,110,115,0.35)", width=1),
                                     name="Sample paths", showlegend=(i == 0), legendgroup="samples", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=pct["P50"], mode="lines", line=dict(color=theme.BLUE_550, width=2.5), name="Median",
                             hovertemplate="%{y:,.0f}<extra>Median</extra>"))
    for col, label in (("P95", "95th pct"), ("P5", "5th pct")):
        fig.add_trace(go.Scatter(x=x, y=pct[col], mode="lines", line=dict(width=0), showlegend=False,
                                 hovertemplate=f"%{{y:,.0f}}<extra>{label}</extra>"))
    fig.add_trace(go.Scatter(x=invested.index, y=invested.values, mode="lines",
                             line=dict(color=theme.TEXT, width=1.5, dash="dot"), name="Net amount invested",
                             hovertemplate="%{y:,.0f}<extra>Invested</extra>"))
    if target:
        fig.add_hline(y=target, line=dict(color=theme.RELATIVE, width=1.5),
                      annotation_text="Target", annotation_position="top left")
    fig.update_layout(height=480, yaxis=dict(tickformat=",.0f", title=currency), title="Projected wealth")
    return fig


def histogram(values: np.ndarray, markers: dict[str, float], title: str) -> go.Figure:
    lo, hi = np.percentile(values, [0.5, 99.5])
    v = values[(values >= lo) & (values <= hi)]
    fig = go.Figure(go.Histogram(x=v, nbinsx=60, marker_color=theme.PORTFOLIO, marker_line=dict(color="#FFFFFF", width=1),
                                 hovertemplate="%{x:,.0f}: %{y} paths<extra></extra>"))
    for i, (label, x) in enumerate(markers.items()):
        fig.add_vline(x=x, line=dict(color=theme.TEXT if i == 0 else theme.RELATIVE, width=1.5),
                      annotation_text=label, annotation_position="top right" if i % 2 == 0 else "top left",
                      annotation_font=dict(size=11, color=theme.TEXT_SECONDARY))
    fig.update_layout(height=340, title=title, showlegend=False, hovermode="closest", bargap=0.02,
                      xaxis=dict(tickformat=",.0f"))
    return fig
