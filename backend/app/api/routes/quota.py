"""
积分/额度状态查询（Phase 4 §3.4）

鉴权规则：绑定调用方自身 user_id（与 /create 的 quota_user_id 同源——
localStorage 指纹 header 链路 X-User-Id or 匿名指纹 anon-{host}），
不接受任意 user_id 查询参数；跨 user_id 查询一律 404（不区分「不存在」
与「无权」，防余额/流水 oracle 枚举）。MVP 过渡期无登录；
登录体系立项后升级为 session-bound 鉴权。
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

import aiosqlite

from ...core.quota import check_quota, check_credits
from ...core.config import settings

# 同步 DDL 常量（与 db.py SCHEMA_SQL 中 user_credits/credit_ledger 逐字一致，幂等）：
# 路由层不用 init_db()（async，lifespan 已负责建表）；冷启动未走 lifespan 时，
# 用 aiosqlite 直连执行本 DDL，避免同步调用 async init_db() 产生的
# "coroutine never awaited" RuntimeWarning + 冷启动 user_credits 缺失 500
_CREDITS_DDL_SQL = """
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
"""

router = APIRouter()


def _resolve_user_id(http_request: Request) -> str:
    """与 generation.py /create L665-670 同源三级解析：
    请求头 X-User-Id（localStorage 指纹链路）→ anon-{host} → anon-unknown"""
    fingerprint = http_request.headers.get("X-User-Id", "").strip()
    if fingerprint:
        return fingerprint
    if http_request.client:
        return f"anon-{http_request.client.host}"
    return "anon-unknown"


@router.get("/status")
async def quota_status(http_request: Request):
    """
    查询当前会话账户的 usage + credits 状态（§3.4 schema）。
    跨 user_id 一律 404 不枚举（不返回 403，不区分「不存在」与「无权」）。
    """
    # 防御性建表（user_credits/credit_ledger，幂等）：
    # 正常路径下 lifespan 已完成建表，此调用为 no-op；
    # 冷启动未走 lifespan 时以同步 DDL 直连保证可查（init_db() 为 async，
    # 同步调用产生 "coroutine never awaited" RuntimeWarning，此处不走该路径）
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    try:
        await conn.executescript(_CREDITS_DDL_SQL)
        await conn.commit()
    finally:
        await conn.close()

    user_id = _resolve_user_id(http_request)

    # 可选查询参数 user_id 仅在与调用方自身指纹一致时放行，否则 404（oracle 防护，R6）
    explicit = http_request.query_params.get("user_id")
    if explicit is not None and explicit != user_id:
        raise HTTPException(status_code=404, detail="not found")

    # M2 PR 2 勘误（随 CreditPanel 数据源同批）：required 不再是 M1 硬编码 0，
    # 改为按 §3.5.1 折算函数 estimate_required 对 quick/auto 场景的默认档取 1
    # （CreditPanel 展示"本次预计消耗"用；§3.4 credits.required 字段对齐 §3.5 折算口径）
    from ...core.quota import estimate_required
    required_hint = estimate_required("quick", 0, "auto")  # 未提供 prompt 长度时按 LIGHT 档默认 1

    allowed, used, limit = await check_quota(user_id)
    credit_allowed, balance, credit_used, credit_limit = await check_credits(user_id, required_hint)

    # §3.4 schema：usage 块 = 免费额度计数（used/limit/reset_at）+ credits 块 = 积分账户
    # required 对齐 §3.5.1 折算口径：未提供 prompt 长度时按 LIGHT 档默认 1（M1 硬编码 0 已作废）
    return JSONResponse(content={
        "usage": {
            "used": used,
            "limit": limit,
            "allowed": allowed,
            "reset_at": _next_utc_midnight_iso(),
        },
        "credits": {
            "balance": balance,
            "required": required_hint,
        },
    })


@router.get("/test/setup-balance")
async def test_setup_balance(http_request: Request):
    """
    测试专用端点（M2 PR 2 E2E 402 用例前置注入）：
    直接给指定 user_id 注入积分余额，绕过 M4 未立项的 /pay 充值通道，
    供 E2E 402 用例构造 0 < balance < required 的中间态。
    仅限 development 环境启用（settings.env 非 development 时返回 404 静默，不暴露端点存在）。
    """
    if settings.env != "development":
        raise HTTPException(status_code=404, detail="not found")
    user_id = http_request.query_params.get("user_id", "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    balance_str = http_request.query_params.get("balance", "0")
    balance = int(balance_str)
    if balance < 0:
        raise HTTPException(status_code=400, detail="balance must be >= 0")

    from ...core.quota import _now_utc_iso

    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    try:
        await conn.executescript(_CREDITS_DDL_SQL)
        await conn.commit()
        await conn.execute(
            "INSERT INTO user_credits (user_id, balance, version, updated_at) "
            "VALUES (?, ?, 0, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET balance = ?, version = version + 1, updated_at = ?",
            (user_id, balance, _now_utc_iso(), balance, _now_utc_iso()),
        )
        await conn.commit()
    finally:
        await conn.close()
    return {"user_id": user_id, "balance": balance, "ok": True}


def _next_utc_midnight_iso() -> str:
    """次日 0 点（UTC 零点口径，与 P1-#7 修复后 generation.py 429 分支 reset_at 同口径）"""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    return (
        (now + timedelta(days=1))
        .replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
