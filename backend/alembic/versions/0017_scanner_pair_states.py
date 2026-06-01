"""Persist scanner pair temperature and cooldown.

Revision ID: 0017_scanner_pair_states
Revises: 0016_opportunity_subtype
Create Date: 2026-05-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0017_scanner_pair_states"
down_revision = "0016_opportunity_subtype"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "scanner_pair_states" in tables:
        return

    op.create_table(
        "scanner_pair_states",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("pair", sa.String(), nullable=False),
        sa.Column("temperature", sa.String(), nullable=False, server_default="warm"),
        sa.Column("last_light_scan_at", sa.DateTime(), nullable=True),
        sa.Column("last_deep_scan_at", sa.DateTime(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cooldown_until", sa.DateTime(), nullable=True),
        sa.Column("last_discard_reason", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scanner_pair_states_exchange", "scanner_pair_states", ["exchange"])
    op.create_index("ix_scanner_pair_states_pair", "scanner_pair_states", ["pair"])
    op.create_index("ix_scanner_pair_states_temperature", "scanner_pair_states", ["temperature"])
    op.create_index("ix_scanner_pair_states_cooldown_until", "scanner_pair_states", ["cooldown_until"])
    op.create_index("ix_scanner_pair_states_last_discard_reason", "scanner_pair_states", ["last_discard_reason"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "scanner_pair_states" not in tables:
        return

    op.drop_index("ix_scanner_pair_states_last_discard_reason", table_name="scanner_pair_states")
    op.drop_index("ix_scanner_pair_states_cooldown_until", table_name="scanner_pair_states")
    op.drop_index("ix_scanner_pair_states_temperature", table_name="scanner_pair_states")
    op.drop_index("ix_scanner_pair_states_pair", table_name="scanner_pair_states")
    op.drop_index("ix_scanner_pair_states_exchange", table_name="scanner_pair_states")
    op.drop_table("scanner_pair_states")
