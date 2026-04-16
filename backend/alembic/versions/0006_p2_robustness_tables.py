"""P2 robustness: scanner_runtime_state, opportunity_snapshots, technical_signals,
workspace_signal_projections, signal_outcomes, repetition_counts,
opportunities.technical_score/score_version/technical_signal_id"""

from alembic import op
import sqlalchemy as sa


revision = "0006_p2_robustness_tables"
down_revision = "0005_organization_invites_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- scanner_runtime_state --
    op.create_table(
        "scanner_runtime_state",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("last_cycle_started_at", sa.DateTime(), nullable=True),
        sa.Column("last_cycle_completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_cycle_duration_ms", sa.Float(), nullable=True),
        sa.Column("last_cycle_error", sa.Text(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("opportunities_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # -- opportunity_snapshots --
    op.create_table(
        "opportunity_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("pair", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("technical_score", sa.Float(), nullable=False),
        sa.Column("score_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("volatility_pct", sa.Float(), nullable=False),
        sa.Column("volume_24h", sa.Float(), nullable=False),
        sa.Column("quote_volume_24h", sa.Float(), nullable=False),
        sa.Column("liquidity_units", sa.Float(), nullable=False),
        sa.Column("spread_pct", sa.Float(), nullable=False),
        sa.Column("movement_type", sa.String(), nullable=False),
        sa.Column("last_price", sa.Float(), nullable=False),
        sa.Column("change_pct", sa.Float(), nullable=False),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("historical_confidence", sa.Float(), server_default="1.0"),
        sa.Column("volatility_score", sa.Float(), server_default="0.0"),
        sa.Column("volume_score", sa.Float(), server_default="0.0"),
        sa.Column("liquidity_score", sa.Float(), server_default="0.0"),
        sa.Column("spread_score", sa.Float(), server_default="0.0"),
        sa.Column("repetition_score", sa.Float(), server_default="0.0"),
        sa.Column("movement_multiplier", sa.Float(), server_default="1.0"),
        sa.Column("cross_exchange_gap_pct", sa.Float(), server_default="0.0"),
        sa.Column("cross_exchange_reference_exchange", sa.String(), nullable=True),
        sa.Column("cross_exchange_reference_price", sa.Float(), nullable=True),
        sa.Column("arbitrage_available", sa.Boolean(), server_default=sa.false()),
        sa.Column("snapshot_cycle_id", sa.String(), nullable=False),
    )
    op.create_index("ix_opportunity_snapshots_exchange", "opportunity_snapshots", ["exchange"])
    op.create_index("ix_opportunity_snapshots_pair", "opportunity_snapshots", ["pair"])
    op.create_index("ix_opportunity_snapshots_snapshot_cycle_id", "opportunity_snapshots", ["snapshot_cycle_id"])

    # -- technical_signals --
    op.create_table(
        "technical_signals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("pair", sa.String(), nullable=False),
        sa.Column("technical_score", sa.Float(), nullable=False),
        sa.Column("score_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("volatility_pct", sa.Float(), nullable=False),
        sa.Column("volatility_score", sa.Float(), server_default="0.0"),
        sa.Column("volume_24h", sa.Float(), nullable=False),
        sa.Column("quote_volume_24h", sa.Float(), nullable=False),
        sa.Column("volume_score", sa.Float(), server_default="0.0"),
        sa.Column("liquidity_units", sa.Float(), nullable=False),
        sa.Column("liquidity_score", sa.Float(), server_default="0.0"),
        sa.Column("spread_pct", sa.Float(), nullable=False),
        sa.Column("spread_score", sa.Float(), server_default="0.0"),
        sa.Column("repetition_score", sa.Float(), server_default="0.0"),
        sa.Column("movement_type", sa.String(), nullable=False),
        sa.Column("movement_multiplier", sa.Float(), server_default="1.0"),
        sa.Column("last_price", sa.Float(), nullable=False),
        sa.Column("change_pct", sa.Float(), nullable=False),
        sa.Column("historical_confidence", sa.Float(), server_default="1.0"),
        sa.Column("cross_exchange_gap_pct", sa.Float(), server_default="0.0"),
        sa.Column("cross_exchange_reference_exchange", sa.String(), nullable=True),
        sa.Column("cross_exchange_reference_price", sa.Float(), nullable=True),
        sa.Column("arbitrage_available", sa.Boolean(), server_default=sa.false()),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_technical_signals_exchange", "technical_signals", ["exchange"])
    op.create_index("ix_technical_signals_pair", "technical_signals", ["pair"])
    op.create_index("ix_technical_signals_technical_score", "technical_signals", ["technical_score"])
    op.create_index("ix_technical_signals_detected_at", "technical_signals", ["detected_at"])
    op.create_index("ix_technical_signals_arbitrage_available", "technical_signals", ["arbitrage_available"])

    # -- workspace_signal_projections --
    op.create_table(
        "workspace_signal_projections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("technical_signal_id", sa.String(), nullable=False),
        sa.Column("workspace_score", sa.Float(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("alert_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("projection_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_workspace_signal_projections_workspace_id", "workspace_signal_projections", ["workspace_id"])
    op.create_index("ix_workspace_signal_projections_technical_signal_id", "workspace_signal_projections", ["technical_signal_id"])
    op.create_index("ix_workspace_signal_projections_created_at", "workspace_signal_projections", ["created_at"])

    # -- signal_outcomes --
    op.create_table(
        "signal_outcomes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("technical_signal_id", sa.String(), nullable=False),
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("pair", sa.String(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("price_after_5m", sa.Float(), nullable=True),
        sa.Column("price_after_15m", sa.Float(), nullable=True),
        sa.Column("price_after_1h", sa.Float(), nullable=True),
        sa.Column("price_after_4h", sa.Float(), nullable=True),
        sa.Column("max_price_1h", sa.Float(), nullable=True),
        sa.Column("min_price_1h", sa.Float(), nullable=True),
        sa.Column("outcome_pct_5m", sa.Float(), nullable=True),
        sa.Column("outcome_pct_15m", sa.Float(), nullable=True),
        sa.Column("outcome_pct_1h", sa.Float(), nullable=True),
        sa.Column("outcome_pct_4h", sa.Float(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=True),
        sa.Column("signal_detected_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_signal_outcomes_technical_signal_id", "signal_outcomes", ["technical_signal_id"])
    op.create_index("ix_signal_outcomes_pair", "signal_outcomes", ["pair"])
    op.create_index("ix_signal_outcomes_signal_detected_at", "signal_outcomes", ["signal_detected_at"])

    # -- repetition_counts --
    op.create_table(
        "repetition_counts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("exchange", sa.String(), nullable=False),
        sa.Column("pair", sa.String(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # -- Add technical_score and score_version to opportunities table --
    op.add_column(
        "opportunities",
        sa.Column("technical_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("score_version", sa.String(), nullable=True, server_default="v1"),
    )
    op.add_column(
        "opportunities",
        sa.Column("technical_signal_id", sa.String(), nullable=True),
    )

    # -- Add telegram_alert_threshold and telegram_alert_cooldown to workspace_configs --
    # These are stored in the JSON config value, so no column changes needed.


def downgrade() -> None:
    op.drop_column("opportunities", "technical_signal_id")
    op.drop_column("opportunities", "score_version")
    op.drop_column("opportunities", "technical_score")
    op.drop_table("repetition_counts")
    op.drop_table("signal_outcomes")
    op.drop_table("workspace_signal_projections")
    op.drop_table("technical_signals")
    op.drop_table("opportunity_snapshots")
    op.drop_table("scanner_runtime_state")
