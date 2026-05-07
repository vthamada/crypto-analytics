"""Add movement phase fields.

Revision ID: 0010_movement_phase_fields
Revises: 0009_scanner_runtime_diagnostics
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0010_movement_phase_fields"
down_revision = "0009_scanner_runtime_diagnostics"
branch_labels = None
depends_on = None


PHASE_COLUMNS = (
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
)


TABLES = ("opportunities", "opportunity_snapshots", "technical_signals")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    for table_name in TABLES:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, column in PHASE_COLUMNS:
            if column_name not in columns:
                op.add_column(table_name, column.copy())


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    for table_name in TABLES:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, _column in reversed(PHASE_COLUMNS):
            if column_name in columns:
                op.drop_column(table_name, column_name)
