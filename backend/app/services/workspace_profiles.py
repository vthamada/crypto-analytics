from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import AppConfig, MovementType, Opportunity


@dataclass(frozen=True)
class TradingProfileSettings:
    trading_profile: str
    order_notional_brl: float
    max_entry_slippage_bps: float
    max_exit_slippage_bps: float
    min_quote_volume_brl: float


PROFILE_DEFAULTS: dict[str, TradingProfileSettings] = {
    "conservador": TradingProfileSettings("conservador", 1_000.0, 300.0, 300.0, 10_000.0),
    "intraday_liquido": TradingProfileSettings("intraday_liquido", 1_000.0, 500.0, 500.0, 3_000.0),
    "agressivo": TradingProfileSettings("agressivo", 300.0, 800.0, 800.0, 3_000.0),
    "scalp": TradingProfileSettings("scalp", 200.0, 300.0, 300.0, 5_000.0),
}


def resolve_trading_profile(config: AppConfig) -> TradingProfileSettings:
    defaults = PROFILE_DEFAULTS.get(config.trading_profile, PROFILE_DEFAULTS["intraday_liquido"])
    return TradingProfileSettings(
        trading_profile=defaults.trading_profile,
        order_notional_brl=float(config.order_notional_brl or defaults.order_notional_brl),
        max_entry_slippage_bps=float(config.max_entry_slippage_bps or defaults.max_entry_slippage_bps),
        max_exit_slippage_bps=float(config.max_exit_slippage_bps or defaults.max_exit_slippage_bps),
        min_quote_volume_brl=float(config.min_quote_volume_brl or defaults.min_quote_volume_brl),
    )


def highest_order_notional(configs: list[AppConfig]) -> float:
    if not configs:
        return PROFILE_DEFAULTS["intraday_liquido"].order_notional_brl
    return max(resolve_trading_profile(config).order_notional_brl for config in configs)


def widest_slippage_cap(configs: list[AppConfig]) -> float:
    if not configs:
        return PROFILE_DEFAULTS["intraday_liquido"].max_exit_slippage_bps
    return max(resolve_trading_profile(config).max_exit_slippage_bps for config in configs)


def opportunity_matches_alert_scope(opportunity: Opportunity, config: AppConfig) -> bool:
    return explain_alert_scope(opportunity, config)[0]


def explain_workspace_visibility(opportunity: Opportunity, config: AppConfig) -> tuple[bool, str | None, dict[str, object]]:
    exchange = opportunity.exchange.value if hasattr(opportunity.exchange, "value") else str(opportunity.exchange)
    movement = (
        opportunity.movement_type.value
        if hasattr(opportunity.movement_type, "value")
        else str(opportunity.movement_type)
    )
    enabled_exchanges = {
        item.value if hasattr(item, "value") else str(item)
        for item in config.enabled_exchanges
    }
    enabled_movements = {item.value if hasattr(item, "value") else str(item) for item in MovementType}
    profile = resolve_trading_profile(config)
    min_quote_volume = max(config.thresholds.min_volume_brl_small, profile.min_quote_volume_brl)

    details: dict[str, object] = {
        "exchange": exchange,
        "pair": opportunity.pair,
        "volatility_pct": opportunity.volatility_pct,
        "min_volatility_pct": config.thresholds.min_volatility_pct,
        "liquidity_units": opportunity.liquidity_units,
        "min_liquidity_units": config.thresholds.min_liquidity_units,
        "spread_pct": opportunity.spread_pct,
        "max_spread_pct": config.thresholds.max_spread_pct,
        "quote_volume_24h": opportunity.quote_volume_24h,
        "min_quote_volume_brl": min_quote_volume,
        "trading_profile": profile.trading_profile,
    }

    if exchange not in enabled_exchanges:
        return False, "exchange_disabled", details
    if config.enabled_pairs and opportunity.pair not in config.enabled_pairs:
        return False, "pair_not_enabled", details
    if opportunity.volatility_pct < config.thresholds.min_volatility_pct:
        return False, "volatility_below_threshold", details
    if opportunity.liquidity_units < config.thresholds.min_liquidity_units:
        return False, "insufficient_liquidity", details
    if opportunity.spread_pct > config.thresholds.max_spread_pct:
        return False, "spread_above_threshold", details
    if opportunity.quote_volume_24h < min_quote_volume:
        return False, "insufficient_volume", details
    if movement not in enabled_movements:
        return False, "movement_type_not_supported", details
    return True, None, details


def explain_alert_scope(opportunity: Opportunity, config: AppConfig) -> tuple[bool, str | None, dict[str, object]]:
    details: dict[str, object] = {
        "score": opportunity.score,
        "opportunity_type": opportunity.opportunity_type,
        "operable_signal": opportunity.operable_signal,
        "executability_score": opportunity.executability_score,
        "telegram_operable_only": config.telegram_operable_only,
        "telegram_min_executability_score": config.telegram_min_executability_score,
    }

    if opportunity.opportunity_type == "avoid":
        return False, "opportunity_type_not_alertable", details

    if config.telegram_alert_exchanges:
        allowed = {
            exchange.value if hasattr(exchange, "value") else str(exchange)
            for exchange in config.telegram_alert_exchanges
        }
        if opportunity.exchange.value not in allowed:
            details["allowed_exchanges"] = sorted(allowed)
            return False, "exchange_not_in_alert_scope", details

    if config.telegram_alert_pairs and opportunity.pair not in set(config.telegram_alert_pairs):
        details["allowed_pairs"] = sorted(config.telegram_alert_pairs)
        return False, "pair_not_in_alert_scope", details

    if config.telegram_operable_only and not opportunity.operable_signal:
        return False, "not_operable_for_alert_scope", details

    if (
        config.telegram_min_executability_score is not None
        and opportunity.executability_score is not None
        and opportunity.executability_score < config.telegram_min_executability_score
    ):
        return False, "below_min_executability", details

    return True, None, details
