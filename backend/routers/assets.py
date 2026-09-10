"""资产接口路由。

GET /api/assets/all  — 返回可用模板、配色方案和布局列表
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.types import AssetsResponse

router = APIRouter()


_TEMPLATES = [
    {"id": "minimal", "name": "极简风格", "description": "干净简洁，适合商务汇报"},
    {"id": "creative", "name": "创意设计", "description": "色彩丰富，适合创意展示"},
    {"id": "academic", "name": "学术风格", "description": "严谨规范，适合论文答辩"},
    {"id": "tech", "name": "科技风格", "description": "现代科技感，适合产品发布"},
]

_COLOR_SCHEMES = [
    {"id": "blue", "name": "深海蓝", "primary": "#1e40af", "secondary": "#60a5fa"},
    {"id": "green", "name": "翡翠绿", "primary": "#065f46", "secondary": "#34d399"},
    {"id": "purple", "name": "葡萄紫", "primary": "#5b21b6", "secondary": "#a78bfa"},
    {"id": "orange", "name": "暖阳橙", "primary": "#c2410c", "secondary": "#fb923c"},
]

_LAYOUTS = [
    {"id": "title_only", "name": "标题页", "description": "居中标题，适合封面"},
    {"id": "two_column", "name": "双栏布局", "description": "左右分栏，适合对比展示"},
    {"id": "bullet_list", "name": "要点列表", "description": "列表排版，适合内容展示"},
    {"id": "image_focus", "name": "图片聚焦", "description": "大图背景，适合视觉冲击"},
]


@router.get("/assets/all", response_model=AssetsResponse)
async def get_all_assets() -> AssetsResponse:
    return AssetsResponse(
        templates=_TEMPLATES,
        color_schemes=_COLOR_SCHEMES,
        layouts=_LAYOUTS,
    )
