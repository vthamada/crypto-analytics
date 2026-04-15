"""add workspace multi-tenant foundations"""

from alembic import op
import sqlalchemy as sa


revision = "0003_workspace_multi_tenant"
down_revision = "0002_admin_auth_and_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("password_updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"])
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])

    op.create_table(
        "workspace_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspace_memberships_workspace_id", "workspace_memberships", ["workspace_id"])
    op.create_index("ix_workspace_memberships_user_id", "workspace_memberships", ["user_id"])
    op.create_index("ix_workspace_memberships_role", "workspace_memberships", ["role"])

    op.create_table(
        "workspace_configs",
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id"),
    )

    op.add_column("audit_logs", sa.Column("actor_user_id", sa.String(), nullable=True))
    op.add_column("audit_logs", sa.Column("workspace_id", sa.String(), nullable=True))
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_workspace_id", "audit_logs", ["workspace_id"])

    op.add_column("opportunities", sa.Column("volatility_score", sa.Float(), nullable=True))
    op.add_column("opportunities", sa.Column("volume_score", sa.Float(), nullable=True))
    op.add_column("opportunities", sa.Column("liquidity_score", sa.Float(), nullable=True))
    op.add_column("opportunities", sa.Column("spread_score", sa.Float(), nullable=True))
    op.add_column("opportunities", sa.Column("repetition_score", sa.Float(), nullable=True))
    op.add_column("opportunities", sa.Column("movement_multiplier", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("opportunities", "movement_multiplier")
    op.drop_column("opportunities", "repetition_score")
    op.drop_column("opportunities", "spread_score")
    op.drop_column("opportunities", "liquidity_score")
    op.drop_column("opportunities", "volume_score")
    op.drop_column("opportunities", "volatility_score")

    op.drop_index("ix_audit_logs_workspace_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_column("audit_logs", "workspace_id")
    op.drop_column("audit_logs", "actor_user_id")

    op.drop_table("workspace_configs")

    op.drop_index("ix_workspace_memberships_role", table_name="workspace_memberships")
    op.drop_index("ix_workspace_memberships_user_id", table_name="workspace_memberships")
    op.drop_index("ix_workspace_memberships_workspace_id", table_name="workspace_memberships")
    op.drop_table("workspace_memberships")

    op.drop_index("ix_workspaces_owner_user_id", table_name="workspaces")
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
