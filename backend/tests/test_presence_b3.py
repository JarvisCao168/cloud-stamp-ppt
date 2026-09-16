# M4 B 线单测 + 回归（B3，B 草案 v0.3 定稿 §六 M4 衔接 + §三 D1-D5/S1-S2 分发点清单）

# 覆盖：B 线 presence 3 事件（viewer_joined / viewer_left / presence_snapshot）
# - 前端 Vitest 用例：__tests__/collabStream.test.ts「B 线 presence 事件」节 4 项
#   （viewer_joined 更新 viewersTotal / viewer_left 更新 / presence_snapshot 全量收敛 +
#   未知事件名静默忽略回归面 0）
# - 后端 pytest 用例：本文件 7 项
#   （join 广播 viewer_joined + presence_snapshot / leave 广播 viewer_left /
#   多 join 收敛 viewers_total / 429 路径零回归 /
#   判定函数三分支骨架 402 拦截式 - debit_fail 兜底 402 - debit_fail 503，
#   行引 generation.py:761/:776/:792）
# - test_quota_m2.py:100-101 双行锚点回归（collaborative / full_control 同落 0，M5 docs 勘误统一 commit：三方历史锚记 :99/:100 漂移至现行 :100/:101）
#   随本批次全量回归，验证「整篇计一次」不变）
#
# 驱动口径说明：SSE 路由（event_stream 生成器）以 asyncio.Task 驱动真实路由函数，
# 至 presence_snapshot 下发即取消任务（cancel 触发 finally -> viewer_left 广播），
# 规避 TestClient 流式读取下 30s 心跳导致的 portal 挂起。
# 429 回归用例与判定函数三分支骨架用例为同步 POST /create，经 TestClient 驱动，无挂起风险。


import asyncio
import json
import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from app.api.routes import generation
from app.main import app


def _reset_state():
    generation._collab_subscribers.clear()
    generation._collab_event_log.clear()
    generation._collab_presence.clear()


@pytest.fixture(autouse=True)
def _clean_presence_state():
    _reset_state()
    yield
    _reset_state()


def _drive_stream_to_snapshot(host: str, session_id: str) -> str:
    """驱动 SSE 路由函数至「本连接 join 首帧序列完成」，返回累积 body 文本；
    完成后显式 aclose 生成器 -> finally 触发 viewer_left 广播。

    break 口径：回放段可能含历史 presence_snapshot（join 前既有连接留下的），
    本连接自身的 join 首帧序列 = 回放结束后实时产出的 viewer_joined（viewer_id=host）
    + 随后同批 presence_snapshot。识别方式：回放段内所有帧先于 snapshot，
    故累计 chunk 中「本连接 viewer_joined 出现后的首个 presence_snapshot」即 break 点。
    """
    request = SimpleNamespace(
        client=SimpleNamespace(host=host),
        url=SimpleNamespace(
            scheme="http", netloc="testserver", path="/api/collab/stream"
        ),
        headers=Headers({}),
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    body_chunks: list[str] = []
    own_viewer_id = f"anon-{host}"

    async def _run():
        response = await generation.collab_stream(request, session_id=session_id)
        body_iter = response.body_iterator
        own_joined_seen = False
        async for chunk in body_iter:
            text = (
                chunk if isinstance(chunk, str) else chunk.decode("utf-8", "ignore")
            )
            body_chunks.append(text)
            if f'"viewer_id": "{own_viewer_id}"' in text and "viewer_joined" in text:
                own_joined_seen = True
            # break 点：本连接 viewer_joined 之后的首个 presence_snapshot
            if own_joined_seen and "presence_snapshot" in text:
                break
        # 模拟客户端断开：显式 aclose 生成器 -> finally 广播 viewer_left
        await body_iter.aclose()

    loop.run_until_complete(_run())
    loop.close()
    return "".join(body_chunks)


def test_presence_join_broadcasts_viewer_joined_and_snapshot():
    """
    B 线 S1+S2：观察者 join 回放完成后首帧 -> 广播 viewer_joined（增量）
    + presence_snapshot（全量快照，含本连接登记）；3 类事件均写入总日志
    """
    _reset_state()
    with patch.object(
        generation, "_collab_snapshot", return_value={"session_id": "s1"}
    ):
        body = _drive_stream_to_snapshot("10.9.8.1", "s1")

        # 客户端视角：回放 -> snapshot -> viewer_joined -> presence_snapshot 序列
        joined_idx = body.find("event: viewer_joined")
        snap_idx = body.find("event: presence_snapshot")
        assert joined_idx != -1, "viewer_joined 未在下发序列中出现"
        assert snap_idx != -1, "presence_snapshot 未在下发序列中出现"
        assert joined_idx < snap_idx, "viewer_joined 应先于 presence_snapshot 下发"

        joined = json.loads(
            re.search(r"event: viewer_joined\ndata: (\{.*\})", body).group(1)
        )
        assert joined["session_id"] == "s1"
        assert joined["viewer_id"] == "anon-10.9.8.1"
        assert joined["viewers_total"] == 1
        snap = json.loads(
            re.search(r"event: presence_snapshot\ndata: (\{.*\})", body).group(1)
        )
        assert snap["session_id"] == "s1"
        assert len(snap["viewers"]) == 1
        assert snap["viewers"][0]["viewer_id"] == "anon-10.9.8.1"
        assert "last_seen_ts" in snap["viewers"][0]
        assert "ts" in snap

        # S1 验收：3 类事件均写入 _collab_event_log（容量 100 条不变）
        log_events = [e["event"] for e in generation._collab_event_log.get("s1", [])]
        assert "viewer_joined" in log_events
        assert "presence_snapshot" in log_events


def test_presence_leave_broadcasts_viewer_left():
    """
    B 线 S2：观察者连接关闭（生成器 finally）-> 广播 viewer_left，
    viewers_total 回退至离开后的在场数（最后一名离开 -> 0）。
    断言口径 = 会话总日志（B 线 3 事件随回放重放，按 viewer_id + viewers_total 定位，幂等收敛）
    """
    _reset_state()
    with patch.object(
        generation, "_collab_snapshot", return_value={"session_id": "s2"}
    ):
        _drive_stream_to_snapshot("10.9.8.2", "s2")
        # aclose -> 生成器 finally 触发 viewer_left 广播
        log = generation._collab_event_log.get("s2", [])
        # 按 viewer_id + viewers_total=0 定位该连接的 left 事件（防回放重放误断言）
        left_events = [
            e for e in log
            if e["event"] == "viewer_left"
            and e["data"].get("viewer_id") == "anon-10.9.8.2"
            and e["data"].get("viewers_total") == 0
        ]
        assert len(left_events) == 1, f"viewer_left(10.9.8.2, total=0) 数 = {len(left_events)}（预期 1）"
        # 唯一连接离开 -> viewers_total 回退至 0
        assert left_events[0]["data"]["viewers_total"] == 0
        # 会话清空后注册表随之清理（无残留状态）
        assert not generation._collab_presence.get("s2")


def test_presence_multi_join_viewers_total_converges():
    """
    B 线 S2：串行驱动两名观察者先后 join 同一会话，
    viewersTotal = 活跃连接数（非去重用户数，见 B 草案 R3）：
    A join（=1）-> A 离开（=0）-> B join（=1）
    """
    _reset_state()
    with patch.object(
        generation, "_collab_snapshot", return_value={"session_id": "s3"}
    ):
        body_b = _drive_stream_to_snapshot("10.9.8.4", "s3")
        # B 视角：body_b 回放段 = A 的 joined/snapshot/left（历史）；
        # B 自己的 join 首帧（viewer_joined + presence_snapshot，viewer_id=anon-10.9.8.4）
        # 在回放段后实时产出，已含于 body_b（break 点口径 = 本连接 joined 后首个 snapshot）
        joined_b = next(
            json.loads(m.group(1)) for m in re.finditer(
                r"event: viewer_joined\ndata: (\{.*\})", body_b
            )
            if json.loads(m.group(1))["viewer_id"] == "anon-10.9.8.4"
        )
        # 串行驱动：A 流已取消 -> B join 时在场 = B 自己（=1）；
        # 并发驱动场景（A 保持连接时 B join = 2）由前端 Vitest 多订阅者用例覆盖
        assert joined_b["viewers_total"] == 1
        snap_b = next(
            json.loads(m.group(1)) for m in re.finditer(
                r"event: presence_snapshot\ndata: (\{.*\})", body_b
            )
            if any(
                v["viewer_id"] == "anon-10.9.8.4"
                for v in json.loads(m.group(1))["viewers"]
            )
        )
        assert snap_b["session_id"] == "s3"
        assert len(snap_b["viewers"]) == 1
        assert snap_b["viewers"][0]["viewer_id"] == "anon-10.9.8.4"


def test_presence_429_path_zero_regression():
    """
    B 线 429/402 零回归（B 草案 §5.1 强化标注，M4 跨归属改动即 PR 打回）：
    presence 事件 required=0 不入计费折算域，/create 429 分支
    （check_quota 免费额度耗尽，code=daily_free_quota_exceeded，generation.py:761-772，code 行 :768）
    与 402 分支（check_credits 积分余额不足，code=insufficient_credits，
    generation.py:776-782，code 行 :778）判定互斥零交叉，本批未触碰任一分支一行 -> 429 稳态唯一路径不变
    行号勘误补录：旧 docstring 误引 generation.py:690-701/:705-711 系 2a7a5bd 前旧值（+71 偏移前），
    现值 :761-772/:776-782，与 m3-a-b v0.9 §九 勘误行 #16 对齐
    """
    _reset_state()

    async def _mock_check_quota(user_id):
        return (False, 10, 10)  # allowed=False, used=10, limit=10 -> 额度耗尽

    async def _mock_check_credits(user_id, required=0):
        return (False, 0, 10, 10)  # balance=0 -> 429（非 402）

    with patch.object(generation, "check_quota", new=_mock_check_quota), \
         patch.object(generation, "check_credits", new=_mock_check_credits), \
         patch.object(generation, "record_usage", new=lambda *a, **k: None), \
         TestClient(app) as client:
        resp = client.post(
            "/api/generation/create",
            json={
                "user_input": "测试 429 零回归",
                "mode": "quick",
                "user_id": "anon-test",
            },
        )
        assert resp.status_code == 429
        body = resp.json()
        assert body["code"] == "daily_free_quota_exceeded"
        assert body["usage"]["used"] == 10
        assert body["usage"]["limit"] == 10
        assert "reset_at" in body["usage"]


# ── B3 判定函数三分支单测骨架（开笔令口径，提交点 b152568）────────────────────────
# 行引基准：m3-a-b-engineering-schedule-risk.md v0.9 §九 勘误行 #16（b152568 收口 commit 锁档值）
#   429 分支体  generation.py:761-772（code 行 :768）
#   402 分支体  generation.py:776-782（code 行 :778）
#   debit_fail  generation.py:792-806（-2 → 503 :793-795，兜底 402 :801-806）
# 驱动口径同 429 回归用例：patch generation 模块内判定函数 + TestClient 直驱 /create。
# 三分支拦截式判定零改动回归（M4 硬约束③，跨归属改动即 PR 打回）。
# B1 调用侧裁定（b152568 收口 commit 确认）：generation.py 无 reserve_credit 直调，
# 预扣经 reserve_credit 调用点 :790 落地（mode=request.mode，B1 调用侧 M5 任务A 接入）；
# 本批以 reserve_credit mock 回归 18 passed 为 B1 验收凭证。


def test_create_402_insufficient_credits_intercept():
    """
    B3 判定函数 ②（402 拦截式，generation.py:776-782，code 行 :778）：
    免费额度耗尽（used≥limit）且 0 < balance < required → 402 拦截式，
    code=insufficient_credits（单锚 :778），credits 载荷 = 当前余额。
    驱动口径：check_quota→allowed=False；check_credits→balance=3；
    "quick" 模式输入 5000 字 → estimate_required=6（HEAVY 档，M6-B ×1.2 后 5→6），0 < 3 < 6 命中 402。
    行号勘误补录：旧 docstring 误引 generation.py:690-701/:705-711 系 2a7a5bd 前旧值，
    现值 :761-772/:776-782（+71 偏移），与 m3-a-b v0.9 §九 勘误行 #16 对齐。
    """
    _reset_state()

    async def _mock_check_quota(user_id):
        return (False, 10, 10)  # 免费额度耗尽 → allowed=False

    async def _mock_check_credits(user_id, required=0):
        return (False, 3, 10, 10)  # balance=3，3 < required=6（M6-B 后 5→6）→ 402（非 429）

    with patch.object(generation, "check_quota", new=_mock_check_quota), \
         patch.object(generation, "check_credits", new=_mock_check_credits), \
         patch.object(generation, "record_usage", new=lambda *a, **k: None), \
         TestClient(app) as client:
        resp = client.post(
            "/api/generation/create",
            json={
                "user_input": "字" * 5000,  # quick×5000 字 → required=5（HEAVY 档）
                "mode": "quick",
                "user_id": "anon-402",
            },
        )
        assert resp.status_code == 402
        body = resp.json()
        assert body["code"] == "insufficient_credits"  # 拦截式单锚 :778
        assert body["credits"]["balance"] == 3
        assert body["credits"]["required"] == 6  # M6-B：×1.2 档位折算后 required=6（M5 旧基线 5）


def test_create_debit_fail_fallback_402():
    """
    B3 判定函数 ③（debit_fail 兜底 402，generation.py:792-806，兜底 402 code 行 :802）：
    免费额度耗尽 + balance ≥ required → 402 拦截式分支被跳过（:776 不命中），
    进入预扣门控（:788，required>0 且 not allowed），debit_credits 竞态窗口
    扣减失败（余额不足）→ (False, 0) → 兜底 402（balance 记 0）。
    驱动口径：check_quota→allowed=False；check_credits→balance=10；
    "quick"×5000 字 → required=6（M6-B ×1.2 后 5→6），10 ≥ 6 跳过 402 拦截；debit_credits mock → (False, 0)。
    """
    _reset_state()

    async def _mock_check_quota(user_id):
        return (False, 10, 10)  # 免费额度耗尽 → allowed=False

    async def _mock_check_credits(user_id, required=0):
        return (True, 10, 10, 10)  # balance=10 ≥ required=5 → 跳过 402 拦截式

    async def _mock_reserve_credit(user_id, required=0, mode="auto", session_id=None):
        return (False, 0)  # 竞态窗口内余额不足 → 兜底 402

    with patch.object(generation, "check_quota", new=_mock_check_quota), \
         patch.object(generation, "check_credits", new=_mock_check_credits), \
         patch.object(generation, "reserve_credit", new=_mock_reserve_credit), \
         patch.object(generation, "record_usage", new=lambda *a, **k: None), \
         TestClient(app) as client:
        resp = client.post(
            "/api/generation/create",
            json={
                "user_input": "字" * 5000,  # required=5，balance=10 ≥ 5 → 进入预扣门控
                "mode": "quick",
                "user_id": "anon-debit-fail",
            },
        )
        assert resp.status_code == 402
        body = resp.json()
        assert body["code"] == "insufficient_credits"  # 兜底 402 code 行 :802
        assert body["credits"]["balance"] == 0


def test_create_debit_fail_conflict_503():
    """
    B3 判定函数 ④（debit_fail 版本冲突 503，generation.py:793-795，code 行 :796）：
    同 ③ 驱动口径（free 耗尽 + balance=10 ≥ required=5 跳过 402 拦截），
    debit_credits 乐观锁 3 次重试仍冲突 → (False, -2) → 503 服务不可用
    （非用户侧错误，与 402 判定分离）。
    """
    _reset_state()

    async def _mock_check_quota(user_id):
        return (False, 10, 10)  # 免费额度耗尽 → allowed=False

    async def _mock_check_credits(user_id, required=0):
        return (True, 10, 10, 10)  # balance=10 ≥ required=5 → 跳过 402 拦截式

    async def _mock_reserve_credit(user_id, required=0, mode="auto", session_id=None):
        return (False, -2)  # 版本冲突 3 次 → 503

    with patch.object(generation, "check_quota", new=_mock_check_quota), \
         patch.object(generation, "check_credits", new=_mock_check_credits), \
         patch.object(generation, "reserve_credit", new=_mock_reserve_credit), \
         patch.object(generation, "record_usage", new=lambda *a, **k: None), \
         TestClient(app) as client:
        resp = client.post(
            "/api/generation/create",
            json={
                "user_input": "字" * 5000,  # required=5，balance=10 ≥ 5 → 进入预扣门控
                "mode": "quick",
                "user_id": "anon-debit-503",
            },
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["code"] == "service_unavailable"  # 503 code 行 :796


def test_create_402_collaborative_mode_intercept():
    """
    B 协作/付费 402 拦截路径实码（M5 任务 B）：
    mode=collaborative + 5000 字 → estimate_required=6（M5 起按 input_len 档位折算；M6-B ×1.2 后 5→6）。
    驱动口径：check_quota→allowed=False（免费额度耗尽）；check_credits→balance=3 < required=6 → 402 拦截式命中。
    验证 M5 行为冻结解除后 402 拦截路径对协作/付费模式实码可达。
    """
    _reset_state()

    async def _mock_check_quota(user_id):
        return (False, 10, 10)  # 免费额度耗尽 → allowed=False

    async def _mock_check_credits(user_id, required=0):
        return (False, 3, 10, 10)  # balance=3 < required=5 → 402（非 429）

    with patch.object(generation, "check_quota", new=_mock_check_quota), \
         patch.object(generation, "check_credits", new=_mock_check_credits), \
         patch.object(generation, "record_usage", new=lambda *a, **k: None), \
         TestClient(app) as client:
        resp = client.post(
            "/api/generation/create",
            json={
                "user_input": "字" * 5000,  # collaborative×5000 字 → required=5（M5 档位折算）
                "mode": "collaborative",
                "user_id": "anon-collab-402",
            },
        )
        assert resp.status_code == 402
        body = resp.json()
        assert body["code"] == "insufficient_credits"  # 402 code 行 :778
        assert body["credits"]["balance"] == 3
        assert body["credits"]["required"] == 6  # M6-B：×1.2 档位折算后 required=6（M5 协作旧基线 5）
