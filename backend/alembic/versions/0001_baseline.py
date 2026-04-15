"""baseline schema"""

from alembic import op
import sqlalchemy as sa


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("pair", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("volatility_pct", sa.Float(), nullable=False),
        sa.Column("volume_24h", sa.Float(), nullable=False),
        sa.Column("quote_volume_24h", sa.Float(), nullable=False),
        sa.Column("liquidity_units", sa.Float(), nullable=False),
        sa.Column("spread_pct", sa.Float(), nullable=False),
        sa.Column("movement_type", sa.String(), nullable=False),
        sa.Column("last_price", sa.Float(), nullable=False),
        sa.Column("change_pct", sa.Float(), nullable=False),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("cross_exchange_gap_pct", sa.Float(), nullable=True),
        sa.Column("cross_exchange_reference_exchange", sa.String(), nullable=True),
        sa.Column("cross_exchange_reference_price", sa.Float(), nullable=True),
        sa.Column("arbitrage_available", sa.Boolean(), nullable=True),
        sa.Column("historical_confidence", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_opportunities_exchange", "opportunities", ["exchange"])
    op.create_index("ix_opportunities_pair", "opportunities", ["pair"])
    op.create_index("ix_opportunities_score", "opportunities", ["score"])
    op.create_index("ix_opportunities_detected_at", "opportunities", ["detected_at"])
    op.create_index("ix_opportunities_arbitrage_available", "opportunities", ["arbitrage_available"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_arbitrage_available", table_name="opportunities")
    op.drop_index("ix_opportunities_detected_at", table_name="opportunities")
    op.drop_index("ix_opportunities_score", table_name="opportunities")
    op.drop_index("ix_opportunities_pair", table_name="opportunities")
    op.drop_index("ix_opportunities_exchange", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_table("config")
