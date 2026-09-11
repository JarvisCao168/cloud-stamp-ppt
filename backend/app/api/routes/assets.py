"""
设计资产路由
提供模板、配色、布局、字体、动效等资产查询接口
支持 SQLite 持久化（序号样式 + 模板-序号关联）
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import aiosqlite

from app.core.config import settings

router = APIRouter()


def _safe_query(conn, sql, default=None):
    """安全执行SQL查询，表不存在时返回默认值"""
    if default is None:
        default = []
    try:
        rows = conn.execute(sql).fetchall()
        return rows if rows else default
    except Exception:
        return default


def _get_db():
    """同步数据库连接（用于同步 CRUD 操作）"""
    db_path = settings.database_url
    # 解析 URL，兼容 sqlite+aiosqlite:// 和直接文件路径
    if db_path.startswith("sqlite+aiosqlite:///"):
        db_path = db_path.replace("sqlite+aiosqlite:///", "")
    elif db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


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

# ========== 第七要素库：序号样式库（30条，覆盖七大类型） ==========
NUMBERING_STYLES = [
    # ---------- numeric (5条) ----------
    {
        "id": "numeric-dot",
        "name": "数字序号·",
        "type": "numeric",
        "symbols": ["1.", "2.", "3.", "4.", "5."],
        "description": "标准数字加点号，适用于商务报告",
        "tags": ["商务", "正式"],
        "max_depth": 3,
        "preview_html": "<ol><li>第一项</li><li>第二项</li></ol>",
        "is_system": True,
    },
    {
        "id": "numeric-paren",
        "name": "数字序号()",
        "type": "numeric",
        "symbols": ["(1)", "(2)", "(3)", "(4)", "(5)"],
        "description": "数字加括号，学术文档常用",
        "tags": ["学术", "正式"],
        "max_depth": 3,
        "preview_html": "<p>(1) 第一项  (2) 第二项</p>",
        "is_system": True,
    },
    {
        "id": "numeric-bracket",
        "name": "数字方括号",
        "type": "numeric",
        "symbols": ["[1]", "[2]", "[3]", "[4]", "[5]"],
        "description": "方括号编号，参考文献风格",
        "tags": ["学术", "引用"],
        "max_depth": 3,
        "preview_html": "<p>[1] 第一项  [2] 第二项</p>",
        "is_system": True,
    },
    {
        "id": "numeric-bracket-n",
        "name": "编号方括号",
        "type": "numeric",
        "symbols": ["1)", "2)", "3)", "4)", "5)"],
        "description": "数字后加右括号，简洁格式",
        "tags": ["简洁", "通用"],
        "max_depth": 3,
        "preview_html": "<p>1) 第一项  2) 第二项</p>",
        "is_system": True,
    },
    {
        "id": "numeric-period-n",
        "name": "圆圈数字",
        "type": "numeric",
        "symbols": ["①", "②", "③", "④", "⑤"],
        "description": "圆圈数字，列表编号友好",
        "tags": ["列表", "友好"],
        "max_depth": 1,
        "preview_html": "<p>① 第一项  ② 第二项</p>",
        "is_system": True,
    },
    # ---------- chinese (4条) ----------
    {
        "id": "chinese-clause",
        "name": "中文顿号",
        "type": "chinese",
        "symbols": ["一、", "二、", "三、", "四、", "五、"],
        "description": "中文数字加顿号，正式公文首选",
        "tags": ["正式", "公文", "政府"],
        "max_depth": 2,
        "preview_html": "<p>一、第一项  二、第二项</p>",
        "is_system": True,
    },
    {
        "id": "chinese-paren",
        "name": "中文括号",
        "type": "chinese",
        "symbols": ["（一）", "（二）", "（三）", "（四）", "（五）"],
        "description": "中文数字加括号，二级标题常用",
        "tags": ["正式", "公文"],
        "max_depth": 2,
        "preview_html": "<p>（一）第一项  （二）第二项</p>",
        "is_system": True,
    },
    {
        "id": "chinese-bracket",
        "name": "中文括号()",
        "type": "chinese",
        "symbols": ["(1)", "(2)", "(3)", "(4)", "(5)"],
        "description": "中文语境下的括号数字，简明报告",
        "tags": ["简洁", "报告"],
        "max_depth": 2,
        "preview_html": "<p>(1) 第一项  (2) 第二项</p>",
        "is_system": True,
    },
    {
        "id": "chinese-ten",
        "name": "中文天干",
        "type": "chinese",
        "symbols": ["甲", "乙", "丙", "丁", "戊"],
        "description": "天干排序，传统文档适用",
        "tags": ["传统", "文化"],
        "max_depth": 1,
        "preview_html": "<p>甲 第一项  乙 第二项</p>",
        "is_system": True,
    },
    # ---------- level (3条) ----------
    {
        "id": "level-nested",
        "name": "层级序号",
        "type": "level",
        "symbols": ["1.1", "1.1.1", "1.1.1.1"],
        "description": "多级嵌套编号，技术文档/手册适用",
        "tags": ["技术", "文档", "手册"],
        "max_depth": 4,
        "preview_html": "<p>1. 一级  1.1 二级  1.1.1 三级</p>",
        "is_system": True,
    },
    {
        "id": "level-decimal",
        "name": "小数层级",
        "type": "level",
        "symbols": ["0.1", "0.1.1", "0.1.1.1"],
        "description": "从零开始的小数层级，规范文档风格",
        "tags": ["规范", "文档"],
        "max_depth": 4,
        "preview_html": "<p>0.1 一级  0.1.1 二级  0.1.1.1 三级</p>",
        "is_system": True,
    },
    {
        "id": "level-bracket",
        "name": "括号层级",
        "type": "level",
        "symbols": ["(1.1)", "(1.1.1)", "(1.1.1.1)"],
        "description": "带括号的层级编号，学术论文常用",
        "tags": ["学术", "论文"],
        "max_depth": 4,
        "preview_html": "<p>(1.1) 二级  (1.1.1) 三级</p>",
        "is_system": True,
    },
    # ---------- graphic (6条) ----------
    {
        "id": "graphic-circle",
        "name": "圆形图形",
        "type": "graphic",
        "symbols": ["●", "○", "■", "□", "★", "☆"],
        "description": "图形符号作序号，视觉化列表",
        "tags": ["创意", "视觉"],
        "max_depth": 1,
        "preview_html": "<p>● 第一项  ○ 第二项  ■ 第三项</p>",
        "is_system": True,
    },
    {
        "id": "graphic-diamond",
        "name": "菱形图形",
        "type": "graphic",
        "symbols": ["◆", "◇", "▸", "◂", "▹", "◃"],
        "description": "菱形箭头系列，方向感列表",
        "tags": ["创意", "方向"],
        "max_depth": 1,
        "preview_html": "<p>◆ 第一项  ◇ 第二项  ▸ 第三项</p>",
        "is_system": True,
    },
    {
        "id": "graphic-square",
        "name": "方块图形",
        "type": "graphic",
        "symbols": ["▣", "▤", "▥", "▦", "▧", "▨"],
        "description": "填充方块变体，现代设计感",
        "tags": ["现代", "设计"],
        "max_depth": 1,
        "preview_html": "<p>▣ 第一项  ▤ 第二项  ▥ 第三项</p>",
        "is_system": True,
    },
    {
        "id": "graphic-triangle",
        "name": "三角形图形",
        "type": "graphic",
        "symbols": ["▲", "△", "▼", "▽", "⬆", "⬇"],
        "description": "三角方向符号，流程指引列表",
        "tags": ["流程", "指引"],
        "max_depth": 1,
        "preview_html": "<p>▲ 第一项  △ 第二项  ▼ 第三项</p>",
        "is_system": True,
    },
    {
        "id": "graphic-check",
        "name": "勾选图形",
        "type": "graphic",
        "symbols": ["✓", "✗", "☆", "★", "●", "○"],
        "description": "勾选状态符号，待办事项列表",
        "tags": ["待办", "清单"],
        "max_depth": 1,
        "preview_html": "<p>✓ 已完成  ✗ 未完成  ☆ 待确认</p>",
        "is_system": True,
    },
    {
        "id": "graphic-bullet",
        "name": "项目符号",
        "type": "graphic",
        "symbols": ["•", "‣", "⁃", "·", "▪", "▫"],
        "description": "经典项目符号，通用列表格式",
        "tags": ["通用", "列表"],
        "max_depth": 1,
        "preview_html": "<p>• 第一项  ‣ 第二项  ⁃ 第三项</p>",
        "is_system": True,
    },
    # ---------- icon (5条) ----------
    {
        "id": "icon-check",
        "name": "箭头图标",
        "type": "icon",
        "symbols": ["→", "✓", "✗", "⚠", "★"],
        "description": "箭头/对钩序列，流程图/步骤展示",
        "tags": ["流程", "步骤", "验证"],
        "max_depth": 1,
        "preview_html": "<p>→ 第一步  → 第二步  ✓ 完成</p>",
        "is_system": True,
    },
    {
        "id": "icon-arrow",
        "name": "步骤箭头链",
        "type": "icon",
        "symbols": ["▶", "▶", "▶", "▶", "▶"],
        "description": "箭头串联步骤，流程图/时间线",
        "tags": ["流程", "时间线", "步骤"],
        "max_depth": 1,
        "preview_html": "<p>▶ 开始 ▶ 进行中 ▶ 完成</p>",
        "is_system": True,
    },
    {
        "id": "icon-star",
        "name": "星级图标",
        "type": "icon",
        "symbols": ["⭐", "☆", "★★", "★★★", "★★★★"],
        "description": "星级评分符号，评价类列表",
        "tags": ["评分", "评价"],
        "max_depth": 1,
        "preview_html": "<p>⭐ 优秀  ☆ 待改进  ★★ 良好</p>",
        "is_system": True,
    },
    {
        "id": "icon-badge",
        "name": "徽章图标",
        "type": "icon",
        "symbols": ["🏆", "🥈", "🥉", "🎖", "🏅"],
        "description": "奖牌徽章序列，排名类展示",
        "tags": ["排名", "荣誉"],
        "max_depth": 1,
        "preview_html": "<p>🏆 冠军  🥈 亚军  🥉 季军</p>",
        "is_system": True,
    },
    {
        "id": "icon-alert",
        "name": "警告图标",
        "type": "icon",
        "symbols": ["⚠", "❗", "❓", "ℹ", "✅"],
        "description": "提示图标序列，注意事项列表",
        "tags": ["提示", "注意", "安全"],
        "max_depth": 1,
        "preview_html": "<p>⚠ 注意  ❗ 重要  ℹ 说明</p>",
        "is_system": True,
    },
    # ---------- english (4条) ----------
    {
        "id": "english-alpha",
        "name": "英文字母",
        "type": "english",
        "symbols": ["A.", "B.", "C.", "D.", "E."],
        "description": "英文字母序号，英文PPT/学术演示",
        "tags": ["英文", "学术"],
        "max_depth": 3,
        "preview_html": "<p>A. First  B. Second  C. Third</p>",
        "is_system": True,
    },
    {
        "id": "english-roman",
        "name": "罗马数字",
        "type": "english",
        "symbols": ["I.", "II.", "III.", "IV.", "V."],
        "description": "罗马数字序号，正式演讲/典礼",
        "tags": ["正式", "典礼", "学术"],
        "max_depth": 3,
        "preview_html": "<p>I. Prima  II. Secunda  III. Tertia</p>",
        "is_system": True,
    },
    {
        "id": "english-alpha-lower",
        "name": "小写英文字母",
        "type": "english",
        "symbols": ["a.", "b.", "c.", "d.", "e."],
        "description": "小写字母序号，温和风格列表",
        "tags": ["英文", "温和"],
        "max_depth": 3,
        "preview_html": "<p>a. first  b. second  c. third</p>",
        "is_system": True,
    },
    {
        "id": "english-roman-lower",
        "name": "小写罗马数字",
        "type": "english",
        "symbols": ["i.", "ii.", "iii.", "iv.", "v."],
        "description": "小写罗马数字，精致正式风格",
        "tags": ["正式", "精致"],
        "max_depth": 3,
        "preview_html": "<p>i. prima  ii. secunda  iii. tertia</p>",
        "is_system": True,
    },
    # ---------- special (3条) ----------
    {
        "id": "special-enclosed",
        "name": "圈码数字",
        "type": "special",
        "symbols": ["①", "②", "③", "④", "⑤"],
        "description": "圆形圈码，创意PPT/儿童教育",
        "tags": ["创意", "教育", "儿童"],
        "max_depth": 1,
        "preview_html": "<p>① 第一项  ② 第二项  ③ 第三项</p>",
        "is_system": True,
    },
    {
        "id": "special-enclosed-caps",
        "name": "大写圈码",
        "type": "special",
        "symbols": ["Ⓐ", "Ⓑ", "Ⓒ", "Ⓓ", "Ⓔ"],
        "description": "大写字母圈码，特殊标记列表",
        "tags": ["特殊", "标记"],
        "max_depth": 1,
        "preview_html": "<p>Ⓐ 第一项  Ⓑ 第二项  Ⓒ 第三项</p>",
        "is_system": True,
    },
    {
        "id": "special-enclosed-small",
        "name": "小写圈码",
        "type": "special",
        "symbols": ["ⓐ", "ⓑ", "ⓒ", "ⓓ", "ⓔ"],
        "description": "小写字母圈码，可爱风格列表",
        "tags": ["可爱", "轻松"],
        "max_depth": 1,
        "preview_html": "<p>ⓐ 第一项  ⓑ 第二项  ⓒ 第三项</p>",
        "is_system": True,
    },
]


class AssetItem(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    colors: Optional[Dict[str, str]] = None
    preview: Optional[str] = None
    hex: Optional[str] = None
    default_colors: Optional[str] = None
    default_fonts: Optional[str] = None
    template_count: Optional[int] = None
    avg_slides: Optional[float] = None


@router.get("/templates", response_model=List[AssetItem])
async def get_templates(category: Optional[str] = None):
    """获取模板列表（从DB读取）"""
    conn = _get_db()
    try:
        if category:
            rows = conn.execute("SELECT id, name, category, preview, description FROM templates WHERE category = ?", (category,)).fetchall()
        else:
            rows = conn.execute("SELECT id, name, category, preview, description FROM templates").fetchall()
        return [AssetItem(id=r['id'], name=r['name'], category=r['category'], preview=r['preview'], description=r['description']) for r in rows]
    finally:
        conn.close()


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


@router.get("/numbering-styles", response_model=List[Dict[str, Any]])
async def get_numbering_styles(
    type: Optional[str] = None,
    tags: Optional[str] = None,
):
    """获取序号样式列表，支持按类型和标签过滤"""
    result = NUMBERING_STYLES
    if type:
        result = [s for s in result if s["type"] == type]
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        result = [s for s in result if any(t in s["tags"] for t in tag_list)]
    return result


@router.get("/all", response_model=Dict[str, List[AssetItem]])
async def get_all_assets():
    """获取所有资产（内置 + DB 混合）"""
    conn = _get_db()
    try:
        # 从DB读取配色方案（降级：表不存在时使用空列表）
        color_rows = _safe_query(conn, "SELECT hex_color, category, tags, usage_count FROM color_palettes ORDER BY usage_count DESC")
        db_color_schemes = [{"id": f"color-{r['hex_color']}", "name": r['hex_color'], "hex": r['hex_color'], "category": r['category']} for r in color_rows]

        # 从DB读取字体
        font_rows = _safe_query(conn, "SELECT font_name, font_type, tags, usage_count FROM font_library ORDER BY usage_count DESC")
        db_fonts = [{"id": f"font-{r['font_name']}", "name": r['font_name'], "category": r['font_type']} for r in font_rows]

        # 从DB读取类别
        cat_rows = _safe_query(conn, "SELECT category_name, description, default_colors, default_fonts, template_count, avg_slides FROM template_categories ORDER BY category_name")
        db_categories = [{"id": r['category_name'], "name": r['category_name'], "description": r['description'], "default_colors": r['default_colors'], "default_fonts": r['default_fonts'], "template_count": r['template_count'], "avg_slides": r['avg_slides']} for r in cat_rows]

        # 从DB读取模板（主键为TEXT类型）
        db_rows = _safe_query(conn, "SELECT id, name, category, preview, description FROM templates")
        db_templates = [AssetItem(id=r['id'], name=r['name'], category=r['category'], preview=r['preview'], description=r['description']) for r in db_rows] if db_rows else [AssetItem(**t) for t in TEMPLATES]

        return {
            "templates": db_templates,
            "color_schemes": [AssetItem(id=c["id"], name=c["name"], colors=c["colors"]) for c in COLOR_SCHEMES],
            "db_color_palettes": db_color_schemes,
            "layouts": [AssetItem(id=l["id"], name=l["name"], description=l["description"]) for l in LAYOUTS],
            "fonts": [AssetItem(id=f["id"], name=f["name"], category=f["category"], description=f["usage"]) for f in FONTS],
            "db_fonts": db_fonts,
            "categories": db_categories,
            "animations": [AssetItem(id=a["id"], name=a["name"], category=a["category"]) for a in ANIMATIONS],
            "numbering_styles": NUMBERING_STYLES,
        }
    finally:
        conn.close()


# ========== 序号样式 CRUD（DB 持久化） ==========

class NumberingStyleRequest(BaseModel):
    id: str
    name: str
    type: str
    symbols: List[str]
    description: Optional[str] = None
    tags: List[str] = []
    max_depth: int = 1
    preview_html: Optional[str] = None
    is_system: bool = False


@router.get("/numbering-styles/list", response_model=List[Dict[str, Any]])
async def list_numbering_styles_db(
    type: Optional[str] = None,
    is_system: Optional[bool] = None,
):
    """从数据库列出序号样式"""
    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM numbering_styles")
        rows = cursor.fetchall()
        result = [dict(r) for r in rows]
        # 将 JSON 字符串字段解析为对象
        for row in result:
            if isinstance(row.get("symbols"), str):
                try:
                    row["symbols"] = json.loads(row["symbols"])
                except Exception:
                    pass
            if isinstance(row.get("tags"), str):
                try:
                    row["tags"] = json.loads(row["tags"])
                except Exception:
                    pass
            row["is_system"] = bool(row.get("is_system", False))
        if type:
            result = [r for r in result if r.get("type") == type]
        if is_system is not None:
            result = [r for r in result if r.get("is_system") == is_system]
        return result
    finally:
        conn.close()


@router.post("/numbering-styles", response_model=Dict[str, Any])
async def create_numbering_style(style: NumberingStyleRequest):
    """创建序号样式"""
    conn = _get_db()
    try:
        # 检查 ID 是否已存在
        row = conn.execute("SELECT id FROM numbering_styles WHERE id = ?", (style.id,)).fetchone()
        if row:
            raise HTTPException(status_code=409, detail=f"序号样式 ID '{style.id}' 已存在")
        conn.execute(
            """INSERT INTO numbering_styles
               (id, name, type, symbols, description, tags, max_depth, preview_html, is_system)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                style.id, style.name, style.type,
                json.dumps(style.symbols, ensure_ascii=False),
                style.description, json.dumps(style.tags, ensure_ascii=False),
                style.max_depth, style.preview_html, style.is_system,
            ),
        )
        conn.commit()
        return {"status": "created", "id": style.id}
    finally:
        conn.close()


@router.put("/numbering-styles/{style_id}", response_model=Dict[str, Any])
async def update_numbering_style(style_id: str, style: NumberingStyleRequest):
    """更新序号样式"""
    conn = _get_db()
    try:
        row = conn.execute("SELECT id FROM numbering_styles WHERE id = ?", (style_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="序号样式不存在")
        conn.execute(
            """UPDATE numbering_styles SET
               name=?, type=?, symbols=?, description=?, tags=?, max_depth=?, preview_html=?, is_system=?
               WHERE id=?""",
            (
                style.name, style.type,
                json.dumps(style.symbols, ensure_ascii=False),
                style.description, json.dumps(style.tags, ensure_ascii=False),
                style.max_depth, style.preview_html, style.is_system,
                style_id,
            ),
        )
        conn.commit()
        return {"status": "updated", "id": style_id}
    finally:
        conn.close()


@router.delete("/numbering-styles/{style_id}", response_model=Dict[str, Any])
async def delete_numbering_style(style_id: str):
    """删除序号样式（仅允许删除非系统样式）"""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT is_system FROM numbering_styles WHERE id = ?", (style_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="序号样式不存在")
        if row[0]:
            raise HTTPException(status_code=403, detail="系统内置序号样式不可删除")
        conn.execute("DELETE FROM numbering_styles WHERE id = ?", (style_id,))
        conn.commit()
        return {"status": "deleted", "id": style_id}
    finally:
        conn.close()


@router.get("/templates/list", response_model=List[Dict[str, Any]])
async def list_templates_db():
    """从数据库列出模板"""
    conn = _get_db()
    try:
        cursor = conn.execute("SELECT * FROM templates")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/templates/{template_id}/numbering")
async def get_template_numbering(template_id: str):
    """获取模板绑定的序号样式"""
    conn = _get_db()
    try:
        row = conn.execute(
            """SELECT tn.template_id, tn.numbering_id, tn.priority, ns.name, ns.type
               FROM template_numbering tn
               JOIN numbering_styles ns ON tn.numbering_id = ns.id
               WHERE tn.template_id = ?
               ORDER BY tn.priority""",
            (template_id,),
        ).fetchall()
        return [dict(r) for r in row]
    finally:
        conn.close()


@router.post("/templates/{template_id}/numbering/{numbering_id}")
async def link_template_numbering(template_id: str, numbering_id: str, priority: int = 0):
    """绑定模板与序号样式"""
    conn = _get_db()
    try:
        # 验证模板和序号样式存在
        t = conn.execute("SELECT id FROM templates WHERE id = ?", (template_id,)).fetchone()
        n = conn.execute("SELECT id FROM numbering_styles WHERE id = ?", (numbering_id,)).fetchone()
        if not t or not n:
            raise HTTPException(status_code=404, detail="模板或序号样式不存在")
        conn.execute(
            """INSERT OR REPLACE INTO template_numbering (template_id, numbering_id, priority)
               VALUES (?, ?, ?)""",
            (template_id, numbering_id, priority),
        )
        # 同时更新 templates.default_numbering_id（优先级最高的作为默认）
        conn.execute(
            """UPDATE templates SET default_numbering_id = ?
               WHERE id = ? AND (? = (SELECT MIN(priority) FROM template_numbering WHERE template_id = ?))""",
            (numbering_id, template_id, priority, template_id),
        )
        conn.commit()
        return {"status": "linked", "template_id": template_id, "numbering_id": numbering_id}
    finally:
        conn.close()


@router.delete("/templates/{template_id}/numbering/{numbering_id}")
async def unlink_template_numbering(template_id: str, numbering_id: str):
    """解除模板与序号样式的绑定"""
    conn = _get_db()
    try:
        conn.execute(
            "DELETE FROM template_numbering WHERE template_id = ? AND numbering_id = ?",
            (template_id, numbering_id),
        )
        # 如果解绑的是默认序号，清空 default_numbering_id
        t = conn.execute(
            "SELECT default_numbering_id FROM templates WHERE id = ?", (template_id,)
        ).fetchone()
        if t and t[0] == numbering_id:
            conn.execute(
                "UPDATE templates SET default_numbering_id = NULL WHERE id = ?",
                (template_id,),
            )
        conn.commit()
        return {"status": "unlinked"}
    finally:
        conn.close()
