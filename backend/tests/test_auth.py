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
        assert await auth.verify_access_token(original_token) is not None

        updated_session = await auth.change_admin_password(
            actor=session_info,
            current_password="initial-secret",
            new_password="updated-super-secret",
        )
        rotated_token = auth.issue_access_token(updated_session)

        assert await auth.verify_access_token(original_token) is None
        assert await auth.verify_access_token(rotated_token) is not None

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())
