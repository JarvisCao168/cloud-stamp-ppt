"""
检查点管理路由
提供检查点状态查询、操作记录等接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ...core.checkpoint_engine import CheckpointEngine, CheckpointStatus

router = APIRouter()

# 全局引擎实例
engine = CheckpointEngine()


class CheckpointStatusResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    user_action: Optional[str] = None
    completed_at: Optional[float] = None


class CheckpointFlowResponse(BaseModel):
    session_id: str
    mode: str
    current_checkpoint: Optional[str] = None
    checkpoints: List[CheckpointStatusResponse]
    created_at: float
    updated_at: float


@router.get("/flow/{session_id}", response_model=CheckpointFlowResponse)
async def get_flow_status(session_id: str):
    """获取检查点流程状态"""
    session = engine.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    checkpoints = [
        CheckpointStatusResponse(
            id=cp.id,
            title=cp.title,
            description=cp.description,
            status=cp.status.value,
            user_action=cp.user_action,
            completed_at=cp.completed_at
        )
        for cp in session["checkpoints"]
    ]
    
    current_idx = session.get("current_index", 0)
    current_checkpoint = checkpoints[current_idx].id if current_idx < len(checkpoints) else None
    
    return CheckpointFlowResponse(
        session_id=session_id,
        mode=session["mode"],
        current_checkpoint=current_checkpoint,
        checkpoints=checkpoints,
        created_at=session["created_at"],
        updated_at=session["updated_at"]
    )


@router.post("/flow/{session_id}/action")
async def record_action(session_id: str, action: Dict[str, Any]):
    """记录检查点操作"""
    checkpoint_id = action.get("checkpoint_id")
    action_type = action.get("action")
    data = action.get("data")
    
    success = await engine.record_decision(session_id, action_type, data)
    
    if not success:
        raise HTTPException(status_code=404, detail="操作失败")
    
    return {"status": "recorded", "session_id": session_id}
