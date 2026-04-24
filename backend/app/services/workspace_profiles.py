from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import AppConfig, Opportunity


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
    if config.telegram_alert_exchanges:
        allowed = {
            exchange.value if hasattr(exchange, "value") else str(exchange)
            for exchange in config.telegram_alert_exchanges
        }
        if opportunity.exchange.value not in allowed:
            return False

    if config.telegram_alert_pairs and opportunity.pair not in set(config.telegram_alert_pairs):
        return False

    if config.telegram_operable_only and not opportunity.operable_signal:
        return False

    if (
        config.telegram_min_executability_score is not None
        and opportunity.executability_score is not None
        and opportunity.executability_score < config.telegram_min_executability_score
    ):
        return False

    return True
