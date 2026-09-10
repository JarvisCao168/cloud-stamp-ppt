"""
设计资产路由
提供模板、配色、布局、字体、动效等资产查询接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter()


# ========== 内置资产数据 ==========

TEMPLATES = [
    {"id": "modern-dark", "name": "现代暗色", "category": "theme", "preview": "/assets/previews/modern-dark.png"},
    {"id": "corporate-clean", "name": "商务简洁", "category": "theme", "preview": "/assets/previews/corporate-clean.png"},
    {"id": "futuristic-neon", "name": "未来霓虹", "category": "theme", "preview": "/assets/previews/futuristic-neon.png"},
    {"id": "minimal-light", "name": "极简浅色系", "category": "theme", "preview": "/assets/previews/minimal-light.png"},
    {"id": "nature-organic", "name": "自然有机", "category": "theme", "preview": "/assets/previews/nature-organic.png"},
    {"id": "academic", "name": "学术严谨", "category": "theme", "preview": "/assets/previews/academic.png"},
]

COLOR_SCHEMES = [
    {
        "id": "ocean-blue",
        "name": "海洋蓝",
        "colors": {"primary": "#2563eb", "secondary": "#64748b", "accent": "#06b6d4", "background": "#f8fafc", "text": "#1e293b"}
    },
    {
        "id": "forest-green",
        "name": "森林绿",
        "colors": {"primary": "#16a34a", "secondary": "#65a30d", "accent": "#84cc16", "background": "#f0fdf4", "text": "#14532d"}
    },
    {
        "id": "sunset-gold",
        "name": "日落金",
        "colors": {"primary": "#ea580c", "secondary": "#f59e0b", "accent": "#fbbf24", "background": "#fffbeb", "text": "#7c2d12"}
    },
    {
        "id": "royal-purple",
        "name": "皇家紫",
        "colors": {"primary": "#7c3aed", "secondary": "#a78bfa", "accent": "#c4b5fd", "background": "#faf5ff", "text": "#4c1d95"}
    },
    {
        "id": "midnight",
        "name": "午夜黑",
        "colors": {"primary": "#1e293b", "secondary": "#334155", "accent": "#475569", "background": "#0f172a", "text": "#f1f5f9"}
    },
]

LAYOUTS = [
    {"id": "cover", "name": "封面", "description": "大标题居中，适合首页"},
    {"id": "title-content", "name": "标题+内容", "description": "经典布局，上标题下内容"},
    {"id": "two-column", "name": "双栏", "description": "左右分栏，适合对比内容"},
    {"id": "three-column", "name": "三栏", "description": "左中右三栏布局"},
    {"id": "quote", "name": "引用", "description": "大字号引用，突出金句"},
    {"id": "timeline", "name": "时间线", "description": "横向时间轴展示"},
    {"id": "comparison", "name": "对比", "description": "左右对比布局"},
    {"id": "process", "name": "流程", "description": "步骤流程展示"},
    {"id": "gallery", "name": "图片集", "description": "多图网格展示"},
    {"id": "ending", "name": "结尾", "description": "感谢页/联系方式"},
]

FONTS = [
    {"id": "microsoft-yahei", "name": "微软雅黑", "category": "sans-serif", "usage": "正文"},
    {"id": "simhei", "name": "黑体", "category": "sans-serif", "usage": "标题"},
    {"id": "simsun", "name": "宋体", "category": "serif", "usage": "正文"},
    {"id": "kaiti", "name": "楷体", "category": "serif", "usage": "引用"},
    {"id": "arial", "name": "Arial", "category": "sans-serif", "usage": "英文"},
    {"id": "times-new-roman", "name": "Times New Roman", "category": "serif", "usage": "英文正文"},
]

ANIMATIONS = [
    {"id": "fade", "name": "淡入", "category": "basic"},
    {"id": "slide-left", "name": "左滑入", "category": "basic"},
    {"id": "slide-right", "name": "右滑入", "category": "basic"},
    {"id": "slide-up", "name": "上滑入", "category": "basic"},
    {"id": "zoom", "name": "缩放", "category": "basic"},
    {"id": "flip", "name": "翻转", "category": "advanced"},
    {"id": "rotate", "name": "旋转", "category": "advanced"},
    {"id": "bounce", "name": "弹跳", "category": "advanced"},
]


class AssetItem(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    colors: Optional[Dict[str, str]] = None
    preview: Optional[str] = None


@router.get("/templates", response_model=List[AssetItem])
async def get_templates(category: Optional[str] = None):
    """获取模板列表"""
    if category:
        return [AssetItem(**t) for t in TEMPLATES if t["category"] == category]
    return [AssetItem(**t) for t in TEMPLATES]


@router.get("/color-schemes", response_model=List[AssetItem])
async def get_color_schemes():
    """获取配色方案"""
    return [AssetItem(id=c["id"], name=c["name"], colors=c["colors"]) for c in COLOR_SCHEMES]


@router.get("/layouts", response_model=List[AssetItem])
async def get_layouts():
    """获取布局类型"""
    return [AssetItem(id=l["id"], name=l["name"], description=l["description"]) for l in LAYOUTS]


@router.get("/fonts", response_model=List[AssetItem])
async def get_fonts():
    """获取字体列表"""
    return [AssetItem(id=f["id"], name=f["name"], category=f["category"], description=f["usage"]) for f in FONTS]


@router.get("/animations", response_model=List[AssetItem])
async def get_animations():
    """获取动效列表"""
    return [AssetItem(id=a["id"], name=a["name"], category=a["category"]) for a in ANIMATIONS]


@router.get("/all", response_model=Dict[str, List[AssetItem]])
async def get_all_assets():
    """获取所有资产"""
    return {
        "templates": [AssetItem(**t) for t in TEMPLATES],
        "color_schemes": [AssetItem(id=c["id"], name=c["name"], colors=c["colors"]) for c in COLOR_SCHEMES],
        "layouts": [AssetItem(id=l["id"], name=l["name"], description=l["description"]) for l in LAYOUTS],
        "fonts": [AssetItem(id=f["id"], name=f["name"], category=f["category"], description=f["usage"]) for f in FONTS],
        "animations": [AssetItem(id=a["id"], name=a["name"], category=a["category"]) for a in ANIMATIONS],
    }
