"""
Identifier handling: ISIN detection and resolution of tickers / ISINs to
Yahoo Finance listings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

import yfinance as yf

ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# Words in an index name that indicate dividends are reinvested.
_TOTAL_RETURN_HINTS = ("total return", "net return", "gross return", "performance", " tr ", " nr ", "(tr)", "(nr)")
# Yahoo indices that reinvest dividends although their name does not say so
# (the German DAX family are "performance" indices).
_KNOWN_TOTAL_RETURN = {"^GDAXI", "^MDAXI", "^SDAXI", "^TECDAX"}


@dataclass
class Listing:
    """One tradable line on Yahoo Finance."""

    symbol: str
    name: str = ""
    exchange: str = ""
    quote_type: str = ""
    currency: str = ""

    @property
    def label(self) -> str:
        text = f"{self.symbol} — {self.name}" if self.name else self.symbol
        detail = " · ".join(p for p in (self.exchange, self.currency, self.quote_type) if p)
        return f"{text} ({detail})" if detail else text

    @property
    def is_price_index(self) -> bool:
        """True for an index that most likely excludes dividends."""
        if self.quote_type.upper() != "INDEX" or self.symbol.upper() in _KNOWN_TOTAL_RETURN:
            return False
        name = f" {self.name.lower()} "
        return not any(h in name for h in _TOTAL_RETURN_HINTS)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Listing":
        return cls(**{k: d.get(k, "") for k in ("symbol", "name", "exchange", "quote_type", "currency")})


def is_isin(value: str) -> bool:
    """
    Check the ISIN format and its Luhn check digit.

    Letters are expanded to two digits (A=10 … Z=35) before applying Luhn.
    """
    value = value.strip().upper()
    if not ISIN_RE.match(value):
        return False
    digits = "".join(str(int(c, 36)) for c in value)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _listing_from_metadata(symbol: str) -> Listing | None:
    """Validate a ticker by fetching a few days of history and its metadata."""
    tk = yf.Ticker(symbol)
    hist = tk.history(period="1mo", auto_adjust=True)
    if hist is None or hist["Close"].dropna().empty:
        return None
    md = tk.history_metadata or {}
    return Listing(
        symbol=symbol,
        name=md.get("longName") or md.get("shortName") or "",
        exchange=md.get("fullExchangeName") or md.get("exchangeName") or "",
        quote_type=md.get("instrumentType") or "",
        currency=md.get("currency") or "",
    )


def search_listings(query: str, max_results: int = 8) -> list[Listing]:
    """Free-text / ISIN search on Yahoo Finance. Returns candidates without currency."""
    quotes = yf.Search(query, max_results=max_results, news_count=0).quotes or []
    out = []
    for q in quotes:
        if not q.get("symbol"):
            continue
        out.append(
            Listing(
                symbol=q["symbol"],
                name=q.get("longname") or q.get("shortname") or "",
                exchange=q.get("exchDisp") or q.get("exchange") or "",
                quote_type=q.get("quoteType") or "",
            )
        )
    return out


def resolve_identifier(identifier: str) -> list[Listing]:
    """
    Resolve a user identifier to candidate listings (with currency filled in).

    - ISIN: Yahoo search, every candidate validated.
    - Ticker: validated directly; if that fails, fall back to a text search.
    """
    identifier = identifier.strip()
    assert identifier, "Empty identifier"

    if not is_isin(identifier):
        direct = _listing_from_metadata(identifier.upper())
        if direct is not None:
            return [direct]

    candidates = []
    for cand in search_listings(identifier):
        full = _listing_from_metadata(cand.symbol)
        if full is None:
            continue
        # Keep the search name when metadata has none
        full.name = full.name or cand.name
        full.exchange = full.exchange or cand.exchange
        full.quote_type = full.quote_type or cand.quote_type
        candidates.append(full)
    return candidates
