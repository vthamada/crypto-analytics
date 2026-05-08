from __future__ import annotations

import asyncio

from app import main
from app.models.schemas import AppConfig, Exchange, MovementType


class FakeManager:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict]] = []

    @property
    def connection_count(self) -> int:
        return 1

    @property
    def workspace_ids(self) -> set[str]:
        return {"workspace-1"}

    async def broadcast_workspace(self, workspace_id: str, data: dict) -> None:
        self.messages.append((workspace_id, data))


def test_build_workspace_broadcast_payloads_uses_shared_snapshots(monkeypatch):
    fake_manager = FakeManager()

    async def fake_load_all_workspace_configs():
        return {
            "workspace-1": AppConfig(
                enabled_exchanges=[Exchange.BINANCE],
                enabled_pairs=["BTC_BRL"],
            )
        }

    async def fake_read_opportunity_snapshots():
        return [
            {
                "id": "opp-1",
                "exchange": "binance",
                "pair": "BTC_BRL",
                "score": 72.5,
                "technical_score": 68.3,
                "score_version": "v1",
                "executability_score": 70.0,
                "operable_signal": True,
                "interesting_signal": True,
                "estimated_net_trade_edge_pct": 0.8,
                "trade_margin_score": 45.0,
                "opportunity_type": "trade",
                "volatility_pct": 3.2,
                "volume_24h": 500.0,
                "quote_volume_24h": 60000.0,
                "liquidity_units": 1200.0,
                "spread_pct": 0.15,
                "movement_type": MovementType.SPIKE.value,
                "last_price": 350000.0,
                "change_pct": 2.1,
                "detected_at": "2026-04-16T12:00:00+00:00",
                "historical_confidence": 1.0,
                "volatility_score": 0.32,
                "volume_score": 0.50,
                "liquidity_score": 0.80,
                "spread_score": 0.70,
                "repetition_score": 0.20,
                "movement_multiplier": 1.15,
                "cross_exchange_gap_pct": 0.0,
                "cross_exchange_reference_exchange": None,
                "cross_exchange_reference_price": None,
                "arbitrage_available": False,
            }
        ]

    monkeypatch.setattr(main, "manager", fake_manager)
    monkeypatch.setattr(main, "load_all_workspace_configs", fake_load_all_workspace_configs)
    monkeypatch.setattr(main, "read_opportunity_snapshots", fake_read_opportunity_snapshots)

    broadcasts = asyncio.run(
        main._build_workspace_broadcast_payloads(timestamp="2026-04-16T12:00:30+00:00")
    )

    assert broadcasts == 1
    assert len(fake_manager.messages) == 1
    workspace_id, payload = fake_manager.messages[0]
    assert workspace_id == "workspace-1"
    assert payload["type"] == "opportunities_update"
    assert payload["count"] == 1
    assert payload["timestamp"] == "2026-04-16T12:00:30+00:00"
    assert payload["data"][0]["pair"] == "BTC_BRL"
