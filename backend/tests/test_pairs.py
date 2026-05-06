from __future__ import annotations

import asyncio

from app.models.schemas import Exchange
from app.services import pairs


def test_available_pairs_catalog_uses_cache(monkeypatch):
    async def run_test():
        calls = 0

        async def fake_fetch_provider_pairs():
            nonlocal calls
            calls += 1
            return {
                Exchange.NOVADAX: ["BTC_BRL"],
                Exchange.MERCADO_BITCOIN: ["BTC_BRL"],
                Exchange.BINANCE: ["BTC_BRL", "POL_BRL"],
            }

        monkeypatch.setattr(pairs, "_pair_catalog_cache", None)
        monkeypatch.setattr(pairs, "_pair_catalog_generated_at", None)
        monkeypatch.setattr(pairs, "_fetch_provider_pairs", fake_fetch_provider_pairs)

        first = await pairs.get_available_pairs_catalog(force_refresh=False)
        second = await pairs.get_available_pairs_catalog(force_refresh=False)

        assert calls == 1
        assert [item["pair"] for item in first["pairs"]] == ["BTC_BRL", "POL_BRL"]
        assert first == second

    asyncio.run(run_test())


def test_select_default_enabled_pairs_prefers_pairs_with_more_exchanges():
    catalog = {
        "pairs": [
            {
                "pair": "DOGE_BRL",
                "display_name": "DOGE/BRL",
                "availability": {"novadax": False, "mercado_bitcoin": False, "binance": True},
            },
            {
                "pair": "BTC_BRL",
                "display_name": "BTC/BRL",
                "availability": {"novadax": True, "mercado_bitcoin": True, "binance": True},
            },
            {
                "pair": "ETH_BRL",
                "display_name": "ETH/BRL",
                "availability": {"novadax": True, "mercado_bitcoin": True, "binance": False},
            },
        ]
    }

    selected = pairs.select_default_enabled_pairs(catalog, limit=2)

    assert selected == ["BTC_BRL", "ETH_BRL"]


def test_filter_pairs_by_availability_returns_only_supported_pairs():
    catalog = {
        "pairs": [
            {
                "pair": "BTC_BRL",
                "display_name": "BTC/BRL",
                "availability": {"novadax": True, "mercado_bitcoin": True, "binance": True},
            },
            {
                "pair": "DOGE_BRL",
                "display_name": "DOGE/BRL",
                "availability": {"novadax": False, "mercado_bitcoin": False, "binance": True},
            },
        ]
    }

    filtered = pairs.filter_pairs_by_availability(
        enabled_pairs=["BTC_BRL", "DOGE_BRL"],
        enabled_exchanges=[Exchange.NOVADAX, Exchange.BINANCE],
        catalog=catalog,
    )

    assert filtered[Exchange.NOVADAX] == ["BTC_BRL"]
    assert filtered[Exchange.BINANCE] == ["BTC_BRL", "DOGE_BRL"]


def test_scannable_pairs_uses_brl_discovery_when_enabled_pairs_empty(monkeypatch):
    async def run_test():
        catalog = {
            "pairs": [
                {
                    "pair": "BTC_BRL",
                    "display_name": "BTC/BRL",
                    "availability": {"novadax": True, "mercado_bitcoin": True, "binance": True},
                },
                {
                    "pair": "ETH_BRL",
                    "display_name": "ETH/BRL",
                    "availability": {"novadax": False, "mercado_bitcoin": True, "binance": True},
                },
                {
                    "pair": "BTC_USDT",
                    "display_name": "BTC/USDT",
                    "availability": {"novadax": False, "mercado_bitcoin": False, "binance": True},
                },
            ]
        }

        async def fake_catalog(force_refresh: bool = False):
            return catalog

        monkeypatch.setattr(pairs, "get_available_pairs_catalog", fake_catalog)

        scannable = await pairs.get_scannable_pairs_by_exchange(
            enabled_pairs=[],
            enabled_exchanges=[Exchange.NOVADAX, Exchange.MERCADO_BITCOIN, Exchange.BINANCE],
        )

        assert scannable[Exchange.NOVADAX] == ["BTC_BRL"]
        assert scannable[Exchange.MERCADO_BITCOIN] == ["BTC_BRL", "ETH_BRL"]
        assert scannable[Exchange.BINANCE] == ["BTC_BRL", "ETH_BRL"]

    asyncio.run(run_test())
