from __future__ import annotations

import html
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.models.schemas import Opportunity
from app.services.operational_visibility import is_telegram_alertable

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
_last_alert_sent_at: dict[str, datetime] = {}
_last_alert_state_by_key: dict[str, str] = {}


def resolve_telegram_destination(*, token: str = "", chat_id: str = "") -> tuple[str, str]:
    return token or settings.telegram_bot_token, chat_id or settings.telegram_chat_id


def telegram_destination_configured(*, token: str = "", chat_id: str = "") -> bool:
    effective_token, effective_chat_id = resolve_telegram_destination(token=token, chat_id=chat_id)
    return bool(effective_token and effective_chat_id)


async def _send_message(*, token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        raise ValueError("Telegram bot token and chat id must be configured")

    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10)
        response.raise_for_status()


def _format_slippage(value_bps: float | None) -> str:
    if value_bps is None:
        return "indisponivel"
    return f"{value_bps / 100:.2f}%"


def _escape_html(value: object) -> str:
    return html.escape(str(value), quote=False)


def _format_opportunity(opp: Opportunity) -> str:
    status = opp.actionability_label or "Vale olhar agora"
    family = (opp.opportunity_family or "observacao").replace("_", " ")
    entry = opp.entry_zone or "n/d"
    exit_zone = opp.exit_zone or "n/d"
    size = opp.suggested_capital_range_brl or "n/d"
    risk = opp.risk_label or "n/d"
    reason = opp.main_reason or opp.alert_reason or "gatilho operacional detectado"
    order_note = " | exige ordem limitada" if opp.requires_limited_order else ""
    transfer_note = " | depende de transferencia" if opp.requires_transfer else ""

    return (
        f"<b>{_escape_html(opp.pair)} - {_escape_html(status)}</b>\n"
        f"   Exchange: {_escape_html(opp.exchange.value)}\n"
        f"   Tipo: {_escape_html(family)}{_escape_html(order_note)}{_escape_html(transfer_note)}\n"
        f"   Entrada provavel: {_escape_html(entry)}\n"
        f"   Saida provavel: {_escape_html(exit_zone)}\n"
        f"   Tamanho sugerido: {_escape_html(size)}\n"
        f"   Risco: {_escape_html(risk)}\n"
        f"   Motivo: {_escape_html(reason)}"
    )


def rank_telegram_opportunity(opp: Opportunity) -> float:
    phase = opp.movement_phase.value if hasattr(opp.movement_phase, "value") else opp.movement_phase
    phase_bonus = {
        "early_breakout": 8.0,
        "continuation": 5.0,
        "accumulation": -6.0,
        "extended": -4.0,
        "distribution_or_profit_zone": -6.0,
        "exhaustion": -8.0,
        "neutral": 0.0,
    }
    range_bonus = {
        "high_quality_reusable_range": 7.0,
        "valid_large_trade": 5.0,
        "valid_medium_trade": 3.0,
        "valid_small_trade": 1.5,
        "weak": -1.0,
        "none": 0.0,
    }
    type_bonus = {"trade": 5.0, "hold": 4.0, "observe": -2.0, "avoid": -12.0}
    base_score = opp.alert_worthiness_score if opp.alert_worthiness_score is not None else opp.score
    return (
        base_score
        + ((opp.executability_score or 0.0) * 0.12)
        + ((opp.trade_margin_score or 0.0) * 0.08)
        + min(max(opp.operational_range_margin_pct or 0.0, 0.0), 20.0) * 0.3
        + phase_bonus.get(str(phase), 0.0)
        + range_bonus.get(opp.operational_range_quality or "none", 0.0)
        + type_bonus.get(opp.opportunity_type or "observe", 0.0)
        - (8.0 if opp.is_late_entry_risk else 0.0)
    )


def _telegram_rank_value(opp: Opportunity) -> float:
    return rank_telegram_opportunity(opp)


def _destination_key(token: str, chat_id: str) -> str:
    token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
    return f"{chat_id}:{token_digest}"


def _alert_key(opp: Opportunity, *, destination_key: str) -> str:
    return f"{destination_key}:{opp.exchange.value}:{opp.pair}"


def _opportunity_alert_state(opp: Opportunity) -> str:
    if opp.alert_state_key:
        return opp.alert_state_key
    phase = opp.movement_phase.value if hasattr(opp.movement_phase, "value") else opp.movement_phase
    operational_score = opp.operational_score if opp.operational_score is not None else opp.score
    return "|".join(
        [
            opp.alert_trigger_type or "no_trigger",
            str(phase or "neutral"),
            str(opp.alert_moment_type or "neutral"),
            str(opp.opportunity_type or "unknown"),
            f"score_{int((operational_score or 0) // 10) * 10}",
        ]
    )


def split_alerts_by_state_change(
    opportunities: list[Opportunity],
    *,
    token: str = "",
    chat_id: str = "",
) -> tuple[list[Opportunity], list[Opportunity]]:
    effective_token, effective_chat_id = resolve_telegram_destination(token=token, chat_id=chat_id)
    if not effective_token or not effective_chat_id:
        return opportunities, []

    destination_key = _destination_key(effective_token, effective_chat_id)
    changed: list[Opportunity] = []
    unchanged: list[Opportunity] = []
    for opp in opportunities:
        key = _alert_key(opp, destination_key=destination_key)
        current_state = _opportunity_alert_state(opp)
        if _last_alert_state_by_key.get(key) == current_state:
            unchanged.append(opp)
        else:
            changed.append(opp)
    return changed, unchanged


def _mark_alert_states_sent(opportunities: list[Opportunity], *, destination_key: str) -> None:
    for opp in opportunities:
        _last_alert_state_by_key[_alert_key(opp, destination_key=destination_key)] = _opportunity_alert_state(opp)


def _filter_by_cooldown(
    opportunities: list[Opportunity],
    *,
    destination_key: str,
    cooldown_seconds: int | None = None,
) -> list[Opportunity]:
    cooldown = max(settings.telegram_alert_cooldown_seconds if cooldown_seconds is None else cooldown_seconds, 0)
    if cooldown == 0:
        return opportunities

    now = datetime.now(timezone.utc)
    eligible: list[Opportunity] = []

    for opp in opportunities:
        key = _alert_key(opp, destination_key=destination_key)
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
    cooldown_seconds: int | None = None,
) -> bool:
    """Send top opportunities to Telegram chat.

    Uses *token* / *chat_id* when provided; falls back to env-var settings.
    """
    effective_token, effective_chat_id = resolve_telegram_destination(token=token, chat_id=chat_id)

    if not effective_token or not effective_chat_id:
        logger.warning("Telegram not configured, skipping alert")
        return False

    opportunities = [opp for opp in opportunities if is_telegram_alertable(opp)]

    if not opportunities:
        return False

    destination_key = _destination_key(effective_token, effective_chat_id)
    eligible = _filter_by_cooldown(
        opportunities,
        destination_key=destination_key,
        cooldown_seconds=cooldown_seconds,
    )
    if not eligible:
        logger.info("Telegram cooldown suppressed all candidate alerts")
        return False

    top = sorted(eligible, key=_telegram_rank_value, reverse=True)[:top_n]

    lines = ["<b>Crypto Analytics - Novas Oportunidades</b>\n"]
    for opp in top:
        lines.append(_format_opportunity(opp))
        lines.append("")

    lines.append(f"<i>Total de sinais candidatos: {_escape_html(len(opportunities))}</i>")
    message = "\n".join(lines)

    try:
        await _send_message(token=effective_token, chat_id=effective_chat_id, text=message)
        now = datetime.now(timezone.utc)
        for opp in top:
            key = _alert_key(opp, destination_key=destination_key)
            _last_alert_sent_at[key] = now
        _mark_alert_states_sent(top, destination_key=destination_key)
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
    effective_token, effective_chat_id = resolve_telegram_destination(token=token, chat_id=chat_id)

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M:%S %Z")
    workspace_label = workspace_name or "Default Workspace"
    actor_label = actor_username or "sistema"
    message = (
        "<b>Crypto Analytics - Teste de Telegram</b>\n\n"
        f"Workspace: <b>{_escape_html(workspace_label)}</b>\n"
        f"Executado por: <b>{_escape_html(actor_label)}</b>\n"
        f"Horario: <code>{_escape_html(timestamp)}</code>\n\n"
        "Se esta mensagem chegou, a configuracao do bot e do chat esta funcional."
    )

    await _send_message(token=effective_token, chat_id=effective_chat_id, text=message)
    logger.info("telegram_test_sent workspace=%s actor=%s", workspace_label, actor_label)
    return True
