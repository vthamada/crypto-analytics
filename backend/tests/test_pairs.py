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