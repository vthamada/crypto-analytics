"""Persist alert worthiness and alert state.

Revision ID: 0015_alert_worthiness_state
Revises: 0014_revoke_public_execute
Create Date: 2026-05-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0015_alert_worthiness_state"
down_revision = "0014_revoke_public_execute"
branch_labels = None
depends_on = None


TABLE_COLUMNS = {
    "opportunities": (
        ("alert_worthiness_score", sa.Float(), {}),
        ("alert_trigger_type", sa.String(), {}),
        ("has_actionable_trigger", sa.Boolean(), {"server_default": "false"}),
        ("alert_state_key", sa.String(), {}),
        ("alert_block_reason", sa.String(), {}),
    ),
    "opportunity_snapshots": (
        ("alert_worthiness_score", sa.Float(), {}),
        ("alert_trigger_type", sa.String(), {}),
        ("has_actionable_trigger", sa.Boolean(), {"server_default": "false"}),
        ("alert_state_key", sa.String(), {}),
        ("alert_block_reason", sa.String(), {}),
    ),
    "workspace_signal_projections": (
        ("alert_worthiness_score", sa.Float(), {}),
        ("alert_trigger_type", sa.String(), {}),
        ("has_actionable_trigger", sa.Boolean(), {"server_default": "false"}),
        ("alert_state_key", sa.String(), {}),
        ("alert_block_reason", sa.String(), {}),
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for table_name, columns in TABLE_COLUMNS.items():
        if table_name not in tables:
            continue
        existing_columns = {
            column["name"]
            for column in inspect(bind).get_columns(table_name)
        }
        for column_name, column_type, kwargs in columns:
            if column_name in existing_columns:
                continue
            op.add_column(table_name, sa.Column(column_name, column_type, nullable=True, **kwargs))


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for table_name, columns in TABLE_COLUMNS.items():
        if table_name not in tables:
            continue
        existing_columns = {
            column["name"]
            for column in inspect(bind).get_columns(table_name)
        }
        for column_name, _, _ in reversed(columns):
            if column_name in existing_columns:
                op.drop_column(table_name, column_name)
