from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.models.schemas import Opportunity

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


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

    top = sorted(opportunities, key=lambda o: o.score, reverse=True)[:top_n]

    lines = ["🔔 *Crypto Analytics - Novas Oportunidades*\n"]
    for opp in top:
        lines.append(_format_opportunity(opp))
        lines.append("")

    lines.append(f"_Total de sinais: {len(opportunities)}_")
    message = "\n".join(lines)

    url = f"{TELEGRAM_API}/bot{effective_token}/sendMessage"
    payload = {
        "chat_id": effective_chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("Telegram alert sent successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False
