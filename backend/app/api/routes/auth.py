"""
M7-A 用户认证路由
- POST /api/auth/register：邮箱+密码注册（MVP 最小实现）
- POST /api/auth/login：登录，返回 session token
- POST /api/auth/logout：登出
- 赠额闸门：首次登录一次性赠送（@JARVIS 裁定值 = 100 积分）
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import aiosqlite
from datetime import datetime, timezone
import os
from typing import Optional

from ...core.config import settings
from ...core.auth import (
    hash_password,
    verify_password,
    create_session,
    destroy_session,
    resolve_user_id_from_session,
)
from ...core.quota import grant_login_bonus

router = APIRouter()

# 赠额默认值（@JARVIS 裁定 100，可配置覆盖）
GRANT_LOGIN_BONUS_DEFAULT = 100

# 同步 DDL（users 表 + 索引，幂等）：
# 路由层不用 init_db()（async，lifespan 已负责建表）；
# 冷启动未走 lifespan 时，用 aiosqlite 直连执行本 DDL。
_AUTH_DDL_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    user_id       TEXT NOT NULL UNIQUE,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
"""


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RegisterRequest(BaseModel):
    email: str
    password: str
    user_id: Optional[str] = None  # 可选，缺省时自动生成


class LoginRequest(BaseModel):
    email: str
    password: str


async def _ensure_auth_tables() -> None:
    """幂等建表（与 quota.py 路由侧同模式）"""
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    try:
        await conn.executescript(_AUTH_DDL_SQL)
        await conn.commit()
    finally:
        await conn.close()


@router.post("/register")
async def register(req: RegisterRequest):
    """
    注册：邮箱 + 密码 + 可选 user_id（MVP 最小实现）。
    首次注册即创建 user_credits 账户行（balance=0），
    赠额在首次登录时触发（M7-A 赠额闸门设计）。
    """
    await _ensure_auth_tables()
    email = req.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 chars")

    user_id = (req.user_id or "").strip() or f"user-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex()}"

    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    try:
        # 检查邮箱是否已存在
        cursor = await conn.execute("SELECT 1 FROM users WHERE email = ?", (email,))
        if await cursor.fetchone():
            raise HTTPException(status_code=409, detail="email already registered")

        salt, digest = hash_password(req.password)
        now = _now_utc_iso()
        await conn.execute(
            "INSERT INTO users (email, password_salt, password_hash, user_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (email, salt.decode("latin-1"), digest.decode("latin-1"), user_id, now),
        )
        # 创建 user_credits 账户行（balance=0，version=0）
        await conn.execute(
            "INSERT OR IGNORE INTO user_credits (user_id, balance, version, updated_at) "
            "VALUES (?, 0, 0, ?)",
            (user_id, now),
        )
        await conn.commit()
    except HTTPException:
        await conn.rollback()
        raise
    finally:
        await conn.close()

    return {"user_id": user_id, "email": email, "ok": True}


@router.post("/login")
async def login(req: LoginRequest):
    """
    登录：邮箱 + 密码验证 → 返回 session token。
    首次登录触发赠额闸门（grant_login_bonus）。
    """
    await _ensure_auth_tables()
    email = req.email.strip().lower()

    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    try:
        cursor = await conn.execute(
            "SELECT user_id, password_salt, password_hash FROM users WHERE email = ?",
            (email,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="invalid credentials")

        user_id = row[0]
        salt = row[1].encode("latin-1")
        expected_digest = row[2].encode("latin-1")

        if not verify_password(req.password, salt, expected_digest):
            raise HTTPException(status_code=401, detail="invalid credentials")

        # 更新 last_login_at
        await conn.execute(
            "UPDATE users SET last_login_at = ? WHERE user_id = ?",
            (_now_utc_iso(), user_id),
        )
        await conn.commit()

        # 赠额闸门：检查是否已赠过（credit_ledger 中 reason='grant_login' 命中即跳过）
        cursor2 = await conn.execute(
            "SELECT 1 FROM credit_ledger WHERE user_id = ? AND reason = 'grant_login' LIMIT 1",
            (user_id,),
        )
        already_granted = await cursor2.fetchone() is not None
        await conn.close()

        if not already_granted:
            grant_amount = GRANT_LOGIN_BONUS_DEFAULT
            await grant_login_bonus(user_id, grant_amount)
    finally:
        # 确保连接已关闭（正常路径已 close，异常路径兜底）
        pass

    token = create_session(user_id)
    return {
        "session_token": token,
        "user_id": user_id,
        "bonus_granted": not already_granted,
        "ok": True,
    }


@router.post("/logout")
async def logout(http_request: Request):
    """登出：销毁 session"""
    token = http_request.headers.get("X-Auth-Token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="X-Auth-Token header required")
    destroyed = destroy_session(token)
    return {"ok": destroyed}
