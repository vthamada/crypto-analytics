from __future__ import annotations

import math
from typing import Literal

from app.models.schemas import OrderBook


def _get_entries(order_book: OrderBook, side: Literal["buy", "sell"]):
    return order_book.asks if side == "buy" else order_book.bids


def estimate_slippage_bps(
    order_book: OrderBook,
    side: Literal["buy", "sell"],
    order_notional_brl: float,
    levels: int = 10,
) -> float:
    """Estimate slippage in basis points by walking the visible book.

    For buys, consume asks from best to worst.
    For sells, consume bids from best to worst.
    """
    if order_notional_brl <= 0:
        return 0.0

    entries = _get_entries(order_book, side)[:levels]
    if not entries:
        return float("inf")

    best_price = entries[0].price
    remaining_notional = order_notional_brl
    total_quote_consumed = 0.0
    total_base_units = 0.0

    for entry in entries:
        level_notional = entry.price * entry.quantity
        taken_notional = min(level_notional, remaining_notional)
        total_quote_consumed += taken_notional
        total_base_units += taken_notional / entry.price
        remaining_notional -= taken_notional
        if remaining_notional <= 1e-9:
            break

    if remaining_notional > 1e-9 or total_base_units <= 0:
        return float("inf")

    average_execution_price = total_quote_consumed / total_base_units
    if best_price <= 0:
        return float("inf")

    if side == "buy":
        slippage = (average_execution_price - best_price) / best_price
    else:
        slippage = (best_price - average_execution_price) / best_price
    return max(slippage * 10_000, 0.0)


def estimate_fillable_notional(
    order_book: OrderBook,
    max_slippage_bps: float,
    side: Literal["buy", "sell"],
    levels: int = 10,
) -> float:
    """Estimate how much notional can be filled without exceeding a slippage cap."""
    if max_slippage_bps < 0:
        return 0.0

    entries = _get_entries(order_book, side)[:levels]
    if not entries:
        return 0.0

    best_price = entries[0].price
    if best_price <= 0:
        return 0.0

    cap_multiplier = 1 + max_slippage_bps / 10_000
    floor_multiplier = 1 - max_slippage_bps / 10_000
    fillable = 0.0

    for entry in entries:
        if side == "buy":
            if entry.price >= best_price * cap_multiplier:
                break
        else:
            if entry.price <= best_price * floor_multiplier:
                break
        fillable += entry.price * entry.quantity

    return fillable


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _normalize_linear(value: float, floor: float, ceiling: float) -> float:
    if ceiling <= floor:
        return 0.0
    return _clamp((value - floor) / (ceiling - floor))


def _normalize_inverse(value: float | None, best: float, worst: float) -> float:
    if value is None or not math.isfinite(value):
        return 0.0
    if value <= best:
        return 1.0
    if value >= worst:
        return 0.0
    return _clamp((worst - value) / (worst - best))


def calculate_executability_score(
    *,
    bid_notional_top_n: float,
    ask_notional_top_n: float,
    estimated_buy_slippage_bps: float | None,
    estimated_sell_slippage_bps: float | None,
    spread_pct: float,
    quote_volume_24h: float,
    fillable_notional_within_slippage_cap: float | None,
    order_notional_brl: float = 1_000.0,
) -> float:
    """Calculate a 0-100 executability score from book quality and exit risk."""
    min_side_notional = min(bid_notional_top_n, ask_notional_top_n)
    notional_depth_score = _normalize_linear(min_side_notional, order_notional_brl, order_notional_brl * 20)
    buy_slippage_score = _normalize_inverse(estimated_buy_slippage_bps, best=5.0, worst=60.0)
    sell_slippage_score = _normalize_inverse(estimated_sell_slippage_bps, best=5.0, worst=60.0)
    spread_score = _normalize_inverse(spread_pct, best=0.05, worst=1.0)
    volume_score = _normalize_linear(quote_volume_24h, floor=10_000.0, ceiling=500_000.0)
    fillable_ratio_score = _normalize_linear(fillable_notional_within_slippage_cap or 0.0, order_notional_brl, order_notional_brl * 2)

    raw = (
        notional_depth_score * 0.30
        + buy_slippage_score * 0.15
        + sell_slippage_score * 0.25
        + spread_score * 0.15
        + volume_score * 0.05
        + fillable_ratio_score * 0.10
    )
    return round(_clamp(raw) * 100, 1)


def rescale_slippage_bps(
    slippage_bps: float | None,
    *,
    baseline_order_notional_brl: float | None,
    target_order_notional_brl: float,
) -> float | None:
    if slippage_bps is None:
        return None
    if not baseline_order_notional_brl or baseline_order_notional_brl <= 0 or target_order_notional_brl <= 0:
        return slippage_bps

    scaling_ratio = target_order_notional_brl / baseline_order_notional_brl
    # Linear would over-penalize quickly. Use a mild square-root escalation.
    return round(slippage_bps * math.sqrt(scaling_ratio), 2)


def classify_executability_band(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 80:
        return "strong"
    if score >= 60:
        return "good"
    if score >= 40:
        return "fair"
    return "poor"
