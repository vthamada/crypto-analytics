"""Add scanner cycle and signal pipeline audit tables.

Revision ID: 0012_signal_pipeline_audit
Revises: 0011_operational_range_outcomes_feedback
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0012_signal_pipeline_audit"
down_revision = "0011_operational_range_outcomes_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "scanner_cycle_audits" not in tables:
        op.create_table(
            "scanner_cycle_audits",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("cycle_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("duration_ms", sa.Float(), nullable=True),
            sa.Column("total_pairs", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("brl_pairs", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("light_candidates", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("deep_candidates", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("deep_completed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("signals_created", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("shortlist_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("alerts_created", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("alerts_sent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("provider_errors", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("discard_reasons", sa.Text(), nullable=True),
            sa.Column("block_reasons", sa.Text(), nullable=True),
            sa.Column("diagnostics", sa.Text(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("cycle_id"),
        )
        op.create_index("ix_scanner_cycle_audits_cycle_id", "scanner_cycle_audits", ["cycle_id"])
        op.create_index("ix_scanner_cycle_audits_status", "scanner_cycle_audits", ["status"])
        op.create_index("ix_scanner_cycle_audits_started_at", "scanner_cycle_audits", ["started_at"])
        op.create_index("ix_scanner_cycle_audits_completed_at", "scanner_cycle_audits", ["completed_at"])
        op.create_index("ix_scanner_cycle_audits_created_at", "scanner_cycle_audits", ["created_at"])

    if "signal_pipeline_events" not in tables:
        op.create_table(
            "signal_pipeline_events",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("cycle_id", sa.String(), nullable=False),
            sa.Column("exchange", sa.String(), nullable=True),
            sa.Column("pair", sa.String(), nullable=True),
            sa.Column("stage", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("reason", sa.String(), nullable=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("workspace_id", sa.String(), nullable=True),
            sa.Column("technical_signal_id", sa.String(), nullable=True),
            sa.Column("opportunity_id", sa.String(), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_signal_pipeline_events_cycle_id", "signal_pipeline_events", ["cycle_id"])
        op.create_index("ix_signal_pipeline_events_exchange", "signal_pipeline_events", ["exchange"])
        op.create_index("ix_signal_pipeline_events_pair", "signal_pipeline_events", ["pair"])
        op.create_index("ix_signal_pipeline_events_stage", "signal_pipeline_events", ["stage"])
        op.create_index("ix_signal_pipeline_events_status", "signal_pipeline_events", ["status"])
        op.create_index("ix_signal_pipeline_events_reason", "signal_pipeline_events", ["reason"])
        op.create_index("ix_signal_pipeline_events_workspace_id", "signal_pipeline_events", ["workspace_id"])
        op.create_index("ix_signal_pipeline_events_technical_signal_id", "signal_pipeline_events", ["technical_signal_id"])
        op.create_index("ix_signal_pipeline_events_opportunity_id", "signal_pipeline_events", ["opportunity_id"])
        op.create_index("ix_signal_pipeline_events_created_at", "signal_pipeline_events", ["created_at"])
        op.create_index(
            "ix_signal_pipeline_events_pair_lookup",
            "signal_pipeline_events",
            ["exchange", "pair", "created_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "signal_pipeline_events" in tables:
        op.drop_table("signal_pipeline_events")
    if "scanner_cycle_audits" in tables:
        op.drop_table("scanner_cycle_audits")
