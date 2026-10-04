"""
Simulateur immobilier CH / FR — point d'entrée Streamlit.

Lancement local depuis la racine du dépôt (même répertoire de travail que
Streamlit Community Cloud) :
    streamlit run simulateur_immobilier/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
APP_PACKAGES = ("core", "ui")


def _source_fingerprint() -> tuple:
    files = sorted(p for pkg in APP_PACKAGES for p in (APP_DIR / pkg).rglob("*.py"))
    return tuple((str(p), os.path.getmtime(p), os.path.getsize(p)) for p in files)


def _drop_stale_app_modules() -> None:
    """
    Streamlit ré-exécute les pages à chaque run mais garde les modules importés
    en mémoire. Après un nouveau commit (Streamlit Cloud), une page pourrait
    tourner sur une ancienne copie de core/ ou ui/. Quand l'empreinte des
    sources change, les modules de l'app sont oubliés et le cache est vidé.
    """
    current = _source_fingerprint()
    previous = getattr(sys, "_immo_app_fingerprint", None)
    loaded = [n for n in sys.modules if n.split(".")[0] in APP_PACKAGES]
    if loaded and (previous is None or previous != current):
        for name in loaded:
            del sys.modules[name]
        st.cache_data.clear()
    sys._immo_app_fingerprint = current


_drop_stale_app_modules()

from ui.state import init_state  # noqa: E402  (importé après le contrôle des modules périmés)
from ui.theme import inject_css  # noqa: E402

st.set_page_config(
    page_title="Simulateur immobilier CH / FR",
    page_icon=":material/home_work:",
    layout="wide",
)
inject_css()
init_state()

pages = [
    st.Page("views/accueil.py", title="Accueil", icon=":material/home:", default=True),
    st.Page("views/capacite_ch.py", title="Capacité d'achat CH", icon=":material/account_balance:"),
    st.Page("views/louer_vs_acheter_ch.py", title="Louer vs acheter CH", icon=":material/compare_arrows:"),
    st.Page("views/locatif_fr.py", title="Locatif France", icon=":material/apartment:"),
    st.Page("views/arbitrage.py", title="Arbitrage portefeuille", icon=":material/balance:"),
    st.Page("views/monte_carlo.py", title="Monte-Carlo", icon=":material/insights:"),
]
pg = st.navigation(pages, position="top")
pg.run()
