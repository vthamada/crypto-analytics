"""Harden Supabase exposed schema privileges.

Revision ID: 0013_supabase_rls_hardening
Revises: 0012_signal_pipeline_audit
Create Date: 2026-05-08
"""

from __future__ import annotations

from alembic import op


revision = "0013_supabase_rls_hardening"
down_revision = "0012_signal_pipeline_audit"
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
            ) THEN
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
            ) THEN
                GRANT EXECUTE ON FUNCTION public.rls_auto_enable() TO anon;
                GRANT EXECUTE ON FUNCTION public.rls_auto_enable() TO authenticated;
            END IF;
        END
        $$;
        """
    )
