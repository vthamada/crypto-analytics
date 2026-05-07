from __future__ import annotations

from app.models.schemas import Kline, MovementPhase, MovementRegime, MovementType


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


def _pct_change(start: float, end: float) -> float:
    return ((end - start) / start * 100) if start else 0.0


def classify_movement_phase(
    klines: list[Kline],
    *,
    movement_regime: MovementRegime | None,
    recent_change_pct: float,
) -> dict:
    """Classify whether a signal is early, continuing, stretched, or neutral."""
    if len(klines) < 4:
        return {
            "movement_phase": MovementPhase.NEUTRAL,
            "phase_confidence_score": 0.25,
            "phase_reason": "historico insuficiente para fase",
            "is_late_entry_risk": False,
            "is_profit_zone_candidate": False,
            "distance_from_accumulation_zone_pct": None,
            "distance_from_breakout_pct": None,
        }

    recent = klines[-8:] if len(klines) >= 8 else klines
    closes = [candle.close for candle in recent]
    highs = [candle.high for candle in recent]
    lows = [candle.low for candle in recent]
    current_price = closes[-1]
    previous = recent[:-1]
    previous_high = max(candle.high for candle in previous)
    previous_low = min(candle.low for candle in previous)
    previous_mid = (previous_high + previous_low) / 2 if previous else current_price
    previous_range_pct = _pct_change(previous_low, previous_high)
    distance_from_accumulation_zone_pct = _pct_change(previous_mid, current_price)
    distance_from_breakout_pct = _pct_change(previous_high, current_price)
    last_volume = recent[-1].volume
    previous_avg_volume = sum(candle.volume for candle in previous) / len(previous) if previous else last_volume
    volume_expansion = last_volume >= previous_avg_volume * 1.5 if previous_avg_volume else False
    broke_previous_range = current_price > previous_high
    is_lateral_before_breakout = previous_range_pct <= 6.0
    total_move_pct = abs(_pct_change(closes[0], closes[-1]))

    phase = MovementPhase.NEUTRAL
    reason = "sem fase operacional clara"
    confidence = 0.35

    if movement_regime == MovementRegime.BREAKOUT_EXHAUSTION:
        phase = MovementPhase.EXHAUSTION
        reason = "rompimento com sinal de exaustao"
        confidence = 0.75
    elif total_move_pct >= 35 or abs(recent_change_pct) >= 35:
        phase = MovementPhase.EXTENDED
        reason = "preco distante da zona recente e movimento ja esticado"
        confidence = 0.85
    elif broke_previous_range and is_lateral_before_breakout and volume_expansion:
        phase = MovementPhase.EARLY_BREAKOUT
        reason = "rompimento acima de faixa lateral recente com expansao de volume"
        confidence = 0.85
    elif movement_regime == MovementRegime.TREND_CONTINUATION and total_move_pct >= 8:
        phase = MovementPhase.CONTINUATION
        reason = "continuidade de tendencia com deslocamento recente relevante"
        confidence = 0.70
    elif is_lateral_before_breakout and total_move_pct <= 4:
        phase = MovementPhase.ACCUMULATION
        reason = "preco lateralizado em faixa curta recente"
        confidence = 0.60

    is_late_entry_risk = phase in {
        MovementPhase.EXTENDED,
        MovementPhase.DISTRIBUTION_OR_PROFIT_ZONE,
        MovementPhase.EXHAUSTION,
    }
    is_profit_zone_candidate = phase in {
        MovementPhase.EXTENDED,
        MovementPhase.DISTRIBUTION_OR_PROFIT_ZONE,
        MovementPhase.EXHAUSTION,
    }

    return {
        "movement_phase": phase,
        "phase_confidence_score": round(confidence, 4),
        "phase_reason": reason,
        "is_late_entry_risk": is_late_entry_risk,
        "is_profit_zone_candidate": is_profit_zone_candidate,
        "distance_from_accumulation_zone_pct": round(distance_from_accumulation_zone_pct, 4),
        "distance_from_breakout_pct": round(distance_from_breakout_pct, 4),
    }


def classify_alert_moment(
    *,
    movement_phase: MovementPhase | str,
    is_late_entry_risk: bool,
    is_profit_zone_candidate: bool,
) -> tuple[str, str]:
    phase = movement_phase.value if hasattr(movement_phase, "value") else str(movement_phase)
    if is_profit_zone_candidate:
        return "profit_zone", "sinal em zona de realizacao ou movimento ja esticado"
    if is_late_entry_risk or phase == MovementPhase.EXTENDED.value:
        return "extended", "movimento avancado com risco de entrada tardia"
    if phase == MovementPhase.EARLY_BREAKOUT.value:
        return "early_breakout", "inicio de rompimento acima da faixa recente"
    if phase == MovementPhase.CONTINUATION.value:
        return "continuation", "continuidade de movimento com leitura operacional ativa"
    if phase == MovementPhase.ACCUMULATION.value:
        return "preparation", "ativo em possivel preparacao/lateralizacao"
    return "neutral", "sem momento operacional claro"
