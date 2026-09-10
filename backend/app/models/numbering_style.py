"""
序号样式 Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


class NumberingStyleCreate(BaseModel):
    """创建序号样式请求"""
    name: str
    type: str = Field(..., pattern=r"^(numeric|chinese|level|graphic|icon|english|special)$")
    symbols: List[str]
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    max_depth: int = Field(default=1, ge=1, le=5)
    preview_html: Optional[str] = None
    is_system: bool = False


class NumberingStyleUpdate(BaseModel):
    """更新序号样式请求"""
    name: Optional[str] = None
    type: Optional[str] = Field(None, pattern=r"^(numeric|chinese|level|graphic|icon|english|special)$")
    symbols: Optional[List[str]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    max_depth: Optional[int] = Field(None, ge=1, le=5)
    preview_html: Optional[str] = None
    is_system: Optional[bool] = None


class NumberingStyleOut(BaseModel):
    """序号样式响应"""
    id: str
    name: str
    type: str
    symbols: List[str]
    description: Optional[str]
    tags: List[str]
    max_depth: int
    preview_html: Optional[str]
    is_system: bool


class TemplateNumberingOut(BaseModel):
    """模板-序号关联响应"""
    template_id: str
    numbering_id: str
    priority: int
