"""
Market data: download from Yahoo Finance, convert to a base currency and
resample to weekly (W-FRI) prices.

Pipeline: daily adjusted close (local ccy) → minor-unit fix (GBp → GBP) →
× daily FX into base ccy → weekly last value (W-FRI).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import yfinance as yf

# Minor currency units quoted by Yahoo → (ISO currency, multiplier)
MINOR_UNITS = {
    "GBp": ("GBP", 0.01),
    "GBX": ("GBP", 0.01),
    "ZAc": ("ZAR", 0.01),
    "ZAC": ("ZAR", 0.01),
    "ILA": ("ILS", 0.01),
}

# Max number of days an FX rate is carried forward over a missing quote.
FX_FFILL_LIMIT = 5
WEEKLY_RULE = "W-FRI"


def normalize_currency(currency: str) -> tuple[str, float]:
    """Return (ISO currency, price multiplier) for a Yahoo currency code."""
    assert currency, "Currency code is empty"
    if currency in MINOR_UNITS:
        return MINOR_UNITS[currency]
    return currency.upper(), 1.0


def _with_retry(fn, attempts: int = 3, base_delay: float = 2.0):
    """Call fn() with exponential backoff (Yahoo rate-limits shared IPs)."""
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # yfinance raises a variety of errors
            last_exc = exc
            time.sleep(base_delay * (2**i))
    raise RuntimeError(f"Yahoo Finance download failed after {attempts} attempts: {last_exc}")


def download_close(symbols: list[str]) -> pd.DataFrame:
    """
    Download the full daily adjusted-close history for several symbols.

    Returns a DataFrame (DatetimeIndex, tz-naive) with one column per symbol.
    Rows where every symbol is NaN are dropped.
    """
    symbols = sorted(set(symbols))
    assert symbols, "No symbols to download"

    def _dl():
        df = yf.download(
            symbols,
            period="max",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if df is None or df.empty:
            raise RuntimeError("empty response")
        return df

    raw = _with_retry(_dl)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if not isinstance(raw.columns, pd.MultiIndex):
        close.columns = symbols
    close = close.reindex(columns=symbols)
    close.index = pd.DatetimeIndex(close.index).tz_localize(None).normalize()
    close = close[~close.index.duplicated(keep="last")].sort_index()
    return close.dropna(how="all")


def fx_pair(from_ccy: str, to_ccy: str) -> str:
    return f"{from_ccy}{to_ccy}=X"


def download_fx(currencies: list[str], base: str) -> pd.DataFrame:
    """
    Daily FX rates converting each currency into `base` (1 unit ccy = x base).

    Uses the direct Yahoo pair; when it is missing, crosses through USD.
    """
    needed = sorted({c for c in currencies if c != base})
    if not needed:
        return pd.DataFrame()

    direct = download_close([fx_pair(c, base) for c in needed])
    out = {}
    missing = []
    for c in needed:
        s = direct.get(fx_pair(c, base))
        if s is None or s.dropna().empty:
            missing.append(c)
        else:
            out[c] = s

    if missing:
        legs = {fx_pair(c, "USD") for c in missing if c != "USD"}
        if base != "USD":
            legs.add(fx_pair("USD", base))
        cross = download_close(sorted(legs))
        usd_to_base = cross[fx_pair("USD", base)] if base != "USD" else 1.0
        for c in missing:
            to_usd = cross[fx_pair(c, "USD")] if c != "USD" else 1.0
            s = to_usd * usd_to_base
            if isinstance(s, pd.Series) and not s.dropna().empty:
                out[c] = s
    return pd.DataFrame(out).sort_index()


def convert_to_base(
    prices: pd.DataFrame,
    currency_by_symbol: dict[str, str],
    fx: pd.DataFrame,
    base: str,
) -> pd.DataFrame:
    """
    Convert daily local-currency prices into the base currency.

    FX is aligned on each price date (carried forward at most FX_FFILL_LIMIT
    days). Dates without a usable FX rate become NaN.
    """
    out = {}
    for sym in prices.columns:
        iso, mult = normalize_currency(currency_by_symbol[sym])
        px = prices[sym] * mult
        if iso == base:
            out[sym] = px
            continue
        assert iso in fx.columns, f"No FX rate available for {iso}->{base}"
        rate = fx[iso].reindex(fx.index.union(px.index)).ffill(limit=FX_FFILL_LIMIT).reindex(px.index)
        out[sym] = px * rate
    return pd.DataFrame(out, index=prices.index)


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """
    Resample daily prices to Friday-ending weeks (last valid price of the week).

    - Gaps inside a series' life are forward-filled (holiday weeks).
    - Values before the first / after the last valid price stay NaN.
    - A trailing incomplete week (label after the last daily date) is dropped.
    """
    weekly = daily.resample(WEEKLY_RULE).last()
    if len(weekly) and weekly.index[-1] > daily.index.max():
        weekly = weekly.iloc[:-1]

    filled = weekly.ffill()
    for col in weekly.columns:
        s = weekly[col]
        first, last = s.first_valid_index(), s.last_valid_index()
        if first is None:
            filled[col] = np.nan
            continue
        filled.loc[filled.index < first, col] = np.nan
        filled.loc[filled.index > last, col] = np.nan
    return filled


@dataclass
class MarketData:
    """Weekly base-currency prices plus per-symbol information."""

    base: str
    weekly: pd.DataFrame  # columns = symbols
    info: dict[str, dict] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def load_market_data(currency_by_symbol: dict[str, str], base: str) -> MarketData:
    """Full pipeline for a set of symbols whose local currencies are known."""
    symbols = sorted(currency_by_symbol)
    daily_local = download_close(symbols)

    warnings = []
    missing = [s for s in symbols if s not in daily_local or daily_local[s].dropna().empty]
    for s in missing:
        warnings.append(f"No price history returned by Yahoo for {s}.")

    present = [s for s in symbols if s not in missing]
    isos = {normalize_currency(currency_by_symbol[s])[0] for s in present}
    fx = download_fx(sorted(isos), base)

    converted_ok = []
    for s in present:
        iso = normalize_currency(currency_by_symbol[s])[0]
        if iso != base and iso not in fx.columns:
            warnings.append(f"No FX rate {iso}→{base} on Yahoo: {s} excluded.")
        else:
            converted_ok.append(s)

    daily_base = convert_to_base(daily_local[converted_ok], currency_by_symbol, fx, base)
    weekly = to_weekly(daily_base)

    info = {}
    for s in symbols:
        if s in weekly and weekly[s].first_valid_index() is not None:
            local_first = daily_local[s].first_valid_index()
            base_first = weekly[s].first_valid_index()
            info[s] = {
                "first_date": base_first,
                "last_date": weekly[s].last_valid_index(),
                "last_daily_date": daily_local[s].last_valid_index(),
                "n_weeks": int(weekly[s].notna().sum()),
                "fx_truncated": bool(local_first is not None and base_first - local_first > pd.Timedelta(days=10)),
            }
            if info[s]["fx_truncated"]:
                warnings.append(
                    f"{s}: history starts {local_first:%d.%m.%Y} but FX into {base} is only available "
                    f"from {base_first:%d.%m.%Y}; earlier data is dropped."
                )
    return MarketData(base=base, weekly=weekly, info=info, warnings=warnings)
