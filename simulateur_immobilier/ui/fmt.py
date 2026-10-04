"""
Formatage des nombres à l'affichage (sans Streamlit, donc testable).

Conventions : CHF 1'200'000 · 250 000 € · 2,3 % · 0,1767 (décimale « , »).
"""

from __future__ import annotations

import math

NNBSP = " "  # espace fine insécable (milliers en euros, avant « % » et « € »)


def _missing(v) -> bool:
    return v is None or (isinstance(v, float) and not math.isfinite(v))


def _group(v: float, decimals: int, sep: str) -> str:
    v = round(v, decimals) + 0.0  # + 0.0 évite d'afficher « −0 »
    s = f"{abs(v):,.{decimals}f}".replace(",", "§").replace(".", ",").replace("§", sep)
    return ("−" if v < 0 else "") + s


def chf(v, decimals: int = 0) -> str:
    return "–" if _missing(v) else f"CHF {_group(v, decimals, chr(39))}"


def eur(v, decimals: int = 0) -> str:
    return "–" if _missing(v) else f"{_group(v, decimals, NNBSP)}{NNBSP}€"


def pct(v, decimals: int = 1) -> str:
    """v en fraction : 0.023 → « 2,3 % »."""
    return "–" if _missing(v) else f"{_group(100 * v, decimals, chr(39))}{NNBSP}%"


def num(v, decimals: int = 2) -> str:
    return "–" if _missing(v) else _group(v, decimals, chr(39))


def years(v, decimals: int = 1) -> str:
    return "–" if _missing(v) else f"{num(v, decimals)} ans"
