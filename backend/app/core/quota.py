"""
免费额度管理
基于 usage_log 表的每日生成次数限流（日级滑动窗口，按 user_id + 当日零点截断）
配置项 FREE_DAILY_LIMIT 控制上限，默认 10
"""
from datetime import datetime, timezone
from typing import Tuple, Optional

import aiosqlite

from .config import settings
from ..db import get_db_sync


def _today_start_utc() -> str:
    """当前UTC日期零点（用于日期键截断）"""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d") + " 00:00:00"


def get_quota_status_sync(user_id: str) -> Tuple[bool, int, int]:
    """
    同步版额度检查（供测试脚本使用）
    返回 (是否允许, 已用次数, 上限)
    """
    limit = settings.free_daily_limit
    since = _today_start_utc()
    conn = get_db_sync()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM usage_log WHERE user_id = ? AND generated_at >= ?",
            (user_id, since),
        ).fetchone()
        used = row[0] if row else 0
    finally:
        conn.close()
    return (used < limit, used, limit)


async def check_credits(user_id: str, required: int = 0) -> Tuple[bool, int, int, int]:
    """
    积分复合判定（M1：免费额度 + 余额；§3.1/§3.3，签名按 §2.3 OR 判定式收敛为 4 元组）
    返回 (allowed, balance, used, limit)
    - allowed = 余额 ≥ 所需（required，M1 固定 0）或 当日免费额度未耗尽
    - 耗尽且余额 = 0 → allowed=False（429 路径，code=daily_free_quota_exceeded）
    - 耗尽且余额 < required → allowed=False（402 路径，M2 预扣点接 required > 0 后生效）
    判定式（v0.2.3 文档对齐，§3.5.3 拦截式，M1 终审 NIT 裁定）：
    免费额度未耗尽 or 余额 ≥ 所需 即放行（allowed）；
    拦截式落码 = generation.py `if not allowed and balance == 0`（429）+ `elif not credit_allowed and balance < required`（402，M2 required>0 后激活）。
    原 §2.3 OR 判定式 `(not 免费额度allowed or not 积分allowed) and balance < required` 为 M1 设计期保守措辞，
    已按 M1 终审 NIT 裁定收敛为上式（M1 required=0 时语义等价，M2 起 required>0 后按 §3.5.3 双分支执行）。
    单连接内同查 user_credits.balance（缺行视为 0）与 usage_log 当日计数（复用 check_quota 的 since 口径）。
    M2 扣减走 user_credits.version 乐观锁（§3.1 并发扣减定稿），M1 仅判定不扣减。
    """
    limit = settings.free_daily_limit
    since = _today_start_utc()
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    try:
        cursor = await conn.execute(
            "SELECT balance FROM user_credits WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        balance = row[0] if row else 0

        cursor = await conn.execute(
            "SELECT COUNT(*) AS cnt FROM usage_log WHERE user_id = ? AND generated_at >= ?",
            (user_id, since),
        )
        row = await cursor.fetchone()
        used = row[0] if row else 0
    finally:
        await conn.close()

    free_allowed = used < limit           # 当日免费额度未耗尽
    credit_allowed = balance >= required  # 余额可覆盖所需积分（M1 required=0 恒 True）
    allowed = free_allowed or credit_allowed
    return (allowed, balance, used, limit)


async def check_quota(user_id: str) -> Tuple[bool, int, int]:
    """
    异步额度检查：是否仍在每日免费额度内
    返回 (是否允许生成, 当日已用次数, 当日上限)
    """
    limit = settings.free_daily_limit
    since = _today_start_utc()
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    try:
        cursor = await conn.execute(
            "SELECT COUNT(*) AS cnt FROM usage_log WHERE user_id = ? AND generated_at >= ?",
            (user_id, since),
        )
        row = await cursor.fetchone()
        used = row[0] if row else 0
    finally:
        await conn.close()
    return (used < limit, used, limit)


def record_usage_sync(user_id: str, ip: Optional[str] = None) -> None:
    """同步写入一条 usage_log（供测试脚本使用）"""
    conn = get_db_sync()
    try:
        conn.execute(
            "INSERT INTO usage_log (user_id, generated_at, ip) VALUES (?, ?, ?)",
            (user_id, _today_start_utc(), ip),  # 占位，实际调用方传时间戳
        )
        conn.commit()
    finally:
        conn.close()


def record_usage(user_id: str, ip: Optional[str] = None) -> None:
    """同步写入一条 usage_log（当前时间戳）"""
    now = datetime.now(timezone.utc)
    conn = get_db_sync()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO usage_log (user_id, generated_at, ip) VALUES (?, ?, ?)",
            (user_id, now.strftime("%Y-%m-%d %H:%M:%S.%f"), ip),
        )
        conn.commit()
    finally:
        conn.close()
