from __future__ import annotations

from app.models.schemas import Kline, MovementPhase, OrderBook


def _pct_change(start: float, end: float) -> float:
    return ((end - start) / start * 100) if start else 0.0


def _notional_depth(order_book: OrderBook) -> float:
    bid_notional = sum(entry.price * entry.quantity for entry in order_book.bids[:10])
    ask_notional = sum(entry.price * entry.quantity for entry in order_book.asks[:10])
    return min(bid_notional, ask_notional)


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _classify_range_quality(
    *,
    margin_pct: float,
    reliability_score: float,
    capacity_brl: float,
    movement_phase: MovementPhase | str,
) -> str:
    if margin_pct < 5 or reliability_score < 0.2:
        return "none"
    if capacity_brl >= 10_000 and margin_pct >= 25 and reliability_score >= 0.6:
        return "high_quality_reusable_range"
    if capacity_brl >= 5_000 and margin_pct >= 15:
        return "valid_large_trade"
    if capacity_brl >= 1_000 and margin_pct >= 10:
        return "valid_medium_trade"
    if capacity_brl >= 250 and margin_pct >= 7:
        return "valid_small_trade"
    if movement_phase in {MovementPhase.ACCUMULATION, "accumulation"} and margin_pct >= 5:
        return "weak"
    return "none"


def calculate_operational_range_metrics(
    klines: list[Kline],
    *,
    order_book: OrderBook,
    movement_phase: MovementPhase | str,
    fillable_notional_within_slippage_cap: float | None,
) -> dict[str, float | int | str | None]:
    if len(klines) < 4:
        return {
            "operational_buy_zone_low": None,
            "operational_buy_zone_high": None,
            "operational_sell_zone_low": None,
            "operational_sell_zone_high": None,
            "operational_range_margin_pct": 0.0,
            "range_reuse_count": 0,
            "range_reliability_score": 0.0,
            "zone_liquidity_score": 0.0,
            "capital_capacity_estimate_brl": 0.0,
            "operational_range_quality": "none",
        }

    recent = klines[-12:] if len(klines) >= 12 else klines
    previous = recent[:-1]
    closes = [candle.close for candle in previous]
    sorted_closes = sorted(closes)
    bucket_size = max(2 if len(sorted_closes) >= 4 else 1, len(sorted_closes) // 3)
    buy_bucket = sorted_closes[:bucket_size]
    sell_bucket = sorted_closes[-bucket_size:]
    buy_zone_low = min(candle.low for candle in previous)
    buy_zone_high = max(buy_bucket)
    if movement_phase in {
        MovementPhase.EARLY_BREAKOUT,
        MovementPhase.CONTINUATION,
        MovementPhase.EXTENDED,
        "early_breakout",
        "continuation",
        "extended",
    }:
        sell_zone_low = max(max(sell_bucket), recent[-1].close * 0.95)
    else:
        sell_zone_low = min(sell_bucket)
    sell_zone_high = max(max(candle.high for candle in previous), recent[-1].close)
    margin_pct = max(_pct_change(buy_zone_high, sell_zone_low), 0.0)
    range_reuse_count = sum(1 for close in closes if buy_zone_low <= close <= sell_zone_high)
    reliability_score = range_reuse_count / len(previous) if previous else 0.0
    depth_capacity = _notional_depth(order_book)
    capacity = min(depth_capacity, fillable_notional_within_slippage_cap or depth_capacity)
    zone_liquidity_score = min(capacity / 10_000, 1.0) * 100
    quality = _classify_range_quality(
        margin_pct=margin_pct,
        reliability_score=reliability_score,
        capacity_brl=capacity,
        movement_phase=movement_phase,
    )

    return {
        "operational_buy_zone_low": round(buy_zone_low, 8),
        "operational_buy_zone_high": round(buy_zone_high, 8),
        "operational_sell_zone_low": round(sell_zone_low, 8),
        "operational_sell_zone_high": round(sell_zone_high, 8),
        "operational_range_margin_pct": round(margin_pct, 4),
        "range_reuse_count": range_reuse_count,
        "range_reliability_score": round(reliability_score, 4),
        "zone_liquidity_score": round(zone_liquidity_score, 4),
        "capital_capacity_estimate_brl": round(capacity, 2),
        "operational_range_quality": quality,
    }
