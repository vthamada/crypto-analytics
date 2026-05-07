from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.filters.movement import classify_movement_phase
from app.models.schemas import Kline, MovementPhase, MovementRegime


def make_kline(index: int, open_price: float, close_price: float, volume: float = 1000) -> Kline:
    now = datetime.now(timezone.utc)
    high = max(open_price, close_price) * 1.01
    low = min(open_price, close_price) * 0.99
    return Kline(
        open_time=now + timedelta(minutes=index * 5),
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=volume,
    )


def test_classify_movement_phase_detects_early_breakout_after_lateralization():
    klines = [
        make_kline(0, 10.0, 10.1, 900),
        make_kline(1, 10.1, 9.9, 850),
        make_kline(2, 9.9, 10.2, 950),
        make_kline(3, 10.0, 10.1, 1000),
        make_kline(4, 10.2, 11.4, 2600),
    ]

    phase = classify_movement_phase(
        klines,
        movement_regime=MovementRegime.BREAKOUT_CLEAN,
        recent_change_pct=11.8,
    )

    assert phase["movement_phase"] == MovementPhase.EARLY_BREAKOUT
    assert phase["is_late_entry_risk"] is False
    assert phase["distance_from_breakout_pct"] > 0


def test_classify_movement_phase_flags_extended_late_entry():
    klines = [
        make_kline(0, 10.0, 10.2, 900),
        make_kline(1, 10.2, 11.0, 1200),
        make_kline(2, 11.0, 12.5, 1400),
        make_kline(3, 12.5, 14.5, 1600),
        make_kline(4, 14.5, 16.8, 1700),
    ]

    phase = classify_movement_phase(
        klines,
        movement_regime=MovementRegime.TREND_CONTINUATION,
        recent_change_pct=64.7,
    )

    assert phase["movement_phase"] == MovementPhase.EXTENDED
    assert phase["is_late_entry_risk"] is True
    assert phase["is_profit_zone_candidate"] is True
