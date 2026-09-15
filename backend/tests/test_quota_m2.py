"""
M2 预扣点接入单测 9 组（§3.5.5 PR 1 验收）

测试基准：docs/phase4-plan.md §3.5（v0.2.3 设计落档）
覆盖范围：
  1. estimate_required 6 场景路由映射（quick/collaborative/full_control × 字数档 + multimodal）
  2. debit_credits 余额充足 → 成功扣减 + 流水写入 + version+1
  3. debit_credits 余额不足 → 失败，不写流水，version 不变
  4. refund_credits 正常退款 → 余额加回 + daily_cost 不出现负数（CASE WHEN 防负数）
  5. debit_credits 账户行不存在 → (False, -1)（402 兜底）
  6. debit_credits required=0 → (True, 0)（M1 语义，门控等价）
  7. update_credit_ledger_session_id 补写命中
  8. 并发 debit 2 请求恰 1 成功（乐观锁 version 竞争）
  9. 并发 402/503 边界（-2 仅在 3 次版本冲突均失败时触发，正常并发 2 请求重试 1 次内可命中）
"""
import asyncio
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

from app.core.quota import (
    estimate_required,
    debit_credits,
    refund_credits,
    update_credit_ledger_session_id,
)
from app.core.config import settings
from app.db import SCHEMA_SQL


# ── 辅助：创建临时测试 DB ──────────────────────────────────────────────────────

def _make_test_db(tmpdir: str) -> str:
    """在 tmpdir 创建含 user_credits + credit_ledger 的测试 DB，返回 DB 路径"""
    db_path = os.path.join(tmpdir, "test_quota_m2.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    return db_path


def _seed_credits(db_path: str, user_id: str, balance: int = 0, version: int = 0) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO user_credits "
        "(user_id, balance, daily_cost, last_cost_date, version, updated_at) "
        "VALUES (?, ?, 0, '1970-01-01', ?, ?)",
        (user_id, balance, version, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")),
    )
    conn.commit()
    conn.close()


def _read_balance(db_path: str, user_id: str):
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT balance FROM user_credits WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None


def _read_version(db_path: str, user_id: str):
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT version FROM user_credits WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None


def _ledger_rows(db_path: str, user_id: str):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT delta, reason, session_id FROM credit_ledger WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


# ── 1. estimate_required 路由映射（6 场景）────────────────────────────────────

def test_estimate_required_matrix():
    """
    §3.5.5 PR 1 单测组 1-6：estimate_required 6 场景覆盖
    覆盖：quick×auto（LIGHT/MEDIUM/HEAVY/HEAVY>8000 封顶）+ quick×multimodal + collaborative + full_control
    """
    # 组 1：LIGHT（≤500 字）
    assert estimate_required("quick", 100, "auto") == 1
    # 组 2：MEDIUM（500 < 输入 ≤4000）
    assert estimate_required("quick", 3000, "auto") == 3
    # 组 3：HEAVY 基础（4000 < 输入 ≤8000）
    assert estimate_required("quick", 5000, "auto") == 5
    # 组 4：HEAVY >8000 字 ×1.5 封顶 = 8
    assert estimate_required("quick", 8500, "auto") == 8
    # 组 5：MULTIMODAL（视觉反思）
    assert estimate_required("quick", 100, "multimodal") == 6
    # 组 6：checkpoint 暂停态不计费
    assert estimate_required("collaborative", 5000, "auto") == 0
    assert estimate_required("full_control", 5000, "auto") == 0
    # 边界：空输入（len=0）→ LIGHT 最低档
    assert estimate_required("quick", 0, "auto") == 1


# ── 2/3. debit_credits 余额充足 / 余额不足 ────────────────────────────────────

def test_debit_credits_sufficient_balance():
    """
    §3.5.5 单测组 7：debit_credits 余额充足 → (True, 新余额)，
    credit_ledger 写入 delta=-required，version +1
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "user-debit-ok", balance=100)

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            ok, new_balance = asyncio.run(
                debit_credits("user-debit-ok", 5, reason="gen_auto")
            )
            assert ok is True
            assert new_balance == 95
            # 余额确实更新
            assert _read_balance(db_path, "user-debit-ok") == 95
            assert _read_version(db_path, "user-debit-ok") == 1
            # 流水写入 delta=-5
            rows = _ledger_rows(db_path, "user-debit-ok")
            assert len(rows) == 1
            assert rows[0][0] == -5
            assert rows[0][1] == "gen_auto"


def test_debit_credits_insufficient_balance():
    """
    §3.5.5 单测组 8：debit_credits 余额不足 → (False, 当前余额)，
    不写流水，version 不变
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "user-debit-fail", balance=3)

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            ok, returned = asyncio.run(
                debit_credits("user-debit-fail", 5, reason="gen_auto")
            )
            assert ok is False
            assert returned == 3  # 返回当前余额，非负数（-1/-2 保留给特殊语义）
            # 流水未写入
            assert len(_ledger_rows(db_path, "user-debit-fail")) == 0
            assert _read_version(db_path, "user-debit-fail") == 0


def test_debit_credits_no_account_row():
    """
    §3.5.5：账户行不存在 → (False, -1)，402 兜底
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        # 不 seed，账户行不存在

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            ok, returned = asyncio.run(
                debit_credits("user-no-account", 5, reason="gen_auto")
            )
            assert ok is False
            assert returned == -1


def test_debit_credits_zero_required():
    """
    M1 required=0 语义：扣减无意义，直接 (True, 0)，不触碰 DB
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            ok, returned = asyncio.run(debit_credits("user-zero", 0))
            assert ok is True
            assert returned == 0
            assert _read_balance(db_path, "user-zero") is None  # 未写入任何行


# ── 4. refund_credits 正常退款 ────────────────────────────────────────────────

def test_refund_credits_normal():
    """
    §3.5.5 单测组 9：refund_credits 正常退款 → 余额加回，
    daily_cost 不出现负数（GREATEST(0, …)）
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "user-refund", balance=20)

        async def _scenario():
            # 先 debit 10（余额 20→10，daily_cost 0→10）
            await debit_credits("user-refund", 10, reason="gen_auto")
            # 再退款 10（余额 10→20，daily_cost GREATEST(0, 10-10)=0）
            return await refund_credits("user-refund", 10, reason="refund")

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            ok = asyncio.run(_scenario())
            assert ok is True
            # 余额加回
            assert _read_balance(db_path, "user-refund") == 20
            # daily_cost = GREATEST(0, 10-10) = 0，非负
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT daily_cost FROM user_credits WHERE user_id = ?", ("user-refund",)
            ).fetchone()
            conn.close()
            assert row[0] == 0
            # 流水 delta=+10 已写入
            rows = _ledger_rows(db_path, "user-refund")
            assert any(r[0] == 10 for r in rows)


def test_refund_credits_idempotent_by_session_id():
    """
    §3.5.2 提醒 ②：refund_credits 幂等按流水号（session_id）去重——
    同一 session_id 重复调用 refund 两次，余额只加回一次（不双重返还）
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "user-refund-idem", balance=50)

        async def _scenario():
            # 先 debit 10（余额 50→40）
            await debit_credits("user-refund-idem", 10, session_id="sess-idem", reason="gen_auto")
            # 第一次 refund（session_id="sess-idem"）→ 余额 40→50
            ok1 = await refund_credits("user-refund-idem", 10, session_id="sess-idem", reason="refund")
            assert ok1 is True
            bal_mid = _read_balance(db_path, "user-refund-idem")
            # 第二次同 session_id 重复 refund → 幂等短路，余额不变
            ok2 = await refund_credits("user-refund-idem", 10, session_id="sess-idem", reason="refund")
            assert ok2 is True
            return bal_mid, _read_balance(db_path, "user-refund-idem")

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            bal_after_first, bal_after_second = asyncio.run(_scenario())
            assert bal_after_first == 50   # 第一次 refund 后余额加回
            assert bal_after_second == 50   # 幂等：第二次同 session_id refund 不再加回
            # 流水：debit 1 条 delta=-10 + refund 1 条 delta=+10（第二次短路不写流水）
            rows = _ledger_rows(db_path, "user-refund-idem")
            assert len(rows) == 2
            assert sum(r[0] for r in rows) == 0


def test_refund_credits_no_account():
    """账户行不存在 → refund 返回 False，不抛异常"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            ok = asyncio.run(refund_credits("user-missing", 5))
            assert ok is False


def test_refund_credits_zero():
    """required=0 → 直接 True（门控等价，不触碰 DB）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            ok = asyncio.run(refund_credits("user-any", 0))
            assert ok is True


# ── 7. update_credit_ledger_session_id 补写 ──────────────────────────────────

def test_update_ledger_session_id_backfill():
    """
    §3.5.2：预扣流水 session_id=NULL，生成成功后补写命中
    命中 1 行（session_id 由 NULL → 真实值）
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "user-backfill", balance=50)

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            asyncio.run(debit_credits("user-backfill", 5, reason="gen_auto"))
            # 此时流水 session_id 为 NULL
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            ok = asyncio.run(
                update_credit_ledger_session_id("sess-12345", "user-backfill", ts)
            )
            assert ok is True
            # 流水 session_id 已补写
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT session_id FROM credit_ledger WHERE user_id = ?",
                ("user-backfill",),
            ).fetchone()
            conn.close()
            assert row[0] == "sess-12345"


# ── 8/9. 并发 debit 乐观锁竞争 ───────────────────────────────────────────────

def test_debit_serial_second_fails():
    """
    §3.5.5：串行 2 请求（余额 10，各扣 10）→ 第 1 个成功（余额 10→0），第 2 个余额不足 (False, 0)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "user-concurrent", balance=10)

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            # 第 1 个：余额 10，required 10 → 成功，余额 0
            ok1, nb1 = asyncio.run(debit_credits("user-concurrent", 10, reason="gen_1"))
            assert ok1 is True
            assert nb1 == 0
            assert len(_ledger_rows(db_path, "user-concurrent")) == 1
            # 第 2 个：余额 0，required 10 → 余额不足
            ok2, ret2 = asyncio.run(debit_credits("user-concurrent", 10, reason="gen_2"))
            assert ok2 is False
            assert ret2 == 0
            # 流水仍 1 条（第 2 个未写入）
            assert len(_ledger_rows(db_path, "user-concurrent")) == 1


def test_debit_concurrent_true_race():
    """
    并发 2 请求恰 1 成功（§3.5.5 单测组 8/9：乐观锁 version 竞争）
    余额 30，2 并发各扣 20 → 恰好 1 成功（余额 30-20=10），1 个余额不足 402
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = _make_test_db(tmpdir)
        _seed_credits(db_path, "user-race", balance=30)

        async def _run_debit(n: int):
            return await debit_credits("user-race", 20, reason=f"gen_{n}")

        async def _gather():
            return await asyncio.gather(_run_debit(1), _run_debit(2))

        with patch.object(settings, "database_url", f"sqlite+aiosqlite:///{db_path}"):
            results = asyncio.run(_gather())

        oks = [r for r in results if r[0]]
        assert len(oks) == 1, f"预期恰好 1 个成功，实际 {len(oks)}：{results}"
        assert results[0][0] != results[1][0], "一成功一失败"
        # 余额 30-20=10
        assert _read_balance(db_path, "user-race") == 10
        # 流水 1 条 delta=-20
        assert len(_ledger_rows(db_path, "user-race")) == 1
        # 失败方返回当前余额 10（≥0，402 语义）
        fail_ret = results[0][1] if not results[0][0] else results[1][1]
        assert fail_ret >= 0, f"失败方返回 {fail_ret}，应为当前余额（≥0）"
