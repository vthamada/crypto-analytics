from __future__ import annotations

from app.filters.executability import (
    calculate_executability_score,
    calculate_trade_margin_metrics,
    classify_executability_band,
    classify_opportunity_type,
    estimate_fillable_notional,
    estimate_slippage_bps,
)
from app.filters.liquidity import (
    calculate_depth_ratio_by_distance,
    calculate_notional_depth,
    calculate_total_notional_depth,
)
from app.models.schemas import Exchange, OrderBook, OrderBookEntry


def _make_order_book(*, pair: str, bids: list[tuple[float, float]], asks: list[tuple[float, float]]) -> OrderBook:
    return OrderBook(
        exchange=Exchange.BINANCE,
        pair=pair,
        bids=[OrderBookEntry(price=price, quantity=quantity) for price, quantity in bids],
        asks=[OrderBookEntry(price=price, quantity=quantity) for price, quantity in asks],
    )


def test_calculate_notional_depth_uses_price_times_quantity():
    cheap_book = _make_order_book(
        pair="DOGE_BRL",
        bids=[(1.0, 10_000)],
        asks=[(1.02, 10_000)],
    )
    expensive_book = _make_order_book(
        pair="BTC_BRL",
        bids=[(100.0, 10_000)],
        asks=[(101.0, 10_000)],
    )

    assert calculate_notional_depth(cheap_book, "bid") == 10_000
    assert calculate_notional_depth(expensive_book, "bid") == 1_000_000
    assert calculate_total_notional_depth(expensive_book) > calculate_total_notional_depth(cheap_book)


def test_calculate_depth_ratio_by_distance_rewards_depth_near_touch():
    compact_book = _make_order_book(
        pair="BTC_BRL",
        bids=[(100.0, 10), (99.9, 10), (99.8, 10)],
        asks=[(100.1, 10), (100.2, 10), (100.3, 10)],
    )
    dispersed_book = _make_order_book(
        pair="BTC_BRL",
        bids=[(100.0, 10), (99.0, 10), (98.0, 10)],
        asks=[(100.1, 10), (101.1, 10), (102.1, 10)],
    )

    assert calculate_depth_ratio_by_distance(compact_book, bps_window=20) > calculate_depth_ratio_by_distance(
        dispersed_book,
        bps_window=20,
    )


def test_estimate_slippage_bps_is_lower_on_deep_book():
    shallow_book = _make_order_book(
        pair="BTC_BRL",
        bids=[(99.5, 2), (99.0, 2)],
        asks=[(100.0, 2), (101.0, 2)],
    )
    deep_book = _make_order_book(
        pair="BTC_BRL",
        bids=[(99.95, 100), (99.90, 100)],
        asks=[(100.0, 100), (100.05, 100)],
    )

    shallow_buy_slippage = estimate_slippage_bps(shallow_book, "buy", 300.0)
    deep_buy_slippage = estimate_slippage_bps(deep_book, "buy", 300.0)

    assert shallow_buy_slippage > deep_buy_slippage
    assert deep_buy_slippage >= 0


def test_estimate_fillable_notional_respects_slippage_cap():
    book = _make_order_book(
        pair="BTC_BRL",
        bids=[(99.95, 10), (99.70, 10), (99.20, 10)],
        asks=[(100.0, 10), (100.25, 10), (100.80, 10)],
    )

    fillable_buy = estimate_fillable_notional(book, max_slippage_bps=25, side="buy")
    fillable_sell = estimate_fillable_notional(book, max_slippage_bps=25, side="sell")

    assert fillable_buy == 1_000.0
    assert fillable_sell == 999.5


def test_estimate_slippage_returns_inf_when_book_cannot_fill_notional():
    book = _make_order_book(
        pair="BTC_BRL",
        bids=[(99.0, 1)],
        asks=[(100.0, 1)],
    )

    assert estimate_slippage_bps(book, "buy", 1_000.0) == float("inf")
    assert estimate_slippage_bps(book, "sell", 1_000.0) == float("inf")


def test_calculate_executability_score_rewards_depth_and_low_exit_friction():
    strong = calculate_executability_score(
        bid_notional_top_n=25_000,
        ask_notional_top_n=24_000,
        estimated_buy_slippage_bps=4.0,
        estimated_sell_slippage_bps=6.0,
        spread_pct=0.08,
        quote_volume_24h=500_000,
        fillable_notional_within_slippage_cap=3_000,
    )
    weak = calculate_executability_score(
        bid_notional_top_n=1_500,
        ask_notional_top_n=1_200,
        estimated_buy_slippage_bps=55.0,
        estimated_sell_slippage_bps=70.0,
        spread_pct=0.95,
        quote_volume_24h=15_000,
        fillable_notional_within_slippage_cap=400,
    )

    assert strong > weak
    assert strong >= 0
    assert weak >= 0


def test_classify_executability_band_maps_score_ranges():
    assert classify_executability_band(None) is None
    assert classify_executability_band(25) == "poor"
    assert classify_executability_band(45) == "fair"
    assert classify_executability_band(65) == "good"
    assert classify_executability_band(85) == "strong"


def test_calculate_trade_margin_metrics_subtracts_operational_friction():
    strong = calculate_trade_margin_metrics(
        volatility_pct=4.0,
        recent_change_pct=2.2,
        spread_pct=0.08,
        estimated_buy_slippage_bps=5.0,
        estimated_sell_slippage_bps=7.0,
        movement_type="strong_range",
        movement_regime="trend_continuation",
        movement_persistence_score=0.7,
    )
    weak = calculate_trade_margin_metrics(
        volatility_pct=2.5,
        recent_change_pct=0.6,
        spread_pct=0.65,
        estimated_buy_slippage_bps=25.0,
        estimated_sell_slippage_bps=35.0,
        movement_type="trap",
        movement_regime="illiquid_spike",
        movement_persistence_score=0.1,
    )

    assert strong["estimated_trade_margin_pct"] > strong["operational_friction_pct"]
    assert strong["estimated_net_trade_edge_pct"] > 0
    assert strong["trade_margin_score"] > weak["trade_margin_score"]
    assert weak["estimated_net_trade_edge_pct"] < 0


def test_classify_opportunity_type_prioritizes_trade_hold_observe_avoid():
    assert classify_opportunity_type(
        operable_signal=True,
        interesting_signal=True,
        executability_score=78,
        trade_margin_score=62,
        estimated_net_trade_edge_pct=0.8,
        movement_regime="trend_continuation",
    ) == "trade"
    assert classify_opportunity_type(
        operable_signal=False,
        interesting_signal=True,
        executability_score=72,
        trade_margin_score=55,
        estimated_net_trade_edge_pct=0.7,
        movement_regime="trend_continuation",
    ) == "hold"
    assert classify_opportunity_type(
        operable_signal=False,
        interesting_signal=True,
        executability_score=45,
        trade_margin_score=18,
        estimated_net_trade_edge_pct=0.1,
        movement_regime="breakout_clean",
    ) == "observe"
    assert classify_opportunity_type(
        operable_signal=True,
        interesting_signal=True,
        executability_score=82,
        trade_margin_score=8,
        estimated_net_trade_edge_pct=-0.4,
        movement_regime="illiquid_spike",
    ) == "avoid"
