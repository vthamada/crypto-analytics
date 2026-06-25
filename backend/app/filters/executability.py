from __future__ import annotations

import math
from typing import Literal

from app.models.schemas import OrderBook

OpportunityType = Literal["trade", "hold", "observe", "avoid"]
DEFAULT_ORDER_SIZE_BUCKETS_BRL = (25.0, 300.0, 1_000.0, 5_000.0, 10_000.0)


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


def _finite_or_none(value: float) -> float | None:
    if not math.isfinite(value):
        return None
    return round(value, 2)


def simulate_order_size(
    order_book: OrderBook,
    *,
    order_notional_brl: float,
    max_entry_slippage_bps: float,
    max_exit_slippage_bps: float,
) -> dict[str, float | bool | str | None]:
    """Simulate if a BRL order size can enter and exit within slippage caps."""
    buy_slippage = estimate_slippage_bps(order_book, "buy", order_notional_brl)
    sell_slippage = estimate_slippage_bps(order_book, "sell", order_notional_brl)
    buy_fillable = estimate_fillable_notional(order_book, max_entry_slippage_bps, "buy")
    sell_fillable = estimate_fillable_notional(order_book, max_exit_slippage_bps, "sell")
    buy_slippage_serialized = _finite_or_none(buy_slippage)
    sell_slippage_serialized = _finite_or_none(sell_slippage)
    executable = (
        buy_slippage_serialized is not None
        and sell_slippage_serialized is not None
        and buy_slippage_serialized <= max_entry_slippage_bps
        and sell_slippage_serialized <= max_exit_slippage_bps
        and order_notional_brl <= buy_fillable
        and order_notional_brl <= sell_fillable
    )
    if executable:
        status = "operable"
    elif buy_slippage_serialized is None or sell_slippage_serialized is None:
        status = "insufficient_depth"
    elif buy_slippage_serialized > max_entry_slippage_bps or sell_slippage_serialized > max_exit_slippage_bps:
        status = "slippage_too_high"
    else:
        status = "not_fillable_within_cap"

    return {
        "notional_brl": float(order_notional_brl),
        "buy_slippage_bps": buy_slippage_serialized,
        "sell_slippage_bps": sell_slippage_serialized,
        "buy_fillable_notional_brl": round(buy_fillable, 2),
        "sell_fillable_notional_brl": round(sell_fillable, 2),
        "executable": executable,
        "status": status,
    }


def simulate_order_size_buckets(
    order_book: OrderBook,
    *,
    max_entry_slippage_bps: float,
    max_exit_slippage_bps: float,
    buckets: tuple[float, ...] = DEFAULT_ORDER_SIZE_BUCKETS_BRL,
) -> list[dict[str, float | bool | str | None]]:
    return [
        simulate_order_size(
            order_book,
            order_notional_brl=notional,
            max_entry_slippage_bps=max_entry_slippage_bps,
            max_exit_slippage_bps=max_exit_slippage_bps,
        )
        for notional in buckets
    ]


def summarize_order_size_simulations(simulations: list[dict[str, float | bool | str | None]]) -> dict[str, float | str]:
    operable_sizes = [
        float(simulation["notional_brl"])
        for simulation in simulations
        if simulation.get("executable") is True and simulation.get("notional_brl") is not None
    ]
    max_operable = max(operable_sizes, default=0.0)
    if max_operable >= 10_000:
        label = "large_operation"
    elif max_operable >= 1_000:
        label = "medium_operation"
    elif max_operable >= 25:
        label = "small_test_only"
    else:
        label = "not_operable"
    return {
        "max_operable_order_notional_brl": round(max_operable, 2),
        "operability_size_label": label,
    }


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


def calculate_trade_margin_metrics(
    *,
    volatility_pct: float,
    recent_change_pct: float,
    spread_pct: float,
    estimated_buy_slippage_bps: float | None,
    estimated_sell_slippage_bps: float | None,
    movement_type: str,
    movement_regime: str | None,
    movement_persistence_score: float | None,
) -> dict[str, float]:
    """Estimate whether the current move leaves enough net edge after friction."""
    buy_slippage_pct = (estimated_buy_slippage_bps or 0.0) / 100.0
    sell_slippage_pct = (estimated_sell_slippage_bps or 0.0) / 100.0
    operational_friction_pct = max(spread_pct, 0.0) + buy_slippage_pct + sell_slippage_pct

    gross_move_pct = max(abs(recent_change_pct), volatility_pct * 0.35, 0.0)
    movement_multiplier = {
        "strong_range": 1.0,
        "spike": 0.75,
        "weak": 0.4,
        "trap": 0.2,
    }.get(movement_type, 0.5)
    regime_multiplier = {
        "trend_continuation": 1.0,
        "breakout_clean": 0.95,
        "mean_reversion_candidate": 0.65,
        "breakout_exhaustion": 0.45,
        "illiquid_spike": 0.25,
    }.get(movement_regime or "", 0.55)
    persistence_multiplier = 0.5 + (_clamp(movement_persistence_score or 0.0) * 0.5)

    estimated_trade_margin_pct = gross_move_pct * movement_multiplier * regime_multiplier * persistence_multiplier
    estimated_net_trade_edge_pct = estimated_trade_margin_pct - operational_friction_pct
    trade_margin_score = _normalize_linear(estimated_net_trade_edge_pct, 0.0, 2.0) * 100

    return {
        "estimated_trade_margin_pct": round(estimated_trade_margin_pct, 4),
        "operational_friction_pct": round(operational_friction_pct, 4),
        "estimated_net_trade_edge_pct": round(estimated_net_trade_edge_pct, 4),
        "trade_margin_score": round(trade_margin_score, 1),
    }


def classify_opportunity_type(
    *,
    operable_signal: bool | None,
    interesting_signal: bool | None,
    executability_score: float | None,
    trade_margin_score: float | None,
    estimated_net_trade_edge_pct: float | None,
    movement_regime: str | None,
) -> OpportunityType:
    """Classify an opportunity by practical actionability, not only by score."""
    exec_score = executability_score or 0.0
    margin_score = trade_margin_score or 0.0
    net_edge = estimated_net_trade_edge_pct if estimated_net_trade_edge_pct is not None else -999.0
    risky_regime = movement_regime in {"illiquid_spike", "breakout_exhaustion"}

    if risky_regime or net_edge < 0 or exec_score < 35:
        return "avoid"
    if operable_signal and exec_score >= 60 and margin_score >= 35 and net_edge >= 0.3:
        return "trade"
    if interesting_signal and exec_score >= 55 and margin_score >= 30 and net_edge >= 0.2:
        return "hold"
    return "observe"
