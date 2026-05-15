"""Add operational opportunity subtype.

Revision ID: 0016_opportunity_subtype
Revises: 0015_alert_worthiness_state
Create Date: 2026-05-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0016_opportunity_subtype"
down_revision = "0015_alert_worthiness_state"
branch_labels = None
depends_on = None


TABLES = ("opportunities", "opportunity_snapshots")


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for table_name in TABLES:
        if table_name not in tables:
            continue
        existing_columns = {
            column["name"]
            for column in inspect(bind).get_columns(table_name)
        }
        if "opportunity_subtype" not in existing_columns:
            op.add_column(table_name, sa.Column("opportunity_subtype", sa.String(), nullable=True))
        existing_indexes = {
            index["name"]
            for index in inspect(bind).get_indexes(table_name)
        }
        index_name = f"ix_{table_name}_opportunity_subtype"
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, ["opportunity_subtype"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for table_name in TABLES:
        if table_name not in tables:
            continue
        existing_indexes = {
            index["name"]
            for index in inspect(bind).get_indexes(table_name)
        }
        index_name = f"ix_{table_name}_opportunity_subtype"
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)
        existing_columns = {
            column["name"]
            for column in inspect(bind).get_columns(table_name)
        }
        if "opportunity_subtype" in existing_columns:
            op.drop_column(table_name, "opportunity_subtype")
