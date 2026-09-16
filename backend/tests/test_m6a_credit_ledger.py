# M6-A credit_ledger 流水断言实测（Hermes seq 19 终锚定版：3 场景 + 3 断言）
#
# 驱动口径同 test_presence_b3.py B3 骨架：patch generation 模块内判定函数
# （check_quota / check_credits）+ TestClient 直驱 POST /create，
# 拦截场景（①②）不 mock reserve_credit——拦截在 :776-782 早于预扣门控 :789，
# 真实 reserve_credit 不被调用，credit_ledger 零增量断言 = 拦截前后行数 diff=0。
# 放行场景（③）不 mock reserve_credit，真实 debit_credits 写流水到临时测试 DB；
# start_generation mock 为确定性响应（避免真实 LLM 调用），update_credit_ledger_session_id
# 真实执行 → 流水 session_id 补写命中定位式断言。
#
# 断言口径（终锚定版锁定）：
#   ① 协作（collaborative）余额不足 → 402 + credit_ledger 行数 diff=0
#   ② 付费（full_control）余额不足 → 402 + credit_ledger 行数 diff=0
#   ③ 余额充足 → 200（现码同步 return，非 202）+ 定位式断言
#      WHERE user_id=? AND delta=-required AND reason LIKE 'gen_%' AND created_at >= ?
#      判 count==1（created_at 窗口防旧流水干扰；预写 reason='test' 旧流水天然被过滤）
#
# DB 隔离：复用 test_quota_m2.py 临时 DB 辅助 + patch settings.database_url，
# 全程不碰主库 backend/yunzhang.db；每场景独立 user_id（新 user_id + 单请求口径，
# reserve_credit 无重放幂等——M6 终审勘误②）。


import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.routes import generation
from app.core.config import settings
from app.db import SCHEMA_SQL
from app.main import app
from app.api.routes.generation import GenerationResponse


def _make_test_db(tmpdir: str) -> str:
    """在 tmpdir 创建全量表结构测试 DB，返回 DB 路径（口径同 test_quota_m2._make_test_db）"""
    db_path = os.path.join(tmpdir, "test_m6a_credit_ledger.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    return db_path


def _seed_credits(db_path: str, user_id: str, balance: int, version: int = 0) -> None:
    """seed user_credits 账户行（口径同 test_quota_m2._seed_credits）"""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO user_credits "
        "(user_id, balance, daily_cost, last_cost_date, version, updated_at) "
        "VALUES (?, ?, 0, '1970-01-01', ?, ?)",
        (user_id, balance, version, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")),
    )
    conn.commit()
    conn.close()


def _count_ledger(db_path: str, user_id: str) -> int:
    """credit_ledger 行数快照（M6-A 拦截断言：拦截前后 diff=0）"""
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT COUNT(*) FROM credit_ledger WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row[0]


def _locate_ledger(db_path: str, user_id: str, required: int, since_ts: str) -> int:
    """
    M6-A 放行定位式断言（终锚定版）：
    WHERE user_id=? AND delta=-required AND reason LIKE 'gen_%' AND created_at >= ?
    判 count==1（created_at 窗口防旧流水干扰）
    """
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT COUNT(*) FROM credit_ledger "
        "WHERE user_id = ? AND delta = ? AND reason LIKE ? AND created_at >= ?",
        (user_id, -required, "gen_%", since_ts),
    ).fetchone()
    conn.close()
    return row[0]


def _seed_stale_ledger(db_path: str, user_id: str) -> str:
    """
    预写 1 条 reason='test' 旧流水（created_at 故意设为 2020 年 1 月 1 日），
    验证定位式断言的 created_at >= T0 窗口过滤效果；返回 T0（测试起始时刻 UTC ISO，
    早于放行流水写入时刻、晚于旧流水时刻）
    """
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO credit_ledger (user_id, delta, reason, session_id, created_at) "
        "VALUES (?, ?, 'test', NULL, '2020-01-01T00:00:00')",
        (user_id, 999),
    )
    conn.commit()
    conn.close()
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ── 判定函数 mock（驱动口径同 test_presence_b3.py B3 骨架）────────────────────

def _mock_quota_exhausted(user_id):
    """免费额度耗尽 → allowed=False（used=limit=10，429/402 域内，非 429）"""
    async def _inner(uid):
        return (False, 10, 10)
    return _inner


async def _mock_check_credits_402(user_id, required=0):
    """余额 3 < required 5 → credit_allowed=False（402 拦截式域，:776-782 命中）"""
    return (False, 3, 10, 10)


# ═══════════════════════════════════════════════════════════════════════════
# 场景 ① 协作（collaborative）余额不足 → 402 + credit_ledger 零增量
# ═══════════════════════════════════════════════════════════════════════════

def test_m6a_collaborative_insufficient_402_ledger_zero():
    """
    M6-A 场景 ①：mode=collaborative + 5000 字 → estimate_required=5（M5 档位折算，
    非 M4 冻结的 0）；余额 3 < 5 → 402 拦截式命中（generation.py:776-782）。
    拦截在预扣门控（:789）之前，真实 reserve_credit 不被调用 →
    credit_ledger 行数 diff=0（零增量断言）。
    """
    generation._collab_presence.clear()
    generation._collab_subscribers.clear()
    generation._collab_event_log.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "m6a-collab-402", balance=3)
        before = _count_ledger(db_path, "m6a-collab-402")

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"), \
             patch.object(generation, "check_quota", new=_mock_quota_exhausted("m6a-collab-402")), \
             patch.object(generation, "check_credits", new=_mock_check_credits_402), \
             patch.object(generation, "record_usage", new=lambda *a, **k: None), \
             TestClient(app) as client:
            resp = client.post(
                "/api/generation/create",
                json={
                    "user_input": "字" * 5000,  # collaborative×5000 字 → required=5（HEAVY 档）
                    "mode": "collaborative",
                    "user_id": "m6a-collab-402",
                },
            )

        assert resp.status_code == 402
        body = resp.json()
        assert body["code"] == "insufficient_credits"
        assert body["credits"]["balance"] == 3
        assert body["credits"]["required"] == 5  # M5 档位折算（M4 为 0，行为冻结已解除）

        # 零增量断言：拦截路径不写流水（before 恒为 0，diff 必须 = 0）
        assert before == 0
        after = _count_ledger(db_path, "m6a-collab-402")
        assert after - before == 0, f"402 拦截后 credit_ledger 增量 {after - before}（预期 0）"


# ═══════════════════════════════════════════════════════════════════════════
# 场景 ② 付费（full_control）余额不足 → 402 + credit_ledger 零增量
# ═══════════════════════════════════════════════════════════════════════════

def test_m6a_full_control_insufficient_402_ledger_zero():
    """
    M6-A 场景 ②：mode=full_control + 5000 字 → estimate_required=5；
    余额 3 < 5 → 402 拦截式命中。零增量断言同场景 ①。
    """
    generation._collab_presence.clear()
    generation._collab_subscribers.clear()
    generation._collab_event_log.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "m6a-fullctrl-402", balance=3)
        before = _count_ledger(db_path, "m6a-fullctrl-402")

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"), \
             patch.object(generation, "check_quota", new=_mock_quota_exhausted("m6a-fullctrl-402")), \
             patch.object(generation, "check_credits", new=_mock_check_credits_402), \
             patch.object(generation, "record_usage", new=lambda *a, **k: None), \
             TestClient(app) as client:
            resp = client.post(
                "/api/generation/create",
                json={
                    "user_input": "字" * 5000,  # full_control×5000 字 → required=5
                    "mode": "full_control",
                    "user_id": "m6a-fullctrl-402",
                },
            )

        assert resp.status_code == 402
        body = resp.json()
        assert body["code"] == "insufficient_credits"
        assert body["credits"]["balance"] == 3
        assert body["credits"]["required"] == 5

        assert before == 0
        after = _count_ledger(db_path, "m6a-fullctrl-402")
        assert after - before == 0, f"402 拦截后 credit_ledger 增量 {after - before}（预期 0）"


# ═══════════════════════════════════════════════════════════════════════════
# 场景 ③ 余额充足 → 放行 + 定位式流水断言 count==1
# ═══════════════════════════════════════════════════════════════════════════

async def _mock_start_generation_sufficient(request):
    """M6-A 场景 ③：start_generation mock（避免真实 LLM 调用），确定性 session_id"""
    return GenerationResponse(
        session_id="m6a-ok-sess",
        status="completed",
        message="M6-A 场景③ 放行确定性响应",
        data={},
    )


async def _mock_check_credits_sufficient(user_id, required=0):
    """余额 100 ≥ required 5 → credit_allowed=True（跳过 402 拦截式，进入预扣门控）"""
    return (True, 100, 10, 10)


def test_m6a_sufficient_pass_located_ledger_one():
    """
    M6-A 场景 ③：免费额度耗尽（used=10/10）+ 余额 100 ≥ required=5 →
    402 拦截式不命中（:776 跳过），进入预扣门控（:789），真实 reserve_credit
    写流水（reason=gen_quick，delta=-5，session_id 补写 m6a-ok-sess）。
    响应 200（现码同步 return GenerationResponse，非 202 queued——M6 终审勘误① 现码口径）。
    定位式断言：WHERE user_id=? AND delta=-5 AND reason LIKE 'gen_%' AND created_at >= ?
    判 count==1；预写 reason='test' 旧流水（created_at=2020）被窗口过滤。
    """
    generation._collab_presence.clear()
    generation._collab_subscribers.clear()
    generation._collab_event_log.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "m6a-ok", balance=100)
        t0 = _seed_stale_ledger(db_path, "m6a-ok")  # 预写旧流水，返回窗口下界

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"), \
             patch.object(generation, "check_quota", new=_mock_quota_exhausted("m6a-ok")), \
             patch.object(generation, "check_credits", new=_mock_check_credits_sufficient), \
             patch.object(generation, "record_usage", new=lambda *a, **k: None), \
             patch.object(
                 generation.generation_service,
                 "start_generation",
                 new=lambda request: _mock_start_generation_sufficient(request),
             ), \
             TestClient(app) as client:
            resp = client.post(
                "/api/generation/create",
                json={
                    "user_input": "字" * 5000,  # quick×5000 字 → required=5
                    "mode": "quick",
                    "user_id": "m6a-ok",
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "m6a-ok-sess"  # 放行成功 + 流水 session_id 补写命中

        # 定位式断言（终锚定版）：count==1，旧流水（reason='test', 2020）被窗口过滤
        count = _locate_ledger(db_path, "m6a-ok", required=5, since_ts=t0)
        assert count == 1, f"定位式断言 count={count}（预期 1；旧流水须被 created_at >= {t0} 过滤）"
