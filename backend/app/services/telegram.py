from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.models.schemas import Opportunity

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
_last_alert_sent_at: dict[str, datetime] = {}


async def _send_message(*, token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        raise ValueError("Telegram bot token and chat id must be configured")

    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10)
        response.raise_for_status()


def _format_opportunity(opp: Opportunity) -> str:
    score_emoji = "🟢" if opp.score >= 70 else "🟡" if opp.score >= 40 else "🔴"
    movement_emoji = {
        "strong_range": "📈",
        "spike": "⚡",
        "weak": "😐",
        "trap": "⚠️",
    }.get(opp.movement_type.value, "❓")

    return (
        f"{score_emoji} *Score {opp.score}* | {opp.pair}\n"
        f"   Exchange: {opp.exchange.value}\n"
        f"   {movement_emoji} Movimento: {opp.movement_type.value}\n"
        f"   💰 Preço: R$ {opp.last_price:,.2f}\n"
        f"   📊 Variação: {opp.change_pct:+.2f}%\n"
        f"   📈 Volatilidade: {opp.volatility_pct:.2f}%\n"
        f"   💵 Volume 24h: R$ {opp.quote_volume_24h:,.0f}\n"
        f"   🏦 Liquidez: {opp.liquidity_units:,.0f} un.\n"
        f"   📏 Spread: {opp.spread_pct:.4f}%"
    )


def _alert_key(opp: Opportunity) -> str:
    return f"{opp.exchange.value}:{opp.pair}"


def _filter_by_cooldown(opportunities: list[Opportunity]) -> list[Opportunity]:
    cooldown = max(settings.telegram_alert_cooldown_seconds, 0)
    if cooldown == 0:
        return opportunities

    now = datetime.now(timezone.utc)
    eligible: list[Opportunity] = []

    for opp in opportunities:
        key = _alert_key(opp)
        last_sent = _last_alert_sent_at.get(key)
        if last_sent and now - last_sent < timedelta(seconds=cooldown):
            continue
        eligible.append(opp)

    return eligible


async def send_telegram_alert(
    opportunities: list[Opportunity],
    token: str = "",
    chat_id: str = "",
    top_n: int = 5,
) -> bool:
    """Send top opportunities to Telegram chat.

    Uses *token* / *chat_id* when provided; falls back to env-var settings.
    """
    effective_token = token or settings.telegram_bot_token
    effective_chat_id = chat_id or settings.telegram_chat_id

    if not effective_token or not effective_chat_id:
        logger.warning("Telegram not configured, skipping alert")
        return False

    if not opportunities:
        return False

    eligible = _filter_by_cooldown(opportunities)
    if not eligible:
        logger.info("Telegram cooldown suppressed all candidate alerts")
        return False

    top = sorted(eligible, key=lambda o: o.score, reverse=True)[:top_n]

    lines = ["🔔 *Crypto Analytics - Novas Oportunidades*\n"]
    for opp in top:
        lines.append(_format_opportunity(opp))
        lines.append("")

    lines.append(f"_Total de sinais: {len(opportunities)}_")
    message = "\n".join(lines)

    try:
        await _send_message(token=effective_token, chat_id=effective_chat_id, text=message)
        now = datetime.now(timezone.utc)
        for opp in top:
            _last_alert_sent_at[_alert_key(opp)] = now
        logger.info("Telegram alert sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


async def send_telegram_test_message(
    *,
    token: str = "",
    chat_id: str = "",
    workspace_name: str = "",
    actor_username: str = "",
) -> bool:
    effective_token = token or settings.telegram_bot_token
    effective_chat_id = chat_id or settings.telegram_chat_id

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M:%S %Z")
    workspace_label = workspace_name or "Default Workspace"
    actor_label = actor_username or "sistema"
    message = (
        "✅ *Crypto Analytics - Teste de Telegram*\n\n"
        f"Workspace: *{workspace_label}*\n"
        f"Executado por: *{actor_label}*\n"
        f"Horário: `{timestamp}`\n\n"
        "Se esta mensagem chegou, a configuração do bot e do chat está funcional."
    )

    await _send_message(token=effective_token, chat_id=effective_chat_id, text=message)
    logger.info("telegram_test_sent workspace=%s actor=%s", workspace_label, actor_label)
    return True
