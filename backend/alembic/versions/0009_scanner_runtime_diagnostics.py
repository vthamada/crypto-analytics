"""Persist scanner runtime diagnostics.

Revision ID: 0009_scanner_runtime_diagnostics
Revises: 0008_operational_margin_classification
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0009_scanner_runtime_diagnostics"
down_revision = "0008_operational_margin_classification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("scanner_runtime_state")}
    if "last_scan_diagnostics" not in columns:
        op.add_column("scanner_runtime_state", sa.Column("last_scan_diagnostics", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("scanner_runtime_state")}
    if "last_scan_diagnostics" in columns:
        op.drop_column("scanner_runtime_state", "last_scan_diagnostics")
