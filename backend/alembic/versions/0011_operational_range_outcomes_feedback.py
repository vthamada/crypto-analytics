"""Add operational range, enriched outcomes, and signal feedback.

Revision ID: 0011_operational_range_outcomes_feedback
Revises: 0010_movement_phase_fields
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0011_operational_range_outcomes_feedback"
down_revision = "0010_movement_phase_fields"
branch_labels = None
depends_on = None


OPERATIONAL_COLUMNS = (
    ("operational_buy_zone_low", sa.Column("operational_buy_zone_low", sa.Float(), nullable=True)),
    ("operational_buy_zone_high", sa.Column("operational_buy_zone_high", sa.Float(), nullable=True)),
    ("operational_sell_zone_low", sa.Column("operational_sell_zone_low", sa.Float(), nullable=True)),
    ("operational_sell_zone_high", sa.Column("operational_sell_zone_high", sa.Float(), nullable=True)),
    ("operational_range_margin_pct", sa.Column("operational_range_margin_pct", sa.Float(), nullable=True)),
    ("range_reuse_count", sa.Column("range_reuse_count", sa.Integer(), nullable=True)),
    ("range_reliability_score", sa.Column("range_reliability_score", sa.Float(), nullable=True)),
    ("zone_liquidity_score", sa.Column("zone_liquidity_score", sa.Float(), nullable=True)),
    ("capital_capacity_estimate_brl", sa.Column("capital_capacity_estimate_brl", sa.Float(), nullable=True)),
    ("operational_range_quality", sa.Column("operational_range_quality", sa.String(), nullable=True)),
    ("alert_moment_type", sa.Column("alert_moment_type", sa.String(), nullable=True)),
    ("alert_reason", sa.Column("alert_reason", sa.String(), nullable=True)),
)

TECHNICAL_SIGNAL_COLUMNS = (
    ("operational_range_margin_pct", sa.Column("operational_range_margin_pct", sa.Float(), nullable=True)),
    ("operational_range_quality", sa.Column("operational_range_quality", sa.String(), nullable=True)),
    ("alert_moment_type", sa.Column("alert_moment_type", sa.String(), nullable=True)),
    ("alert_reason", sa.Column("alert_reason", sa.String(), nullable=True)),
)

RAW_OBSERVATION_COLUMNS = (
    ("movement_phase", sa.Column("movement_phase", sa.String(), nullable=True)),
    ("phase_confidence_score", sa.Column("phase_confidence_score", sa.Float(), nullable=True)),
    ("phase_reason", sa.Column("phase_reason", sa.String(), nullable=True)),
    ("is_late_entry_risk", sa.Column("is_late_entry_risk", sa.Boolean(), nullable=True)),
    ("is_profit_zone_candidate", sa.Column("is_profit_zone_candidate", sa.Boolean(), nullable=True)),
    (
        "distance_from_accumulation_zone_pct",
        sa.Column("distance_from_accumulation_zone_pct", sa.Float(), nullable=True),
    ),
    ("distance_from_breakout_pct", sa.Column("distance_from_breakout_pct", sa.Float(), nullable=True)),
    ("operational_range_margin_pct", sa.Column("operational_range_margin_pct", sa.Float(), nullable=True)),
    ("operational_range_quality", sa.Column("operational_range_quality", sa.String(), nullable=True)),
    ("alert_moment_type", sa.Column("alert_moment_type", sa.String(), nullable=True)),
    ("alert_reason", sa.Column("alert_reason", sa.String(), nullable=True)),
)

OUTCOME_COLUMNS = (
    ("price_after_24h", sa.Column("price_after_24h", sa.Float(), nullable=True)),
    ("max_price_after_signal", sa.Column("max_price_after_signal", sa.Float(), nullable=True)),
    ("min_price_after_signal", sa.Column("min_price_after_signal", sa.Float(), nullable=True)),
    ("outcome_pct_24h", sa.Column("outcome_pct_24h", sa.Float(), nullable=True)),
    ("max_favorable_excursion_pct", sa.Column("max_favorable_excursion_pct", sa.Float(), nullable=True)),
    ("max_adverse_excursion_pct", sa.Column("max_adverse_excursion_pct", sa.Float(), nullable=True)),
    ("volume_after_signal", sa.Column("volume_after_signal", sa.Float(), nullable=True)),
    ("movement_continued", sa.Column("movement_continued", sa.Boolean(), nullable=True)),
    ("breakout_confirmed", sa.Column("breakout_confirmed", sa.Boolean(), nullable=True)),
    ("late_signal_detected", sa.Column("late_signal_detected", sa.Boolean(), nullable=True)),
    ("outcome_label", sa.Column("outcome_label", sa.String(), nullable=True)),
)


def _add_missing_columns(table_name: str, columns: tuple[tuple[str, sa.Column], ...]) -> None:
    inspector = inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, column in columns:
        if column_name not in existing_columns:
            op.add_column(table_name, column.copy())


def _drop_existing_columns(table_name: str, columns: tuple[tuple[str, sa.Column], ...]) -> None:
    inspector = inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, _column in reversed(columns):
        if column_name in existing_columns:
            op.drop_column(table_name, column_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    for table_name in ("opportunities", "opportunity_snapshots"):
        if table_name in tables:
            _add_missing_columns(table_name, OPERATIONAL_COLUMNS)

    if "technical_signals" in tables:
        _add_missing_columns("technical_signals", TECHNICAL_SIGNAL_COLUMNS)

    if "raw_market_observations" in tables:
        _add_missing_columns("raw_market_observations", RAW_OBSERVATION_COLUMNS)

    if "signal_outcomes" in tables:
        _add_missing_columns("signal_outcomes", OUTCOME_COLUMNS)

    if "signal_feedback" not in tables:
        op.create_table(
            "signal_feedback",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("signal_id", sa.String(), nullable=True),
            sa.Column("opportunity_id", sa.String(), nullable=True),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("workspace_id", sa.String(), nullable=True),
            sa.Column("feedback_label", sa.String(), nullable=False),
            sa.Column("feedback_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_signal_feedback_signal_id", "signal_feedback", ["signal_id"])
        op.create_index("ix_signal_feedback_opportunity_id", "signal_feedback", ["opportunity_id"])
        op.create_index("ix_signal_feedback_user_id", "signal_feedback", ["user_id"])
        op.create_index("ix_signal_feedback_workspace_id", "signal_feedback", ["workspace_id"])
        op.create_index("ix_signal_feedback_feedback_label", "signal_feedback", ["feedback_label"])
        op.create_index("ix_signal_feedback_created_at", "signal_feedback", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "signal_feedback" in tables:
        op.drop_table("signal_feedback")

    if "signal_outcomes" in tables:
        _drop_existing_columns("signal_outcomes", OUTCOME_COLUMNS)
    if "raw_market_observations" in tables:
        _drop_existing_columns("raw_market_observations", RAW_OBSERVATION_COLUMNS)
    if "technical_signals" in tables:
        _drop_existing_columns("technical_signals", TECHNICAL_SIGNAL_COLUMNS)
    for table_name in ("opportunities", "opportunity_snapshots"):
        if table_name in tables:
            _drop_existing_columns(table_name, OPERATIONAL_COLUMNS)
