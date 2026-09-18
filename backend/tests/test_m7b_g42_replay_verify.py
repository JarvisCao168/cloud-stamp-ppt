# M7-B G4-2: 断线回放 E2E 回归 + 收尾验证项（docs/m7-plan.md v0.2 sec2 content 2/3）
# 基线锚点：HEAD 763d7e9（G4-1 出账），门禁 ≥48/0（42 baseline + G4-1 新增 6）
# 本批次新增 6 条（disconnection replay E2E regression + final verification items），
# 全量 pytest ≥ 54 passed / 0 failed，test_presence_b3.py 零触碰。
# zero-diff redline: quota.py / db.py / generation.py /create 3-branch
# (check_quota :836 / check_credits :842 / reserve_credit :874 / record_usage :907)
# untouched; this file adds test-only coverage.
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from app.api.routes import generation
from app.core.auth import create_session, destroy_session, resolve_user_id_from_session
from app.main import app


def _reset_state():
    generation._collab_subscribers.clear()
    generation._collab_event_log.clear()
    generation._collab_presence.clear()
    generation.sessions.clear()


@pytest.fixture(autouse=True)
def _clean_m7b_g42_state():
    _reset_state()
    yield
    _reset_state()


def _sse_frame_data(body, event, nth=0):
    # same parser as G4-1: SSE frames as event: X\ndata: {...}\n\n line pairs.
    lines = body.split("\n")
    frames = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if (
            line.startswith("event: ")
            and i + 1 < len(lines)
            and lines[i + 1].startswith("data: ")
        ):
            frames.append((line[len("event: "):], json.loads(lines[i + 1][len("data: "):])))
            i += 2
        else:
            i += 1
    matching = [d for name, d in frames if name == event]
    assert nth < len(matching), f"event: {event} frame #{nth} not found (total {len(matching)})"
    return matching[nth]


def _drive_stream_to_snapshot(host, session_id, token=""):
    # Drive collab_stream to the break point used by B-line presence tests:
    # own viewer_joined frame followed by own presence_snapshot.
    # aclose triggers generator finally -> viewer_left broadcast.
    headers = Headers({"X-Auth-Token": token} if token else {})
    request = SimpleNamespace(
        client=SimpleNamespace(host=host),
        url=SimpleNamespace(scheme="http", netloc="testserver", path="/api/collab/stream"),
        headers=headers,
    )
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    body_chunks = []

    async def _run():
        response = await generation.collab_stream(request, session_id=session_id)
        body_iter = response.body_iterator
        own_viewer_id = resolve_user_id_from_session(token) or f"anon-{host}"
        own_joined_seen = False
        async for chunk in body_iter:
            text = chunk if isinstance(chunk, str) else chunk.decode("utf-8", "ignore")
            body_chunks.append(text)
            if f'"viewer_id": "{own_viewer_id}"' in text and "viewer_joined" in text:
                own_joined_seen = True
            if own_joined_seen and "presence_snapshot" in text:
                break
        await body_iter.aclose()

    loop.run_until_complete(_run())
    loop.close()
    return "".join(body_chunks)


# --- G4-2 断线回放 E2E 回归（M7-A 登录态下）--------------------------------

def test_g42_disconnection_replay_anon_session_joined_then_left():
    """
    G4-2 断线回放核心回归（sec2 content 2）：匿名连接 join 后断线（aclose ->
    generator finally -> viewer_left），事件日志写入 viewer_joined +
    presence_snapshot + viewer_left 全链；会话清空后 _collab_presence 无残留，
    新 join 者回放历史事件（viewer_joined / presence_snapshot / viewer_left
    按序可重放，幂等收敛口径同 B 线 S1+S2）。
    """
    _reset_state()
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-g42-anon"}):
        body = _drive_stream_to_snapshot("10.42.1.1", "s-g42-anon")
        joined = _sse_frame_data(body, "viewer_joined")
        assert joined["viewer_id"] == "anon-10.42.1.1"
        assert "user_id" not in joined
        status = _sse_frame_data(body, "collab_status")
        assert status["status"] == "anon"

        log = generation._collab_event_log.get("s-g42-anon", [])
        left_events = [
            e for e in log
            if e["event"] == "viewer_left" and e["data"].get("viewer_id") == "anon-10.42.1.1"
        ]
        assert len(left_events) == 1
        assert left_events[0]["data"]["viewers_total"] == 0
        # 会话无残留：presence 注册表清理
        assert not generation._collab_presence.get("s-g42-anon")

        # 新 join 者（不同 IP）回放历史全链事件
        body2 = _drive_stream_to_snapshot("10.42.1.2", "s-g42-anon")
        replay_left = _sse_frame_data(body2, "viewer_left")
        assert replay_left["viewer_id"] == "anon-10.42.1.1"
        assert "user_id" not in replay_left
        # 回放段（history）中的首个 viewer_joined = 匿名连接自己的历史帧；
        # 本连接实时帧 = 第二个 viewer_joined（nth=1）
        replay_joined_hist = _sse_frame_data(body2, "viewer_joined", nth=0)
        assert replay_joined_hist["viewer_id"] == "anon-10.42.1.1"
        assert "user_id" not in replay_joined_hist["data"] if "user_id" in replay_joined_hist else True
        joined2 = _sse_frame_data(body2, "viewer_joined", nth=1)
        assert joined2["viewer_id"] == "anon-10.42.1.2"
        assert joined2["viewers_total"] == 1


def test_g42_disconnection_replay_session_bound_user_joined_then_left():
    """
    G4-2 登录态断线回放：session-bound 连接（有效 X-Auth-Token）join 后断线，
    viewer_joined/viewer_left 双发 user_id 字段（sec2 content 3 收尾验证项），
    回放段历史帧 user_id 保留可重放（同一会话历史事件日志含 user_id 字段，
    新 join 者回放时字段完整，无静默降级）。
    """
    _reset_state()
    token = create_session("user-g42")
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-g42-bound"}):
        body = _drive_stream_to_snapshot("10.42.2.1", "s-g42-bound", token=token)
        joined = _sse_frame_data(body, "viewer_joined")
        assert joined["viewer_id"] == "user-g42"
        assert joined["user_id"] == "user-g42"
        status = _sse_frame_data(body, "collab_status")
        assert status["status"] == "session_bound"
        assert status["user_id"] == "user-g42"

        log = generation._collab_event_log.get("s-g42-bound", [])
        left_events = [
            e for e in log
            if e["event"] == "viewer_left" and e["data"].get("viewer_id") == "user-g42"
        ]
        assert len(left_events) == 1
        assert left_events[0]["data"]["user_id"] == "user-g42"
        assert left_events[0]["data"]["viewers_total"] == 0

        # 新 join 者（匿名）回放历史，user_id 字段在回放帧中完整保留
        body2 = _drive_stream_to_snapshot("10.42.2.2", "s-g42-bound")
        # 回放段（history）首个 viewer_joined = session-bound 连接历史帧（含 user_id）
        replay_joined_hist = _sse_frame_data(body2, "viewer_joined", nth=0)
        assert replay_joined_hist["viewer_id"] == "user-g42"
        assert replay_joined_hist["user_id"] == "user-g42"
        # 本连接（匿名）实时帧 = 第二个 viewer_joined（nth=1），无 user_id 字段
        joined2 = _sse_frame_data(body2, "viewer_joined", nth=1)
        assert joined2["viewer_id"] == "anon-10.42.2.2"
        assert "user_id" not in joined2
        assert joined2["viewers_total"] == 1
        # 回放段历史 viewer_left 帧（session-bound 连接断线）
        replay_left = _sse_frame_data(body2, "viewer_left")
        assert replay_left["viewer_id"] == "user-g42"
        assert replay_left["user_id"] == "user-g42"
        assert replay_left["viewers_total"] == 0

        destroy_session(token)


def test_g42_invalid_session_bound_falls_back_to_anon_replay():
    """
    G4-2 降级路径收尾验证（sec2 content 3）：无效 token（resolve_user_id_from_session
    -> None）回退 anon-{IP}，join/left 历史回放中 user_id 字段缺失（匿名口径
    与 B 线 S2 既有协议一致，前端 m3-b 草案 §九-补 ①「未上报」降级不命中本地
    默认值，零静默篡改）。
    """
    _reset_state()
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-g42-invalid"}):
        body = _drive_stream_to_snapshot("10.42.3.1", "s-g42-invalid", token="expired-token")
        joined = _sse_frame_data(body, "viewer_joined")
        assert joined["viewer_id"] == "anon-10.42.3.1"
        assert "user_id" not in joined
        status = _sse_frame_data(body, "collab_status")
        assert status["status"] == "anon"
        assert "user_id" not in status

        log = generation._collab_event_log.get("s-g42-invalid", [])
        left_events = [
            e for e in log
            if e["event"] == "viewer_left" and e["data"].get("viewer_id") == "anon-10.42.3.1"
        ]
        assert len(left_events) == 1
        assert "user_id" not in left_events[0]["data"]


# --- G4-2 收尾验证项：_COLLAB_MAX_LOG 截断回放不变量 -----------------------

def test_g42_event_log_truncation_preserves_latest_100_entries():
    """
    G4-2 收尾验证（sec2 content 2 回放通道容量不变量）：_COLLAB_MAX_LOG = 100
    （B 草案 S1 既有口径，零改动红线）。连续写入 105 条事件后，日志容量保持
    100 条，最旧 5 条被弹出；回放截断仅影响「最早 5 条」，最近 100 条（含
    viewer_joined / presence_snapshot / viewer_left 序列尾部）完整可重放。
    新 join 者回放不会因截断漏掉最近一次断线回放链（join -> left -> 再 join
    序列尾部完整保留）。
    """
    _reset_state()
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-g42-log"}):
        # 预灌 105 条 generation_progress 事件（超出容量 5 条）
        for i in range(105):
            generation.collab_publish(
                "s-g42-log",
                "generation_progress",
                {"stage": "intent", "detail": f"seed-{i}", "ts": i},
            )
        log = generation._collab_event_log.get("s-g42-log", [])
        assert len(log) == 100
        # 最旧 5 条（seed-0..seed-4）被截断，seed-5 成为日志首条
        assert log[0]["data"]["detail"] == "seed-5"
        assert log[-1]["data"]["detail"] == "seed-104"

        # 再驱动一次断线回放链：viewer_joined -> presence_snapshot -> viewer_left
        # 写入后容量仍 100 条，且 viewer_joined / presence_snapshot /
        # viewer_left 三条全在日志尾部（最近 3 条），回放时完整重放
        _drive_stream_to_snapshot("10.42.4.1", "s-g42-log")
        log2 = generation._collab_event_log.get("s-g42-log", [])
        assert len(log2) == 100
        tail_events = [e["event"] for e in log2[-3:]]
        assert tail_events == ["viewer_joined", "presence_snapshot", "viewer_left"]
        # 最近一次断线回放链（join -> left）完整保留在日志尾部，新 join 者可重放
        # 匿名连接：viewer_left data 无 user_id 字段（匿名口径不变）
        last_left = log2[-1]
        assert last_left["data"]["viewer_id"] == "anon-10.42.4.1"
        assert "user_id" not in last_left["data"]


# --- G4-2 收尾验证项：presence 注册表清理不变量 ----------------------------

def test_g42_presence_registry_cleanup_on_last_viewer_leave():
    """
    G4-2 收尾验证（sec2 content 2 会话状态清理不变量）：最后一名观察者断线
    （viewer_left viewers_total=0）后，_collab_presence 对应会话键被清理
    （generation.py 既有 finally 清理逻辑，零改动红线）。连续两次断线后
    会话键不复存在，防止注册表无限膨胀。
    """
    _reset_state()
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-g42-cleanup"}):
        _drive_stream_to_snapshot("10.42.5.1", "s-g42-cleanup")
        assert not generation._collab_presence.get("s-g42-cleanup"), \
            "最后一名观察者断线后 presence 注册表应清理"
        # 新 join 者（匿名）重新注册
        _drive_stream_to_snapshot("10.42.5.2", "s-g42-cleanup")
        assert not generation._collab_presence.get("s-g42-cleanup"), \
            "第二次断线后 presence 注册表应再次清理"


# --- G4-2 收尾验证项：viewer_left 事件在断线回放 E2E 驱动下不重复广播 ------

def test_g42_viewer_left_broadcasted_exactly_once_per_connection():
    """
    G4-2 断线回放幂等不变量（B 线 S2 既有口径）：单个连接 aclose 触发
    generator finally 后，viewer_left 恰好广播 1 次（viewers_total=0）。
    生成器 finally 路径防重复 left 闭包标记 _conn_state["joined"]=True ->
    aclose 后置 False，即使事件日志容量截断（MAX_LOG=100）也不产生重复
    left 帧（与 test_presence_b3.py::test_presence_leave_broadcasts_viewer_left
    既有口径一致，零回归）。
    """
    _reset_state()
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-g42-once"}):
        _drive_stream_to_snapshot("10.42.6.1", "s-g42-once")
        log = generation._collab_event_log.get("s-g42-once", [])
        left_events = [
            e for e in log
            if e["event"] == "viewer_left" and e["data"].get("viewer_id") == "anon-10.42.6.1"
        ]
        assert len(left_events) == 1, \
            f"viewer_left(10.42.6.1) 应恰好 1 次，实得 {len(left_events)}"
        assert left_events[0]["data"]["viewers_total"] == 0
        assert "user_id" not in left_events[0]["data"]
