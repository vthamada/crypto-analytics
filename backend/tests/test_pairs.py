from __future__ import annotations

import asyncio

from app.models.schemas import AppConfig, Exchange
from app.services import pairs


def test_app_config_defaults_to_brl_core_exchanges():
    assert AppConfig().enabled_exchanges == [Exchange.NOVADAX, Exchange.MERCADO_BITCOIN]


def test_available_pairs_catalog_uses_cache(monkeypatch):
    async def run_test():
        calls = 0

        async def fake_fetch_provider_pairs(enabled_exchanges):
            nonlocal calls
            calls += 1
            provider_pairs = {
                Exchange.NOVADAX: ["BTC_BRL"],
                Exchange.MERCADO_BITCOIN: ["BTC_BRL"],
                Exchange.BINANCE: ["BTC_BRL", "POL_BRL"],
            }
            return {
                exchange: provider_pairs[exchange]
                for exchange in enabled_exchanges
                if exchange in provider_pairs
            }

        monkeypatch.setattr(pairs, "_pair_catalog_cache", None)
        monkeypatch.setattr(pairs, "_pair_catalog_generated_at", None)
        monkeypatch.setattr(pairs, "_fetch_provider_pairs", fake_fetch_provider_pairs)

        first = await pairs.get_available_pairs_catalog(force_refresh=False)
        second = await pairs.get_available_pairs_catalog(force_refresh=False)

        assert calls == 1
        assert [item["pair"] for item in first["pairs"]] == ["BTC_BRL"]
        assert first["pairs"][0]["base_asset"] == "BTC"
        assert first["pairs"][0]["quote_asset"] == "BRL"
        assert first["pairs"][0]["is_brl_pair"] is True
        assert first["pairs"][0]["status"]["novadax"] == "tradable"
        assert first["provider_status"][0]["exchange"] == Exchange.NOVADAX
        assert first == second

    asyncio.run(run_test())


def test_available_pairs_catalog_uses_default_brl_core_exchanges(monkeypatch):
    async def run_test():
        requested_exchanges = None

        async def fake_fetch_provider_pairs(enabled_exchanges):
            nonlocal requested_exchanges
            requested_exchanges = enabled_exchanges
            return {
                Exchange.NOVADAX: ["SOL_BRL"],
                Exchange.MERCADO_BITCOIN: ["WBTC_BRL"],
            }

        monkeypatch.setattr(pairs, "_pair_catalog_cache", None)
        monkeypatch.setattr(pairs, "_pair_catalog_generated_at", None)
        monkeypatch.setattr(pairs, "_fetch_provider_pairs", fake_fetch_provider_pairs)

        catalog = await pairs.get_available_pairs_catalog(force_refresh=True)

        assert requested_exchanges == [Exchange.NOVADAX, Exchange.MERCADO_BITCOIN]
        assert {item["pair"] for item in catalog["pairs"]} == {"SOL_BRL", "WBTC_BRL"}
        assert next(item for item in catalog["provider_status"] if item["exchange"] == Exchange.BINANCE)["status"] == "disabled"

    asyncio.run(run_test())


def test_available_pairs_catalog_cache_is_scoped_by_enabled_exchanges(monkeypatch):
    async def run_test():
        calls: list[tuple[Exchange, ...]] = []

        async def fake_fetch_provider_pairs(enabled_exchanges):
            key = tuple(enabled_exchanges)
            calls.append(key)
            payload = {
                Exchange.NOVADAX: ["SOL_BRL"],
                Exchange.MERCADO_BITCOIN: ["WBTC_BRL"],
            }
            if Exchange.BINANCE in enabled_exchanges:
                payload[Exchange.BINANCE] = ["BTC_USDT"]
            return payload

        monkeypatch.setattr(pairs, "_pair_catalog_cache", None)
        monkeypatch.setattr(pairs, "_pair_catalog_generated_at", None)
        monkeypatch.setattr(pairs, "_fetch_provider_pairs", fake_fetch_provider_pairs)

        await pairs.get_available_pairs_catalog(force_refresh=False)
        await pairs.get_available_pairs_catalog(force_refresh=False)
        catalog_with_binance = await pairs.get_available_pairs_catalog(
            enabled_exchanges=[Exchange.NOVADAX, Exchange.MERCADO_BITCOIN, Exchange.BINANCE],
            force_refresh=False,
        )

        assert calls == [
            (Exchange.NOVADAX, Exchange.MERCADO_BITCOIN),
            (Exchange.NOVADAX, Exchange.MERCADO_BITCOIN, Exchange.BINANCE),
        ]
        assert any(item["pair"] == "BTC_USDT" for item in catalog_with_binance["pairs"])

    asyncio.run(run_test())


def test_normalize_pair_symbol_accepts_exchange_formats():
    assert pairs.normalize_pair_symbol("SOLBRL") == "SOL_BRL"
    assert pairs.normalize_pair_symbol("wbtc/brl") == "WBTC_BRL"
    assert pairs.normalize_pair_symbol("btc-usdt") == "BTC_USDT"


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

        async def fake_catalog(enabled_exchanges=None, force_refresh: bool = False):
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
