"""
检查点引擎
管理三档模式的检查点流程，支持暂停/恢复/回退
"""
import json
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class CheckpointStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class Checkpoint:
    """检查点"""
    id: str
    title: str
    description: str
    status: CheckpointStatus = CheckpointStatus.PENDING
    user_action: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[float] = None


class CheckpointEngine:
    """检查点引擎 - 管理流程状态"""
    
    # 各模式的检查点定义
    MODE_CHECKPOINTS = {
        "quick": [],
        "collaborative": [
            Checkpoint("outline_review", "大纲确认", "确认或修改AI生成的PPT大纲"),
            Checkpoint("style_selection", "风格选择", "从推荐方案中选择主题风格"),
            Checkpoint("content_review", "内容审阅", "逐页审阅并修改内容"),
            Checkpoint("final_review", "最终确认", "最终预览并导出"),
        ],
        "full_control": [
            Checkpoint("outline_structure", "大纲结构", "选择大纲逻辑结构"),
            Checkpoint("template_selection", "模板与主题", "从模板库选择模板"),
            Checkpoint("color_scheme", "配色方案", "选择或自定义配色"),
            Checkpoint("font_selection", "字体组合", "选择标题和正文字体"),
            Checkpoint("layout_selection", "逐页布局", "为每页选择布局类型"),
            Checkpoint("content_edit", "内容编辑", "逐页编辑内容和素材"),
            Checkpoint("animation_selection", "动效方案", "选择页面切换和元素入场动效"),
            Checkpoint("final_review", "最终审阅", "完整预览并导出"),
        ]
    }
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, session_id: str, mode: str) -> Dict[str, Any]:
        """创建新会话"""
        checkpoints = self.MODE_CHECKPOINTS.get(mode, [])
        
        session = {
            "session_id": session_id,
            "mode": mode,
            "checkpoints": checkpoints,
            "current_index": 0,
            "decisions": {},
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        
        # 设置第一个检查点为active
        if checkpoints:
            checkpoints[0].status = CheckpointStatus.ACTIVE
        
        self.sessions[session_id] = session
        return session
    
    async def pause_at_checkpoint(self, session_id: str) -> Optional[Checkpoint]:
        """在当前检查点暂停，等待用户决策"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        checkpoints = session["checkpoints"]
        current_idx = session["current_index"]
        
        if current_idx >= len(checkpoints):
            return None
        
        checkpoint = checkpoints[current_idx]
        checkpoint.status = CheckpointStatus.ACTIVE
        session["updated_at"] = time.time()
        
        return checkpoint
    
    async def record_decision(self, session_id: str, action: str, data: Dict[str, Any] = None) -> bool:
        """记录用户决策并推进到下一个检查点"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        checkpoints = session["checkpoints"]
        current_idx = session["current_index"]
        
        if current_idx >= len(checkpoints):
            return False
        
        checkpoint = checkpoints[current_idx]
        checkpoint.status = CheckpointStatus.COMPLETED
        checkpoint.user_action = action
        checkpoint.completed_at = time.time()
        
        # 保存用户决策
        if data:
            session["decisions"][checkpoint.id] = data
        
        # 推进到下一个检查点
        session["current_index"] += 1
        session["updated_at"] = time.time()
        
        # 设置下一个检查点为active
        if session["current_index"] < len(checkpoints):
            next_checkpoint = checkpoints[session["current_index"]]
            next_checkpoint.status = CheckpointStatus.ACTIVE
        
        return True
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话状态"""
        return self.sessions.get(session_id)
    
    def complete_session(self, session_id: str) -> bool:
        """标记会话完成"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session["status"] = "completed"
        session["completed_at"] = time.time()
        
        # 标记所有剩余检查点为跳过
        for cp in session["checkpoints"][session["current_index"]:]:
            cp.status = CheckpointStatus.SKIPPED
        
        return True
