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


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _sort_pair_key(pair: str) -> tuple[str, str]:
    if "_" not in pair:
        return "", pair
    base, quote = pair.split("_", 1)
    return quote, base


async def _fetch_provider_pairs() -> dict[Exchange, list[str]]:
    providers = [NovaDaxProvider(), MercadoBitcoinProvider(), BinanceProvider()]
    try:
        results = await asyncio.gather(
            *(provider.get_available_pairs() for provider in providers),
            return_exceptions=True,
        )

        provider_pairs: dict[Exchange, list[str]] = {}
        for provider, result in zip(providers, results, strict=False):
            if isinstance(result, Exception):
                logger.warning("available_pairs_fetch_failed exchange=%s error=%s", provider.exchange.value, result)
                provider_pairs[provider.exchange] = []
                continue

            provider_pairs[provider.exchange] = sorted({pair.upper() for pair in result})

        return provider_pairs
    finally:
        await asyncio.gather(*(provider.close() for provider in providers), return_exceptions=True)


def _build_catalog_payload(provider_pairs: dict[Exchange, list[str]], generated_at: datetime) -> dict:
    known_exchanges = [Exchange.NOVADAX, Exchange.MERCADO_BITCOIN, Exchange.BINANCE]
    provider_pair_sets = {exchange: set(pairs) for exchange, pairs in provider_pairs.items()}
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
                "availability": {
                    exchange.value: pair in provider_pair_sets.get(exchange, set())
                    for exchange in known_exchanges
                },
            }
            for pair in all_pairs
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
    if not enabled_pairs or not enabled_exchanges:
        return {exchange: [] for exchange in enabled_exchanges}

    catalog = await get_available_pairs_catalog(force_refresh=force_refresh)
    return filter_pairs_by_availability(
        enabled_pairs=enabled_pairs,
        enabled_exchanges=enabled_exchanges,
        catalog=catalog,
    )
