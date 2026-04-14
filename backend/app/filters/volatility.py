from __future__ import annotations

from app.models.schemas import Kline


def calculate_volatility(klines: list[Kline], window: int | None = None) -> float:
    """Calculate price volatility as percentage change over the given klines.

    Returns the max price swing (high-low range) as a percentage of the average price.
    """
    if not klines:
        return 0.0

    subset = klines[-window:] if window else klines

    if not subset:
        return 0.0

    highs = [k.high for k in subset]
    lows = [k.low for k in subset]
    closes = [k.close for k in subset]

    max_high = max(highs)
    min_low = min(lows)
    avg_price = sum(closes) / len(closes)

    if avg_price == 0:
        return 0.0

    return ((max_high - min_low) / avg_price) * 100


def calculate_recent_change(klines: list[Kline], n: int = 5) -> float:
    """Calculate percentage change over the last n candles."""
    if len(klines) < 2:
        return 0.0

    subset = klines[-n:]
    first_close = subset[0].open
    last_close = subset[-1].close

    if first_close == 0:
        return 0.0

    return ((last_close - first_close) / first_close) * 100


def passes_volatility_filter(klines: list[Kline], min_pct: float = 2.0) -> bool:
    """Check if volatility exceeds the minimum threshold."""
    return calculate_volatility(klines) >= min_pct
