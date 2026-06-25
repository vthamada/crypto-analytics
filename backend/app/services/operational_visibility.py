from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from app.models.schemas import Opportunity, OpportunitySubtype

PipelineStatus = Literal[
    "observed_pair",
    "discarded_observation",
    "candidate",
    "evaluated_signal",
    "operational_opportunity",
    "published_opportunity",
    "alerted_opportunity",
    "blocked_signal",
    "technical_audit_event",
    "signal_outcome",
]


def _value(value: object) -> str:
    return str(getattr(value, "value", value) or "")


def _get(data: Mapping[str, Any] | Opportunity, key: str, default: Any = None) -> Any:
    if isinstance(data, Mapping):
        return data.get(key, default)
    return getattr(data, key, default)


def classify_pipeline_visibility_payload(data: Mapping[str, Any] | Opportunity) -> tuple[PipelineStatus, str, bool]:
    """Derive whether a signal is suitable for user-facing operational surfaces.

    This is intentionally stricter than "the scanner saw something". Weak moves,
    negative margin, low executability, and avoid signals remain audit data.
    """
    opportunity_type = _get(data, "opportunity_type") or "observe"
    movement_type = _value(_get(data, "movement_type"))
    movement_phase = _value(_get(data, "movement_phase", "neutral"))
    alert_moment_type = _value(_get(data, "alert_moment_type", "neutral"))
    net_edge = _get(data, "estimated_net_trade_edge_pct")
    executability = _get(data, "executability_score")

    if opportunity_type == "avoid":
        return "blocked_signal", "opportunity_type_not_alertable", False
    if net_edge is not None and net_edge < 0:
        return "blocked_signal", "insufficient_operational_margin", False
    if movement_type == "weak" and not (_get(data, "operable_signal") and derive_operational_score(data) >= 60):
        return "discarded_observation", "weak_movement", False
    if (_get(data, "quote_volume_24h") or 0) < 3_000:
        return "blocked_signal", "insufficient_volume", False
    if _get(data, "operability_size_label") == "not_operable":
        return "blocked_signal", "insufficient_liquidity", False
    if executability is not None and executability < 35:
        return "blocked_signal", "insufficient_liquidity", False
    if _get(data, "is_late_entry_risk") and alert_moment_type in {"extended", "profit_zone"}:
        return "blocked_signal", "high_late_entry_risk", False

    if opportunity_type in {"trade", "hold"}:
        if executability is None or executability >= 45:
            return "operational_opportunity", f"{opportunity_type}_qualified", True

    if _get(data, "operable_signal"):
        return "operational_opportunity", "operable_signal", True

    strong_observable = (
        bool(_get(data, "interesting_signal"))
        and derive_operational_score(data) >= 70
        and (executability is None or executability >= 55)
        and (net_edge is None or net_edge >= 0.2)
        and movement_type not in {"weak", "trap"}
        and movement_phase in {"accumulation", "early_breakout", "continuation", "neutral"}
    )
    if strong_observable:
        return "operational_opportunity", "strong_observable_signal", True

    if _get(data, "arbitrage_available") and (executability is None or executability >= 50):
        return "operational_opportunity", "arbitrage_operational", True

    return "evaluated_signal", "not_operational", False


def classify_pipeline_visibility(opportunity: Opportunity) -> tuple[PipelineStatus, str, bool]:
    return classify_pipeline_visibility_payload(opportunity)


def classify_opportunity_subtype(data: Mapping[str, Any] | Opportunity) -> OpportunitySubtype:
    """Map the broad opportunity type into the operational taxonomy.

    This keeps the legacy opportunity_type stable while giving the product a
    richer language for routing dashboards, Telegram copy, and future
    multi-exchange/spread logic.
    """
    stored_subtype = _get(data, "opportunity_subtype")
    valid_subtypes = set(OpportunitySubtype.__args__)
    if stored_subtype in valid_subtypes:
        return stored_subtype

    opportunity_type = _get(data, "opportunity_type") or "observe"
    movement_phase = _value(_get(data, "movement_phase", "neutral"))
    alert_moment_type = _value(_get(data, "alert_moment_type", "neutral"))
    range_quality = _get(data, "operational_range_quality") or "none"
    range_margin = _get(data, "operational_range_margin_pct") or 0.0
    movement_regime = _value(_get(data, "movement_regime"))

    if opportunity_type == "avoid":
        return "avoid"
    if _get(data, "arbitrage_available"):
        return "cross_exchange_arbitrage"
    if alert_moment_type == "profit_zone" or _get(data, "is_profit_zone_candidate"):
        return "profit_zone"
    if movement_phase == "early_breakout" or alert_moment_type == "early_breakout":
        return "breakout_trade"
    if (
        range_quality in {"high_quality_reusable_range", "valid_large_trade", "valid_medium_trade", "valid_small_trade"}
        and range_margin >= 1.0
    ):
        return "range_trade"
    if opportunity_type == "hold" or movement_phase == "continuation" or alert_moment_type == "continuation":
        return "hold_continuation"
    if opportunity_type == "trade" or movement_regime in {"trend_continuation", "breakout_clean"}:
        return "directional_trade"
    return "observe_only"


def derive_operational_score(data: Mapping[str, Any] | Opportunity) -> float:
    """Score for operational health; alert urgency is calculated separately."""
    operational_score = _get(data, "operational_score")
    if operational_score is not None:
        return float(operational_score)
    return float(_get(data, "score") or 0.0)


def _fmt_money(value: float | int | None) -> str | None:
    if value is None:
        return None
    return f"R$ {float(value):,.2f}"


def _fmt_money_compact(value: float | int | None) -> str | None:
    if value is None:
        return None
    number = float(value)
    if number >= 1_000_000:
        return f"R$ {number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"R$ {number / 1_000:.1f}K"
    return f"R$ {number:.0f}"


def _fmt_zone(low: float | None, high: float | None) -> str | None:
    if low is None and high is None:
        return None
    if low is not None and high is not None:
        if abs(low - high) < 1e-9:
            return _fmt_money(low)
        return f"{_fmt_money(low)} - {_fmt_money(high)}"
    return _fmt_money(low if low is not None else high)


def _suggested_capital_label(data: Mapping[str, Any] | Opportunity) -> str | None:
    label = _get(data, "operability_size_label")
    max_notional = _get(data, "max_operable_order_notional_brl")
    if label == "not_operable":
        return "sem tamanho operavel"
    if max_notional is not None and max_notional > 0:
        return f"ate {_fmt_money_compact(max_notional)}"
    capacity = _get(data, "capital_capacity_estimate_brl")
    if capacity is not None and capacity > 0:
        return f"ate {_fmt_money_compact(capacity)}"
    return None


def _liquidity_label(data: Mapping[str, Any] | Opportunity) -> str:
    volume = float(_get(data, "quote_volume_24h") or 0.0)
    max_notional = float(_get(data, "max_operable_order_notional_brl") or 0.0)
    if volume < 3_000 or _get(data, "operability_size_label") == "not_operable":
        return "sem_liquidez"
    if volume >= 10_000 and max_notional >= 1_000:
        return "liquidez_boa"
    if volume >= 5_000 or max_notional >= 300:
        return "liquidez_media"
    return "liquidez_baixa"


def _risk_label(data: Mapping[str, Any] | Opportunity) -> str:
    if _get(data, "is_late_entry_risk"):
        return "alto"
    if _get(data, "alert_block_reason") in {"high_late_entry_risk", "late_entry_risk"}:
        return "alto"
    if (_get(data, "estimated_net_trade_edge_pct") or 0.0) < 0:
        return "alto"
    if _get(data, "operability_size_label") in {"not_operable", "small_test_only"}:
        return "medio"
    sell_slippage = _get(data, "estimated_sell_slippage_bps")
    if sell_slippage is not None and sell_slippage > 300:
        return "alto"
    if sell_slippage is not None and sell_slippage > 100:
        return "medio"
    return "baixo"


def _opportunity_family(data: Mapping[str, Any] | Opportunity) -> str:
    subtype = _get(data, "opportunity_subtype") or classify_opportunity_subtype(data)
    phase = _value(_get(data, "movement_phase", "neutral"))
    moment = _value(_get(data, "alert_moment_type", "neutral"))
    if subtype in {"intra_exchange_spread", "book_scalping"}:
        return "spread_interno"
    if subtype in {"cross_exchange_arbitrage", "inventory_arbitrage", "transfer_arbitrage"} or _get(data, "arbitrage_available"):
        return "arbitragem"
    if subtype == "range_trade" or (_get(data, "operational_range_quality") or "none") not in {"none", "weak"}:
        return "faixa_operacional"
    if subtype == "profit_zone" or moment == "profit_zone":
        return "realizacao"
    if subtype == "breakout_trade" or phase == "early_breakout" or moment == "early_breakout":
        return "rompimento"
    if _value(_get(data, "movement_regime")) in {"breakout_clean", "trend_continuation"}:
        return "mudanca_de_regime"
    return "observacao"


def _operation_status(data: Mapping[str, Any] | Opportunity) -> str:
    alert_block_reason = _get(data, "alert_block_reason")
    visibility_reason = _get(data, "visibility_reason")
    if _get(data, "opportunity_type") == "avoid":
        return "evitar"
    if visibility_reason in {"insufficient_volume", "insufficient_liquidity"} or alert_block_reason in {
        "low_liquidity",
        "no_exit_liquidity",
    }:
        return "sem_liquidez"
    if _get(data, "operability_size_label") == "not_operable":
        return "sem_liquidez"
    if _get(data, "is_late_entry_risk") and _value(_get(data, "alert_moment_type")) in {"extended", "profit_zone"}:
        return "ja_passou_do_ponto"
    if alert_block_reason in {"accumulation_only", "preparation_without_trigger", "no_actionable_operation"}:
        return "aguardando_gatilho"
    if bool(_get(data, "has_actionable_trigger")) and not alert_block_reason:
        return "vale_olhar_agora"
    if bool(_get(data, "operationally_visible")):
        return "so_observar"
    return "evitar" if visibility_reason else "so_observar"


def build_operational_thesis(data: Mapping[str, Any] | Opportunity) -> dict[str, Any]:
    family = _opportunity_family(data)
    status = _operation_status(data)
    entry_zone = _fmt_zone(_get(data, "operational_buy_zone_low"), _get(data, "operational_buy_zone_high"))
    exit_zone = _fmt_zone(_get(data, "operational_sell_zone_low"), _get(data, "operational_sell_zone_high"))
    if entry_zone is None:
        entry_zone = _fmt_money(_get(data, "last_price"))
    if exit_zone is None and _get(data, "cross_exchange_reference_price") is not None:
        exit_zone = _fmt_money(_get(data, "cross_exchange_reference_price"))

    liquidity_label = _liquidity_label(data)
    risk_label = _risk_label(data)
    trigger = _get(data, "alert_trigger_type")
    reason = _get(data, "alert_reason") or _get(data, "visibility_reason") or _get(data, "alert_block_reason")
    if status == "vale_olhar_agora":
        main_reason = reason or "gatilho operacional com liquidez suficiente"
    elif status == "aguardando_gatilho":
        main_reason = "ativo monitoravel, mas ainda sem gatilho operacional"
    elif status == "sem_liquidez":
        main_reason = "liquidez insuficiente para entrada e saida segura"
    elif status == "ja_passou_do_ponto":
        main_reason = "movimento esticado com risco de entrada tardia"
    elif status == "evitar":
        main_reason = reason or "risco operacional elevado"
    else:
        main_reason = reason or "ativo em observacao"

    actionability = {
        "vale_olhar_agora": "Vale olhar agora",
        "so_observar": "So observar",
        "aguardando_gatilho": "Aguardando gatilho",
        "evitar": "Evitar",
        "sem_liquidez": "Sem liquidez",
        "ja_passou_do_ponto": "Ja passou do ponto",
    }.get(status, "So observar")

    return {
        "operation_status": status,
        "opportunity_family": family,
        "entry_zone": entry_zone,
        "exit_zone": exit_zone,
        "suggested_capital_range_brl": _suggested_capital_label(data),
        "liquidity_label": liquidity_label,
        "risk_label": risk_label,
        "main_reason": main_reason,
        "actionability_label": actionability,
        "requires_limited_order": family == "spread_interno" or float(_get(data, "spread_pct") or 0.0) >= 0.5,
        "requires_transfer": family == "arbitragem" and _get(data, "opportunity_subtype") == "transfer_arbitrage",
        "alert_trigger_type": trigger,
        "alert_block_reason": _get(data, "alert_block_reason"),
    }


def add_visibility_fields(data: dict[str, Any]) -> dict[str, Any]:
    pipeline_status, visibility_reason, operationally_visible = classify_pipeline_visibility_payload(data)
    opportunity_subtype = classify_opportunity_subtype(data)
    operational_score = derive_operational_score(data)
    enriched = {
        **data,
        "operational_score": operational_score,
        "pipeline_status": pipeline_status,
        "visibility_reason": visibility_reason,
        "operationally_visible": operationally_visible,
        "opportunity_subtype": opportunity_subtype,
    }
    enriched.update(build_operational_thesis(enriched))
    return enriched


def enrich_operational_visibility(opportunity: Opportunity) -> Opportunity:
    pipeline_status, visibility_reason, operationally_visible = classify_pipeline_visibility(opportunity)
    data = opportunity.model_dump()
    data["operational_score"] = derive_operational_score(opportunity)
    data["opportunity_subtype"] = classify_opportunity_subtype(opportunity)
    data.update(
        {
            "pipeline_status": pipeline_status,
            "visibility_reason": visibility_reason,
            "operationally_visible": operationally_visible,
        }
    )
    data.update(build_operational_thesis(data))
    return Opportunity(**data)


def is_operationally_visible(opportunity: Opportunity) -> bool:
    return classify_pipeline_visibility(opportunity)[2]


def _alert_state_key(
    *,
    opportunity: Opportunity,
    trigger_type: str | None,
    phase: str,
    moment: str,
) -> str:
    score_bucket = int(derive_operational_score(opportunity) // 10) * 10
    return "|".join(
        [
            trigger_type or "no_trigger",
            phase or "neutral",
            moment or "neutral",
            opportunity.opportunity_type or "unknown",
            opportunity.operational_range_quality or "none",
            f"score_{score_bucket}",
            f"late_{bool(opportunity.is_late_entry_risk)}",
        ]
    )


def classify_alert_worthiness(opportunity: Opportunity) -> tuple[bool, str | None, dict[str, Any]]:
    """Decide if an operational signal is worth interrupting the user now.

    A healthy/operable asset is not necessarily an actionable alert. Accumulation
    and preparation are useful for the dashboard, but Telegram needs a fresh
    trigger such as breakout, continuation with margin, or arbitrage.
    """
    status, _, visible = classify_pipeline_visibility(opportunity)
    if not visible or status != "operational_opportunity":
        return False, opportunity.visibility_reason or "opportunity_type_not_alertable", {
            "alert_worthiness_score": 0.0,
            "alert_trigger_type": None,
            "has_actionable_trigger": False,
            "alert_state_key": None,
            "operational_score": derive_operational_score(opportunity),
            "pipeline_status": status,
            "operationally_visible": visible,
        }

    phase = _value(opportunity.movement_phase)
    moment = _value(opportunity.alert_moment_type)
    movement_type = _value(opportunity.movement_type)
    score = float(opportunity.score or 0.0)
    operational_score = derive_operational_score(opportunity)
    executability = float(opportunity.executability_score or 0.0)
    net_edge = opportunity.estimated_net_trade_edge_pct
    range_margin = opportunity.operational_range_margin_pct or 0.0

    trigger_type: str | None = None
    trigger_bonus = 0.0

    if opportunity.arbitrage_available:
        trigger_type = "cross_exchange_arbitrage"
        trigger_bonus = 35.0
    elif moment == "early_breakout" or phase == "early_breakout":
        trigger_type = "early_breakout"
        trigger_bonus = 30.0
    elif moment == "continuation" or phase == "continuation":
        trigger_type = "continuation"
        trigger_bonus = 22.0
    elif movement_type == "spike" and opportunity.quote_volume_24h >= 10_000:
        trigger_type = "directional_momentum"
        trigger_bonus = 18.0
    elif (
        opportunity.operational_range_quality in {"high_quality_reusable_range", "valid_large_trade", "valid_medium_trade"}
        and range_margin >= 1.0
        and phase not in {"accumulation"}
        and moment not in {"preparation"}
    ):
        trigger_type = "range_trade"
        trigger_bonus = 14.0

    has_actionable_trigger = trigger_type is not None
    alert_state_key = _alert_state_key(
        opportunity=opportunity,
        trigger_type=trigger_type,
        phase=phase,
        moment=moment,
    )
    alert_worthiness_score = min(
        100.0,
        round(
            (operational_score * 0.45)
            + (executability * 0.2)
            + (max(net_edge or 0.0, 0.0) * 6.0)
            + min(max(range_margin, 0.0), 10.0)
            + trigger_bonus
            - (18.0 if opportunity.is_late_entry_risk else 0.0),
            2,
        ),
    )
    details = {
        "alert_worthiness_score": alert_worthiness_score,
        "alert_trigger_type": trigger_type,
        "has_actionable_trigger": has_actionable_trigger,
        "alert_state_key": alert_state_key,
        "movement_phase": phase,
        "alert_moment_type": moment,
        "opportunity_type": opportunity.opportunity_type,
        "score": score,
        "operational_score": operational_score,
        "executability_score": opportunity.executability_score,
        "estimated_net_trade_edge_pct": net_edge,
    }

    if not (opportunity.opportunity_type in {"trade", "hold"} or bool(opportunity.operable_signal)):
        return False, "opportunity_type_not_alertable", details
    if phase == "accumulation" and not has_actionable_trigger:
        return False, "accumulation_only", details
    if moment == "preparation" and not has_actionable_trigger:
        return False, "preparation_without_trigger", details
    if phase in {"neutral"} and moment in {"neutral"} and not has_actionable_trigger:
        return False, "no_actionable_operation", details
    if alert_worthiness_score < 55:
        return False, "insufficient_alert_worthiness", details
    return True, None, details


def enrich_alert_worthiness(opportunity: Opportunity) -> Opportunity:
    alertable, block_reason, details = classify_alert_worthiness(opportunity)
    data = opportunity.model_dump()
    data.update(
        {
            "operational_score": details.get("operational_score", derive_operational_score(opportunity)),
            "alert_worthiness_score": details.get("alert_worthiness_score"),
            "alert_trigger_type": details.get("alert_trigger_type"),
            "has_actionable_trigger": bool(details.get("has_actionable_trigger")),
            "alert_state_key": details.get("alert_state_key"),
            "alert_block_reason": None if alertable else block_reason,
        }
    )
    data.update(build_operational_thesis(data))
    return Opportunity(**data)


def is_telegram_alertable(opportunity: Opportunity) -> bool:
    return classify_alert_worthiness(opportunity)[0]
