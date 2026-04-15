from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.database import Base
from app.services import auth


def test_password_hash_roundtrip():
    password_hash = auth.hash_password("super-secure-password")

    assert auth.verify_password("super-secure-password", password_hash) is True
    assert auth.verify_password("wrong-password", password_hash) is False


def test_access_token_is_revoked_after_password_change(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"auth-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(auth, "async_session", session_factory)
        monkeypatch.setattr(auth.settings, "admin_username", "admin")
        monkeypatch.setattr(auth.settings, "admin_password", "initial-secret")
        monkeypatch.setattr(auth.settings, "auth_secret_key", "signing-key")
        monkeypatch.setattr(auth.settings, "admin_token", "")

        await auth.ensure_admin_bootstrap()
        session_info = await auth.authenticate_admin_credentials("admin", "initial-secret")
        assert session_info is not None

        original_token = auth.issue_access_token(session_info)
        original_refresh_token = auth.issue_refresh_token(session_info)
        assert await auth.verify_access_token(original_token) is not None
        assert await auth.verify_refresh_token(original_refresh_token) is not None

        updated_session = await auth.change_admin_password(
            actor=session_info,
            current_password="initial-secret",
            new_password="updated-super-secret",
        )
        rotated_token = auth.issue_access_token(updated_session)
        rotated_refresh_token = auth.issue_refresh_token(updated_session)

        assert await auth.verify_access_token(original_token) is None
        assert await auth.verify_access_token(rotated_token) is not None
        assert await auth.verify_refresh_token(original_refresh_token) is None
        assert await auth.verify_refresh_token(rotated_refresh_token) is not None

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_admin_created_user_receives_workspace_membership(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"auth-membership-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(auth, "async_session", session_factory)
        monkeypatch.setattr(auth.settings, "admin_username", "admin")
        monkeypatch.setattr(auth.settings, "admin_password", "initial-secret")
        monkeypatch.setattr(auth.settings, "auth_secret_key", "signing-key")
        monkeypatch.setattr(auth.settings, "admin_token", "")

        await auth.ensure_admin_bootstrap()
        admin_session = await auth.authenticate_admin_credentials("admin", "initial-secret")
        assert admin_session is not None

        admin_workspaces = await auth.list_user_workspaces(admin_session.user_id)
        assert admin_workspaces

        created_user, temporary_password = await auth.create_user_by_admin(
            actor=admin_session,
            workspace_id=admin_workspaces[0].id,
            username="pai",
            role="member",
        )
        assert temporary_password

        member_session = await auth.authenticate_admin_credentials("pai", temporary_password)
        assert member_session is not None

        member_workspaces = await auth.list_user_workspaces(member_session.user_id)
        workspace_users = await auth.list_users_for_workspace(admin_workspaces[0].id)

        assert [workspace.id for workspace in member_workspaces] == [admin_workspaces[0].id]
        assert any(user["username"] == created_user["username"] for user in workspace_users)

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())
