"""Tests for GET /api/health endpoint."""
import pytest
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    """GET /api/health returns status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}
