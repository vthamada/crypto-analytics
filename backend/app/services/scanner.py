from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from app.models.schemas import (
    Exchange, Opportunity, Ticker, OrderBook, Kline,
    FilterThresholds, ScoreWeights, AppConfig,
)
from app.providers.base import ExchangeProvider
from app.providers.novadax import NovaDaxProvider
from app.providers.mercado_bitcoin import MercadoBitcoinProvider
from app.providers.binance import BinanceProvider
from app.services.pairs import get_scannable_pairs_by_exchange
from app.services.shared_state import (
    EXECUTABILITY_VERSION,
    MOVEMENT_VERSION,
    PROFILE_VERSION,
    SCORE_VERSION,
    calculate_technical_score,
)
from app.services.workspace_profiles import resolve_trading_profile
from app.filters.volatility import calculate_volatility, passes_volatility_filter, calculate_recent_change
from app.filters.volume import passes_volume_filter, volume_score
from app.filters.executability import (
    calculate_executability_score,
    calculate_trade_margin_metrics,
    classify_opportunity_type,
    classify_executability_band,
    estimate_fillable_notional,
    estimate_slippage_bps,
)
from app.filters.liquidity import (
    calculate_liquidity,
    calculate_notional_depth,
    calculate_total_notional_depth,
    passes_liquidity_filter,
    liquidity_score,
)
from app.filters.spread import calculate_spread, passes_spread_filter, spread_score
from app.filters.movement import classify_movement
from app.filters.movement import classify_movement_regime
from app.filters.scoring import calculate_score

logger = logging.getLogger(__name__)

DEFAULT_OPERABLE_EXECUTABILITY_SCORE = 60.0
DEFAULT_STAGE2_CANDIDATES_PER_EXCHANGE = 24
PAIR_TEMPERATURE_INTERVAL_SECONDS = {
    "hot": 0,
    "warm": 60,
    "cold": 300,
}
MAX_PROVIDER_PAIR_COOLDOWN_SECONDS = 900


MOVEMENT_MODIFIERS = {
    "strong_range": 1.15,
    "spike": 1.05,
    "weak": 0.7,
    "trap": 0.5,
}


@dataclass(frozen=True)
class LightScanCandidate:
    provider: ExchangeProvider
    pair: str
    ticker: Ticker
    preliminary_score: float
    reason: str


@dataclass
class PairScanState:
    temperature: str = "warm"
    last_light_scan_at: datetime | None = None
    last_deep_scan_at: datetime | None = None
    failure_count: int = 0
    cooldown_until: datetime | None = None
    last_discard_reason: str | None = None


class Scanner:
    """Main scanner that collects data from all exchanges and detects opportunities."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self._providers: dict[Exchange, ExchangeProvider] = {}
        self._opportunities: list[Opportunity] = []
        self._repetition_counts: dict[str, int] = {}  # pair -> count
        self._historical_calibration: dict[str, dict[str, float]] = {}
        self._pair_scan_state: dict[str, PairScanState] = {}
        self._scan_diagnostics: dict = {}
        self._running = False

        self._init_providers()

    def load_repetition_counts(self, counts: dict[str, int]) -> None:
        """Restore repetition counts from persistent storage."""
        self._repetition_counts.update(counts)

    def _init_providers(self) -> None:
        provider_map: dict[Exchange, type[ExchangeProvider]] = {
            Exchange.NOVADAX: NovaDaxProvider,
            Exchange.MERCADO_BITCOIN: MercadoBitcoinProvider,
            Exchange.BINANCE: BinanceProvider,
        }
        for exchange in self.config.enabled_exchanges:
            if exchange in provider_map:
                self._providers[exchange] = provider_map[exchange]()

    @property
    def opportunities(self) -> list[Opportunity]:
        return sorted(self._opportunities, key=lambda o: o.score, reverse=True)

    @property
    def providers(self) -> dict[Exchange, ExchangeProvider]:
        return self._providers

    @property
    def scan_diagnostics(self) -> dict:
        return deepcopy(self._scan_diagnostics)

    def set_historical_calibration(self, calibration: dict[str, dict[str, float]]) -> None:
        self._historical_calibration = calibration

    def _build_semantic_signal_key(
        self,
        *,
        exchange: Exchange,
        pair: str,
        movement_type: str,
        movement_regime: str | None,
    ) -> str:
        return ":".join(
            [
                exchange.value,
                pair,
                movement_type,
                movement_regime or "regime_unknown",
            ]
        )

    def _preliminary_movement_pct(self, ticker: Ticker) -> float:
        intraday_range_pct = 0.0
        if ticker.last_price > 0:
            intraday_range_pct = abs(ticker.high_24h - ticker.low_24h) / ticker.last_price * 100
        return max(abs(ticker.change_pct_24h), intraday_range_pct)

    def _light_triage_min_movement_pct(self) -> float:
        # Stage 1 should be permissive: it only decides whether a pair deserves
        # expensive book/candle analysis, not whether it is already a signal.
        return max(0.25, self.config.thresholds.min_volatility_pct * 0.25)

    def _light_triage_score(self, ticker: Ticker) -> float:
        movement_pct = self._preliminary_movement_pct(ticker)
        movement_score = min(movement_pct / max(self.config.thresholds.min_volatility_pct, 1.0), 1.0)
        preliminary_volume_score = volume_score(ticker)
        return round((movement_score * 0.55 + preliminary_volume_score * 0.45) * 100, 2)

    def _scan_state_key(self, exchange: Exchange, pair: str) -> str:
        return f"{exchange.value}:{pair.upper()}"

    def _get_pair_state(self, exchange: Exchange, pair: str) -> PairScanState:
        key = self._scan_state_key(exchange, pair)
        if key not in self._pair_scan_state:
            self._pair_scan_state[key] = PairScanState()
        return self._pair_scan_state[key]

    def _classify_temperature(self, preliminary_score: float | None = None, opportunity: Opportunity | None = None) -> str:
        if opportunity is not None:
            if opportunity.opportunity_type in {"trade", "hold"} or opportunity.operable_signal:
                return "hot"
            if opportunity.interesting_signal or opportunity.score >= 40:
                return "warm"
            return "cold"
        if preliminary_score is None:
            return "cold"
        if preliminary_score >= 70:
            return "hot"
        if preliminary_score >= 35:
            return "warm"
        return "cold"

    def _reset_scan_diagnostics(self, scannable_pairs: dict[Exchange, list[str]]) -> None:
        self._scan_diagnostics = {
            "total_pairs": sum(len(pairs) for pairs in scannable_pairs.values()),
            "light_requests": 0,
            "light_candidates": 0,
            "light_discards": 0,
            "light_discard_reasons": {},
            "skipped_pairs": 0,
            "skip_reasons": {},
            "deep_candidates": 0,
            "deep_completed": 0,
            "deep_discards": 0,
            "deep_discard_reasons": {},
            "opportunities": 0,
            "temperatures": {"hot": 0, "warm": 0, "cold": 0},
        }

    def _increment_scan_counter(self, section: str, key: str | None = None, amount: int = 1) -> None:
        if not self._scan_diagnostics:
            return
        if key is None:
            self._scan_diagnostics[section] = self._scan_diagnostics.get(section, 0) + amount
            return
        bucket = self._scan_diagnostics.setdefault(section, {})
        bucket[key] = bucket.get(key, 0) + amount

    def _refresh_temperature_diagnostics(self) -> None:
        if not self._scan_diagnostics:
            return
        counts = {"hot": 0, "warm": 0, "cold": 0}
        for state in self._pair_scan_state.values():
            counts[state.temperature] = counts.get(state.temperature, 0) + 1
        self._scan_diagnostics["temperatures"] = counts

    def _should_run_light_scan(self, exchange: Exchange, pair: str, now: datetime) -> tuple[bool, str | None]:
        state = self._get_pair_state(exchange, pair)
        if state.cooldown_until and now < state.cooldown_until:
            logger.debug(
                "light_scan_skipped_cooldown exchange=%s pair=%s until=%s",
                exchange.value,
                pair,
                state.cooldown_until.isoformat(),
            )
            return False, "cooldown"

        if state.last_light_scan_at is None:
            return True, None

        interval_seconds = PAIR_TEMPERATURE_INTERVAL_SECONDS.get(state.temperature, 60)
        if interval_seconds <= 0:
            return True, None

        should_run = (now - state.last_light_scan_at).total_seconds() >= interval_seconds
        return should_run, None if should_run else f"temperature_{state.temperature}"

    def _record_light_scan_success(
        self,
        exchange: Exchange,
        pair: str,
        now: datetime,
        *,
        preliminary_score: float | None = None,
        discard_reason: str | None = None,
    ) -> None:
        state = self._get_pair_state(exchange, pair)
        state.last_light_scan_at = now
        state.failure_count = 0
        state.cooldown_until = None
        state.last_discard_reason = discard_reason
        if discard_reason:
            state.temperature = "cold" if discard_reason in {"volume_below_threshold", "movement_below_light_threshold"} else "warm"
        else:
            state.temperature = self._classify_temperature(preliminary_score=preliminary_score)

    def _record_deep_scan_success(self, exchange: Exchange, pair: str, now: datetime, opportunity: Opportunity | None) -> None:
        state = self._get_pair_state(exchange, pair)
        state.last_deep_scan_at = now
        state.failure_count = 0
        state.cooldown_until = None
        state.temperature = self._classify_temperature(opportunity=opportunity)
        state.last_discard_reason = None if opportunity else "deep_filters_rejected"

    def _record_provider_pair_failure(self, exchange: Exchange, pair: str, reason: str, now: datetime) -> None:
        state = self._get_pair_state(exchange, pair)
        state.failure_count += 1
        cooldown_seconds = min(60 * (2 ** max(state.failure_count - 1, 0)), MAX_PROVIDER_PAIR_COOLDOWN_SECONDS)
        state.cooldown_until = now + timedelta(seconds=cooldown_seconds)
        state.temperature = "cold"
        state.last_discard_reason = reason
        logger.warning(
            "provider_pair_cooldown exchange=%s pair=%s reason=%s failures=%s cooldown_seconds=%s",
            exchange.value,
            pair,
            reason,
            state.failure_count,
            cooldown_seconds,
        )

    def _passes_light_triage(self, ticker: Ticker) -> tuple[bool, str]:
        if ticker.last_price <= 0:
            return False, "invalid_price"

        if not passes_volume_filter(
            ticker,
            self.config.thresholds.min_volume_brl,
            self.config.thresholds.min_volume_brl_small,
        ):
            return False, "volume_below_threshold"

        if self._preliminary_movement_pct(ticker) < self._light_triage_min_movement_pct():
            return False, "movement_below_light_threshold"

        return True, "candidate"

    async def _scan_light_candidate(self, provider: ExchangeProvider, pair: str) -> LightScanCandidate | None:
        now = datetime.now(timezone.utc)
        self._increment_scan_counter("light_requests")
        try:
            ticker = await provider.get_light_ticker(pair)
        except Exception as exc:
            self._record_provider_pair_failure(provider.exchange, pair, "ticker_failed", now)
            self._increment_scan_counter("light_discards")
            self._increment_scan_counter("light_discard_reasons", "ticker_failed")
            logger.debug(
                "light_scan_ticker_failed exchange=%s pair=%s error=%s",
                provider.exchange.value,
                pair,
                exc,
            )
            return None

        passed, reason = self._passes_light_triage(ticker)
        preliminary_score = self._light_triage_score(ticker)
        if not passed:
            self._increment_scan_counter("light_discards")
            self._increment_scan_counter("light_discard_reasons", reason)
            self._record_light_scan_success(
                provider.exchange,
                pair,
                now,
                preliminary_score=preliminary_score,
                discard_reason=reason,
            )
            logger.debug(
                "light_scan_discarded exchange=%s pair=%s reason=%s quote_volume_24h=%.2f movement_pct=%.4f",
                provider.exchange.value,
                pair,
                reason,
                ticker.quote_volume_24h,
                self._preliminary_movement_pct(ticker),
            )
            return None

        self._record_light_scan_success(
            provider.exchange,
            pair,
            now,
            preliminary_score=preliminary_score,
        )
        self._increment_scan_counter("light_candidates")
        return LightScanCandidate(
            provider=provider,
            pair=pair,
            ticker=ticker,
            preliminary_score=preliminary_score,
            reason=reason,
        )

    async def _get_scannable_pairs_by_exchange(self) -> dict[Exchange, list[str]]:
        enabled_exchanges = list(self._providers.keys())
        try:
            return await get_scannable_pairs_by_exchange(
                enabled_pairs=self.config.enabled_pairs,
                enabled_exchanges=enabled_exchanges,
            )
        except Exception as exc:
            logger.warning("scan_pair_catalog_filter_failed error=%s", exc)
            return {
                exchange: list(self.config.enabled_pairs)
                for exchange in enabled_exchanges
            }

    async def scan_pair(
        self,
        provider: ExchangeProvider,
        pair: str,
        *,
        ticker: Ticker | None = None,
    ) -> Opportunity | None:
        """Scan a single pair on a single exchange and return an opportunity if filters pass."""
        now = datetime.now(timezone.utc)
        try:
            if ticker is None:
                ticker = await provider.get_light_ticker(pair)
                passed, reason = self._passes_light_triage(ticker)
                if not passed:
                    logger.debug(
                        "scan_pair_light_triage_discarded exchange=%s pair=%s reason=%s",
                        provider.exchange.value,
                        pair,
                        reason,
                    )
                    return None
                self._record_light_scan_success(
                    provider.exchange,
                    pair,
                    now,
                    preliminary_score=self._light_triage_score(ticker),
                )

            order_book, klines = await asyncio.gather(
                provider.get_order_book(pair),
                provider.get_klines(pair, interval="5m", limit=50),
                return_exceptions=True,
            )

            # Skip if any request failed
            if isinstance(order_book, Exception):
                self._record_provider_pair_failure(provider.exchange, pair, "order_book_failed", now)
                self._increment_scan_counter("deep_discards")
                self._increment_scan_counter("deep_discard_reasons", "order_book_failed")
                logger.debug(f"[{provider.exchange}] OrderBook failed for {pair}: {order_book}")
                return None
            if isinstance(klines, Exception):
                self._record_provider_pair_failure(provider.exchange, pair, "klines_failed", now)
                self._increment_scan_counter("deep_discards")
                self._increment_scan_counter("deep_discard_reasons", "klines_failed")
                logger.debug(f"[{provider.exchange}] Klines failed for {pair}: {klines}")
                return None

            thresholds = self.config.thresholds
            trading_profile = resolve_trading_profile(self.config)

            # Apply filters
            if not passes_volatility_filter(klines, thresholds.min_volatility_pct):
                self._increment_scan_counter("deep_discards")
                self._increment_scan_counter("deep_discard_reasons", "volatility_filter")
                self._record_deep_scan_success(provider.exchange, pair, now, None)
                return None

            if not passes_volume_filter(ticker, thresholds.min_volume_brl, thresholds.min_volume_brl_small):
                self._increment_scan_counter("deep_discards")
                self._increment_scan_counter("deep_discard_reasons", "volume_filter")
                self._record_deep_scan_success(provider.exchange, pair, now, None)
                return None

            if not passes_liquidity_filter(order_book, thresholds.min_liquidity_units):
                self._increment_scan_counter("deep_discards")
                self._increment_scan_counter("deep_discard_reasons", "liquidity_filter")
                self._record_deep_scan_success(provider.exchange, pair, now, None)
                return None

            if not passes_spread_filter(order_book, thresholds.max_spread_pct):
                self._increment_scan_counter("deep_discards")
                self._increment_scan_counter("deep_discard_reasons", "spread_filter")
                self._record_deep_scan_success(provider.exchange, pair, now, None)
                return None

            # Classify movement
            movement_type = classify_movement(klines)
            spread_pct = round(calculate_spread(order_book), 4)
            movement_regime = classify_movement_regime(
                klines,
                spread_pct=spread_pct,
                quote_volume_24h=ticker.quote_volume_24h,
            )

            # Track repetition
            key = f"{provider.exchange}:{pair}"
            self._repetition_counts[key] = self._repetition_counts.get(key, 0) + 1
            duration_minutes = round((self._repetition_counts[key] * self.config.scan_interval_seconds) / 60, 2)
            persistence_baseline = min(duration_minutes / 20.0, 1.0)
            movement_persistence_score = round(
                min(
                    1.0,
                    persistence_baseline
                    * (1.1 if movement_type.value in {"strong_range", "spike"} else 0.95),
                ),
                4,
            )
            semantic_signal_key = self._build_semantic_signal_key(
                exchange=provider.exchange,
                pair=pair,
                movement_type=movement_type.value,
                movement_regime=movement_regime.value,
            )

            # Calculate score
            volatility_pct = calculate_volatility(klines)
            volatility_component = min(volatility_pct / 10.0, 1.0)
            volume_component = volume_score(ticker)
            liquidity_component = liquidity_score(order_book)
            spread_component = spread_score(order_book)
            repetition_component = min(self._repetition_counts[key] / 5.0, 1.0)
            movement_multiplier = MOVEMENT_MODIFIERS.get(movement_type.value, 1.0)
            bid_notional_top_n = calculate_notional_depth(order_book, "bid")
            ask_notional_top_n = calculate_notional_depth(order_book, "ask")
            total_notional_top_n = calculate_total_notional_depth(order_book)
            estimated_buy_slippage_bps = estimate_slippage_bps(
                order_book,
                "buy",
                order_notional_brl=trading_profile.order_notional_brl,
            )
            estimated_sell_slippage_bps = estimate_slippage_bps(
                order_book,
                "sell",
                order_notional_brl=trading_profile.order_notional_brl,
            )
            fillable_notional_within_slippage_cap = min(
                estimate_fillable_notional(order_book, trading_profile.max_entry_slippage_bps, "buy"),
                estimate_fillable_notional(order_book, trading_profile.max_exit_slippage_bps, "sell"),
            )
            serialized_buy_slippage = (
                None if estimated_buy_slippage_bps == float("inf") else round(estimated_buy_slippage_bps, 2)
            )
            serialized_sell_slippage = (
                None if estimated_sell_slippage_bps == float("inf") else round(estimated_sell_slippage_bps, 2)
            )
            serialized_fillable_notional = round(fillable_notional_within_slippage_cap, 2)
            executability_score = calculate_executability_score(
                bid_notional_top_n=bid_notional_top_n,
                ask_notional_top_n=ask_notional_top_n,
                estimated_buy_slippage_bps=serialized_buy_slippage,
                estimated_sell_slippage_bps=serialized_sell_slippage,
                spread_pct=spread_pct,
                quote_volume_24h=ticker.quote_volume_24h,
                fillable_notional_within_slippage_cap=serialized_fillable_notional,
                order_notional_brl=trading_profile.order_notional_brl,
            )
            executability_band = classify_executability_band(executability_score)

            score = calculate_score(
                ticker=ticker,
                order_book=order_book,
                klines=klines,
                movement_type=movement_type,
                weights=self.config.weights,
                repetition_count=self._repetition_counts[key],
            )
            historical_confidence = self._historical_calibration.get(pair, {}).get("factor", 1.0)
            score = min(max(round(score * historical_confidence, 1), 0), 100)
            interesting_signal = score >= 40
            operable_signal = (
                executability_score >= DEFAULT_OPERABLE_EXECUTABILITY_SCORE
                and ticker.quote_volume_24h >= trading_profile.min_quote_volume_brl
                and serialized_sell_slippage is not None
                and serialized_sell_slippage <= trading_profile.max_exit_slippage_bps
                and serialized_buy_slippage is not None
                and serialized_buy_slippage <= trading_profile.max_entry_slippage_bps
                and spread_pct <= self.config.thresholds.max_spread_pct
                and movement_persistence_score >= 0.02
            )
            recent_change_pct = round(calculate_recent_change(klines), 2)
            trade_margin_metrics = calculate_trade_margin_metrics(
                volatility_pct=volatility_pct,
                recent_change_pct=recent_change_pct,
                spread_pct=spread_pct,
                estimated_buy_slippage_bps=serialized_buy_slippage,
                estimated_sell_slippage_bps=serialized_sell_slippage,
                movement_type=movement_type.value,
                movement_regime=movement_regime.value,
                movement_persistence_score=movement_persistence_score,
            )
            opportunity_type = classify_opportunity_type(
                operable_signal=operable_signal,
                interesting_signal=interesting_signal,
                executability_score=executability_score,
                trade_margin_score=trade_margin_metrics["trade_margin_score"],
                estimated_net_trade_edge_pct=trade_margin_metrics["estimated_net_trade_edge_pct"],
                movement_regime=movement_regime.value,
            )

            technical_score = calculate_technical_score(
                volatility_score=volatility_component,
                volume_score=volume_component,
                liquidity_score=liquidity_component,
                spread_score=spread_component,
                repetition_score=repetition_component,
                movement_multiplier=movement_multiplier,
                historical_confidence=historical_confidence,
            )

            opportunity = Opportunity(
                id=str(uuid.uuid4()),
                exchange=provider.exchange,
                pair=pair,
                score=score,
                technical_score=technical_score,
                score_version=SCORE_VERSION,
                executability_version=EXECUTABILITY_VERSION,
                movement_version=MOVEMENT_VERSION,
                profile_version=PROFILE_VERSION,
                executability_score=executability_score,
                executability_band=executability_band,
                interesting_signal=interesting_signal,
                operable_signal=operable_signal,
                estimated_trade_margin_pct=trade_margin_metrics["estimated_trade_margin_pct"],
                operational_friction_pct=trade_margin_metrics["operational_friction_pct"],
                estimated_net_trade_edge_pct=trade_margin_metrics["estimated_net_trade_edge_pct"],
                trade_margin_score=trade_margin_metrics["trade_margin_score"],
                opportunity_type=opportunity_type,
                semantic_signal_key=semantic_signal_key,
                reweighting_version="v1",
                volatility_pct=round(volatility_pct, 2),
                volume_24h=ticker.volume_24h,
                quote_volume_24h=ticker.quote_volume_24h,
                liquidity_units=round(calculate_liquidity(order_book), 2),
                bid_notional_top_n=round(bid_notional_top_n, 2),
                ask_notional_top_n=round(ask_notional_top_n, 2),
                total_notional_top_n=round(total_notional_top_n, 2),
                spread_pct=spread_pct,
                estimated_buy_slippage_bps=serialized_buy_slippage,
                estimated_sell_slippage_bps=serialized_sell_slippage,
                fillable_notional_within_slippage_cap=serialized_fillable_notional,
                baseline_order_notional_brl=trading_profile.order_notional_brl,
                movement_type=movement_type,
                movement_regime=movement_regime,
                movement_persistence_score=movement_persistence_score,
                last_price=ticker.last_price,
                change_pct=recent_change_pct,
                detected_at=datetime.now(timezone.utc),
                duration_minutes=duration_minutes,
                historical_confidence=historical_confidence,
                volatility_score=round(volatility_component, 4),
                volume_score=round(volume_component, 4),
                liquidity_score=round(liquidity_component, 4),
                spread_score=round(spread_component, 4),
                repetition_score=round(repetition_component, 4),
                movement_multiplier=movement_multiplier,
                klines=klines[-20:],
            )
            self._record_deep_scan_success(provider.exchange, pair, now, opportunity)
            self._increment_scan_counter("deep_completed")
            return opportunity

        except Exception as e:
            self._record_provider_pair_failure(provider.exchange, pair, "scan_pair_exception", now)
            self._increment_scan_counter("deep_discards")
            self._increment_scan_counter("deep_discard_reasons", "scan_pair_exception")
            logger.error(f"[{provider.exchange}] Error scanning {pair}: {e}")
            return None

    async def scan_all(self) -> list[Opportunity]:
        """Run a full scan across all enabled exchanges and pairs."""
        scannable_pairs = await self._get_scannable_pairs_by_exchange()
        self._reset_scan_diagnostics(scannable_pairs)

        light_scan_tasks = []
        now = datetime.now(timezone.utc)
        for exchange, provider in self._providers.items():
            for pair in scannable_pairs.get(exchange, []):
                should_run, skip_reason = self._should_run_light_scan(exchange, pair, now)
                if not should_run:
                    self._increment_scan_counter("skipped_pairs")
                    self._increment_scan_counter("skip_reasons", skip_reason or "unknown")
                    continue
                light_scan_tasks.append(self._scan_light_candidate(provider, pair))

        light_results = await asyncio.gather(*light_scan_tasks, return_exceptions=True)
        candidates_by_exchange: dict[Exchange, list[LightScanCandidate]] = {}
        for result in light_results:
            if isinstance(result, LightScanCandidate):
                candidates_by_exchange.setdefault(result.provider.exchange, []).append(result)
            elif isinstance(result, Exception):
                logger.error(f"Light scan task error: {result}")

        deep_candidates: list[LightScanCandidate] = []
        for exchange, candidates in candidates_by_exchange.items():
            selected = sorted(candidates, key=lambda candidate: candidate.preliminary_score, reverse=True)[
                :DEFAULT_STAGE2_CANDIDATES_PER_EXCHANGE
            ]
            deep_candidates.extend(selected)
            logger.info(
                "light_scan_selected exchange=%s candidates=%s selected=%s",
                exchange.value,
                len(candidates),
                len(selected),
            )

        self._scan_diagnostics["deep_candidates"] = len(deep_candidates)
        tasks = [
            self.scan_pair(candidate.provider, candidate.pair, ticker=candidate.ticker)
            for candidate in deep_candidates
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        new_opportunities = []
        for result in results:
            if isinstance(result, Opportunity):
                new_opportunities.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Scan task error: {result}")

        self._opportunities = self._enrich_cross_exchange_context(new_opportunities)
        self._scan_diagnostics["opportunities"] = len(new_opportunities)
        self._refresh_temperature_diagnostics()
        logger.info(
            "scan_complete opportunities=%s diagnostics=%s",
            len(new_opportunities),
            self._scan_diagnostics,
        )
        return self._opportunities

    def _enrich_cross_exchange_context(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        opportunities_by_pair: dict[str, list[Opportunity]] = {}
        for opportunity in opportunities:
            opportunities_by_pair.setdefault(opportunity.pair, []).append(opportunity)

        for pair_opportunities in opportunities_by_pair.values():
            if len(pair_opportunities) < 2:
                continue

            cheapest = min(pair_opportunities, key=lambda opp: opp.last_price)
            priciest = max(pair_opportunities, key=lambda opp: opp.last_price)
            avg_price = (cheapest.last_price + priciest.last_price) / 2
            if avg_price <= 0:
                continue

            gap_pct = abs(priciest.last_price - cheapest.last_price) / avg_price * 100
            estimated_friction = cheapest.spread_pct + priciest.spread_pct + 0.2
            arbitrage = gap_pct > estimated_friction

            for opportunity in pair_opportunities:
                reference = priciest if opportunity.exchange != priciest.exchange else cheapest
                opportunity.cross_exchange_gap_pct = round(gap_pct, 4)
                opportunity.cross_exchange_reference_exchange = reference.exchange
                opportunity.cross_exchange_reference_price = reference.last_price
                opportunity.arbitrage_available = arbitrage

                if arbitrage:
                    boosted = opportunity.score * 1.05
                    opportunity.score = min(round(boosted, 1), 100)

        return opportunities

    async def close(self) -> None:
        for provider in self._providers.values():
            await provider.close()
