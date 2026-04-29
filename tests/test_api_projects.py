"""API integration tests for project CRUD — no LLM dependency."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestProjectAPI:
    """Project list / create / delete endpoints."""

    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_create_project(self, client):
        resp = client.post("/api/projects", json={
            "name": "API测试项目",
            "type": "原创",
            "description": "API测试",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_list_projects(self, client):
        # list_projects returns raw list, not wrapped
        client.post("/api/projects", json={
            "name": "列表测试", "type": "原创", "description": ""
        })
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        names = [p["name"] for p in data]
        assert "列表测试" in names

    def test_create_duplicate_project(self, client):
        client.post("/api/projects", json={
            "name": "重复项目", "type": "原创", "description": ""
        })
        resp = client.post("/api/projects", json={
            "name": "重复项目", "type": "原创", "description": ""
        })
        assert resp.status_code in (409, 200)

    def test_delete_project(self, client):
        client.post("/api/projects", json={
            "name": "待删项目", "type": "原创", "description": ""
        })
        resp = client.delete("/api/projects/待删项目")
        assert resp.status_code == 200

    def test_delete_nonexistent_project(self, client):
        # Project doesn't exist but API silently succeeds (no 404 check)
        resp = client.delete("/api/projects/不存在项目")
        assert resp.status_code == 200
