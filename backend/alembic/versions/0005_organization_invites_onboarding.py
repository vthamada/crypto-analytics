"""add organization, invites, email, and onboarding foundations"""

from datetime import datetime, timedelta, timezone
import uuid

from alembic import op
import sqlalchemy as sa


revision = "0005_org_invites_onboard"
down_revision = "0004_user_management"
branch_labels = None
depends_on = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("subscription_status", sa.String(), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("organization_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.add_column("workspaces", sa.Column("organization_id", sa.String(), nullable=True))
    op.create_index("ix_workspaces_organization_id", "workspaces", ["organization_id"])

    op.create_table(
        "invites",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_invites_code", "invites", ["code"])
    op.create_index("ix_invites_email", "invites", ["email"])
    op.create_index("ix_invites_organization_id", "invites", ["organization_id"])
    op.create_index("ix_invites_workspace_id", "invites", ["workspace_id"])
    op.create_index("ix_invites_created_by_user_id", "invites", ["created_by_user_id"])

    default_org_id = str(uuid.uuid4())
    now = utcnow()
    bind.execute(
        sa.text(
            """
            INSERT INTO organizations (
                id,
                name,
                slug,
                plan,
                stripe_customer_id,
                subscription_status,
                trial_ends_at,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :name,
                :slug,
                :plan,
                NULL,
                :subscription_status,
                :trial_ends_at,
                :created_at,
                :updated_at
            )
            """
        ),
        {
            "id": default_org_id,
            "name": "Default Organization",
            "slug": "default-org",
            "plan": "trial",
            "subscription_status": "trialing",
            "trial_ends_at": now + timedelta(days=14),
            "created_at": now,
            "updated_at": now,
        },
    )
    bind.execute(
        sa.text("UPDATE users SET organization_id = :organization_id WHERE organization_id IS NULL"),
        {"organization_id": default_org_id},
    )
    bind.execute(
        sa.text("UPDATE workspaces SET organization_id = :organization_id WHERE organization_id IS NULL"),
        {"organization_id": default_org_id},
    )


def downgrade() -> None:
    op.drop_index("ix_invites_created_by_user_id", table_name="invites")
    op.drop_index("ix_invites_workspace_id", table_name="invites")
    op.drop_index("ix_invites_organization_id", table_name="invites")
    op.drop_index("ix_invites_email", table_name="invites")
    op.drop_index("ix_invites_code", table_name="invites")
    op.drop_table("invites")

    op.drop_index("ix_workspaces_organization_id", table_name="workspaces")
    op.drop_column("workspaces", "organization_id")

    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "organization_id")
    op.drop_column("users", "email")

    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
