# M7-B G4-1 unit tests (docs/m7-plan.md v0.2, sec2 content 1/3):
# - slide edit domain optimistic lock guard (_slide_edit_guard, user_credits.version
#   WHERE version=? semantics extended to slide edit domain, sec2 content 1)
#   hit / conflict / rebase retry / sequential four scenarios + zero-mutation zero-broadcast on conflict
# - session-bound dual-compat (sec2 content 3 "final verification"):
#   collab_stream with valid X-Auth-Token -> viewer_id = session user_id,
#   viewer_joined/viewer_left data carries dual user_id field, join batch collab_status
#   first frame (status=session_bound/anon, data with user_id);
#   invalid/not-logged-in falls back to anon-{IP} (user_id field absent, m3-b draft sec9-supp 1)
# zero-diff redline: quota.py / db.py / generation.py /create 3-branch (line anchors per actual def lines)
# / test_presence_b3.py this file zero diff.
# gate: this file 6 new tests, batch out-bill full pytest >= 48 passed / 0 failed
# (42 baseline + 6; baseline confirmed by batch out-bill measured).
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from starlette.datastructures import Headers

from app.api.routes import generation
from app.core.auth import create_session


def _reset_state():
    generation._collab_subscribers.clear()
    generation._collab_event_log.clear()
    generation._collab_presence.clear()
    generation.sessions.clear()


@pytest.fixture(autouse=True)
def _clean_m7b_state():
    _reset_state()
    yield
    _reset_state()


def _sse_frame_data(body, event, nth=0):
    # parse SSE frames line-by-line (event: X\ndata: {...}\n\n format),
    # avoids nested-brace regex truncation (presence_snapshot viewers array)
    lines = body.split("\n")
    frames = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("event: ") and i + 1 < len(lines) and lines[i + 1].startswith("data: "):
            frames.append((line[len("event: "):], json.loads(lines[i + 1][len("data: "):])))
            i += 2
        else:
            i += 1
    matching = [d for name, d in frames if name == event]
    assert nth < len(matching), f"event: {event} frame #{nth} not found (total {len(matching)})"
    return matching[nth]


def _drive_stream_to_snapshot(host, session_id, token="", bound=False):
    # same driver as test_presence_b3._drive_stream_to_snapshot,
    # optional X-Auth-Token header (session-bound);
    # bound=True: token is valid (viewer_id = session user_id, collab_status status=session_bound);
    #   break point = own collab_status(session_bound) frame (replayed frames only have
    #   status=anon from anon history -> zero false-positive);
    # bound=False (token="" or invalid token): falls back to anon-{IP} fingerprint;
    #   break point = anon-{host} viewer_joined frame per existing B-line spec.
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
        own_joined_seen = False
        async for chunk in body_iter:
            text = chunk if isinstance(chunk, str) else chunk.decode("utf-8", "ignore")
            body_chunks.append(text)
            if bound:
                # valid bound connection: break on own collab_status(session_bound) frame
                if "session_bound" in text and "collab_status" in text:
                    own_joined_seen = True
            else:
                # anon/invalid-token connection: break on anon-{host} viewer_joined frame
                if "viewer_joined" in text:
                    if f'"viewer_id": "anon-{host}"' in text:
                        own_joined_seen = True
            if own_joined_seen and "presence_snapshot" in text:
                break
        await body_iter.aclose()

    loop.run_until_complete(_run())
    loop.close()
    return "".join(body_chunks)


# --- session-bound dual-compat (sec2 content 3) ---------------------------------

def test_m7b_bound_session_viewers_id_uses_user_id_and_doubles_user_id():
    """
    G4-1 core: valid session token -> viewer_id = session user_id (R5 closure),
    viewer_joined data dual-carries user_id field (m3-b draft sec9-supp 1:
    present -> consume; absent -> "not reported" fallback, forbid default 1),
    join batch collab_status first frame status=session_bound.
    """
    _reset_state()
    token = create_session("user-m7b-1")
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-bound"}):
        body = _drive_stream_to_snapshot("10.7.7.7", "s-bound", token=token, bound=True)
        joined = _sse_frame_data(body, "viewer_joined")
        assert joined["viewer_id"] == "user-m7b-1"
        assert joined["user_id"] == "user-m7b-1"
        assert joined["viewers_total"] == 1
        snap = _sse_frame_data(body, "presence_snapshot")
        assert snap["viewers"][0]["viewer_id"] == "user-m7b-1"
        status = _sse_frame_data(body, "collab_status")
        assert status["status"] == "session_bound"
        assert status["user_id"] == "user-m7b-1"
        log_events = [e["event"] for e in generation._collab_event_log.get("s-bound", [])]
        assert "viewer_joined" in log_events
        assert "presence_snapshot" in log_events
        assert "collab_status" in log_events


def test_m7b_invalid_token_falls_back_to_anon_ip_without_user_id_field():
    """
    G4-1 degradation: invalid/expired token (resolve_user_id_from_session returns None)
    -> falls back to anon-{IP}, user_id field absent (m3-b draft sec9-supp 1
    "not reported" fallback path), collab_status status=anon; existing B-line join/left
    sequence zero-regression.
    """
    _reset_state()
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-invalid"}):
        body = _drive_stream_to_snapshot("10.7.7.8", "s-invalid", token="deadbeef", bound=False)
        joined = _sse_frame_data(body, "viewer_joined")
        assert joined["viewer_id"] == "anon-10.7.7.8"
        assert "user_id" not in joined
        status = _sse_frame_data(body, "collab_status")
        assert status["status"] == "anon"
        assert "user_id" not in status
        log = generation._collab_event_log.get("s-invalid", [])
        left_events = [
            e for e in log
            if e["event"] == "viewer_left"
            and e["data"].get("viewer_id") == "anon-10.7.7.8"
        ]
        assert len(left_events) == 1
        assert "user_id" not in left_events[0]["data"]
        assert left_events[0]["data"]["viewers_total"] == 0


def test_m7b_mixed_bound_and_anon_converge_to_one_viewer():
    """
    G4-1 convergence: same-IP anon connection + same-user session-bound connection
    join the same session sequentially (simulates logged-in + anon coexistence).
    Spec = B draft R3 "viewersTotal is active connection count, not dedup user count":
    two connections have distinct viewer_id (user-m7b-2 vs anon-10.7.7.9), no cross-talk.
    Serial drive (A cancels then B joins, same as test_presence_b3 multi-connection spec):
    bound first-frame viewers_total = 1 (anon already left), replay section contains
    anon history joined/left (anon history frame user_id field absent, consistent spec).
    """
    _reset_state()
    token = create_session("user-m7b-2")
    with patch.object(generation, "_collab_snapshot", return_value={"session_id": "s-mixed"}):
        _drive_stream_to_snapshot("10.7.7.9", "s-mixed", token="", bound=False)
        body = _drive_stream_to_snapshot("10.7.7.9", "s-mixed", token=token, bound=True)
        # anon connection's collab_status(status=anon) is in replay section;
        # bound connection's join batch collab_status(status=session_bound) + viewer_joined
        # are real-time frames
        anon_status = _sse_frame_data(body, "collab_status", nth=0)
        assert anon_status["status"] == "anon"
        assert "user_id" not in anon_status
        anon_joined = _sse_frame_data(body, "viewer_joined", nth=0)
        assert anon_joined["viewer_id"] == "anon-10.7.7.9"
        assert "user_id" not in anon_joined
        bound_status = _sse_frame_data(body, "collab_status", nth=1)
        assert bound_status["status"] == "session_bound"
        assert bound_status["user_id"] == "user-m7b-2"
        joined = _sse_frame_data(body, "viewer_joined", nth=1)
        assert joined["viewer_id"] == "user-m7b-2"
        assert joined["user_id"] == "user-m7b-2"
        assert joined["viewers_total"] == 1


# --- slide edit domain optimistic lock guard + conflict rebase (sec2 content 1) --

def _apply_title(slides, index, revision):
    # mutation contract: replace slide index title (M7-B in-domain booking)
    slides[index]["title"] = f"title-v{revision}"


def test_m7b_slide_guard_success_applies_revision_and_publishes():
    """
    G4-1 slide-level collab reinforcement: hit path (base_revision = current)
    -> mutation applied + revision +1 + broadcast slide_update (Phase 4 reserved
    event name, m4-b2-collabstream-prewrite.diff sec33 existing spec).
    Zero-diff redline: user_credits / debit_credits optimistic lock structure
    (quota.py:88-138) untouched, guard is in-memory booking, DB schema unchanged.
    """
    _reset_state()
    reg = generation.sessions.setdefault("s-slide", {})
    reg["slides"] = [{"title": "old"}, {"title": "old"}]
    result = generation._slide_edit_guard(
        "s-slide", 0, 0, lambda slides, i, r: _apply_title(reg["slides"], i, r)
    )
    assert result["ok"] is True
    assert result["revision"] == 1
    assert reg["slides"][0]["title"] == "title-v1"
    assert reg["_slide_revisions"][0] == 1
    log_events = [e["event"] for e in generation._collab_event_log.get("s-slide", [])]
    assert "slide_update" in log_events


def test_m7b_slide_guard_conflict_rebase_and_retry_succeeds():
    """
    G4-1 conflict rebase edge case (sec2 content 1 "supplement conflict rebase edge scenarios"):
    two editors based on same baseline (revision=0) edit same slide:
    1) editor A hits (0->1, revision written back)
    2) editor B submits with base=0 -> conflict (current=1 != 0), zero-mutation zero-broadcast
    3) B rebases: pull snapshot (current revision=1, title baseline advanced) -> replay
       intent on latest baseline (title-v2 synthesized on top of A's v1) -> retry with
       current_revision=1 as base -> hit (1->2)
    Acceptance: conflict path response.ok=False + current_revision correct; retry path converges.
    """
    _reset_state()
    reg = generation.sessions.setdefault("s-rebase", {})
    reg["slides"] = [{"title": "v0"}, {"title": "v0"}]
    res_a = generation._slide_edit_guard(
        "s-rebase", 0, 0, lambda slides, i, r: _apply_title(reg["slides"], i, r)
    )
    assert res_a["ok"] is True and res_a["revision"] == 1
    events_before = len(generation._collab_event_log.get("s-rebase", []))
    res_b = generation._slide_edit_guard(
        "s-rebase", 0, 0, lambda slides, i, r: _apply_title(reg["slides"], i, r)
    )
    assert res_b["ok"] is False
    assert res_b["reason"] == "slide_conflict"
    assert res_b["current_revision"] == 1
    # zero-mutation assertion (conflict does not apply mutation)
    assert reg["slides"][0]["title"] == "title-v1"
    # zero-broadcast assertion (conflict path does not write to total log)
    events_after = len(generation._collab_event_log.get("s-rebase", []))
    assert events_after == events_before, "conflict path incorrectly wrote slide_update log"
    # B rebase retry: base = current_revision (=1), replay intent (synthesize v2 on v1 baseline)
    res_b2 = generation._slide_edit_guard(
        "s-rebase", 0, 1, lambda slides, i, r: _apply_title(reg["slides"], i, r)
    )
    assert res_b2["ok"] is True
    assert res_b2["revision"] == 2
    assert reg["slides"][0]["title"] == "title-v2"


def test_m7b_slide_guard_sequential_same_editor_no_false_conflict():
    """
    G4-1 adjacent-revision scenario: same editor submits sequentially
    (base always tracks current_revision) -> no false conflict, revision monotonically
    increasing; prevents "editor itself being falsely identified as conflicted by rebase"
    edge case (rebase edge: sequential edit path and conflict path do not cross).
    """
    _reset_state()
    reg = generation.sessions.setdefault("s-seq", {})
    reg["slides"] = [{"title": "base"}, {"title": "base"}]
    r1 = generation._slide_edit_guard(
        "s-seq", 0, 0, lambda slides, i, r: _apply_title(reg["slides"], i, r)
    )
    r2 = generation._slide_edit_guard(
        "s-seq", 0, r1["revision"], lambda slides, i, r: _apply_title(reg["slides"], i, r)
    )
    assert r1["revision"] == 1
    assert r2["ok"] is True and r2["revision"] == 2
    assert reg["slides"][0]["title"] == "title-v2"
    # slide_update event total = 2 (two hits each 1, zero false-positive)
    slide_events = [
        e for e in generation._collab_event_log.get("s-seq", []) if e["event"] == "slide_update"
    ]
    assert len(slide_events) == 2