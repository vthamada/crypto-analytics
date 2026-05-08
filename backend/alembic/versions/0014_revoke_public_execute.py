"""Revoke inherited public execute on RLS helper.

Revision ID: 0014_revoke_public_execute
Revises: 0013_supabase_rls_hardening
Create Date: 2026-05-08
"""

from __future__ import annotations

from alembic import op


revision = "0014_revoke_public_execute"
down_revision = "0013_supabase_rls_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public'
                  AND p.proname = 'rls_auto_enable'
                  AND pg_get_function_arguments(p.oid) = ''
                  AND pg_get_userbyid(p.proowner) = current_user
            ) THEN
                REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC;
                REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM anon;
                REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM authenticated;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public'
                  AND p.proname = 'rls_auto_enable'
                  AND pg_get_function_arguments(p.oid) = ''
                  AND pg_get_userbyid(p.proowner) = current_user
            ) THEN
                GRANT EXECUTE ON FUNCTION public.rls_auto_enable() TO PUBLIC;
            END IF;
        END
        $$;
        """
    )
