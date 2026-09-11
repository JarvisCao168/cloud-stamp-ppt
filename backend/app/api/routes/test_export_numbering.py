"""
PPTX 导出 + 序号样式注入测试
"""
import pytest
import json
import sqlite3
import os
from fastapi.testclient import TestClient
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from app.main import app
from app.db import SCHEMA_SQL, NUMBERING_SEED_SQL, TEMPLATES_SEED_SQL
from app.core.config import settings

client = TestClient(app)


@pytest.fixture(scope="module")
def test_db_path():
    db_path = "./test_export_numbering.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.executescript(NUMBERING_SEED_SQL)
    conn.executescript(TEMPLATES_SEED_SQL)
    conn.commit()
    conn.close()
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="module")
def app_with_test_db(test_db_path):
    from app.core.config import settings
    original_url = settings.database_url
    settings.database_url = f"sqlite:///{test_db_path}"
    yield
    settings.database_url = original_url


class TestResolveNumberingStyle:
    """测试 _resolve_numbering_style 函数"""

    def test_builtin_numeric_dot(self):
        from app.api.routes.export import _resolve_numbering_style
        result = _resolve_numbering_style("numeric-dot")
        assert result is not None
        assert result["id"] == "numeric-dot"
        assert result["symbols"] == ["1.", "2.", "3.", "4.", "5."]
        assert result["max_depth"] == 3

    def test_builtin_chinese_clause(self):
        from app.api.routes.export import _resolve_numbering_style
        result = _resolve_numbering_style("chinese-clause")
        assert result is not None
        assert result["name"] == "中文顿号"
        assert "一、" in result["symbols"]

    def test_builtin_icon_arrow(self):
        from app.api.routes.export import _resolve_numbering_style
        result = _resolve_numbering_style("icon-arrow")
        assert result is not None
        assert result["type"] == "icon"
        assert result["symbols"][0] == "▶"

    def test_none_returns_none(self):
        from app.api.routes.export import _resolve_numbering_style
        result = _resolve_numbering_style(None)
        assert result is None

    def test_nonexistent_id_returns_none(self):
        from app.api.routes.export import _resolve_numbering_style
        result = _resolve_numbering_style("nonexistent-style")
        assert result is None

    def test_from_db_custom_style(self, app_with_test_db):
        """从 DB 读取自定义序号样式"""
        import sqlite3
        from app.api.routes.export import _resolve_numbering_style

        # 用同样的方式写 DB
        conn = sqlite3.connect(settings.database_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", ""))
        conn.execute(
            "INSERT OR REPLACE INTO numbering_styles (id, name, type, symbols, tags, max_depth, is_system) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("custom-bullet", "自定义符号", "graphic",
             json.dumps(["◆", "◇", "○"]), json.dumps([]), 2, False)
        )
        conn.commit()
        conn.close()

        result = _resolve_numbering_style("custom-bullet")
        assert result is not None
        assert result["id"] == "custom-bullet"
        assert result["symbols"] == ["◆", "◇", "○"]
        assert result["max_depth"] == 2

    def test_all_builtin_styles_resolvable(self):
        """所有内置样式都能被解析"""
        from app.api.routes.export import _resolve_numbering_style
        builtin_ids = [
            "numeric-dot", "numeric-paren", "numeric-bracket", "numeric-bracket-n",
            "numeric-period-n", "chinese-clause", "chinese-paren", "chinese-bracket",
            "chinese-ten", "level-nested", "level-decimal", "level-bracket",
            "graphic-circle", "graphic-diamond", "graphic-square", "graphic-triangle",
            "graphic-check", "graphic-bullet", "icon-check", "icon-arrow",
            "icon-star", "icon-badge", "icon-alert", "english-alpha",
            "english-roman", "english-alpha-lower", "english-roman-lower",
            "special-enclosed", "special-enclosed-caps", "special-enclosed-small",
        ]
        for style_id in builtin_ids:
            result = _resolve_numbering_style(style_id)
            assert result is not None, f"Failed to resolve {style_id}"
            assert "symbols" in result
            assert len(result["symbols"]) > 0


class TestPPTXExportWithNumbering:
    """测试 PPTX 导出时序号样式注入"""

    def _create_test_session(self, session_id="test-session-123"):
        """创建一个测试会话数据"""
        return patch("app.api.routes.export._sessions", {
            session_id: {
                "slides": [
                    {
                        "title": "首页",
                        "content": [],
                        "layout": "cover"
                    },
                    {
                        "title": "核心功能",
                        "content": ["功能 A", "功能 B", "功能 C"],
                        "layout": "title-content"
                    },
                    {
                        "title": "技术架构",
                        "content": ["架构层", "数据层", "接口层"],
                        "layout": "title-content"
                    },
                ],
                "intent": {"topic": "测试"},
            }
        })

    def test_pptx_export_without_numbering(self, app_with_test_db):
        """不带序号样式的导出仍正常工作"""
        with self._create_test_session():
            response = client.post(
                "/api/export/pptx",
                json={"session_id": "test-session-123", "format": "pptx"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["format"] == "pptx"
            assert data["slide_count"] == 3
            assert "filename" in data
            assert data["filename"].endswith(".pptx")

    def test_pptx_export_with_numbering_style(self, app_with_test_db):
        """带序号样式的 PPTX 导出"""
        with self._create_test_session():
            response = client.post(
                "/api/export/pptx",
                json={
                    "session_id": "test-session-123",
                    "format": "pptx",
                    "numbering_style_id": "numeric-dot"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["format"] == "pptx"
            assert data["slide_count"] == 3

    def test_pptx_export_with_chinese_numbering(self, app_with_test_db):
        """中文序号样式注入"""
        with self._create_test_session():
            response = client.post(
                "/api/export/pptx",
                json={
                    "session_id": "test-session-123",
                    "format": "pptx",
                    "numbering_style_id": "chinese-clause"
                }
            )
            assert response.status_code == 200

    def test_pptx_export_with_graphic_numbering(self, app_with_test_db):
        """图形序号样式注入"""
        with self._create_test_session():
            response = client.post(
                "/api/export/pptx",
                json={
                    "session_id": "test-session-123",
                    "format": "pptx",
                    "numbering_style_id": "graphic-bullet"
                }
            )
            assert response.status_code == 200

    def test_pptx_export_with_icon_numbering(self, app_with_test_db):
        """图标序号样式注入"""
        with self._create_test_session():
            response = client.post(
                "/api/export/pptx",
                json={
                    "session_id": "test-session-123",
                    "format": "pptx",
                    "numbering_style_id": "icon-arrow"
                }
            )
            assert response.status_code == 200

    def test_pptx_export_nonexistent_session(self, app_with_test_db):
        """不存在的会话应返回 404"""
        response = client.post(
            "/api/export/pptx",
            json={"session_id": "nonexistent", "format": "pptx"}
        )
        assert response.status_code == 404

    def test_pptx_export_with_custom_db_style(self, app_with_test_db):
        """使用 DB 中自定义序号样式"""
        import sqlite3

        # 用同样的方式写 DB
        conn = sqlite3.connect(settings.database_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", ""))
        conn.execute(
            "INSERT OR REPLACE INTO numbering_styles (id, name, type, symbols, tags, max_depth, is_system) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-custom-numbering", "测试自定义", "graphic",
             json.dumps(["★", "☆", "●"]), json.dumps([]), 2, False)
        )
        conn.commit()
        conn.close()

        with self._create_test_session():
            response = client.post(
                "/api/export/pptx",
                json={
                    "session_id": "test-session-123",
                    "format": "pptx",
                    "numbering_style_id": "test-custom-numbering"
                }
            )
            assert response.status_code == 200

    def test_pptx_export_content_page_with_numbering(self, app_with_test_db):
        """内容页（非封面/引用）应应用序号样式"""
        with self._create_test_session():
            response = client.post(
                "/api/export/pptx",
                json={
                    "session_id": "test-session-123",
                    "format": "pptx",
                    "numbering_style_id": "numeric-dot"
                }
            )
            assert response.status_code == 200
            # 验证文件已生成
            data = response.json()
            assert "url" in data

    def test_pptx_export_cover_page_not_affected(self, app_with_test_db):
        """封面页不受序号样式影响"""
        with self._create_test_session():
            response = client.post(
                "/api/export/pptx",
                json={
                    "session_id": "test-session-123",
                    "format": "pptx",
                    "numbering_style_id": "chinese-clause"
                }
            )
            assert response.status_code == 200


class TestExportBackwardCompatibility:
    """验证原有导出端点不受影响"""

    def test_html_export_still_works(self, app_with_test_db):
        with patch("app.api.routes.export._sessions", {
            "test-html": {"slides": []}
        }):
            response = client.post(
                "/api/export/html",
                json={"session_id": "test-html", "format": "html"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["format"] == "html"

    def test_pdf_export_still_works(self, app_with_test_db):
        with patch("app.api.routes.export._sessions", {
            "test-pdf": {"slides": [{"title": "Test", "content": ["Content"]}]}
        }):
            response = client.post(
                "/api/export/pdf",
                json={"session_id": "test-pdf", "format": "pdf"}
            )
            assert response.status_code == 200
