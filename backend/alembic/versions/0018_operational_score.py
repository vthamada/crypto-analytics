"""Add explicit operational score.

Revision ID: 0018_operational_score
Revises: 0017_scanner_pair_states
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "0018_operational_score"
down_revision = "0017_scanner_pair_states"
branch_labels = None
depends_on = None


def _add_column_if_missing(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if table_name not in tables:
        return
    columns = {column["name"] for column in inspect(bind).get_columns(table_name)}
    if column_name not in columns:
        op.add_column(table_name, sa.Column(column_name, sa.Float(), nullable=True))
    op.execute(text(f"UPDATE {table_name} SET {column_name} = score WHERE {column_name} IS NULL"))


def upgrade() -> None:
    _add_column_if_missing("opportunities", "operational_score")
    _add_column_if_missing("opportunity_snapshots", "operational_score")

    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "opportunities" in tables:
        indexes = {index["name"] for index in inspect(bind).get_indexes("opportunities")}
        if "ix_opportunities_operational_score" not in indexes:
            op.create_index("ix_opportunities_operational_score", "opportunities", ["operational_score"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "opportunities" in tables:
        indexes = {index["name"] for index in inspect(bind).get_indexes("opportunities")}
        if "ix_opportunities_operational_score" in indexes:
            op.drop_index("ix_opportunities_operational_score", table_name="opportunities")
        columns = {column["name"] for column in inspect(bind).get_columns("opportunities")}
        if "operational_score" in columns:
            op.drop_column("opportunities", "operational_score")

    if "opportunity_snapshots" in tables:
        columns = {column["name"] for column in inspect(bind).get_columns("opportunity_snapshots")}
        if "operational_score" in columns:
            op.drop_column("opportunity_snapshots", "operational_score")
