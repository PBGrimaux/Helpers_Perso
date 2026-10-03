"""
Portfolio file (JSON) save / load and Excel export.
"""

from __future__ import annotations

import io
import json
import re

import pandas as pd

SCHEMA_VERSION = 1


def portfolio_to_json(lines: pd.DataFrame, settings: dict, listings: dict,
                      expected_returns: dict | None = None, cash_flows: pd.DataFrame | None = None) -> str:
    """Serialise the user's inputs. Dates are stored as ISO strings."""
    cf = []
    if cash_flows is not None and len(cash_flows):
        for rec in cash_flows.to_dict("records"):
            cf.append({k: (v.isoformat() if hasattr(v, "isoformat") else (None if pd.isna(v) else v))
                       for k, v in rec.items()})
    payload = {
        "schema_version": SCHEMA_VERSION,
        "settings": settings,
        "lines": lines.fillna("").to_dict("records"),
        "listings": listings,
        "expected_returns": expected_returns or {},
        "cash_flows": cf,
    }
    return json.dumps(payload, indent=2, default=str)


def portfolio_from_json(text: str) -> dict:
    data = json.loads(text)
    assert isinstance(data, dict) and "lines" in data, "Not a portfolio file"
    assert data.get("schema_version", 1) <= SCHEMA_VERSION, "File created by a newer version of the app"
    lines = pd.DataFrame(data["lines"])
    cf = pd.DataFrame(data.get("cash_flows") or [])
    for col in ("Start", "End"):
        if col in cf:
            cf[col] = pd.to_datetime(cf[col], errors="coerce").dt.date
    return {
        "lines": lines,
        "settings": data.get("settings", {}),
        "listings": data.get("listings", {}),
        "expected_returns": data.get("expected_returns", {}),
        "cash_flows": cf,
    }


def _sheet_name(name: str, used: set) -> str:
    base = re.sub(r"[\[\]\*\?/\\:]", "-", str(name))[:31] or "Sheet"
    candidate, i = base, 2
    while candidate in used:
        suffix = f" ({i})"
        candidate = base[: 31 - len(suffix)] + suffix
        i += 1
    used.add(candidate)
    return candidate


def to_excel(sheets: dict[str, pd.DataFrame | pd.Series]) -> bytes:
    """Write several tables to one .xlsx file in memory."""
    buf = io.BytesIO()
    used: set = set()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in sheets.items():
            if df is None:
                continue
            if isinstance(df, pd.Series):
                df = df.to_frame()
            df = df.copy()
            if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df.to_excel(xw, sheet_name=_sheet_name(name, used))
    return buf.getvalue()
