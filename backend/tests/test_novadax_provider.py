from __future__ import annotations

import asyncio

import pytest

from app.providers.novadax import NovaDaxProvider


def test_novadax_get_klines_accepts_timestamp_field(monkeypatch):
    provider = NovaDaxProvider()

    async def fake_request(method: str, path: str, **kwargs):
        return {
            "data": [
                {
                    "timestamp": 1713350400,
                    "openPrice": "1.10",
                    "highPrice": "1.20",
                    "lowPrice": "1.00",
                    "closePrice": "1.15",
                    "vol": "1500",
                }
            ]
        }

    monkeypatch.setattr(provider, "_request", fake_request)

    klines = asyncio.run(provider.get_klines("ADA_BRL"))

    assert len(klines) == 1
    assert klines[0].open == 1.10
    assert klines[0].close == 1.15
    assert int(klines[0].open_time.timestamp()) == 1713350400


def test_novadax_get_available_pairs_normalizes_active_brl_symbols(monkeypatch):
    provider = NovaDaxProvider()

    async def fake_request(method: str, path: str, **kwargs):
        return {
            "data": [
                {"symbol": "BTC_BRL", "status": "ONLINE"},
                {"symbol": "SOLBRL", "status": "TRADING"},
                {"symbol": "eth/brl", "status": "ONLINE"},
                {"baseCurrency": "USDT", "quoteCurrency": "BRL", "status": "ONLINE"},
                {"symbol": "ETH_USDT", "status": "ONLINE"},
                {"symbol": "LAB_BRL", "status": "OFFLINE"},
                {"symbol": "TON_BRL", "status": "ONLINE"},
            ]
        }

    monkeypatch.setattr(provider, "_request", fake_request)

    assert asyncio.run(provider.get_available_pairs()) == [
        "BTC_BRL",
        "ETH_BRL",
        "SOL_BRL",
        "TON_BRL",
        "USDT_BRL",
    ]


def test_novadax_get_available_pairs_propagates_request_failures(monkeypatch):
    provider = NovaDaxProvider()

    async def fake_request(method: str, path: str, **kwargs):
        raise RuntimeError("connect failed")

    monkeypatch.setattr(provider, "_request", fake_request)

    with pytest.raises(RuntimeError, match="connect failed"):
        asyncio.run(provider.get_available_pairs())


def test_novadax_get_ticker_derives_change_pct_from_open24h_when_change24h_missing(monkeypatch):
    provider = NovaDaxProvider()

    async def fake_request(method: str, path: str, **kwargs):
        return {
            "data": {
                "lastPrice": "110.00",
                "high24h": "120.00",
                "low24h": "90.00",
                "open24h": "100.00",
                "baseVolume24h": "42.00",
                "quoteVolume24h": "4200.00",
            }
        }

    monkeypatch.setattr(provider, "_request", fake_request)

    ticker = asyncio.run(provider.get_ticker("SOL_BRL"))

    assert ticker.last_price == 110.0
    assert ticker.change_pct_24h == 10.0
