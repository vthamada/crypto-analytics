"""add user management fields"""

from alembic import op
import sqlalchemy as sa


revision = "0004_user_management"
down_revision = "0003_workspace_multi_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("created_by_user_id", sa.String(), nullable=True),
    )
    op.create_index("ix_users_created_by_user_id", "users", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_users_created_by_user_id", table_name="users")
    op.drop_column("users", "created_by_user_id")
    op.drop_column("users", "must_change_password")
