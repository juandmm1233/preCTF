"""
Test hint endpoint: reveal hint, points deducted only once.
"""

import pytest

from tests.conftest import reset_rate_limiter


class TestHintEndpoint:
    """Tests for POST /api/levels/{level_id}/hint."""

    def test_first_hint_request_returns_hint_text(self, client, auth_headers):
        """First hint request reveals hint text."""
        response = client.post("/api/levels/1/hint", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "hint" in data
        assert len(data["hint"]) > 0
        assert data["already_used"] is False

    def test_first_hint_deducts_points(self, client, auth_headers):
        """First hint request deducts hint_cost points."""
        dash_before = client.get("/api/dashboard", headers=auth_headers).json()
        initial_score = dash_before["user"]["score"]
        level_1 = next(l for l in dash_before["levels"] if l["order_index"] == 1)
        hint_cost = level_1["hint_cost"]
        
        response = client.post("/api/levels/1/hint", headers=auth_headers)
        data = response.json()
        assert data["points_delta"] == -hint_cost
        assert data["score"] == max(0, initial_score - hint_cost)

    def test_second_hint_request_no_additional_deduction(self, client, auth_headers):
        """Second hint request returns hint but deducts 0 points."""
        client.post("/api/levels/1/hint", headers=auth_headers)
        
        dash_mid = client.get("/api/dashboard", headers=auth_headers).json()
        score_after_first = dash_mid["user"]["score"]
        
        response = client.post("/api/levels/1/hint", headers=auth_headers)
        data = response.json()
        assert data["already_used"] is True
        assert data["points_delta"] == 0
        assert data["score"] == score_after_first

    def test_hint_for_locked_level_returns_403(self, client, auth_headers):
        """Requesting hint for locked level returns 403."""
        response = client.post("/api/levels/2/hint", headers=auth_headers)
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "LEVEL_LOCKED"

    def test_hint_for_nonexistent_level_returns_404(self, client, auth_headers):
        """Requesting hint for non-existent level returns 404."""
        response = client.post("/api/levels/999/hint", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "LEVEL_NOT_FOUND"

    def test_hint_marked_in_dashboard(self, client, auth_headers):
        """After using hint, dashboard shows hint_used=True."""
        client.post("/api/levels/1/hint", headers=auth_headers)
        
        dash = client.get("/api/dashboard", headers=auth_headers).json()
        level_1 = next(l for l in dash["levels"] if l["order_index"] == 1)
        assert level_1["hint_used"] is True

    def test_multiple_levels_hints_independent(self, client, auth_headers, test_flags):
        """Using hints on different levels are tracked independently."""
        reset_rate_limiter()
        
        client.post("/api/levels/1/hint", headers=auth_headers)
        
        client.post(
            "/api/levels/1/submit",
            json={"flag": test_flags[1]},
            headers=auth_headers,
        )
        
        response = client.post("/api/levels/2/hint", headers=auth_headers)
        data = response.json()
        assert data["already_used"] is False
        assert data["points_delta"] < 0
        
        dash = client.get("/api/dashboard", headers=auth_headers).json()
        level_1 = next(l for l in dash["levels"] if l["order_index"] == 1)
        level_2 = next(l for l in dash["levels"] if l["order_index"] == 2)
        assert level_1["hint_used"] is True
        assert level_2["hint_used"] is True
