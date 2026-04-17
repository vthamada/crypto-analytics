from __future__ import annotations

from app.filters.scoring import calculate_score
from app.filters.volatility import calculate_recent_change, calculate_volatility
from app.filters.liquidity import calculate_notional_depth, calculate_total_notional_depth
from app.models.schemas import MovementType


def test_calculate_volatility_returns_positive_percentage(sample_klines):
    result = calculate_volatility(sample_klines)
    assert result > 0


def test_calculate_recent_change_uses_recent_window(sample_klines):
    result = calculate_recent_change(sample_klines, n=3)
    assert result > 0


def test_calculate_score_rewards_stronger_movement(sample_ticker, sample_order_book, sample_klines):
    strong = calculate_score(
        ticker=sample_ticker,
        order_book=sample_order_book,
        klines=sample_klines,
        movement_type=MovementType.STRONG_RANGE,
        repetition_count=3,
    )
    weak = calculate_score(
        ticker=sample_ticker,
        order_book=sample_order_book,
        klines=sample_klines,
        movement_type=MovementType.WEAK,
        repetition_count=3,
    )

    assert strong > weak
    assert 0 <= strong <= 100


def test_notional_liquidity_metrics_are_available(sample_order_book):
    bid_notional = calculate_notional_depth(sample_order_book, "bid")
    ask_notional = calculate_notional_depth(sample_order_book, "ask")
    total_notional = calculate_total_notional_depth(sample_order_book)

    assert bid_notional > 0
    assert ask_notional > 0
    assert total_notional == bid_notional + ask_notional
