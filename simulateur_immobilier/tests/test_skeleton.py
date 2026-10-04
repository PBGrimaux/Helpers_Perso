"""Tests du squelette : formatage des nombres et indépendance de core/ vis-à-vis de Streamlit."""

import ast
from pathlib import Path

from ui import fmt

APP_DIR = Path(__file__).resolve().parent.parent


def test_chf_eur_pct_formats():
    assert fmt.chf(1_200_000) == "CHF 1'200'000"
    assert fmt.eur(250_000) == f"250{fmt.NNBSP}000{fmt.NNBSP}€"
    assert fmt.eur(-8_739) == f"−8{fmt.NNBSP}739{fmt.NNBSP}€"
    assert fmt.pct(0.023) == f"2,3{fmt.NNBSP}%"
    assert fmt.num(0.17667, 4) == "0,1767"
    assert fmt.chf(-0.4) == "CHF 0"
    assert fmt.chf(float("nan")) == "–"


def test_core_does_not_import_streamlit():
    for path in (APP_DIR / "core").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            assert not any(n.split(".")[0] == "streamlit" for n in names), path
