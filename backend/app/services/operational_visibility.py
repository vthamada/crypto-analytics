from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from app.models.schemas import Opportunity

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
    if movement_type == "weak" and not (_get(data, "operable_signal") and (_get(data, "score") or 0) >= 60):
        return "discarded_observation", "weak_movement", False
    if (_get(data, "quote_volume_24h") or 0) < 3_000:
        return "blocked_signal", "insufficient_volume", False
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
        and (_get(data, "score") or 0) >= 70
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


def add_visibility_fields(data: dict[str, Any]) -> dict[str, Any]:
    pipeline_status, visibility_reason, operationally_visible = classify_pipeline_visibility_payload(data)
    return {
        **data,
        "pipeline_status": pipeline_status,
        "visibility_reason": visibility_reason,
        "operationally_visible": operationally_visible,
    }


def enrich_operational_visibility(opportunity: Opportunity) -> Opportunity:
    pipeline_status, visibility_reason, operationally_visible = classify_pipeline_visibility(opportunity)
    data = opportunity.model_dump()
    data.update(
        {
            "pipeline_status": pipeline_status,
            "visibility_reason": visibility_reason,
            "operationally_visible": operationally_visible,
        }
    )
    return Opportunity(**data)


def is_operationally_visible(opportunity: Opportunity) -> bool:
    return classify_pipeline_visibility(opportunity)[2]


def is_telegram_alertable(opportunity: Opportunity) -> bool:
    status, _, visible = classify_pipeline_visibility(opportunity)
    if not visible or status != "operational_opportunity":
        return False
    return opportunity.opportunity_type in {"trade", "hold"} or bool(opportunity.operable_signal)
