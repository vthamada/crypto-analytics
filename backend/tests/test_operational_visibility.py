from __future__ import annotations

from app.models.schemas import Exchange, MovementType, Opportunity
from app.services.operational_visibility import classify_pipeline_visibility, is_telegram_alertable


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
