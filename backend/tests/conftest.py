from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.schemas import Exchange, Kline, OrderBook, OrderBookEntry, Ticker


@pytest.fixture
def sample_klines() -> list[Kline]:
    now = datetime.now(timezone.utc)
    return [
        Kline(
            open_time=now - timedelta(minutes=25 - i * 5),
            open=100 + i,
            high=103 + i,
            low=99 + i,
            close=102 + i,
            volume=1000 + i * 50,
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_ticker() -> Ticker:
    return Ticker(
        exchange=Exchange.BINANCE,
        pair="BTC_BRL",
        last_price=120.0,
        high_24h=125.0,
        low_24h=98.0,
        volume_24h=1500.0,
        quote_volume_24h=250000.0,
        change_pct_24h=4.2,
    )


@pytest.fixture
def sample_order_book() -> OrderBook:
    return OrderBook(
        exchange=Exchange.BINANCE,
        pair="BTC_BRL",
        bids=[OrderBookEntry(price=119.8, quantity=800), OrderBookEntry(price=119.5, quantity=600)],
        asks=[OrderBookEntry(price=120.2, quantity=900), OrderBookEntry(price=120.5, quantity=700)],
    )
