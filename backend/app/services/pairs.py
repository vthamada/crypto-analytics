from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.models.schemas import Exchange
from app.providers.binance import BinanceProvider
from app.providers.mercado_bitcoin import MercadoBitcoinProvider
from app.providers.novadax import NovaDaxProvider

logger = logging.getLogger(__name__)

PAIR_CATALOG_TTL_SECONDS = 3600
DEFAULT_ENABLED_PAIR_LIMIT = 10
DEFAULT_CATALOG_EXCHANGES = [Exchange.NOVADAX, Exchange.MERCADO_BITCOIN]
KNOWN_EXCHANGES = [Exchange.NOVADAX, Exchange.MERCADO_BITCOIN, Exchange.BINANCE]

_pair_catalog_cache: dict[tuple[str, ...], dict] | dict | None = {}
_pair_catalog_generated_at: dict[tuple[str, ...], datetime] | datetime | None = {}
_pair_catalog_provider_status: dict[tuple[str, ...], list[dict]] | list[dict] = {}
_provider_last_successful_pairs: dict[Exchange, list[str]] = {}


def _provider_map() -> dict[Exchange, type]:
    return {
        Exchange.NOVADAX: NovaDaxProvider,
        Exchange.MERCADO_BITCOIN: MercadoBitcoinProvider,
        Exchange.BINANCE: BinanceProvider,
    }


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _sort_pair_key(pair: str) -> tuple[str, str]:
    if "_" not in pair:
        return "", pair
    base, quote = pair.split("_", 1)
    return quote, base


def _split_pair(pair: str) -> tuple[str | None, str | None]:
    normalized = pair.upper().replace("/", "_").replace("-", "_")
    if "_" in normalized:
        base, quote = normalized.split("_", 1)
        return base or None, quote or None
    for quote in ("BRL", "USDT", "USD"):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)], quote
    return normalized or None, None


def normalize_pair_symbol(pair: str) -> str:
    base, quote = _split_pair(pair)
    if base and quote:
        return f"{base}_{quote}"
    return pair.upper().replace("/", "_").replace("-", "_")


def _normalize_enabled_exchanges(enabled_exchanges: list[Exchange] | None = None) -> list[Exchange]:
    selected = enabled_exchanges or DEFAULT_CATALOG_EXCHANGES
    normalized: list[Exchange] = []
    for exchange in selected:
        parsed = exchange if isinstance(exchange, Exchange) else Exchange(str(exchange))
        if parsed not in normalized:
            normalized.append(parsed)
    return normalized


def _catalog_cache_key(enabled_exchanges: list[Exchange] | None = None) -> tuple[str, ...]:
    return tuple(exchange.value for exchange in _normalize_enabled_exchanges(enabled_exchanges))


def _get_cache_entry(key: tuple[str, ...], now: datetime) -> dict | None:
    if not isinstance(_pair_catalog_cache, dict) or not isinstance(_pair_catalog_generated_at, dict):
        return None
    cached = _pair_catalog_cache.get(key)
    generated_at = _pair_catalog_generated_at.get(key)
    if cached is None or generated_at is None:
        return None
    if (now - generated_at).total_seconds() >= PAIR_CATALOG_TTL_SECONDS:
        return None
    return cached


def _set_cache_entry(key: tuple[str, ...], payload: dict, generated_at: datetime) -> None:
    global _pair_catalog_cache, _pair_catalog_generated_at
    if not isinstance(_pair_catalog_cache, dict):
        _pair_catalog_cache = {}
    if not isinstance(_pair_catalog_generated_at, dict):
        _pair_catalog_generated_at = {}
    _pair_catalog_cache[key] = payload
    _pair_catalog_generated_at[key] = generated_at


async def _fetch_provider_pairs(enabled_exchanges: list[Exchange] | None = None) -> dict[Exchange, list[str]]:
    global _pair_catalog_provider_status

    provider_map = _provider_map()
    active_exchanges = _normalize_enabled_exchanges(enabled_exchanges)
    providers = [provider_map[exchange]() for exchange in active_exchanges if exchange in provider_map]
    checked_at = utcnow()
    try:
        results = await asyncio.gather(
            *(provider.get_available_pairs() for provider in providers),
            return_exceptions=True,
        )

        provider_pairs: dict[Exchange, list[str]] = {}
        provider_status: list[dict] = []
        for provider, result in zip(providers, results, strict=False):
            if isinstance(result, Exception):
                logger.warning("available_pairs_fetch_failed exchange=%s error=%s", provider.exchange.value, result)
                stale_pairs = _provider_last_successful_pairs.get(provider.exchange, [])
                provider_pairs[provider.exchange] = stale_pairs
                provider_status.append(
                    {
                        "exchange": provider.exchange,
                        "returned_pairs": len(stale_pairs),
                        "brl_pairs": len([pair for pair in stale_pairs if pair.endswith("_BRL")]),
                        "status": "stale" if stale_pairs else "error",
                        "checked_at": checked_at,
                        "error_message": str(result),
                        "examples": stale_pairs[:5],
                    }
                )
                continue

            normalized_pairs = sorted({normalize_pair_symbol(pair) for pair in result if pair})
            if not normalized_pairs:
                stale_pairs = _provider_last_successful_pairs.get(provider.exchange, [])
                provider_pairs[provider.exchange] = stale_pairs
                provider_status.append(
                    {
                        "exchange": provider.exchange,
                        "returned_pairs": len(stale_pairs),
                        "brl_pairs": len([pair for pair in stale_pairs if pair.endswith("_BRL")]),
                        "status": "stale" if stale_pairs else "empty",
                        "checked_at": checked_at,
                        "error_message": "provider returned an empty catalog"
                        if stale_pairs
                        else "provider returned no catalog pairs",
                        "examples": stale_pairs[:5],
                    }
                )
                logger.warning(
                    "available_pairs_provider_empty exchange=%s stale_pairs=%s",
                    provider.exchange.value,
                    len(stale_pairs),
                )
                continue

            brl_pairs = [pair for pair in normalized_pairs if pair.endswith("_BRL")]
            _provider_last_successful_pairs[provider.exchange] = normalized_pairs
            provider_pairs[provider.exchange] = normalized_pairs
            provider_status.append(
                {
                    "exchange": provider.exchange,
                    "returned_pairs": len(normalized_pairs),
                    "brl_pairs": len(brl_pairs),
                    "status": "ok" if normalized_pairs else "empty",
                    "checked_at": checked_at,
                    "error_message": None,
                    "examples": normalized_pairs[:5],
                }
            )
            logger.info(
                "available_pairs_provider_catalog exchange=%s returned=%s brl_pairs=%s examples=%s",
                provider.exchange.value,
                len(normalized_pairs),
                len(brl_pairs),
                normalized_pairs[:5],
            )

        if not isinstance(_pair_catalog_provider_status, dict):
            _pair_catalog_provider_status = {}
        _pair_catalog_provider_status[_catalog_cache_key(active_exchanges)] = provider_status
        return provider_pairs
    finally:
        await asyncio.gather(*(provider.close() for provider in providers), return_exceptions=True)


def _provider_status_for_key(key: tuple[str, ...]) -> list[dict]:
    if isinstance(_pair_catalog_provider_status, dict):
        return _pair_catalog_provider_status.get(key, [])
    return _pair_catalog_provider_status


def _provider_for_exchange(exchange: Exchange):
    provider_map = _provider_map()
    provider_cls = provider_map.get(exchange)
    if provider_cls is None:
        raise ValueError(f"Unsupported exchange: {exchange}")
    return provider_cls()


async def _run_diagnostic_check(name: str, func) -> dict:
    try:
        result = await func()
        details: dict[str, object] = {}
        if isinstance(result, list):
            details["count"] = len(result)
        elif hasattr(result, "model_dump"):
            details = result.model_dump(mode="json")
        return {"name": name, "status": "ok", "message": None, "details": details}
    except Exception as exc:
        return {"name": name, "status": "error", "message": str(exc), "details": {}}


async def get_pair_exchange_diagnostic(exchange: Exchange, pair: str) -> dict:
    parsed_exchange = exchange if isinstance(exchange, Exchange) else Exchange(str(exchange))
    normalized_pair = normalize_pair_symbol(pair)
    provider = _provider_for_exchange(parsed_exchange)
    checked_at = utcnow()
    try:
        raw_symbol = provider.normalize_pair(normalized_pair)
        available_pairs: list[str] = []
        try:
            available_pairs = await provider.get_available_pairs()
            catalog_status = "ok"
            catalog_message = None
        except Exception as exc:
            catalog_status = "error"
            catalog_message = str(exc)

        normalized_available_pairs = [normalize_pair_symbol(item) for item in available_pairs]
        exists_in_catalog = normalized_pair in set(normalized_available_pairs)
        if catalog_status == "error" and not normalized_available_pairs:
            monitorability_reason = "cache_empty"
        elif not normalized_pair.endswith("_BRL"):
            monitorability_reason = "not_brl_pair"
        elif not exists_in_catalog:
            monitorability_reason = "pair_not_in_catalog"
        else:
            monitorability_reason = None

        checks = [
            {
                "name": "catalog",
                "status": catalog_status,
                "message": catalog_message,
                "details": {
                    "returned_pairs": len(normalized_available_pairs),
                    "examples": normalized_available_pairs[:5],
                    "exists_in_catalog": exists_in_catalog,
                },
            },
            await _run_diagnostic_check("ticker", lambda: provider.get_ticker(normalized_pair)),
            await _run_diagnostic_check("order_book", lambda: provider.get_order_book(normalized_pair)),
            await _run_diagnostic_check(
                "klines",
                lambda: provider.get_klines(normalized_pair, interval="5m", limit=50),
            ),
        ]
        has_errors = any(check["status"] == "error" for check in checks)
        overall_status = "error" if has_errors else "ok" if exists_in_catalog else "warning"
        return {
            "exchange": parsed_exchange,
            "pair": normalized_pair,
            "display_name": normalized_pair.replace("_", "/"),
            "raw_symbol": raw_symbol,
            "exists_in_catalog": exists_in_catalog,
            "overall_status": overall_status,
            "checked_at": checked_at,
            "checks": checks,
            "monitorable": monitorability_reason is None,
            "monitorability_reason": monitorability_reason,
        }
    finally:
        await provider.close()


def _build_catalog_payload(
    provider_pairs: dict[Exchange, list[str]],
    generated_at: datetime,
    *,
    enabled_exchanges: list[Exchange] | None = None,
) -> dict:
    active_exchanges = _normalize_enabled_exchanges(enabled_exchanges)
    active_exchange_set = set(active_exchanges)
    provider_pair_sets = {exchange: set(pairs) for exchange, pairs in provider_pairs.items()}
    provider_status = _provider_status_for_key(_catalog_cache_key(active_exchanges))
    provider_status_by_exchange = {
        item["exchange"]: item
        for item in provider_status
        if item.get("exchange") in KNOWN_EXCHANGES
    }
    all_pairs = sorted(
        {pair for pairs in provider_pair_sets.values() for pair in pairs},
        key=_sort_pair_key,
    )

    return {
        "generated_at": generated_at,
        "expires_at": generated_at + timedelta(seconds=PAIR_CATALOG_TTL_SECONDS),
        "pairs": [
            {
                "pair": pair,
                "display_name": pair.replace("_", "/"),
                "normalized_symbol": pair,
                "base_asset": _split_pair(pair)[0],
                "quote_asset": _split_pair(pair)[1],
                "is_brl_pair": pair.endswith("_BRL"),
                "availability": {
                    exchange.value: pair in provider_pair_sets.get(exchange, set())
                    for exchange in KNOWN_EXCHANGES
                },
                "raw_symbols": {
                    exchange.value: pair if pair in provider_pair_sets.get(exchange, set()) else None
                    for exchange in KNOWN_EXCHANGES
                },
                "is_active": {
                    exchange.value: exchange in active_exchange_set and pair in provider_pair_sets.get(exchange, set())
                    for exchange in KNOWN_EXCHANGES
                },
                "is_tradable": {
                    exchange.value: exchange in active_exchange_set and pair in provider_pair_sets.get(exchange, set())
                    for exchange in KNOWN_EXCHANGES
                },
                "status": {
                    exchange.value: (
                        "disabled"
                        if exchange not in active_exchange_set
                        else "tradable"
                        if pair in provider_pair_sets.get(exchange, set())
                        else provider_status_by_exchange.get(exchange, {}).get("status", "not_listed")
                    )
                    for exchange in KNOWN_EXCHANGES
                },
                "error_message": {
                    exchange.value: provider_status_by_exchange.get(exchange, {}).get("error_message")
                    for exchange in KNOWN_EXCHANGES
                },
            }
            for pair in all_pairs
        ],
        "provider_status": [
            provider_status_by_exchange.get(
                exchange,
                {
                    "exchange": exchange,
                    "returned_pairs": len(provider_pair_sets.get(exchange, set())),
                    "brl_pairs": len([pair for pair in provider_pair_sets.get(exchange, set()) if pair.endswith("_BRL")]),
                    "status": "disabled"
                    if exchange not in active_exchange_set
                    else "ok"
                    if provider_pair_sets.get(exchange, set())
                    else "empty",
                    "checked_at": generated_at,
                    "error_message": None,
                    "examples": sorted(provider_pair_sets.get(exchange, set()))[:5],
                },
            )
            for exchange in KNOWN_EXCHANGES
        ],
    }


def select_default_enabled_pairs(catalog: dict, limit: int = DEFAULT_ENABLED_PAIR_LIMIT) -> list[str]:
    pairs = catalog.get("pairs", []) if isinstance(catalog, dict) else []
    if not pairs or limit <= 0:
        return []

    ranked_pairs = sorted(
        pairs,
        key=lambda item: (
            -sum(1 for available in item.get("availability", {}).values() if available),
            _sort_pair_key(item.get("pair", "")),
        ),
    )
    return [item["pair"] for item in ranked_pairs[:limit] if item.get("pair")]


def select_relevant_brl_pairs(catalog: dict, limit: int | None = None) -> list[str]:
    pairs = catalog.get("pairs", []) if isinstance(catalog, dict) else []
    brl_pairs = [
        item
        for item in pairs
        if isinstance(item.get("pair"), str) and item["pair"].upper().endswith("_BRL")
    ]
    ranked_pairs = sorted(
        brl_pairs,
        key=lambda item: (
            -sum(1 for available in item.get("availability", {}).values() if available),
            _sort_pair_key(item.get("pair", "")),
        ),
    )
    selected = [item["pair"] for item in ranked_pairs if item.get("pair")]
    return selected[:limit] if limit is not None else selected


def filter_pairs_by_availability(
    *,
    enabled_pairs: list[str],
    enabled_exchanges: list[Exchange],
    catalog: dict,
) -> dict[Exchange, list[str]]:
    catalog_pairs = {
        item["pair"]: item.get("availability", {})
        for item in catalog.get("pairs", [])
        if item.get("pair")
    }

    filtered_pairs: dict[Exchange, list[str]] = {}
    for exchange in enabled_exchanges:
        exchange_key = exchange.value if hasattr(exchange, "value") else str(exchange)
        filtered_pairs[exchange] = [
            pair
            for pair in enabled_pairs
            if catalog_pairs.get(pair, {}).get(exchange_key, False)
        ]

    return filtered_pairs


def explain_pair_monitorability(*, catalog: dict, exchange: Exchange, pair: str) -> dict:
    normalized_pair = normalize_pair_symbol(pair)
    exchange_key = exchange.value if hasattr(exchange, "value") else str(exchange)
    provider_status = {
        (item.get("exchange").value if hasattr(item.get("exchange"), "value") else str(item.get("exchange"))): item
        for item in catalog.get("provider_status", [])
        if item.get("exchange") is not None
    }
    provider = provider_status.get(exchange_key, {})
    pair_record = next(
        (item for item in catalog.get("pairs", []) if item.get("pair") == normalized_pair),
        None,
    )

    if provider.get("status") == "disabled":
        reason = "exchange_disabled"
    elif provider.get("status") == "error":
        reason = "cache_empty" if int(provider.get("returned_pairs") or 0) == 0 else "cache_stale"
    elif provider.get("status") == "empty":
        reason = "cache_empty"
    elif provider.get("status") == "stale":
        reason = "cache_stale"
    elif not normalized_pair.endswith("_BRL"):
        reason = "not_brl_pair"
    elif pair_record is None:
        reason = "pair_not_in_catalog"
    elif not pair_record.get("availability", {}).get(exchange_key, False):
        reason = "pair_not_in_catalog"
    elif not pair_record.get("is_active", {}).get(exchange_key, False):
        reason = "pair_inactive"
    elif not pair_record.get("is_tradable", {}).get(exchange_key, False):
        reason = "pair_not_tradable"
    else:
        reason = None

    return {
        "exchange": exchange_key,
        "pair": normalized_pair,
        "monitorable": reason is None,
        "monitorability_reason": reason,
        "provider_status": provider.get("status"),
        "provider_error": provider.get("error_message"),
        "catalog_generated_at": catalog.get("generated_at"),
        "catalog_expires_at": catalog.get("expires_at"),
        "pair_status": (pair_record or {}).get("status", {}).get(exchange_key),
        "exists_in_catalog": pair_record is not None and pair_record.get("availability", {}).get(exchange_key, False),
        "is_active": (pair_record or {}).get("is_active", {}).get(exchange_key, False),
        "is_tradable": (pair_record or {}).get("is_tradable", {}).get(exchange_key, False),
        "is_brl_pair": normalized_pair.endswith("_BRL"),
    }


async def get_available_pairs_catalog(
    *,
    enabled_exchanges: list[Exchange] | None = None,
    force_refresh: bool = False,
) -> dict:
    now = utcnow()
    normalized_exchanges = _normalize_enabled_exchanges(enabled_exchanges)
    cache_key = _catalog_cache_key(normalized_exchanges)
    if not force_refresh:
        cached = _get_cache_entry(cache_key, now)
        if cached is not None:
            return cached

    provider_pairs = await _fetch_provider_pairs(normalized_exchanges)
    payload = _build_catalog_payload(provider_pairs, now, enabled_exchanges=normalized_exchanges)
    has_any_catalog_pairs = any(provider_pairs.get(exchange) for exchange in normalized_exchanges)
    if has_any_catalog_pairs:
        _set_cache_entry(cache_key, payload, now)
    else:
        logger.warning(
            "available_pairs_catalog_empty_not_cached exchanges=%s",
            [exchange.value for exchange in normalized_exchanges],
        )
    return payload


async def get_scannable_pairs_by_exchange(
    *,
    enabled_pairs: list[str],
    enabled_exchanges: list[Exchange],
    pair_universe_mode: str = "all_brl",
    force_refresh: bool = False,
) -> dict[Exchange, list[str]]:
    if not enabled_exchanges:
        return {exchange: [] for exchange in enabled_exchanges}

    catalog = await get_available_pairs_catalog(enabled_exchanges=enabled_exchanges, force_refresh=force_refresh)
    if pair_universe_mode == "watchlist_only":
        selected_pairs = [pair.upper().replace("/", "_").replace("-", "_") for pair in enabled_pairs]
    else:
        selected_pairs = select_relevant_brl_pairs(catalog)
    if pair_universe_mode != "watchlist_only" and enabled_pairs:
        selected_pairs = sorted(
            {pair.upper().replace("/", "_").replace("-", "_") for pair in [*selected_pairs, *enabled_pairs]},
            key=_sort_pair_key,
        )

    return filter_pairs_by_availability(
        enabled_pairs=selected_pairs,
        enabled_exchanges=enabled_exchanges,
        catalog=catalog,
    )
