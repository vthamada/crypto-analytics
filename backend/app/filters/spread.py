from __future__ import annotations

from app.models.schemas import OrderBook


def calculate_spread(order_book: OrderBook) -> float:
    """Calculate spread as percentage difference between best ask and best bid."""
    if not order_book.bids or not order_book.asks:
        return float("inf")

    best_bid = order_book.bids[0].price
    best_ask = order_book.asks[0].price

    if best_bid == 0:
        return float("inf")

    mid_price = (best_bid + best_ask) / 2
    return ((best_ask - best_bid) / mid_price) * 100


def passes_spread_filter(order_book: OrderBook, max_spread_pct: float = 1.0) -> bool:
    """Check if spread is below the maximum threshold."""
    return calculate_spread(order_book) <= max_spread_pct


def spread_score(order_book: OrderBook, max_spread: float = 1.0) -> float:
    """Return normalized spread score between 0 and 1 (lower spread = higher score)."""
    spread = calculate_spread(order_book)
    if spread >= max_spread:
        return 0.0
    if spread <= 0.01:
        return 1.0
    return 1.0 - (spread / max_spread)
