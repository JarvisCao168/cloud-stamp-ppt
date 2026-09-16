"""
免费额度管理
基于 usage_log 表的每日生成次数限流（日级滑动窗口，按 user_id + 当日零点截断）
配置项 FREE_DAILY_LIMIT 控制上限，默认 10
"""
from datetime import datetime, timezone
from typing import Tuple, Optional

import asyncio

import aiosqlite

from .config import settings
from ..db import get_db_sync


def _today_start_utc() -> str:
    """当前UTC日期零点（用于日期键截断）"""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d") + " 00:00:00"


def estimate_required(mode: str, input_len: int, complexity: str = "auto") -> int:
    """
    M2 计费点折算纯函数（§3.5.1）：按 /create 请求入口的生成模式 + 输入字数 + 复杂度档位，
    折算本次应预扣的积分数 required（整数，单位=积分；整篇算一次，不按段落拆分）。

    路由映射（§3.5.1 表，M6-B 起档位折算公式加中文 ×1.2 保守系数）：
    - mode=quick + complexity=auto：≤500 字 → 1（LIGHT）；500 < 输入 ≤4000 → 3（MEDIUM）；
      4000 < 输入 ≤8000 → 5（HEAVY）；>8000 → 8（HEAVY ×1.5 封顶，R4）
    - mode=quick + complexity=multimodal（视觉反思/多模态）→ 6（MULTIMODAL，字数档位不参与）
    - mode=collaborative / full_control（M5-B 起按 input_len 档位折算，与 quick 同表，
      不再固定 0；M5 任务 B a525605 已移除两行 `return 0`）
    - 未知 mode 兜底 → 0（宁免扣错扣，M4 运营侧再校准）

    M6-B 中文系数（×1.2 保守值，落档位公式内，纯函数无副作用）：
    - 本函数入参为 input_len（int，字符数），无字符级信息可区分中/英占比
    - 按备案口径采用保守值 ×1.2 直接乘于档位基础值后向上取整（等价于全中文输入 ratio=1）
      （1→2，3→4，5→6，8→10，精确 ceiling，无浮点参与：ceil(1.2×base)=base+(base+4)//5）；
      若需按实际中文字符占比动态折算，需将入参从 input_len 改为 text（str），超出 M6-B 变更边界，不在此处实施
    - 变更边界：仅本函数档位折算公式；check_credits / generation.py 三分支 /
      record_usage / usage_log 主键与索引 / debit_credits 乐观锁结构 均零改动

    独立实现，不接 model_router 字段（§3.5.1 设计约束：model_router 只负责模型通道
    选择，不承担计费折算；§二 现状锚点 estimated_cost/estimated_tokens 字段无消费点，本函数
    入参 (mode: str, input_len: int, complexity: str = "auto") → 出参 int，纯函数无副作用）。
    """
    if complexity == "multimodal":
        return 6
    if input_len <= 500:
        base = 1
    elif input_len <= 4000:
        base = 3
    elif input_len <= 8000:
        base = 5
    else:
        base = 8
    # M6-B：×1.2 中文保守系数，ceiling 取整（整数运算 ceil(6×base/5) = base + (base + 4) // 5，
    # 无浮点参与，精确映射 1→2 / 3→4 / 5→6 / 8→10；multimodal 早返 6 不经档位公式不受影响）
    return base + (base + 4) // 5


def reserve_credit(
    user_id: str,
    required: int = 0,
    mode: str = "auto",
    session_id: Optional[str] = None,
) -> Tuple[bool, int]:
    """
    B1 预扣点（M4 协作/付费生成入口）：

    - mode="collaborative"：按 required 预扣积分；required<=0 时直接返回 (True, 0)，
      不触碰 DB，与 estimate_required 对 checkpoint 暂停态返回 0 的语义对齐。
    - mode="full_control"：同样按 required 预扣；unknown mode 兜底保持 required 原样，
      由 estimate_required 或上游计费折算负责决定 required 是否为 0。

    实现复用 debit_credits 的乐观锁扣减与流水写入，不改变三条硬约束：
    quota.py:23 函数体/签名、quota.py:57-107 乐观锁结构、record_usage INSERT OR REPLACE。
    """
    return debit_credits(user_id, required, session_id=session_id, reason=f"gen_{mode}")


def _now_utc_iso() -> str:
    """UTC ISO 时间戳（流水/updated_at 写入口径，与 reset_at 同 UTC 时区）"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


async def debit_credits(
    user_id: str, required: int, session_id: Optional[str] = None, reason: str = "gen"
) -> Tuple[bool, int]:
    """
    M2 预扣积分（§3.5.2，version 乐观锁并发扣减定稿，§3.1）
    返回 (成功, 新余额)；语义映射：
    - 余额不足 → (False, 当前余额)，调用方走 402
    - 账户行不存在（M1 不赠额，R5；required>0 时余额视为 0）→ (False, -1)，调用方 402 兜底
    - version 冲突重试 3 次仍失败 → (False, -2)，调用方 503（服务不可用，非用户侧错误）
    - 成功 → (True, 新余额)；流水 credit_ledger delta=-required，允许 session_id=NULL
      （预扣时点生成尚未开始，session_id 由生成成功后调用方补写）
    """
    if required <= 0:
        # M1 required=0 语义：扣减无意义，直接放行（与 §3.5.3 `if required > 0` 门控等价）
        return (True, 0)
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    for _ in range(3):
        conn = await aiosqlite.connect(db_path)
        try:
            cursor = await conn.execute(
                "SELECT version, balance FROM user_credits WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return (False, -1)
            old_version, balance = row[0], row[1]
            if balance < required:
                return (False, balance)
            # 原子更新（乐观锁定稿 SQL 形态，§3.1）：WHERE version=? 命中 0 行 = 版本已被并发推进
            # → 重试（退避固定 50ms 起步，非忙等；§3.5.2 Codex 工程核认提醒 ① 已吸收）
            cursor = await conn.execute(
                "UPDATE user_credits SET balance = ?, daily_cost = daily_cost + ?, "
                "version = version + 1, updated_at = ? WHERE user_id = ? AND version = ?",
                (balance - required, required, _now_utc_iso(), user_id, old_version),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                # 版本冲突：退避 50ms 后重读 version 重试（不忙等，§3.5.2 提醒 ①）
                await asyncio.sleep(0.05)
                continue
            await conn.execute(
                "INSERT INTO credit_ledger (user_id, delta, reason, session_id, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, -required, reason, session_id, _now_utc_iso()),
            )
            await conn.commit()
            return (True, balance - required)
        finally:
            await conn.close()
    return (False, -2)


async def refund_credits(
    user_id: str, required: int, session_id: Optional[str] = None, reason: str = "refund"
) -> bool:
    """
    M2 生成失败/中止退款（§3.5.2，乐观锁同 debit；流水 delta=+required，
    daily_cost 用 CASE WHEN 防负数（SQLite 无 GREATEST 标量函数，§3.5.2 勘误行））
    幂等去重（§3.5.2 提醒 ② 吸收）：同一流水号（session_id）重复调用不产生二次返还——
    先查 credit_ledger 中同 session_id + delta=+required 的既有流水，命中则直接返回 True；
    调用方未传 session_id（session_id=None）时不做去重，保持与 debit 相同语义
    账户行不存在或 3 次版本冲突均失败 → 返回 False（不抛异常，由调用方记日志，
    M4 运营看板告警，不影响生成响应）
    """
    if required <= 0:
        return True
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    # 幂等去重：同流水号（session_id）已有 delta=+required 的退款流水 → 直接返回成功
    if session_id is not None:
        conn = await aiosqlite.connect(db_path)
        try:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM credit_ledger WHERE user_id = ? AND session_id = ? "
                "AND delta = ? AND reason = 'refund'",
                (user_id, session_id, +required),
            )
            row = await cursor.fetchone()
            if row and row[0] > 0:
                return True
        finally:
            await conn.close()
    for _ in range(3):
        conn = await aiosqlite.connect(db_path)
        try:
            cursor = await conn.execute(
                "SELECT version FROM user_credits WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return False
            old_version = row[0]
            # SQLite 无 GREATEST 标量函数，用 CASE WHEN 等价写法防 daily_cost 负数
            cursor = await conn.execute(
                "UPDATE user_credits SET balance = balance + ?, "
                "daily_cost = CASE WHEN daily_cost - ? > 0 THEN daily_cost - ? ELSE 0 END, "
                "version = version + 1, updated_at = ? WHERE user_id = ? AND version = ?",
                (required, required, required, _now_utc_iso(), user_id, old_version),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                # 版本冲突：退避 50ms 后重读 version 重试（不忙等，§3.5.2 提醒 ①）
                await asyncio.sleep(0.05)
                continue
            await conn.execute(
                "INSERT INTO credit_ledger (user_id, delta, reason, session_id, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, +required, reason, session_id, _now_utc_iso()),
            )
            await conn.commit()
            return True
        finally:
            await conn.close()
    return False


async def update_credit_ledger_session_id(session_id: str, user_id: str, since_ts: str) -> bool:
    """
    M2 预扣流水 session_id 补写（§3.5.2 关键设计决策：预扣时点生成尚未开始，
    流水允许 session_id=NULL；生成成功后由调用方按 user_id + since_ts 窗口补写，
    命中 credit_ledger 最近一次 NULL session_id 流水）
    命中 0 行也返回 False，不抛异常
    """
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    conn = await aiosqlite.connect(db_path)
    try:
        cursor = await conn.execute(
            "UPDATE credit_ledger SET session_id = ? WHERE user_id = ? "
            "AND session_id IS NULL AND created_at >= ? AND delta < 0",
            (session_id, user_id, since_ts),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


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
    判定式定稿（§3.5.3 v0.2.3，M2 PR 1 落档版）：
    免费额度优先：free_allowed = used < limit；credit_allowed = balance ≥ required。
    - free_allowed = True → 直接放行，不扣积分（免费额度未耗尽时不额外消耗余额）
    - free_allowed = False and balance ≥ required → 放行 + 预扣 required
    - free_allowed = False and 0 < balance < required → 拦截 402（余额不足）
    - free_allowed = False and balance = 0 → 拦截 429（免费额度耗尽且无积分）
    拦截式落码 = generation.py `if not allowed and balance == 0`（429）
    + `if not credit_allowed and balance < required`（402，M2 required>0 后激活）。
    本定稿取代原 §2.3 OR 判定式 `(not 免费额度allowed or not 积分allowed) and balance < required`
    （M1 设计期保守措辞，required=0 时两者语义等价；M2 起按本定稿双分支执行）。
    单连接内同查 user_credits.balance（缺行视为 0）与 usage_log 当日计数（复用 check_quota 的 since 口径）。
    M2 扣减走 user_credits.version 乐观锁（§3.1 并发扣减定稿，见 debit_credits/refund_credits），
    M1 仅判定不扣减（required 固定 0，debit_credits 门控 `if required > 0` 不触发）。
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
