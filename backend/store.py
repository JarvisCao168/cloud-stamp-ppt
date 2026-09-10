"""Session 存储与生命周期管理（内存实现）。

每个 session 持有用户输入、模式、生成的幻灯片数据以及检查点状态。
使用 dict 存储，进程重启后数据丢失；生产环境可替换为 Redis 或 SQLite。
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckpointState:
    id: str
    title: str
    description: str
    status: str = "pending"          # pending | active | completed
    user_action: str | None = None
    completed_at: float | None = None


@dataclass
class Session:
    session_id: str
    user_input: str
    mode: str                           # quick | collaborative | full_control
    created_at: float
    slides: list[dict[str, Any]] = field(default_factory=list)
    intent: dict[str, Any] = field(default_factory=dict)
    checkpoints: dict[str, CheckpointState] = field(default_factory=dict)
    current_checkpoint: str | None = None
    status: str = "processing"          # processing | completed | failed
    error: str | None = None

    def __post_init__(self) -> None:
        if self.mode == "full_control":
            self._init_mastery_checkpoints()
        elif self.mode == "collaborative":
            self._init_collaborative_checkpoints()

    def _init_mastery_checkpoints(self) -> None:
        """掌控模式：8 个检查点"""
        names = [
            ("outline_structure", "大纲结构"),
            ("template_selection", "模板与主题"),
            ("color_scheme", "配色方案"),
            ("font_selection", "字体组合"),
            ("layout_selection", "逐页布局"),
            ("content_edit", "内容编辑"),
            ("animation_selection", "动效方案"),
            ("final_review", "最终审阅"),
        ]
        now = time.time()
        for idx, (cp_id, cp_name) in enumerate(names):
            state = CheckpointState(
                id=cp_id,
                title=cp_name,
                description=f"检查点 {idx + 1}: {cp_name}",
                status="active" if idx == 0 else "pending",
                completed_at=now if idx == 0 else None,
            )
            self.checkpoints[cp_id] = state
        self.current_checkpoint = "outline_structure"

    def _init_collaborative_checkpoints(self) -> None:
        """协作模式：3 个检查点"""
        names = [
            ("outline_structure", "大纲结构"),
            ("content_review", "内容审阅"),
            ("style_finalization", "风格定稿"),
        ]
        now = time.time()
        for idx, (cp_id, cp_name) in enumerate(names):
            state = CheckpointState(
                id=cp_id,
                title=cp_name,
                description=f"检查点 {idx + 1}: {cp_name}",
                status="active" if idx == 0 else "pending",
                completed_at=now if idx == 0 else None,
            )
            self.checkpoints[cp_id] = state
        self.current_checkpoint = "outline_structure"


# ── 内存存储 ────────────────────────────────────────────────────────────────

_sessions: dict[str, Session] = {}


def create_session(user_input: str, mode: str) -> Session:
    sid = uuid.uuid4().hex[:16]
    session = Session(
        session_id=sid,
        user_input=user_input,
        mode=mode,
        created_at=time.time(),
    )
    _sessions[sid] = session
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def list_sessions() -> list[str]:
    return list(_sessions.keys())
