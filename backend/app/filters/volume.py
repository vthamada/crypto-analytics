from __future__ import annotations

from app.models.schemas import Ticker


def passes_volume_filter(
    ticker: Ticker,
    min_volume_brl: float = 10000.0,
    min_volume_brl_small: float = 3000.0,
) -> bool:
    """Check if the 24h quote volume meets the minimum threshold.

    Uses min_volume_brl for major pairs, min_volume_brl_small for altcoins.
    """
    major_bases = {"BTC", "ETH"}
    base = ticker.pair.split("_")[0].upper()

    threshold = min_volume_brl if base in major_bases else min_volume_brl_small
    return ticker.quote_volume_24h >= threshold


def volume_score(ticker: Ticker, min_volume: float = 3000.0, max_volume: float = 500000.0) -> float:
    """Return normalized volume score between 0 and 1."""
    vol = ticker.quote_volume_24h
    if vol <= min_volume:
        return 0.0
    if vol >= max_volume:
        return 1.0
    return (vol - min_volume) / (max_volume - min_volume)
