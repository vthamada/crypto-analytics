"""Add order size simulations.

Revision ID: 0019_order_size_simulations
Revises: 0018_operational_score
Create Date: 2026-06-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0019_order_size_simulations"
down_revision = "0018_operational_score"
branch_labels = None
depends_on = None


TABLES = ("opportunities", "opportunity_snapshots")


def _add_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if table_name not in tables:
        return
    columns = {item["name"] for item in inspect(bind).get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def upgrade() -> None:
    for table_name in TABLES:
        _add_if_missing(table_name, sa.Column("order_size_simulations", sa.Text(), nullable=True))
        _add_if_missing(table_name, sa.Column("max_operable_order_notional_brl", sa.Float(), nullable=True))
        _add_if_missing(table_name, sa.Column("operability_size_label", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for table_name in TABLES:
        if table_name not in tables:
            continue
        columns = {item["name"] for item in inspect(bind).get_columns(table_name)}
        for column_name in (
            "operability_size_label",
            "max_operable_order_notional_brl",
            "order_size_simulations",
        ):
            if column_name in columns:
                op.drop_column(table_name, column_name)
