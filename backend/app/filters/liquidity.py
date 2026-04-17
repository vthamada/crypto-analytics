from __future__ import annotations

from typing import Literal

from app.models.schemas import OrderBook


def calculate_liquidity(order_book: OrderBook, depth: int = 10) -> float:
    """Calculate liquidity as total quantity available in top N bid+ask levels."""
    bid_qty = sum(b.quantity for b in order_book.bids[:depth])
    ask_qty = sum(a.quantity for a in order_book.asks[:depth])
    return bid_qty + ask_qty


def passes_liquidity_filter(order_book: OrderBook, min_units: float = 1000.0) -> bool:
    """Check if total liquidity (bid+ask quantity) meets the minimum."""
    return calculate_liquidity(order_book) >= min_units


def liquidity_score(order_book: OrderBook, min_units: float = 500.0, max_units: float = 50000.0) -> float:
    """Return normalized liquidity score between 0 and 1."""
    liq = calculate_liquidity(order_book)
    if liq <= min_units:
        return 0.0
    if liq >= max_units:
        return 1.0
    return (liq - min_units) / (max_units - min_units)


def calculate_notional_depth(
    order_book: OrderBook,
    side: Literal["bid", "ask"],
    levels: int = 10,
) -> float:
    """Calculate BRL notional depth for the selected side in the top N levels."""
    entries = order_book.bids if side == "bid" else order_book.asks
    return sum(entry.price * entry.quantity for entry in entries[:levels])


def calculate_total_notional_depth(order_book: OrderBook, levels: int = 10) -> float:
    """Calculate combined BRL notional depth across bids and asks."""
    return calculate_notional_depth(order_book, "bid", levels) + calculate_notional_depth(order_book, "ask", levels)


def calculate_depth_ratio_by_distance(
    order_book: OrderBook,
    bps_window: float = 50.0,
    levels: int = 10,
) -> float:
    """Return the fraction of visible notional that sits close to the touch price.

    A higher ratio suggests that more book depth is concentrated near the best bid/ask,
    which is a better proxy for near-term executability than raw quantity alone.
    """
    if not order_book.bids or not order_book.asks:
        return 0.0

    best_bid = order_book.bids[0].price
    best_ask = order_book.asks[0].price
    bid_floor = best_bid * (1 - bps_window / 10_000)
    ask_ceiling = best_ask * (1 + bps_window / 10_000)

    visible_bid_notional = calculate_notional_depth(order_book, "bid", levels)
    visible_ask_notional = calculate_notional_depth(order_book, "ask", levels)
    visible_total = visible_bid_notional + visible_ask_notional
    if visible_total <= 0:
        return 0.0

    near_bid_notional = sum(
        entry.price * entry.quantity
        for entry in order_book.bids[:levels]
        if entry.price >= bid_floor
    )
    near_ask_notional = sum(
        entry.price * entry.quantity
        for entry in order_book.asks[:levels]
        if entry.price <= ask_ceiling
    )
    return (near_bid_notional + near_ask_notional) / visible_total
