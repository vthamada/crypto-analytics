from __future__ import annotations

from app.models.schemas import Opportunity
from app.services.telegram import rank_telegram_opportunity


def build_signal_pipeline_event(
    opportunity: Opportunity,
    *,
    stage: str,
    status: str,
    reason: str,
    event_type: str,
    workspace_id: str | None = None,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "exchange": opportunity.exchange,
        "pair": opportunity.pair,
        "stage": stage,
        "status": status,
        "reason": reason,
        "event_type": event_type,
        "workspace_id": workspace_id,
        "technical_signal_id": opportunity.technical_signal_id,
        "opportunity_id": opportunity.id,
        "details": details or {},
    }


def split_top_telegram_candidates(
    opportunities: list[Opportunity],
    *,
    top_n: int = 5,
) -> tuple[list[Opportunity], list[Opportunity]]:
    ranked = sorted(opportunities, key=rank_telegram_opportunity, reverse=True)
    return ranked[:top_n], ranked[top_n:]
