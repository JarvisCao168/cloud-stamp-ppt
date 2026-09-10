"""数据模型定义。

与前端 app/types.ts 保持同步，同时定义 FastAPI Pydantic 请求/响应体。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── 枚举 ─────────────────────────────────────────────────────────────────────

PresentationMode = Literal["quick", "collaborative", "full_control"]


# ── 请求体 ───────────────────────────────────────────────────────────────────

class GenerationRequest(BaseModel):
    user_input: str = Field(..., min_length=1, max_length=2000)
    mode: PresentationMode = "quick"


class CheckpointActionRequest(BaseModel):
    session_id: str
    checkpoint_id: str
    action: Literal["confirm", "edit", "regenerate", "select"]
    data: dict[str, object] | None = None


# ── 响应体 ───────────────────────────────────────────────────────────────────

class SlideOut(BaseModel):
    title: str
    content: str
    image: str | None = None
    notes: str | None = None


class CheckpointOut(BaseModel):
    id: str
    title: str
    description: str
    status: str = "pending"
    user_action: str | None = None
    completed_at: float | None = None


class GenerationResponse(BaseModel):
    session_id: str
    status: Literal["completed", "checkpoint"]
    message: str
    data: dict[str, object] | None = None
    checkpoints: list[CheckpointOut] | None = None


class SessionResponse(BaseModel):
    session_id: str
    mode: str
    status: str
    slides: list[SlideOut] | None = None
    intent: dict[str, object] | None = None
    checkpoints: list[CheckpointOut] | None = None
    current_checkpoint: str | None = None


class CheckpointFlowResponse(BaseModel):
    session_id: str
    mode: str
    current_checkpoint: str | None
    checkpoints: list[CheckpointOut]


class ExportResponse(BaseModel):
    filename: str
    url: str
    format: str
    size_bytes: int | None = None


class AssetsResponse(BaseModel):
    templates: list[dict[str, object]]
    color_schemes: list[dict[str, object]]
    layouts: list[dict[str, object]]


class HardwareInfo(BaseModel):
    tier: str
    cpu_cores: int
    recommended_model: str
