"""API integration tests for settings CRUD — no LLM dependency."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_project(client):
    client.post("/api/projects", json={
        "name": "设定测试项目", "type": "原创", "description": ""
    })
    return "设定测试项目"


class TestSettingsAPI:
    """Settings read/write endpoints."""

    def test_get_all_settings_empty(self, client, test_project):
        resp = client.get(f"/api/settings/{test_project}/all")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "settings" in data
        assert isinstance(data["settings"], list)

    def test_save_and_read_world_setting(self, client, test_project):
        resp = client.put(
            f"/api/settings/{test_project}/world",
            json={"project": test_project, "content": "# 测试世界\n这是测试内容"}
        )
        assert resp.status_code == 200
        resp2 = client.get(f"/api/settings/{test_project}/world")
        assert resp2.status_code == 200
        data = resp2.json()
        assert "测试世界" in data.get("content", "")

    def test_save_and_read_character(self, client, test_project):
        resp = client.put(
            f"/api/settings/{test_project}/characters/测试角色",
            json={"project": test_project, "content": "## 基本信息\n测试角色内容"}
        )
        assert resp.status_code == 200
        resp2 = client.get(f"/api/settings/{test_project}/characters/测试角色")
        assert resp2.status_code == 200
        data = resp2.json()
        assert "基本信息" in data.get("content", "")

    def test_list_characters(self, client, test_project):
        client.put(
            f"/api/settings/{test_project}/characters/角色A",
            json={"project": test_project, "content": "内容A"}
        )
        client.put(
            f"/api/settings/{test_project}/characters/角色B",
            json={"project": test_project, "content": "内容B"}
        )
        resp = client.get(f"/api/settings/{test_project}/characters")
        assert resp.status_code == 200
        data = resp.json()
        assert "角色A" in data.get("characters", [])
        assert "角色B" in data.get("characters", [])

    def test_delete_character(self, client, test_project):
        client.put(
            f"/api/settings/{test_project}/characters/待删角色",
            json={"project": test_project, "content": "内容"}
        )
        resp = client.delete(f"/api/settings/{test_project}/characters/待删角色")
        assert resp.status_code == 200
        resp2 = client.get(f"/api/settings/{test_project}/characters")
        assert "待删角色" not in resp2.json().get("characters", [])

    def test_save_timeline(self, client, test_project):
        resp = client.put(
            f"/api/settings/{test_project}/timeline",
            json={"project": test_project, "background": "# 背景时间线\n测试", "story": "# 故事时间线\n测试"}
        )
        assert resp.status_code == 200

    def test_save_relationship(self, client, test_project):
        resp = client.put(
            f"/api/settings/{test_project}/relationship",
            json={"project": test_project, "content": "# 人物关系\n测试"}
        )
        assert resp.status_code == 200

    def test_save_style_guide(self, client, test_project):
        resp = client.put(
            f"/api/settings/{test_project}/style-guide",
            json={"project": test_project, "content": "# 风格指南\n测试"}
        )
        assert resp.status_code == 200
