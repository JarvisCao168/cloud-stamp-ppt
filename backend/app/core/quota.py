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
