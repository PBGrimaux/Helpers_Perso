"""Éléments de page réutilisables : en-têtes, sections, tuiles KPI, export CSV."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import streamlit as st


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.markdown(f'<p class="subtitle">{subtitle}</p>', unsafe_allow_html=True)


def section(label: str) -> None:
    st.markdown(f'<p class="section-label">{label}</p>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<p class="note">{text}</p>', unsafe_allow_html=True)


def kpi_row(items: list[tuple[str, float, Callable[[float], str], str | None]]) -> None:
    """items : (libellé, valeur, formateur, aide ou None)."""
    cols = st.columns(len(items))
    for col, (label, value, fmt, help_text) in zip(cols, items):
        col.metric(label, fmt(value), help=help_text)


def coming_soon(phase: int, content: str) -> None:
    """Page pas encore développée : indique la phase du plan qui la livrera."""
    st.info(f"Cette page sera livrée en **phase {phase}** : {content}", icon=":material/construction:")


def csv_button(df: pd.DataFrame, filename: str, key: str) -> None:
    st.download_button(
        "Télécharger en CSV", data=df.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=filename, mime="text/csv", key=key, icon=":material/download:",
    )
