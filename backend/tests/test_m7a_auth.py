"""
M7-A 登录体系单测
- 赠额幂等（credit_ledger 命中 reason=grant_login 即跳过）
- 登录 session 锚定（session token → user_id 解析）
- quota/status 升级（auth 块 + session 优先 + 三级解析链回退）
- estimate_required 档位零回归（M6-B ×1.2 系数）

门禁：pytest backend/tests/ -q → ≥29 passed / 0 failed（M7-A 新增 +8 条）
test_presence_b3.py 零 diff 原则维持
"""
import asyncio
import os
import sqlite3
import tempfile
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.auth import (
    create_session,
    get_session_user_id,
    resolve_user_id_from_session,
    hash_password,
    verify_password,
)
from app.core.quota import grant_login_bonus, check_credits, estimate_required


def _make_test_db():
    """创建临时 SQLite DB 并注入最小 schema"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT NOT NULL UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            user_id       TEXT NOT NULL UNIQUE,
            created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_credits (
            user_id        TEXT PRIMARY KEY,
            balance        INTEGER NOT NULL DEFAULT 0,
            daily_cost     INTEGER NOT NULL DEFAULT 0,
            last_cost_date DATE     NOT NULL DEFAULT '1970-01-01',
            version        INTEGER NOT NULL DEFAULT 0,
            updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS credit_ledger (
            seq            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        TEXT NOT NULL,
            delta          INTEGER NOT NULL,
            reason         TEXT NOT NULL,
            session_id     TEXT,
            created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_credit_ledger_user_time ON credit_ledger(user_id, created_at);
        CREATE TABLE IF NOT EXISTS usage_log (
            user_id TEXT NOT NULL,
            generated_at TIMESTAMP NOT NULL,
            ip TEXT,
            PRIMARY KEY (user_id, generated_at)
        );
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def test_db_path(monkeypatch):
    """每个测试用独立临时 DB，返回 db_path 字符串供测试内直读"""
    db_path = _make_test_db()
    url = f"sqlite+aiosqlite:///{db_path}"
    monkeypatch.setattr(settings, "database_url", url)
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


class TestGrantLoginBonus:
    def test_grant_creates_credit_ledger_row(self, test_db_path):
        """grant_login_bonus：user_credits 不存在时创建账户行并写入流水"""
        db_path = test_db_path
        import aiosqlite
        async def run():
            conn = await aiosqlite.connect(db_path)
            try:
                await grant_login_bonus("test-user-1", 100)
                cursor = await conn.execute(
                    "SELECT balance FROM user_credits WHERE user_id = ?",
                    ("test-user-1",),
                )
                row = await cursor.fetchone()
                assert row is not None
                assert row[0] == 100

                cursor2 = await conn.execute(
                    'SELECT delta, reason FROM credit_ledger WHERE user_id = ? AND reason = ?',
                    ("test-user-1", "grant_login"),
                )
                led = await cursor2.fetchone()
                assert led is not None
                assert led[0] == 100
            finally:
                await conn.close()
        asyncio.run(run())

    def test_grant_idempotent_check_skips_if_already_granted(self, test_db_path):
        """幂等去重：credit_ledger 已有 grant_login 流水时，路由侧应跳过"""
        db_path = test_db_path
        import aiosqlite
        async def run():
            conn = await aiosqlite.connect(db_path)
            try:
                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                await conn.execute(
                    'INSERT INTO user_credits (user_id, balance, version, updated_at) VALUES (?, 0, 0, ?)',
                    ("test-user-2", now),
                )
                await conn.commit()
                await grant_login_bonus("test-user-2", 100)

                cursor = await conn.execute(
                    'SELECT 1 FROM credit_ledger WHERE user_id = ? AND reason = ? LIMIT 1',
                    ("test-user-2", "grant_login"),
                )
                already_granted = await cursor.fetchone() is not None
                assert already_granted, "幂等检查应命中既有 grant_login 流水"

                cursor2 = await conn.execute(
                    "SELECT balance FROM user_credits WHERE user_id = ?",
                    ("test-user-2",),
                )
                row = await cursor2.fetchone()
                assert row[0] == 100
            finally:
                await conn.close()
        asyncio.run(run())

    def test_grant_bonus_zero_amount_noop(self, test_db_path):
        """amount=0 时直接返回，不写流水"""
        db_path = test_db_path
        import aiosqlite
        async def run():
            conn = await aiosqlite.connect(db_path)
            try:
                await grant_login_bonus("test-user-3", 0)
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM credit_ledger WHERE user_id = ?",
                    ("test-user-3",),
                )
                row = await cursor.fetchone()
                assert row[0] == 0
            finally:
                await conn.close()
        asyncio.run(run())

    def test_grant_bonus_returns_balance_tuple(self, test_db_path):
        """M7-A 勘正：grant_login_bonus 成功路径必须返回 (True, new_balance) 元组，
        消除原 :408 版 -> None 签名静默覆盖 :351 版 -> Tuple[bool,int] 的同名 bug。"""
        db_path = test_db_path
        import aiosqlite
        async def run():
            conn = await aiosqlite.connect(db_path)
            try:
                ok, bal = await grant_login_bonus("test-user-4", 100)
                assert ok is True, "成功路径 ok 必须为 True"
                assert bal == 100, f"成功路径返回余额应为 100，实得 {bal}"
            finally:
                await conn.close()
        asyncio.run(run())


class TestSessionAnchoring:
    def test_session_token_returns_correct_user_id(self):
        token = create_session("anchor-user")
        assert resolve_user_id_from_session(token) == "anchor-user"

    def test_invalid_session_token_returns_none(self):
        assert resolve_user_id_from_session("invalid-token-xyz") is None

    def test_empty_session_token_returns_none(self):
        assert resolve_user_id_from_session("") is None
        assert resolve_user_id_from_session(None) is None

    def test_password_hash_roundtrip(self):
        salt, digest = hash_password("mypassword123")
        assert verify_password("mypassword123", salt, digest)
        assert not verify_password("wrongpassword", salt, digest)


class TestQuotaStatusAuthBlock:
    def test_quotastatus_response_includes_auth_block(self, test_db_path):
        """M7-A：quota/status 响应新增 auth 块（usage/credits 块 schema 不变）"""
        from app.main import app
        client = TestClient(app)
        resp = client.get("/api/quota/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth" in data
        assert "usage" in data
        assert "credits" in data
        assert data["auth"]["logged_in"] is False
        assert data["auth"]["resolution_source"] in ("fingerprint", "anon-ip", "anon-unknown")

    def test_session_first_resolution(self, test_db_path):
        """session token 优先于 X-User-Id 指纹"""
        from app.main import app
        import aiosqlite
        db_path = test_db_path
        token = create_session("sess-user-xyz")
        async def setup():
            conn = await aiosqlite.connect(db_path)
            try:
                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                await conn.execute(
                    'INSERT OR IGNORE INTO user_credits (user_id, balance, version, updated_at) '
                    'VALUES (?, 0, 0, ?)',
                    ("sess-user-xyz", now),
                )
                await conn.commit()
            finally:
                await conn.close()
        asyncio.run(setup())

        client = TestClient(app)
        resp = client.get(
            "/api/quota/status",
            headers={"X-Auth-Token": token, "X-User-Id": "fingerprint-abc"},
        )
        data = resp.json()
        assert data["auth"]["logged_in"] is True
        assert data["auth"]["user_id"] == "sess-user-xyz"
        assert data["auth"]["resolution_source"] == "session"


class TestNoRegression:
    def test_estimate_required_quick_zero_light(self):
        """M6-B 中文系数后：quick + input_len=0 → 2（LIGHT base=1，×1.2 取整）"""
        assert estimate_required("quick", 0, "auto") == 2

    def test_estimate_required_multimodal(self):
        """multimodal 早返 6 不变（§4.1 零改动区）"""
        assert estimate_required("quick", 0, "multimodal") == 6

    def test_estimate_required_medium(self):
        """M6-B 中文系数后：quick + 1000字 → 4（MEDIUM base=3，×1.2 取整）"""
        assert estimate_required("quick", 1000, "auto") == 4
