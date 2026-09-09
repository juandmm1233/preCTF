"""Tests for dashboard endpoint."""
import pytest
from fastapi.testclient import TestClient


class TestDashboard:
    """Tests for GET /api/dashboard."""

    def test_dashboard_returns_8_levels(self, seeded_client: TestClient, student_token: str) -> None:
        """Dashboard returns exactly 8 levels."""
        response = seeded_client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["levels"]) == 8

    def test_dashboard_no_flag_plaintext(self, seeded_client: TestClient, student_token: str) -> None:
        """Dashboard never returns flag plaintext."""
        response = seeded_client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        data = response.json()
        response_text = str(data)
        assert "FLAG{" not in response_text
        for level in data["levels"]:
            assert "flag" not in level
            assert "flag_hash" not in level

    def test_dashboard_level_statuses(self, seeded_client: TestClient, student_token: str) -> None:
        """Dashboard shows correct level statuses: first available, rest locked."""
        response = seeded_client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        data = response.json()
        levels = data["levels"]
        assert levels[0]["status"] == "available"
        for level in levels[1:]:
            assert level["status"] == "locked"

    def test_dashboard_after_completing_level(self, seeded_client: TestClient, student_token: str) -> None:
        """After completing level 1, it shows completed and level 2 is available."""
        seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{PRECTF_N1_SQLI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        data = response.json()
        levels = data["levels"]
        assert levels[0]["status"] == "completed"
        assert levels[1]["status"] == "available"
        assert levels[2]["status"] == "locked"

    def test_dashboard_user_info(self, seeded_client: TestClient, student_token: str) -> None:
        """Dashboard returns correct user info."""
        response = seeded_client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        data = response.json()
        assert data["user"]["email"] == "student@test.local"
        assert data["user"]["score"] == 0
        assert data["completed"] == 0
        assert data["total"] == 8

    def test_dashboard_score_updates(self, seeded_client: TestClient, student_token: str) -> None:
        """Dashboard shows updated score after completing levels."""
        seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{PRECTF_N1_SQLI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        data = response.json()
        assert data["user"]["score"] == 50
        assert data["completed"] == 1

    def test_dashboard_unauthenticated_fails(self, seeded_client: TestClient) -> None:
        """Dashboard without auth returns 401."""
        response = seeded_client.get("/api/dashboard")
        assert response.status_code == 401
