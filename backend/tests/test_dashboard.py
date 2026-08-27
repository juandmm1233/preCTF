"""
Test dashboard endpoint.
"""

import pytest

from tests.conftest import reset_rate_limiter


class TestDashboard:
    """Tests for GET /api/dashboard."""

    def test_dashboard_returns_user_info(self, client, auth_headers):
        """Dashboard includes user information."""
        response = client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "email" in data["user"]
        assert "score" in data["user"]

    def test_dashboard_returns_all_8_levels(self, client, auth_headers):
        """Dashboard includes all 8 training levels."""
        response = client.get("/api/dashboard", headers=auth_headers)
        data = response.json()
        assert len(data["levels"]) == 8
        assert data["total"] == 8

    def test_dashboard_shows_correct_completion_count(self, client, auth_headers, test_flags):
        """Dashboard shows correct completed count after progress."""
        reset_rate_limiter()
        
        dash_initial = client.get("/api/dashboard", headers=auth_headers).json()
        assert dash_initial["completed"] == 0
        
        client.post(
            "/api/levels/1/submit",
            json={"flag": test_flags[1]},
            headers=auth_headers,
        )
        
        dash_after = client.get("/api/dashboard", headers=auth_headers).json()
        assert dash_after["completed"] == 1

    def test_dashboard_without_auth_fails(self, client):
        """Dashboard without authentication returns 401."""
        response = client.get("/api/dashboard")
        assert response.status_code == 401

    def test_dashboard_levels_have_required_fields(self, client, auth_headers):
        """Each level card has all required fields."""
        response = client.get("/api/dashboard", headers=auth_headers)
        data = response.json()
        
        required_fields = [
            "id", "order_index", "slug", "title", "vector_name",
            "lab_endpoint", "description", "points", "hint_cost",
            "is_bonus", "status", "hint_used"
        ]
        
        for level in data["levels"]:
            for field in required_fields:
                assert field in level, f"Level missing field: {field}"

    def test_dashboard_no_flag_plaintext_exposed(self, client, auth_headers):
        """Dashboard response does not expose flag plaintext."""
        response = client.get("/api/dashboard", headers=auth_headers)
        data = response.json()
        
        response_str = str(data)
        assert "FLAG{" not in response_str
        assert "PRECTF_N" not in response_str
