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

_pair_catalog_cache: dict | None = None
_pair_catalog_generated_at: datetime | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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