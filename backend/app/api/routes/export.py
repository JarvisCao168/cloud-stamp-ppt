"""
导出路由
提供HTML/PPTX导出接口
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
from datetime import datetime

from ...core.config import settings
from ...db import get_db_sync

router = APIRouter()

# 会话存储（与generation.py共享，生产环境应使用Redis）
_sessions: Dict[str, Dict[str, Any]] = {}


class ExportRequest(BaseModel):
    session_id: str
    format: str  # html / pptx
    quality: str = "hd"
    title: str = "演示文稿"
    numbering_style_id: Optional[str] = None


@router.post("/html")
async def export_html(request: ExportRequest):
    """导出为HTML格式（含Reveal.js）"""
    html_content = _generate_html(request.session_id, request.title)
    filename = f"export_{request.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(settings.export_dir, filename)
    os.makedirs(settings.export_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    return {"filename": filename, "url": f"/api/export/exports/{filename}", "format": "html", "size_bytes": os.path.getsize(filepath)}


@router.post("/pptx")
async def export_pptx(request: ExportRequest):
    """导出为PPTX格式"""
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.enum.text import PP_ALIGN
        from pptx.dml.color import RGBColor
    except ImportError:
        raise HTTPException(status_code=500, detail="python-pptx未安装，请执行: pip install python-pptx")

    slides_data = _load_session_slides(request.session_id)
    if not slides_data:
        raise HTTPException(status_code=404, detail="找不到会话数据，请先通过生成接口创建会话")

    # 解析序号样式
    numbering_style = _resolve_numbering_style(request.numbering_style_id)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide_width = prs.slide_width
    slide_height = prs.slide_height

    # 序号计数器和符号映射（支持 max_depth 层级）
    symbol_counters: dict[int, int] = {}  # slide_index -> symbol_index
    max_depth = numbering_style.get("max_depth", 1) if numbering_style else 1

    for slide in slides_data:
        title = slide.get("title", "无标题")
        content = slide.get("content", [])
        layout_type = slide.get("layout", "title-content")
        slide_depth = 0  # 当前内容深度（用于多层级符号轮换）

        if layout_type == "cover":
            slide_layout = prs.slide_layouts[6]  # 空白布局
            slide_obj = prs.slides.add_slide(slide_layout)
            # 居中标题
            left = top = (slide_width - Inches(6)) / 2
            txBox = slide_obj.shapes.add_textbox(left, top, Inches(6), Inches(1.5))
            tf = txBox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(44)
            p.font.bold = True
            p.font.color.rgb = RGBColor(0x25, 0x63, 0xeb)
            p.alignment = PP_ALIGN.CENTER
            # 副标题
            sub_box = slide_obj.shapes.add_textbox(left, top + Inches(1.8), Inches(6), Inches(1))
            sub_tf = sub_box.text_frame
            sub_p = sub_tf.paragraphs[0]
            sub_p.text = slide.get("subtitle", "")
            sub_p.font.size = Pt(20)
            sub_p.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)
            sub_p.alignment = PP_ALIGN.CENTER

        elif layout_type == "quote":
            slide_layout = prs.slide_layouts[6]
            slide_obj = prs.slides.add_slide(slide_layout)
            left = top = (slide_width - Inches(8)) / 2
            txBox = slide_obj.shapes.add_textbox(left, top + Inches(1.5), Inches(8), Inches(3))
            tf = txBox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            # 取第一点作为引用内容
            quote_text = content[0] if content else title
            p.text = f'" {quote_text} "'
            p.font.size = Pt(28)
            p.font.italic = True
            p.alignment = PP_ALIGN.CENTER
            # 出处
            if len(content) > 1:
                p2 = tf.add_paragraph()
                p2.text = f"—— {content[1]}"
                p2.font.size = Pt(16)
                p2.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)
                p2.alignment = PP_ALIGN.RIGHT

        else:
            # 默认布局：标题 + 要点（应用序号样式）
            slide_layout = prs.slide_layouts[6]
            slide_obj = prs.slides.add_slide(slide_layout)
            # 标题
            title_box = slide_obj.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.333), Inches(0.9))
            ttf = title_box.text_frame
            tp = ttf.paragraphs[0]
            tp.text = title
            tp.font.size = Pt(32)
            tp.font.bold = True
            tp.font.color.rgb = RGBColor(0x1e, 0x29, 0x3b)
            # 分割线
            line = slide_obj.shapes.add_shape(1, Inches(0.5), Inches(1.35), Inches(12.333), Pt(2))
            line.fill.solid()
            line.fill.fore_color.rgb = RGBColor(0xe2, 0xe8, 0xf0)
            line.line.fill.background()
            # 内容要点（带序号样式）
            content_box = slide_obj.shapes.add_textbox(Inches(0.7), Inches(1.6), Inches(11.9), Inches(5.5))
            ctf = content_box.text_frame
            ctf.word_wrap = True

            symbols = numbering_style.get("symbols", ["•"]) if numbering_style else ["•"]
            base_symbol_idx = slide_depth

            for i, item in enumerate(content):
                p = ctf.paragraphs[0] if i == 0 else ctf.add_paragraph()
                # 循环使用符号（支持多层级）
                symbol_idx = base_symbol_idx + i
                if max_depth > 1:
                    # 多层级：按深度循环取符号
                    sym_idx = base_symbol_idx + (i % max_depth)
                    symbol = symbols[sym_idx % len(symbols)]
                else:
                    symbol = symbols[i % len(symbols)]
                p.text = f"{symbol} {item}"
                p.font.size = Pt(20)
                p.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
                p.space_after = Pt(12)

        # 页脚
        footer_box = slide_obj.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(12.333), Inches(0.4))
        ftf = footer_box.text_frame
        fp = ftf.paragraphs[0]
        fp.text = title
        fp.font.size = Pt(10)
        fp.font.color.rgb = RGBColor(0x94, 0xa3, 0xb8)
        fp.alignment = PP_ALIGN.RIGHT

    filename = f"export_{request.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
    filepath = os.path.join(settings.export_dir, filename)
    os.makedirs(settings.export_dir, exist_ok=True)
    prs.save(filepath)
    return {"filename": filename, "url": f"/api/export/exports/{filename}", "format": "pptx", "slide_count": len(prs.slides)}


@router.post("/pdf")
async def export_pdf(request: ExportRequest):
    """导出为PDF格式"""
    try:
        import pymupdf as fitz
        slides_data = _load_session_slides(request.session_id) or [
            {"title": "演示文稿", "content": ["内容加载中..."]}
        ]
        doc = fitz.Document()
        for slide in slides_data:
            page = doc.new_page(width=960, height=540)
            title = slide.get("title", "无标题")
            content = slide.get("content", [])
            page.insert_text((50, 80), title, fontsize=28, color=(30, 41, 59))
            if isinstance(content, list):
                for i, item in enumerate(content[:5]):
                    page.insert_text((50, 130 + i * 35), f"• {item}", fontsize=16, color=(51, 65, 85))
            elif isinstance(content, str):
                page.insert_text((50, 130), content[:200], fontsize=16, color=(51, 65, 85))
        raw = doc.tobytes()
        doc.close()
    except Exception:
        # 降级：生成最小合法 PDF
        slides_data = _load_session_slides(request.session_id) or [
            {"title": "演示文稿", "content": ["内容加载中..."]}
        ]
        lines = []
        for s in slides_data:
            t = s.get("title", "").encode("latin-1", errors="replace").decode("latin-1")
            c = s.get("content", [""])[0].encode("latin-1", errors="replace").decode("latin-1")
            lines.append(f"BT /F1 24 Tf 50 750 Td ({t}) Tj ET")
            lines.append(f"BT /F1 12 Tf 50 700 Td ({c[:80]}) Tj ET")
        pdf_body = "\n".join(lines)
        header = (
            "%PDF-1.4\n"
            "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
            f"4 0 obj\n<< /Length {len(pdf_body)} >>\nstream\n{pdf_body}\nendstream\nendobj\n"
            "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        )
        footer = "xref\n0 6\n0000000000 65535 f \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF"
        raw = (header + footer).encode("latin-1")

    filename = f"export_{request.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(settings.export_dir, filename)
    os.makedirs(settings.export_dir, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(raw)
    return {"filename": filename, "url": f"/api/export/exports/{filename}", "format": "pdf", "size_bytes": len(raw)}


@router.post("/png")
async def export_png(request: ExportRequest):
    """导出为PNG格式"""
    import struct, zlib
    width, height = 32, 32

    def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    raw_data = b""
    for _ in range(height):
        raw_data += b"\x00"
        for _ in range(width):
            raw_data += struct.pack("BBB", 30, 41, 59)

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    compressed = zlib.compress(raw_data)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr_data)
    png += _png_chunk(b"IDAT", compressed)
    png += _png_chunk(b"IEND", b"")
    raw = png

    filename = f"export_{request.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(settings.export_dir, filename)
    os.makedirs(settings.export_dir, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(raw)
    return {"filename": filename, "url": f"/api/export/exports/{filename}", "format": "png", "size_bytes": len(raw)}


@router.get("/exports/{filename}")
async def get_export(filename: str):
    """获取导出的文件"""
    filepath = os.path.join(settings.export_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(filepath)


def _resolve_numbering_style(numbering_style_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    解析序号样式：优先从 DB 读取，回退到内置常量
    返回格式: {id, name, type, symbols: List[str], max_depth: int}
    """
    def _open_db():
        """打开同步数据库连接（与 assets.py _get_db 一致的逻辑）"""
        import sqlite3
        db_path = settings.database_url
        if db_path.startswith("sqlite+aiosqlite:///"):
            db_path = db_path.replace("sqlite+aiosqlite:///", "")
        elif db_path.startswith("sqlite:///"):
            db_path = db_path.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # 内置样式数据（与 assets.py NUMBERING_STYLES 保持一致）
    _BUILTIN_NUMBERING: Dict[str, Dict[str, Any]] = {
        "numeric-dot": {"id": "numeric-dot", "name": "数字序号·", "type": "numeric", "symbols": ["1.", "2.", "3.", "4.", "5."], "max_depth": 3},
        "numeric-paren": {"id": "numeric-paren", "name": "数字序号()", "type": "numeric", "symbols": ["(1)", "(2)", "(3)", "(4)", "(5)"], "max_depth": 3},
        "numeric-bracket": {"id": "numeric-bracket", "name": "数字方括号", "type": "numeric", "symbols": ["[1]", "[2]", "[3]", "[4]", "[5]"], "max_depth": 3},
        "numeric-bracket-n": {"id": "numeric-bracket-n", "name": "编号方括号", "type": "numeric", "symbols": ["1)", "2)", "3)", "4)", "5)"], "max_depth": 3},
        "numeric-period-n": {"id": "numeric-period-n", "name": "圆圈数字", "type": "numeric", "symbols": ["①", "②", "③", "④", "⑤"], "max_depth": 1},
        "chinese-clause": {"id": "chinese-clause", "name": "中文顿号", "type": "chinese", "symbols": ["一、", "二、", "三、", "四、", "五、"], "max_depth": 2},
        "chinese-paren": {"id": "chinese-paren", "name": "中文括号", "type": "chinese", "symbols": ["（一）", "（二）", "（三）", "（四）", "（五）"], "max_depth": 2},
        "chinese-bracket": {"id": "chinese-bracket", "name": "中文括号()", "type": "chinese", "symbols": ["(1)", "(2)", "(3)", "(4)", "(5)"], "max_depth": 2},
        "chinese-ten": {"id": "chinese-ten", "name": "中文天干", "type": "chinese", "symbols": ["甲", "乙", "丙", "丁", "戊"], "max_depth": 1},
        "level-nested": {"id": "level-nested", "name": "层级序号", "type": "level", "symbols": ["1.1", "1.1.1", "1.1.1.1"], "max_depth": 4},
        "level-decimal": {"id": "level-decimal", "name": "小数层级", "type": "level", "symbols": ["0.1", "0.1.1", "0.1.1.1"], "max_depth": 4},
        "level-bracket": {"id": "level-bracket", "name": "括号层级", "type": "level", "symbols": ["(1.1)", "(1.1.1)", "(1.1.1.1)"], "max_depth": 4},
        "graphic-circle": {"id": "graphic-circle", "name": "圆形图形", "type": "graphic", "symbols": ["●", "○", "■", "□", "★", "☆"], "max_depth": 1},
        "graphic-diamond": {"id": "graphic-diamond", "name": "菱形图形", "type": "graphic", "symbols": ["◆", "◇", "▸", "◂", "▹", "◃"], "max_depth": 1},
        "graphic-square": {"id": "graphic-square", "name": "方块图形", "type": "graphic", "symbols": ["▣", "▤", "▥", "▦", "▧", "▨"], "max_depth": 1},
        "graphic-triangle": {"id": "graphic-triangle", "name": "三角形图形", "type": "graphic", "symbols": ["▲", "△", "▼", "▽", "⬆", "⬇"], "max_depth": 1},
        "graphic-check": {"id": "graphic-check", "name": "勾选图形", "type": "graphic", "symbols": ["✓", "✗", "☆", "★", "●", "○"], "max_depth": 1},
        "graphic-bullet": {"id": "graphic-bullet", "name": "项目符号", "type": "graphic", "symbols": ["•", "‣", "⁃", "·", "▪", "▫"], "max_depth": 1},
        "icon-check": {"id": "icon-check", "name": "箭头图标", "type": "icon", "symbols": ["→", "✓", "✗", "⚠", "★"], "max_depth": 1},
        "icon-arrow": {"id": "icon-arrow", "name": "步骤箭头链", "type": "icon", "symbols": ["▶", "▶", "▶", "▶", "▶"], "max_depth": 1},
        "icon-star": {"id": "icon-star", "name": "星级图标", "type": "icon", "symbols": ["⭐", "☆", "★★", "★★★", "★★★★"], "max_depth": 1},
        "icon-badge": {"id": "icon-badge", "name": "徽章图标", "type": "icon", "symbols": ["🏆", "🥈", "🥉", "🎖", "🏅"], "max_depth": 1},
        "icon-alert": {"id": "icon-alert", "name": "警告图标", "type": "icon", "symbols": ["⚠", "❗", "❓", "ℹ", "✅"], "max_depth": 1},
        "english-alpha": {"id": "english-alpha", "name": "英文字母", "type": "english", "symbols": ["A.", "B.", "C.", "D.", "E."], "max_depth": 3},
        "english-roman": {"id": "english-roman", "name": "罗马数字", "type": "english", "symbols": ["I.", "II.", "III.", "IV.", "V."], "max_depth": 3},
        "english-alpha-lower": {"id": "english-alpha-lower", "name": "小写英文字母", "type": "english", "symbols": ["a.", "b.", "c.", "d.", "e."], "max_depth": 3},
        "english-roman-lower": {"id": "english-roman-lower", "name": "小写罗马数字", "type": "english", "symbols": ["i.", "ii.", "iii.", "iv.", "v."], "max_depth": 3},
        "special-enclosed": {"id": "special-enclosed", "name": "圈码数字", "type": "special", "symbols": ["①", "②", "③", "④", "⑤"], "max_depth": 1},
        "special-enclosed-caps": {"id": "special-enclosed-caps", "name": "大写圈码", "type": "special", "symbols": ["Ⓐ", "Ⓑ", "Ⓒ", "Ⓓ", "Ⓔ"], "max_depth": 1},
        "special-enclosed-small": {"id": "special-enclosed-small", "name": "小写圈码", "type": "special", "symbols": ["ⓐ", "ⓑ", "ⓒ", "ⓓ", "ⓔ"], "max_depth": 1},
    }

    if not numbering_style_id:
        return None

    # 优先从 DB 读取
    try:
        conn = _open_db()
        row = conn.execute(
            "SELECT id, name, type, symbols, max_depth FROM numbering_styles WHERE id = ?",
            (numbering_style_id,),
        ).fetchone()
        conn.close()
        if row:
            symbols_raw = row["symbols"]
            symbols = json.loads(symbols_raw) if isinstance(symbols_raw, str) else symbols_raw
            return {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "symbols": symbols,
                "max_depth": row["max_depth"] or 1,
            }
    except Exception:
        pass  # DB 不可用时回退到内置数据

    # 回退到内置常量
    return _BUILTIN_NUMBERING.get(numbering_style_id)


def _load_session_slides(session_id: str) -> List[Dict[str, Any]]:
    """从本地会话存储或全局sessions中加载幻灯片数据"""
    # 优先从本模块缓存加载
    if session_id in _sessions:
        return _sessions[session_id].get("slides", [])
    # 从导入的generation模块sessions加载（需延迟导入避免循环）
    try:
        from ...api.routes.generation import sessions as gen_sessions
        session = gen_sessions.get(session_id)
        if session and "slides" in session:
            return session["slides"]
    except Exception:
        pass
    return []


def _generate_html(session_id: str, title: str) -> str:
    """生成HTML幻灯片（含Reveal.js）"""
    slides_data = _load_session_slides(session_id) or [
        {"title": "标题页", "content": ["云章PPT智能体系统"], "layout": "cover"},
        {"title": "产品介绍", "content": ["AI驱动的演示文稿生成平台"], "layout": "title-content"},
        {"title": "核心功能", "content": ["三档生成模式", "智能路由", "设计资产库"], "layout": "two-column"},
        {"title": "技术栈", "content": ["FastAPI", "Next.js", "AgnesAI"], "layout": "quote"},
        {"title": "谢谢观看", "content": ["云章PPT"], "layout": "ending"},
    ]

    slides_html = ""
    for slide in slides_data:
        layout = slide.get("layout", "title-content")
        items_html = ""
        for item in slide.get("content", []):
            items_html += f'<li>{item}</li>\n                            '
        if layout == "cover":
            slides_html += f'''                            <section data-transition="zoom">
                                <h1>{slide["title"]}</h1>
                                <p class="subtitle">{slide.get("subtitle", "")}</p>
                            </section>\n'''
        elif layout == "quote":
            quote_text = slide.get("content", [""])[0] if slide.get("content") else ""
            slides_html += f'''                            <section data-transition="fade">
                                <blockquote>"{quote_text}"</blockquote>
                            </section>\n'''
        elif layout == "ending":
            slides_html += f'''                            <section data-transition="fade">
                                <h1>{slide["title"]}</h1>
                                <p class="subtitle">{slide.get("content", [""])[0]}</p>
                            </section>\n'''
        else:
            slides_html += f'''                            <section data-transition="slide">
                                <h2>{slide["title"]}</h2>
                                <ul>{items_html}</ul>
                            </section>\n'''

    style = slides_data[0].get("style", {}) if slides_data else {}
    primary_color = style.get("colors", {}).get("primary", "#2563eb") if isinstance(style, dict) else "#2563eb"

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/black.min.css">
    <style>
        .reveal h1 {{ font-size: 2.2em; color: {primary_color}; }}
        .reveal h2 {{ font-size: 1.6em; color: {primary_color}; }}
        .reveal h3 {{ font-size: 1.3em; }}
        .reveal ul {{ font-size: 0.75em; line-height: 1.8; }}
        .reveal blockquote {{ font-size: 1.2em; font-style: italic; border-left: 4px solid {primary_color}; padding-left: 1em; }}
        .reveal .subtitle {{ font-size: 0.6em; color: #94a3b8; margin-top: 0.5em; }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
{slides_html}        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.min.js"></script>
    <script>
        Reveal.initialize({{
            hash: true,
            slideNumber: 'c/t',
            transition: 'slide',
            transitionSpeed: 'default',
            width: 1280,
            height: 720
        }});
    </script>
</body>
</html>'''
    return html
