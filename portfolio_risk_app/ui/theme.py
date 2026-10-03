"""
Visual identity: neutral, Apple-like. Colours for charts follow the validated
categorical palette (dataviz reference instance); the widget accent is set
in .streamlit/config.toml.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

TEXT = "#1D1D1F"
TEXT_SECONDARY = "#6E6E73"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F5F5F7"
GRID = "#E5E5EA"
ACCENT = "#0071E3"

# Categorical palette — fixed order, never cycled (fold the tail into "Other").
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
OTHER = "#B8B8BD"

PORTFOLIO = CATEGORICAL[0]
BENCHMARK = "#8E8E93"
RELATIVE = CATEGORICAL[1]
POSITIVE = "#2a78d6"
NEGATIVE = "#e34948"

# Sequential blue ramp (light → dark) for bands
BLUE_100, BLUE_200, BLUE_300, BLUE_550 = "#cde2fb", "#9ec5f4", "#6da7ec", "#1c5cab"
# Diverging blue ↔ gray ↔ red (correlation: negative blue, positive red)
DIVERGING = [[0.0, "#2a78d6"], [0.5, "#f0efec"], [1.0, "#e34948"]]

FONT = 'Inter, -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif'

_CSS = f"""
<style>
.block-container {{ max-width: 1240px; padding-top: 2.2rem; padding-bottom: 4rem; }}
h1, h2, h3 {{ letter-spacing: -0.02em; color: {TEXT}; }}
h1 {{ font-size: 2.4rem !important; }}
p.subtitle {{ color: {TEXT_SECONDARY}; font-size: 1.08rem; margin-top: -0.6rem; margin-bottom: 1.6rem; }}
p.note {{ color: {TEXT_SECONDARY}; font-size: 0.86rem; }}
[data-testid="stMetric"] {{
    background: {SURFACE_ALT}; border-radius: 18px; padding: 14px 18px 12px 18px;
}}
[data-testid="stMetricLabel"] p {{ color: {TEXT_SECONDARY}; font-size: 0.84rem; }}
[data-testid="stMetricValue"] {{ font-size: 1.55rem; font-weight: 600; }}
[data-testid="stExpander"] details {{ border-radius: 14px; }}
.section-label {{
    text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.75rem;
    color: {TEXT_SECONDARY}; font-weight: 600; margin: 1.6rem 0 0.2rem 0;
}}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def _template() -> go.layout.Template:
    t = go.layout.Template()
    t.layout = go.Layout(
        font=dict(family=FONT, color=TEXT, size=13),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        colorway=CATEGORICAL,
        separators=".'",
        margin=dict(l=8, r=8, t=78, b=8),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=GRID, font=dict(family=FONT, color=TEXT)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, linecolor=GRID, ticks="", zeroline=False),
        yaxis=dict(gridcolor=GRID, gridwidth=1, zeroline=False, ticks="", linecolor=GRID),
        title=dict(font=dict(size=15, color=TEXT), x=0, xanchor="left", xref="paper",
                   yref="container", y=0.985, yanchor="top"),
    )
    return t


pio.templates["apple_neutral"] = _template()
pio.templates.default = "apple_neutral"
