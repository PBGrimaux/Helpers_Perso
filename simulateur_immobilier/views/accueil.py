"""Accueil : les trois questions de l'application et le plan des pages."""

from __future__ import annotations

import streamlit as st

from ui.components import note, page_header, section

page_header(
    "Simulateur immobilier CH / FR",
    "Résidence principale à Genève, locatif en France, et la même somme investie en bourse : "
    "trois façons d'utiliser son épargne, comparées sur vos propres chiffres.",
)

section("Trois questions")
c1, c2, c3 = st.columns(3)
with c1.container(border=True):
    st.markdown("**Combien puis-je acheter ?**\n\nPrix maximal, contrainte active, cash nécessaire, part LPP mobilisable.")
with c2.container(border=True):
    st.markdown("**Combien cela coûte vraiment ?**\n\nCoût d'usage, flux mensuels et annuels, impôts des deux pays, TRI.")
with c3.container(border=True):
    st.markdown("**Que vaut la décision ?**\n\nPatrimoine acheteur vs locataire investisseur, point mort, sensibilités, Monte-Carlo.")

section("Pages")
st.page_link("views/capacite_ch.py", label="Capacité d'achat CH", icon=":material/account_balance:")
st.page_link("views/louer_vs_acheter_ch.py", label="Louer vs acheter CH", icon=":material/compare_arrows:")
st.page_link("views/locatif_fr.py", label="Locatif France", icon=":material/apartment:")
st.page_link("views/arbitrage.py", label="Arbitrage portefeuille", icon=":material/balance:")
st.page_link("views/monte_carlo.py", label="Monte-Carlo", icon=":material/insights:")

note("Règles en vigueur en octobre 2026. Document de compréhension : ne constitue pas un conseil fiscal, "
     "juridique ou financier.")
