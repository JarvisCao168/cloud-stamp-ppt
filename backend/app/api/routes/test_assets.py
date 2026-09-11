"""
序号样式 CRUD API 测试
"""
import pytest
import json
import sqlite3
import os
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from app.main import app
from app.db import SCHEMA_SQL, NUMBERING_SEED_SQL, TEMPLATES_SEED_SQL
from app.api.routes.assets import _safe_query

client = TestClient(app)


@pytest.fixture(scope="module")
def test_db_path():
    """为测试创建临时 SQLite 数据库"""
    db_path = "./test_numbering_styles.db"
    # 删除旧数据库
    if os.path.exists(db_path):
        os.remove(db_path)
    # 创建测试数据库
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.executescript(NUMBERING_SEED_SQL)
    conn.executescript(TEMPLATES_SEED_SQL)
    conn.commit()
    conn.close()
    yield db_path
    # 清理
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="module")
def app_with_test_db(test_db_path):
    """使用测试数据库的 FastAPI 应用"""
    from app.core.config import settings
    original_url = settings.database_url
    settings.database_url = f"sqlite:///{test_db_path}"
    yield
    settings.database_url = original_url


class TestListNumberingStyles:
    """测试 GET /api/assets/numbering-styles/list"""

    def test_list_all(self, app_with_test_db):
        response = client.get("/api/assets/numbering-styles/list")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 30

    def test_filter_by_type(self, app_with_test_db):
        response = client.get("/api/assets/numbering-styles/list?type=numeric")
        assert response.status_code == 200
        data = response.json()
        assert all(item["type"] == "numeric" for item in data)
        assert len(data) == 5

    def test_filter_by_is_system_true(self, app_with_test_db):
        response = client.get("/api/assets/numbering-styles/list?is_system=true")
        assert response.status_code == 200
        data = response.json()
        assert all(item["is_system"] is True for item in data)

    def test_json_fields_parsed(self, app_with_test_db):
        response = client.get("/api/assets/numbering-styles/list?type=numeric&is_system=true")
        data = response.json()
        item = data[0]
        assert isinstance(item["symbols"], list)
        assert isinstance(item["tags"], list)
        assert item["symbols"][0] == "1."


class TestCreateNumberingStyle:
    """测试 POST /api/assets/numbering-styles"""

    def test_create_new_style(self, app_with_test_db):
        payload = {
            "id": "custom-test-001",
            "name": "测试自定义样式",
            "type": "numeric",
            "symbols": ["A1.", "A2.", "A3."],
            "description": "测试用",
            "tags": ["测试"],
            "max_depth": 3,
            "preview_html": "<p>测试</p>",
            "is_system": False,
        }
        response = client.post("/api/assets/numbering-styles", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "created"

    def test_create_duplicate_id(self, app_with_test_db):
        payload = {
            "id": "numeric-dot",  # 已存在
            "name": "重复测试",
            "type": "numeric",
            "symbols": ["1.", "2."],
            "tags": [],
            "max_depth": 3,
            "is_system": False,
        }
        response = client.post("/api/assets/numbering-styles", json=payload)
        assert response.status_code == 409


class TestUpdateNumberingStyle:
    """测试 PUT /api/assets/numbering-styles/{id}"""

    def test_update_existing(self, app_with_test_db):
        payload = {
            "id": "numeric-dot",
            "name": "更新后的数字序号",
            "type": "numeric",
            "symbols": ["1.", "2.", "3.", "4.", "5."],
            "tags": ["商务"],
            "max_depth": 3,
            "is_system": True,
        }
        response = client.put("/api/assets/numbering-styles/numeric-dot", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "updated"

    def test_update_nonexistent(self, app_with_test_db):
        payload = {
            "id": "nonexistent-style",
            "name": "不存在",
            "type": "numeric",
            "symbols": [],
            "tags": [],
            "max_depth": 1,
            "is_system": False,
        }
        response = client.put("/api/assets/numbering-styles/nonexistent-style", json=payload)
        assert response.status_code == 404


class TestDeleteNumberingStyle:
    """测试 DELETE /api/assets/numbering-styles/{id}"""

    def test_delete_user_created(self, app_with_test_db):
        # 先创建一个用户样式
        create_payload = {
            "id": "delete-test-001",
            "name": "待删除样式",
            "type": "numeric",
            "symbols": ["X1."],
            "tags": [],
            "max_depth": 1,
            "is_system": False,
        }
        client.post("/api/assets/numbering-styles", json=create_payload)

        response = client.delete("/api/assets/numbering-styles/delete-test-001")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_system_style_forbidden(self, app_with_test_db):
        response = client.delete("/api/assets/numbering-styles/numeric-dot")
        assert response.status_code == 403

    def test_delete_nonexistent(self, app_with_test_db):
        response = client.delete("/api/assets/numbering-styles/nonexistent-style")
        assert response.status_code == 404


class TestTemplateNumbering:
    """测试模板与序号样式的关联"""

    def test_get_template_numbering(self, app_with_test_db):
        response = client.get("/api/assets/templates/modern-dark/numbering")
        assert response.status_code == 200

    def test_link_template_numbering(self, app_with_test_db):
        response = client.post(
            "/api/assets/templates/modern-dark/numbering/chinese-clause",
            params={"priority": 0},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "linked"

    def test_unlink_template_numbering(self, app_with_test_db):
        response = client.delete(
            "/api/assets/templates/modern-dark/numbering/chinese-clause"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "unlinked"


class TestBackwardCompatibility:
    """验证原有端点不受影响"""

    def test_numbering_styles_endpoint(self, app_with_test_db):
        response = client.get("/api/assets/numbering-styles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 30

    def test_all_assets_endpoint(self, app_with_test_db):
        response = client.get("/api/assets/all")
        assert response.status_code == 200
        data = response.json()
        assert "numbering_styles" in data
        assert len(data["numbering_styles"]) == 30

    def test_templates_endpoint(self, app_with_test_db):
        response = client.get("/api/assets/templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6
