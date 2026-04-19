from __future__ import annotations

from app.models.schemas import Kline, MovementRegime, MovementType


def classify_movement(klines: list[Kline]) -> MovementType:
    """Classify the recent price movement based on candle patterns.

    - STRONG_RANGE: consistent directional movement with increasing volume
    - SPIKE: sudden sharp movement (single candle) with high volume
    - WEAK: small movement, low conviction
    - TRAP: sharp move followed by reversal (wick-heavy candles)
    """
    if len(klines) < 3:
        return MovementType.WEAK

    recent = klines[-5:] if len(klines) >= 5 else klines

    # Calculate body and wick ratios
    bodies = []
    wicks = []
    directions = []
    volumes = []

    for k in recent:
        body = abs(k.close - k.open)
        full_range = k.high - k.low
        if full_range == 0:
            bodies.append(0)
            wicks.append(0)
        else:
            bodies.append(body / full_range)
            wicks.append(1 - body / full_range)

        directions.append(1 if k.close >= k.open else -1)
        volumes.append(k.volume)

    avg_body_ratio = sum(bodies) / len(bodies)
    avg_wick_ratio = sum(wicks) / len(wicks)

    # Check for consistent direction
    direction_sum = sum(directions)
    is_consistent = abs(direction_sum) >= len(recent) * 0.6

    # Check for volume trend
    if len(volumes) >= 2:
        vol_increasing = volumes[-1] > sum(volumes[:-1]) / len(volumes[:-1]) if volumes[:-1] else False
    else:
        vol_increasing = False

    # Check for spike (single candle dominates the move)
    if len(recent) >= 2:
        last_body = abs(recent[-1].close - recent[-1].open)
        prev_avg_body = sum(abs(k.close - k.open) for k in recent[:-1]) / len(recent[:-1])
        is_spike = last_body > prev_avg_body * 3 if prev_avg_body > 0 else False
    else:
        is_spike = False

    # Check for trap (reversal pattern)
    if len(recent) >= 3:
        last_dir = directions[-1]
        prev_dir = directions[-2]
        is_reversal = last_dir != prev_dir and avg_wick_ratio > 0.6
    else:
        is_reversal = False

    # Classify
    if is_reversal and avg_wick_ratio > 0.5:
        return MovementType.TRAP

    if is_spike:
        return MovementType.SPIKE

    if is_consistent and avg_body_ratio > 0.5 and vol_increasing:
        return MovementType.STRONG_RANGE

    if is_consistent and avg_body_ratio > 0.4:
        return MovementType.STRONG_RANGE

    return MovementType.WEAK


def classify_movement_regime(
    klines: list[Kline],
    *,
    spread_pct: float,
    quote_volume_24h: float,
) -> MovementRegime:
    movement_type = classify_movement(klines)
    recent = klines[-5:] if len(klines) >= 5 else klines

    if len(recent) < 2:
        return MovementRegime.MEAN_REVERSION_CANDIDATE

    closes = [candle.close for candle in recent]
    change_pct = ((closes[-1] - closes[0]) / closes[0] * 100) if closes[0] else 0.0
    last_candle = recent[-1]
    last_body = abs(last_candle.close - last_candle.open)
    recent_bodies = [abs(candle.close - candle.open) for candle in recent[:-1]] or [0.0]
    avg_body = sum(recent_bodies) / len(recent_bodies)
    exhaustion = last_body > avg_body * 2.5 and len(recent) >= 3 and recent[-1].close < recent[-2].close

    if spread_pct >= 0.8 or quote_volume_24h < 25_000:
        return MovementRegime.ILLIQUID_SPIKE
    if movement_type == MovementType.SPIKE and exhaustion:
        return MovementRegime.BREAKOUT_EXHAUSTION
    if movement_type == MovementType.SPIKE:
        return MovementRegime.BREAKOUT_CLEAN
    if movement_type == MovementType.STRONG_RANGE and abs(change_pct) >= 2.0:
        return MovementRegime.TREND_CONTINUATION
    return MovementRegime.MEAN_REVERSION_CANDIDATE
