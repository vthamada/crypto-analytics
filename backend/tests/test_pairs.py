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


def test_fetch_provider_pairs_uses_stale_success_when_provider_fails(monkeypatch):
    async def run_test():
        class WorkingNovaDaxProvider:
            exchange = Exchange.NOVADAX

            async def get_available_pairs(self):
                return ["LAB_BRL", "TON_BRL"]

            async def close(self):
                return None

        class FailingNovaDaxProvider:
            exchange = Exchange.NOVADAX

            async def get_available_pairs(self):
                raise RuntimeError("novadax unavailable")

            async def close(self):
                return None

        monkeypatch.setattr(pairs, "_pair_catalog_provider_status", {})
        monkeypatch.setattr(pairs, "_provider_last_successful_pairs", {})
        monkeypatch.setattr(pairs, "NovaDaxProvider", WorkingNovaDaxProvider)

        first = await pairs._fetch_provider_pairs([Exchange.NOVADAX])

        monkeypatch.setattr(pairs, "NovaDaxProvider", FailingNovaDaxProvider)
        second = await pairs._fetch_provider_pairs([Exchange.NOVADAX])
        status = pairs._provider_status_for_key((Exchange.NOVADAX.value,))[0]

        assert first[Exchange.NOVADAX] == ["LAB_BRL", "TON_BRL"]
        assert second[Exchange.NOVADAX] == ["LAB_BRL", "TON_BRL"]
        assert status["status"] == "stale"
        assert status["error_message"] == "novadax unavailable"

    asyncio.run(run_test())


def test_fetch_provider_pairs_uses_stale_success_when_provider_returns_empty(monkeypatch):
    async def run_test():
        class WorkingNovaDaxProvider:
            exchange = Exchange.NOVADAX

            async def get_available_pairs(self):
                return ["SOL_BRL", "USDT_BRL"]

            async def close(self):
                return None

        class EmptyNovaDaxProvider:
            exchange = Exchange.NOVADAX

            async def get_available_pairs(self):
                return []

            async def close(self):
                return None

        monkeypatch.setattr(pairs, "_pair_catalog_provider_status", {})
        monkeypatch.setattr(pairs, "_provider_last_successful_pairs", {})
        monkeypatch.setattr(pairs, "NovaDaxProvider", WorkingNovaDaxProvider)

        first = await pairs._fetch_provider_pairs([Exchange.NOVADAX])

        monkeypatch.setattr(pairs, "NovaDaxProvider", EmptyNovaDaxProvider)
        second = await pairs._fetch_provider_pairs([Exchange.NOVADAX])
        status = pairs._provider_status_for_key((Exchange.NOVADAX.value,))[0]

        assert first[Exchange.NOVADAX] == ["SOL_BRL", "USDT_BRL"]
        assert second[Exchange.NOVADAX] == ["SOL_BRL", "USDT_BRL"]
        assert status["status"] == "stale"
        assert status["error_message"] == "provider returned an empty catalog"

    asyncio.run(run_test())


def test_pair_diagnostic_reports_symbol_and_endpoint_checks(monkeypatch, sample_ticker, sample_order_book, sample_klines):
    async def run_test():
        class DiagnosticProvider:
            exchange = Exchange.NOVADAX

            def normalize_pair(self, pair: str):
                return pair.upper()

            async def get_available_pairs(self):
                return ["LAB_BRL"]

            async def get_ticker(self, pair: str):
                return sample_ticker.model_copy(update={"exchange": Exchange.NOVADAX, "pair": pair})

            async def get_order_book(self, pair: str):
                return sample_order_book.model_copy(update={"exchange": Exchange.NOVADAX, "pair": pair})

            async def get_klines(self, pair: str, interval: str = "5m", limit: int = 50):
                return sample_klines

            async def close(self):
                return None

        monkeypatch.setattr(pairs, "NovaDaxProvider", DiagnosticProvider)

        diagnostic = await pairs.get_pair_exchange_diagnostic(Exchange.NOVADAX, "LAB/BRL")

        assert diagnostic["exchange"] == Exchange.NOVADAX
        assert diagnostic["pair"] == "LAB_BRL"
        assert diagnostic["raw_symbol"] == "LAB_BRL"
        assert diagnostic["exists_in_catalog"] is True
        assert diagnostic["monitorable"] is True
        assert diagnostic["monitorability_reason"] is None
        assert diagnostic["overall_status"] == "ok"
        assert {check["name"]: check["status"] for check in diagnostic["checks"]} == {
            "catalog": "ok",
            "ticker": "ok",
            "order_book": "ok",
            "klines": "ok",
        }

    asyncio.run(run_test())


def test_pair_monitorability_explains_catalog_blocks():
    catalog = pairs._build_catalog_payload(
        {Exchange.NOVADAX: ["SOL_BRL"], Exchange.MERCADO_BITCOIN: []},
        pairs.utcnow(),
        enabled_exchanges=[Exchange.NOVADAX],
    )

    assert pairs.explain_pair_monitorability(
        catalog=catalog,
        exchange=Exchange.NOVADAX,
        pair="SOL_BRL",
    )["monitorable"] is True
    assert pairs.explain_pair_monitorability(
        catalog=catalog,
        exchange=Exchange.NOVADAX,
        pair="DOGE_BRL",
    )["monitorability_reason"] == "pair_not_in_catalog"
    assert pairs.explain_pair_monitorability(
        catalog=catalog,
        exchange=Exchange.NOVADAX,
        pair="BTC_USDT",
    )["monitorability_reason"] == "not_brl_pair"
    assert pairs.explain_pair_monitorability(
        catalog=catalog,
        exchange=Exchange.BINANCE,
        pair="SOL_BRL",
    )["monitorability_reason"] == "exchange_disabled"


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


def test_scannable_pairs_keeps_catalog_discovery_when_watchlist_is_set(monkeypatch):
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
                    "pair": "SOL_BRL",
                    "display_name": "SOL/BRL",
                    "availability": {"novadax": True, "mercado_bitcoin": False, "binance": False},
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
            enabled_pairs=["SOL_BRL"],
            enabled_exchanges=[Exchange.NOVADAX, Exchange.MERCADO_BITCOIN, Exchange.BINANCE],
        )

        assert scannable[Exchange.NOVADAX] == ["BTC_BRL", "SOL_BRL"]
        assert scannable[Exchange.MERCADO_BITCOIN] == ["BTC_BRL", "ETH_BRL"]
        assert scannable[Exchange.BINANCE] == ["BTC_BRL", "ETH_BRL"]

    asyncio.run(run_test())


def test_scannable_pairs_can_limit_scan_to_watchlist(monkeypatch):
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
                    "pair": "SOL_BRL",
                    "display_name": "SOL/BRL",
                    "availability": {"novadax": True, "mercado_bitcoin": False, "binance": False},
                },
            ]
        }

        async def fake_catalog(enabled_exchanges=None, force_refresh: bool = False):
            return catalog

        monkeypatch.setattr(pairs, "get_available_pairs_catalog", fake_catalog)

        scannable = await pairs.get_scannable_pairs_by_exchange(
            enabled_pairs=["SOL_BRL"],
            enabled_exchanges=[Exchange.NOVADAX, Exchange.MERCADO_BITCOIN, Exchange.BINANCE],
            pair_universe_mode="watchlist_only",
        )

        assert scannable[Exchange.NOVADAX] == ["SOL_BRL"]
        assert scannable[Exchange.MERCADO_BITCOIN] == []
        assert scannable[Exchange.BINANCE] == []

    asyncio.run(run_test())
