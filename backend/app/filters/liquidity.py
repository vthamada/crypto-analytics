from __future__ import annotations

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
