"""add operational profile, reweighting, movement regime, and raw observations"""

from alembic import op
import sqlalchemy as sa


revision = "0007_operational_profiles_and_history_layers"
down_revision = "0006_p2_robustness_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("opportunities",):
        op.add_column(table_name, sa.Column("reweighting_version", sa.String(), nullable=True, server_default="v1"))
        op.add_column(table_name, sa.Column("semantic_signal_key", sa.String(), nullable=True))
        op.add_column(table_name, sa.Column("baseline_order_notional_brl", sa.Float(), nullable=True))
        op.add_column(table_name, sa.Column("movement_regime", sa.String(), nullable=True))

    op.create_index("ix_opportunities_semantic_signal_key", "opportunities", ["semantic_signal_key"])

    for table_name in ("opportunity_snapshots",):
        op.add_column(table_name, sa.Column("reweighting_version", sa.String(), nullable=False, server_default="v1"))
        op.add_column(table_name, sa.Column("baseline_order_notional_brl", sa.Float(), nullable=True))
        op.add_column(table_name, sa.Column("movement_regime", sa.String(), nullable=True))

    for table_name in ("technical_signals",):
        op.add_column(table_name, sa.Column("reweighting_version", sa.String(), nullable=False, server_default="v1"))
        op.add_column(table_name, sa.Column("movement_regime", sa.String(), nullable=True))
        op.add_column(table_name, sa.Column("semantic_signal_key", sa.String(), nullable=True))

    op.create_index("ix_technical_signals_semantic_signal_key", "technical_signals", ["semantic_signal_key"])

    for table_name in ("workspace_signal_projections",):
        op.add_column(table_name, sa.Column("reweighting_version", sa.String(), nullable=False, server_default="v1"))

    op.create_table(
        "raw_market_observations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("observation_cycle_id", sa.String(), nullable=False),
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("pair", sa.String(), nullable=False),
        sa.Column("semantic_signal_key", sa.String(), nullable=True),
        sa.Column("movement_type", sa.String(), nullable=False),
        sa.Column("movement_regime", sa.String(), nullable=True),
        sa.Column("last_price", sa.Float(), nullable=False),
        sa.Column("quote_volume_24h", sa.Float(), nullable=False),
        sa.Column("liquidity_units", sa.Float(), nullable=False),
        sa.Column("spread_pct", sa.Float(), nullable=False),
        sa.Column("bid_notional_top_n", sa.Float(), nullable=True),
        sa.Column("ask_notional_top_n", sa.Float(), nullable=True),
        sa.Column("total_notional_top_n", sa.Float(), nullable=True),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_raw_market_observations_observation_cycle_id", "raw_market_observations", ["observation_cycle_id"])
    op.create_index("ix_raw_market_observations_exchange", "raw_market_observations", ["exchange"])
    op.create_index("ix_raw_market_observations_pair", "raw_market_observations", ["pair"])
    op.create_index("ix_raw_market_observations_semantic_signal_key", "raw_market_observations", ["semantic_signal_key"])
    op.create_index("ix_raw_market_observations_detected_at", "raw_market_observations", ["detected_at"])


def downgrade() -> None:
    op.drop_index("ix_raw_market_observations_detected_at", table_name="raw_market_observations")
    op.drop_index("ix_raw_market_observations_semantic_signal_key", table_name="raw_market_observations")
    op.drop_index("ix_raw_market_observations_pair", table_name="raw_market_observations")
    op.drop_index("ix_raw_market_observations_exchange", table_name="raw_market_observations")
    op.drop_index("ix_raw_market_observations_observation_cycle_id", table_name="raw_market_observations")
    op.drop_table("raw_market_observations")

    op.drop_column("workspace_signal_projections", "reweighting_version")

    op.drop_index("ix_technical_signals_semantic_signal_key", table_name="technical_signals")
    op.drop_column("technical_signals", "semantic_signal_key")
    op.drop_column("technical_signals", "movement_regime")
    op.drop_column("technical_signals", "reweighting_version")

    op.drop_column("opportunity_snapshots", "movement_regime")
    op.drop_column("opportunity_snapshots", "baseline_order_notional_brl")
    op.drop_column("opportunity_snapshots", "reweighting_version")

    op.drop_index("ix_opportunities_semantic_signal_key", table_name="opportunities")
    op.drop_column("opportunities", "movement_regime")
    op.drop_column("opportunities", "baseline_order_notional_brl")
    op.drop_column("opportunities", "semantic_signal_key")
    op.drop_column("opportunities", "reweighting_version")
