"""Tests for the outcome evaluator service."""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.outcome_evaluator import evaluate_pending_outcomes, _window_ready


class TestWindowReady:
    def test_5m_not_ready(self):
        now = datetime.now(timezone.utc)
        detected = now - timedelta(minutes=3)
        assert _window_ready(detected, timedelta(minutes=5), now) is False

    def test_5m_ready(self):
        now = datetime.now(timezone.utc)
        detected = now - timedelta(minutes=6)
        assert _window_ready(detected, timedelta(minutes=5), now) is True

    def test_1h_ready(self):
        now = datetime.now(timezone.utc)
        detected = now - timedelta(hours=1, minutes=1)
        assert _window_ready(detected, timedelta(hours=1), now) is True

    def test_4h_not_ready(self):
        now = datetime.now(timezone.utc)
        detected = now - timedelta(hours=3)
        assert _window_ready(detected, timedelta(hours=4), now) is False


class TestEvaluatePendingOutcomes:
    def test_no_pending_returns_zero(self):
        async def run_test():
            with patch(
                "app.services.outcome_evaluator.get_pending_outcomes",
                new_callable=AsyncMock,
                return_value=[],
            ):
                result = await evaluate_pending_outcomes()
                assert result == 0

        asyncio.run(run_test())

    def test_evaluates_5m_window(self):
        async def run_test():
            now = datetime.now(timezone.utc)
            detected = now - timedelta(minutes=10)

            pending = [
                {
                    "id": "outcome-1",
                    "technical_signal_id": "sig-1",
                    "exchange": "binance",
                    "pair": "BTC_BRL",
                    "entry_price": 100000.0,
                    "signal_detected_at": detected,
                }
            ]

            mock_ticker = MagicMock()
            mock_ticker.last_price = 101000.0

            mock_provider = AsyncMock()
            mock_provider.get_ticker = AsyncMock(return_value=mock_ticker)
            mock_provider.close = AsyncMock()

            mock_provider_cls = MagicMock(return_value=mock_provider)

            with (
                patch(
                    "app.services.outcome_evaluator.get_pending_outcomes",
                    new_callable=AsyncMock,
                    return_value=pending,
                ),
                patch(
                    "app.services.outcome_evaluator.update_outcome",
                    new_callable=AsyncMock,
                ) as mock_update,
                patch.dict(
                    "app.services.outcome_evaluator._PROVIDER_MAP",
                    {"binance": mock_provider_cls},
                ),
            ):
                result = await evaluate_pending_outcomes()
                assert result == 1
                mock_update.assert_called_once()
                call_kwargs = mock_update.call_args
                assert call_kwargs[0][0] == "outcome-1"
                assert call_kwargs[1]["price_after_5m"] == 101000.0

        asyncio.run(run_test())

    def test_skips_when_ticker_fails(self):
        async def run_test():
            now = datetime.now(timezone.utc)
            detected = now - timedelta(minutes=10)

            pending = [
                {
                    "id": "outcome-1",
                    "technical_signal_id": "sig-1",
                    "exchange": "binance",
                    "pair": "UNKNOWN_PAIR",
                    "entry_price": 100.0,
                    "signal_detected_at": detected,
                }
            ]

            mock_provider = AsyncMock()
            mock_provider.get_ticker = AsyncMock(side_effect=Exception("ticker failed"))
            mock_provider.close = AsyncMock()

            mock_provider_cls = MagicMock(return_value=mock_provider)

            with (
                patch(
                    "app.services.outcome_evaluator.get_pending_outcomes",
                    new_callable=AsyncMock,
                    return_value=pending,
                ),
                patch(
                    "app.services.outcome_evaluator.update_outcome",
                    new_callable=AsyncMock,
                ) as mock_update,
                patch.dict(
                    "app.services.outcome_evaluator._PROVIDER_MAP",
                    {"binance": mock_provider_cls},
                ),
            ):
                result = await evaluate_pending_outcomes()
                assert result == 0
                mock_update.assert_not_called()

        asyncio.run(run_test())

    def test_evaluates_multiple_windows(self):
        async def run_test():
            now = datetime.now(timezone.utc)
            detected = now - timedelta(hours=2)

            pending = [
                {
                    "id": "outcome-2",
                    "technical_signal_id": "sig-2",
                    "exchange": "novadax",
                    "pair": "ETH_BRL",
                    "entry_price": 5000.0,
                    "signal_detected_at": detected,
                }
            ]

            mock_ticker = MagicMock()
            mock_ticker.last_price = 5100.0

            mock_provider = AsyncMock()
            mock_provider.get_ticker = AsyncMock(return_value=mock_ticker)
            mock_provider.close = AsyncMock()

            mock_provider_cls = MagicMock(return_value=mock_provider)

            with (
                patch(
                    "app.services.outcome_evaluator.get_pending_outcomes",
                    new_callable=AsyncMock,
                    return_value=pending,
                ),
                patch(
                    "app.services.outcome_evaluator.update_outcome",
                    new_callable=AsyncMock,
                ) as mock_update,
                patch.dict(
                    "app.services.outcome_evaluator._PROVIDER_MAP",
                    {"novadax": mock_provider_cls},
                ),
            ):
                result = await evaluate_pending_outcomes()
                assert result == 1
                call_kwargs = mock_update.call_args[1]
                assert call_kwargs["price_after_5m"] == 5100.0
                assert call_kwargs["price_after_15m"] == 5100.0
                assert call_kwargs["price_after_1h"] == 5100.0
                assert "price_after_4h" not in call_kwargs  # 2h < 4h window

        asyncio.run(run_test())
