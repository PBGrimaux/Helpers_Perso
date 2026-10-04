"""
Schéma de st.session_state. Les paramètres saisis sur une page sont partagés
avec les autres (ex. le prix retenu en capacité d'achat alimente louer vs acheter).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = APP_DIR / "config"

DEFAULTS = {
    "scenario": dict,  # paramètres courants, remplis à partir de config/defaults.yaml (phase 1)
}


def init_state() -> None:
    for k, factory in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = factory()
