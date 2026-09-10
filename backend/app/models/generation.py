"""
生成进度状态
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ProgressStep(BaseModel):
    name: str
    status: str  # pending / running / completed / failed
    detail: Optional[str] = None


class ProgressResponse(BaseModel):
    session_id: str
    status: str  # processing / checkpoint / completed / failed
    progress: int  # 0-100
    current_step: Optional[str] = None
    steps: Optional[List[ProgressStep]] = None
    checkpoints: Optional[List[Dict[str, Any]]] = None


class PresentationData(BaseModel):
    session_id: str
    intent: Optional[Dict[str, Any]] = None
    outline: Optional[List[Dict[str, Any]]] = None
    slides: Optional[List[Dict[str, Any]]] = None
    style: Optional[Dict[str, Any]] = None
    mode: Optional[str] = None
