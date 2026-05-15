from __future__ import annotations

import asyncio

from app.models.schemas import Exchange, MovementPhase, MovementType, Opportunity
from app.services import telegram


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClient:
    def __init__(self, *, recorder: dict[str, object]):
        self._recorder = recorder

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json: dict[str, object], timeout: int):
        self._recorder["url"] = url
        self._recorder["json"] = json
        self._recorder["timeout"] = timeout
        return _FakeResponse()


def _make_opportunity() -> Opportunity:
    return Opportunity(
        id="opp-1",
        exchange=Exchange.MERCADO_BITCOIN,
        pair="BTC_BRL",
        movement_type=MovementType.STRONG_RANGE,
        movement_phase=MovementPhase.EARLY_BREAKOUT,
        alert_moment_type="early_breakout",
        score=82.5,
        operable_signal=True,
        executability_score=91.2,
        last_price=123456.78,
        change_pct=4.56,
        volatility_pct=7.89,
        volume_24h=12.3,
        quote_volume_24h=1230000,
        liquidity_units=3456.0,
        ask_notional_top_n=50000,
        bid_notional_top_n=48000,
        estimated_buy_slippage_bps=25,
        estimated_sell_slippage_bps=30,
        spread_pct=0.12,
    )


def test_send_telegram_alert_uses_html_parse_mode_and_escapes_dynamic_values(monkeypatch):
    recorded: dict[str, object] = {}
    telegram._last_alert_sent_at.clear()
    telegram._last_alert_state_by_key.clear()

    monkeypatch.setattr(
        telegram.httpx,
        "AsyncClient",
        lambda: _FakeAsyncClient(recorder=recorded),
    )

    sent = asyncio.run(
        telegram.send_telegram_alert(
            [_make_opportunity()],
            token="bot-token",
            chat_id="chat-id",
            cooldown_seconds=0,
        )
    )

    assert sent is True
    assert recorded["json"]["parse_mode"] == "HTML"
    assert "mercado_bitcoin" in recorded["json"]["text"]
    assert "BTC_BRL" in recorded["json"]["text"]
    assert "*Crypto Analytics" not in recorded["json"]["text"]
    assert "<b>Crypto Analytics - Novas Oportunidades</b>" in recorded["json"]["text"]


def test_split_alerts_by_state_change_blocks_repeated_state_after_send(monkeypatch):
    recorded: dict[str, object] = {}
    telegram._last_alert_sent_at.clear()
    telegram._last_alert_state_by_key.clear()

    monkeypatch.setattr(
        telegram.httpx,
        "AsyncClient",
        lambda: _FakeAsyncClient(recorder=recorded),
    )

    first = _make_opportunity()
    sent = asyncio.run(
        telegram.send_telegram_alert(
            [first],
            token="bot-token",
            chat_id="chat-id",
            cooldown_seconds=0,
        )
    )
    changed, unchanged = telegram.split_alerts_by_state_change(
        [_make_opportunity()],
        token="bot-token",
        chat_id="chat-id",
    )

    assert sent is True
    assert changed == []
    assert len(unchanged) == 1


def test_send_telegram_test_message_escapes_workspace_and_actor_names(monkeypatch):
    recorded: dict[str, object] = {}

    monkeypatch.setattr(
        telegram.httpx,
        "AsyncClient",
        lambda: _FakeAsyncClient(recorder=recorded),
    )

    sent = asyncio.run(
        telegram.send_telegram_test_message(
            token="bot-token",
            chat_id="chat-id",
            workspace_name="Desk <Alpha>",
            actor_username="admin_ops",
        )
    )

    assert sent is True
    assert recorded["json"]["parse_mode"] == "HTML"
    assert "Desk &lt;Alpha&gt;" in recorded["json"]["text"]
    assert "admin_ops" in recorded["json"]["text"]
    assert "<code>" in recorded["json"]["text"]


def test_telegram_destination_configured_uses_settings_fallback(monkeypatch):
    monkeypatch.setattr(telegram.settings, "telegram_bot_token", "env-bot")
    monkeypatch.setattr(telegram.settings, "telegram_chat_id", "env-chat")

    assert telegram.telegram_destination_configured(token="", chat_id="") is True
    assert telegram.resolve_telegram_destination(token="", chat_id="") == ("env-bot", "env-chat")
