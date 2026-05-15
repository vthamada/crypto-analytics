from __future__ import annotations

from app.models.schemas import Exchange, MovementPhase, MovementType, Opportunity
from app.services.operational_visibility import (
    classify_alert_worthiness,
    classify_opportunity_subtype,
    classify_pipeline_visibility,
    is_telegram_alertable,
)


def make_opportunity(**overrides) -> Opportunity:
    payload = {
        "id": "opp-1",
        "exchange": Exchange.NOVADAX,
        "pair": "BTC_BRL",
        "score": 72.0,
        "executability_score": 70.0,
        "interesting_signal": True,
        "operable_signal": True,
        "estimated_net_trade_edge_pct": 0.8,
        "trade_margin_score": 45.0,
        "opportunity_type": "trade",
        "volatility_pct": 3.5,
        "volume_24h": 10.0,
        "quote_volume_24h": 80_000.0,
        "liquidity_units": 2_000.0,
        "spread_pct": 0.2,
        "movement_type": MovementType.STRONG_RANGE,
        "movement_phase": MovementPhase.EARLY_BREAKOUT,
        "alert_moment_type": "early_breakout",
        "last_price": 10.0,
        "change_pct": 2.0,
    }
    payload.update(overrides)
    return Opportunity(**payload)


def test_trade_signal_is_operational_and_alertable():
    status, reason, visible = classify_pipeline_visibility(make_opportunity())

    assert status == "operational_opportunity"
    assert reason == "trade_qualified"
    assert visible is True
    assert is_telegram_alertable(make_opportunity()) is True
    assert classify_opportunity_subtype(make_opportunity()) == "breakout_trade"


def test_range_signal_gets_range_trade_subtype():
    opportunity = make_opportunity(
        movement_phase=MovementPhase.NEUTRAL,
        alert_moment_type="neutral",
        operational_range_quality="valid_medium_trade",
        operational_range_margin_pct=1.4,
    )

    assert classify_opportunity_subtype(opportunity) == "range_trade"


def test_arbitrage_and_avoid_subtypes_are_explicit():
    assert classify_opportunity_subtype(make_opportunity(arbitrage_available=True)) == "cross_exchange_arbitrage"
    assert classify_opportunity_subtype(make_opportunity(opportunity_type="avoid")) == "avoid"


def test_accumulation_without_trigger_is_visible_but_not_alertable():
    opportunity = make_opportunity(
        movement_phase=MovementPhase.ACCUMULATION,
        alert_moment_type="preparation",
        alert_reason="ativo em possivel preparacao/lateralizacao",
    )

    status, reason, visible = classify_pipeline_visibility(opportunity)
    alertable, block_reason, details = classify_alert_worthiness(opportunity)

    assert status == "operational_opportunity"
    assert reason == "trade_qualified"
    assert visible is True
    assert alertable is False
    assert block_reason == "accumulation_only"
    assert details["has_actionable_trigger"] is False
    assert details["alert_state_key"].startswith("no_trigger|accumulation")
    assert is_telegram_alertable(opportunity) is False


def test_preparation_without_trigger_is_not_alertable():
    opportunity = make_opportunity(
        movement_phase=MovementPhase.NEUTRAL,
        alert_moment_type="preparation",
    )

    alertable, block_reason, details = classify_alert_worthiness(opportunity)

    assert alertable is False
    assert block_reason == "preparation_without_trigger"
    assert details["alert_worthiness_score"] > 0


def test_actionable_alert_has_trigger_and_state_key():
    alertable, block_reason, details = classify_alert_worthiness(make_opportunity())

    assert alertable is True
    assert block_reason is None
    assert details["alert_trigger_type"] == "early_breakout"
    assert details["has_actionable_trigger"] is True
    assert details["alert_state_key"].startswith("early_breakout|early_breakout|early_breakout")


def test_avoid_signal_is_blocked_even_when_score_is_high():
    opportunity = make_opportunity(
        score=99.0,
        opportunity_type="avoid",
        operable_signal=True,
        estimated_net_trade_edge_pct=1.0,
    )

    status, reason, visible = classify_pipeline_visibility(opportunity)

    assert status == "blocked_signal"
    assert reason == "opportunity_type_not_alertable"
    assert visible is False
    assert is_telegram_alertable(opportunity) is False


def test_negative_margin_stays_in_audit_not_dashboard():
    opportunity = make_opportunity(
        opportunity_type="trade",
        estimated_net_trade_edge_pct=-0.2,
    )

    status, reason, visible = classify_pipeline_visibility(opportunity)

    assert status == "blocked_signal"
    assert reason == "insufficient_operational_margin"
    assert visible is False


def test_strong_observable_can_be_visible_but_not_telegram_alertable():
    opportunity = make_opportunity(
        opportunity_type="observe",
        operable_signal=False,
        score=82.0,
        executability_score=62.0,
        estimated_net_trade_edge_pct=0.35,
    )

    status, reason, visible = classify_pipeline_visibility(opportunity)

    assert status == "operational_opportunity"
    assert reason == "strong_observable_signal"
    assert visible is True
    assert is_telegram_alertable(opportunity) is False
