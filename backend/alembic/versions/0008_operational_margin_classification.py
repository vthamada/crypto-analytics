"""add operational margin and opportunity classification fields"""

from alembic import op
import sqlalchemy as sa


revision = "0008_operational_margin"
down_revision = "0007_operational_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def columns(table_name: str) -> set[str]:
        return {column["name"] for column in inspector.get_columns(table_name)}

    def indexes(table_name: str) -> set[str]:
        return {index["name"] for index in inspector.get_indexes(table_name)}

    def add_column_if_missing(table_name: str, column: sa.Column) -> None:
        if column.name not in columns(table_name):
            op.add_column(table_name, column)

    def create_index_if_missing(index_name: str, table_name: str, column_names: list[str]) -> None:
        if index_name not in indexes(table_name):
            op.create_index(index_name, table_name, column_names)

    for table_name in ("opportunities", "opportunity_snapshots"):
        add_column_if_missing(table_name, sa.Column("estimated_trade_margin_pct", sa.Float(), nullable=True))
        add_column_if_missing(table_name, sa.Column("operational_friction_pct", sa.Float(), nullable=True))
        add_column_if_missing(table_name, sa.Column("estimated_net_trade_edge_pct", sa.Float(), nullable=True))
        add_column_if_missing(table_name, sa.Column("trade_margin_score", sa.Float(), nullable=True))
        add_column_if_missing(table_name, sa.Column("opportunity_type", sa.String(), nullable=True))
        create_index_if_missing(f"ix_{table_name}_opportunity_type", table_name, ["opportunity_type"])


def downgrade() -> None:
    for table_name in ("opportunity_snapshots", "opportunities"):
        op.drop_index(f"ix_{table_name}_opportunity_type", table_name=table_name)
        op.drop_column(table_name, "opportunity_type")
        op.drop_column(table_name, "trade_margin_score")
        op.drop_column(table_name, "estimated_net_trade_edge_pct")
        op.drop_column(table_name, "operational_friction_pct")
        op.drop_column(table_name, "estimated_trade_margin_pct")
