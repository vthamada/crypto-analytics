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

_pair_catalog_cache: dict | None = None
_pair_catalog_generated_at: datetime | None = None
_pair_catalog_provider_status: list[dict] = []


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


async def _fetch_provider_pairs() -> dict[Exchange, list[str]]:
    global _pair_catalog_provider_status

    providers = [NovaDaxProvider(), MercadoBitcoinProvider(), BinanceProvider()]
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
                provider_pairs[provider.exchange] = []
                provider_status.append(
                    {
                        "exchange": provider.exchange,
                        "returned_pairs": 0,
                        "brl_pairs": 0,
                        "status": "error",
                        "checked_at": checked_at,
                        "error_message": str(result),
                        "examples": [],
                    }
                )
                continue

            normalized_pairs = sorted({normalize_pair_symbol(pair) for pair in result if pair})
            brl_pairs = [pair for pair in normalized_pairs if pair.endswith("_BRL")]
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

        _pair_catalog_provider_status = provider_status
        return provider_pairs
    finally:
        await asyncio.gather(*(provider.close() for provider in providers), return_exceptions=True)


def _build_catalog_payload(provider_pairs: dict[Exchange, list[str]], generated_at: datetime) -> dict:
    known_exchanges = [Exchange.NOVADAX, Exchange.MERCADO_BITCOIN, Exchange.BINANCE]
    provider_pair_sets = {exchange: set(pairs) for exchange, pairs in provider_pairs.items()}
    provider_status_by_exchange = {
        item["exchange"]: item
        for item in _pair_catalog_provider_status
        if item.get("exchange") in known_exchanges
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
                    for exchange in known_exchanges
                },
                "raw_symbols": {
                    exchange.value: pair if pair in provider_pair_sets.get(exchange, set()) else None
                    for exchange in known_exchanges
                },
                "is_active": {
                    exchange.value: pair in provider_pair_sets.get(exchange, set())
                    for exchange in known_exchanges
                },
                "is_tradable": {
                    exchange.value: pair in provider_pair_sets.get(exchange, set())
                    for exchange in known_exchanges
                },
                "status": {
                    exchange.value: (
                        "tradable"
                        if pair in provider_pair_sets.get(exchange, set())
                        else provider_status_by_exchange.get(exchange, {}).get("status", "not_listed")
                    )
                    for exchange in known_exchanges
                },
                "error_message": {
                    exchange.value: provider_status_by_exchange.get(exchange, {}).get("error_message")
                    for exchange in known_exchanges
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
                    "status": "ok" if provider_pair_sets.get(exchange, set()) else "empty",
                    "checked_at": generated_at,
                    "error_message": None,
                    "examples": sorted(provider_pair_sets.get(exchange, set()))[:5],
                },
            )
            for exchange in known_exchanges
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


async def get_available_pairs_catalog(*, force_refresh: bool = False) -> dict:
    global _pair_catalog_cache, _pair_catalog_generated_at

    now = utcnow()
    if (
        not force_refresh
        and _pair_catalog_cache is not None
        and _pair_catalog_generated_at is not None
        and (now - _pair_catalog_generated_at).total_seconds() < PAIR_CATALOG_TTL_SECONDS
    ):
        return _pair_catalog_cache

    provider_pairs = await _fetch_provider_pairs()
    payload = _build_catalog_payload(provider_pairs, now)
    _pair_catalog_cache = payload
    _pair_catalog_generated_at = now
    return payload


async def get_scannable_pairs_by_exchange(
    *,
    enabled_pairs: list[str],
    enabled_exchanges: list[Exchange],
    force_refresh: bool = False,
) -> dict[Exchange, list[str]]:
    if not enabled_exchanges:
        return {exchange: [] for exchange in enabled_exchanges}

    catalog = await get_available_pairs_catalog(force_refresh=force_refresh)
    if not enabled_pairs:
        enabled_pairs = select_relevant_brl_pairs(catalog)

    return filter_pairs_by_availability(
        enabled_pairs=enabled_pairs,
        enabled_exchanges=enabled_exchanges,
        catalog=catalog,
    )
