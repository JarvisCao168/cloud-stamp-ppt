"""生成接口路由。

POST /api/generation/create          — 创建生成会话
GET  /api/generation/session/{id}    — 查询会话状态
POST /api/generation/checkpoint/{sid}/{cid}/action  — 提交检查点操作
GET  /api/checkpoints/flow/{sid}     — 获取检查点流程状态
"""

from __future__ import annotations

import re
import time
from fastapi import APIRouter, HTTPException

from backend.types import (
    GenerationRequest,
    GenerationResponse,
    CheckpointActionRequest,
    SessionResponse,
    CheckpointFlowResponse,
    CheckpointOut,
)
from backend.store import create_session, get_session

router = APIRouter()


# ── 模板数据（无 AI Key 时降级使用）──────────────────────────────────────────

_DEFAULT_TEMPLATES: dict[str, list[dict]] = {
    "quick": [
        {"title": "概述", "content": "基于「{prompt}」的核心要点"},
        {"title": "背景", "content": "当前行业趋势与关键挑战分析"},
        {"title": "解决方案", "content": "创新方法与实施路径"},
        {"title": "成果展望", "content": "预期收益与后续规划"},
    ],
    "collaborative": [
        {"title": "项目概览", "content": "目标：{prompt}\n范围与关键里程碑"},
        {"title": "团队分工", "content": "角色定义与责任划分\n协作流程与沟通机制"},
        {"title": "进度跟踪", "content": "已完成任务 · 进行中 · 待启动"},
        {"title": "风险与对策", "content": "识别关键风险并制定应对方案"},
        {"title": "下一步行动", "content": "短期目标与长期规划"},
    ],
    "full_control": [
        {"title": "封面", "content": "主题：{prompt}\n生成日期：2026年9月"},
        {"title": "目录", "content": "1. 背景介绍\n2. 核心分析\n3. 解决方案\n4. 实施方案\n5. 总结展望"},
        {"title": "背景介绍", "content": "阐述「{prompt}」的研究背景与意义"},
        {"title": "核心分析", "content": "多维度深入分析关键问题\n数据分析与洞察发现"},
        {"title": "解决方案", "content": "提出系统性解决思路\n技术路线与实现策略"},
        {"title": "实施方案", "content": "分阶段实施计划\n资源分配与时间线"},
        {"title": "总结展望", "content": "主要结论\n未来研究方向与应用前景"},
        {"title": "致谢", "content": "感谢聆听，欢迎交流"},
    ],
}


def _generate_slides(user_input: str, mode: str) -> tuple[list[dict], dict]:
    """根据模式生成模拟幻灯片数据（降级实现）。"""
    templates = _DEFAULT_TEMPLATES.get(mode, _DEFAULT_TEMPLATES["quick"])
    slides = []
    for t in templates:
        content = t["content"].format(prompt=user_input)
        content = re.sub(r"\n+", "\n", content).strip()
        slides.append({"title": t["title"], "content": content})

    intent = {
        "theme": user_input[:50],
        "mode": mode,
        "slide_count": len(slides),
        "language": "zh-CN",
    }
    return slides, intent


# ── 路由实现 ─────────────────────────────────────────────────────────────────

@router.post("/generation/create", response_model=GenerationResponse)
async def create_generation(req: GenerationRequest) -> GenerationResponse:
    session = create_session(req.user_input, req.mode)
    slides, intent = _generate_slides(req.user_input, req.mode)
    session.slides = slides
    session.intent = intent

    if req.mode == "full_control":
        cp_outs = [
            CheckpointOut(
                id=cp.id,
                title=cp.title,
                description=cp.description,
                status=cp.status,
            )
            for cp in session.checkpoints.values()
        ]
        session.status = "completed"
        return GenerationResponse(
            session_id=session.session_id,
            status="checkpoint",
            message=f"已生成 {len(slides)} 页内容，请确认检查点",
            data={"slides": slides, "intent": intent},
            checkpoints=cp_outs,
        )

    session.status = "completed"
    return GenerationResponse(
        session_id=session.session_id,
        status="completed",
        message=f"成功生成 {len(slides)} 页演示文稿",
        data={"slides": slides, "intent": intent},
    )


@router.get("/generation/session/{session_id}", response_model=SessionResponse)
async def get_generation_session(session_id: str) -> SessionResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    checkpoints = [
        CheckpointOut(
            id=cp.id,
            title=cp.title,
            description=cp.description,
            status=cp.status,
            user_action=cp.user_action,
            completed_at=cp.completed_at,
        )
        for cp in session.checkpoints.values()
    ] if session.checkpoints else None

    slides_out = [
        {"title": s["title"], "content": s["content"]}
        for s in session.slides
    ] if session.slides else None

    return SessionResponse(
        session_id=session.session_id,
        mode=session.mode,
        status=session.status,
        slides=slides_out,
        intent=session.intent,
        checkpoints=checkpoints,
        current_checkpoint=session.current_checkpoint,
    )


@router.post(
    "/generation/checkpoint/{session_id}/{checkpoint_id}/action",
    response_model=dict,
)
async def submit_checkpoint_action(
    session_id: str,
    checkpoint_id: str,
    req: CheckpointActionRequest,
) -> dict:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    cp = session.checkpoints.get(checkpoint_id)
    if cp is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    cp.user_action = req.action
    cp.status = "completed"
    cp.completed_at = time.time()

    _advance_checkpoint(session)

    return {
        "status": "recorded",
        "session_id": session_id,
        "checkpoint_id": checkpoint_id,
        "next_checkpoint": session.current_checkpoint,
    }


@router.get("/checkpoints/flow/{session_id}", response_model=CheckpointFlowResponse)
async def get_checkpoint_flow(session_id: str) -> CheckpointFlowResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    checkpoints = [
        CheckpointOut(
            id=cp.id,
            title=cp.title,
            description=cp.description,
            status=cp.status,
            user_action=cp.user_action,
            completed_at=cp.completed_at,
        )
        for cp in session.checkpoints.values()
    ]

    return CheckpointFlowResponse(
        session_id=session.session_id,
        mode=session.mode,
        current_checkpoint=session.current_checkpoint,
        checkpoints=checkpoints,
    )


def _advance_checkpoint(session) -> None:
    """将当前检查点标记为完成，并激活下一个检查点。"""
    if session.current_checkpoint is None:
        return

    cp = session.checkpoints.get(session.current_checkpoint)
    if cp:
        cp.status = "completed"
        cp.completed_at = time.time()

    for state in session.checkpoints.values():
        if state.status == "pending":
            state.status = "active"
            session.current_checkpoint = state.id
            return

    session.current_checkpoint = None
