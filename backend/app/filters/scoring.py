from __future__ import annotations

from app.models.schemas import (
    Ticker, OrderBook, Kline, MovementType, ScoreWeights,
)
from app.filters.volatility import calculate_volatility
from app.filters.volume import volume_score
from app.filters.liquidity import liquidity_score
from app.filters.spread import spread_score


def calculate_score(
    ticker: Ticker,
    order_book: OrderBook,
    klines: list[Kline],
    movement_type: MovementType,
    weights: ScoreWeights | None = None,
    repetition_count: int = 0,
) -> float:
    """Calculate opportunity score from 0 to 100.

    Combines volatility, volume, liquidity, spread, and repetition scores
    using configurable weights.
    """
    if weights is None:
        weights = ScoreWeights()

    # Volatility score (0-1): normalized from 0-10% range
    vol_pct = calculate_volatility(klines)
    vol_s = min(vol_pct / 10.0, 1.0)

    # Volume score (0-1)
    vol_score = volume_score(ticker)

    # Liquidity score (0-1)
    liq_score = liquidity_score(order_book)

    # Spread score (0-1)
    spr_score = spread_score(order_book)

    # Repetition score (0-1): signals that appeared multiple times are stronger
    rep_score = min(repetition_count / 5.0, 1.0)

    # Weighted combination
    raw_score = (
        vol_s * weights.volatility
        + vol_score * weights.volume
        + liq_score * weights.liquidity
        + spr_score * weights.spread
        + rep_score * weights.repetition
    )

    # Scale to 0-100
    score = raw_score * 100

    # Movement type bonus/penalty
    movement_modifiers = {
        MovementType.STRONG_RANGE: 1.15,
        MovementType.SPIKE: 1.05,
        MovementType.WEAK: 0.7,
        MovementType.TRAP: 0.5,
    }
    score *= movement_modifiers.get(movement_type, 1.0)

    return min(max(round(score, 1), 0), 100)
