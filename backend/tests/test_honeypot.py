"""
Test honeypot / fake flag detection and scoring penalties.
"""

import pytest

from tests.conftest import reset_rate_limiter


class TestHoneypotFlags:
    """Tests for honeypot flag detection."""

    def test_honeypot_flag_subtracts_50_points(self, client, auth_headers, honeypot_flags):
        """Submitting a honeypot flag subtracts 50 points."""
        reset_rate_limiter()
        
        dash_before = client.get("/api/dashboard", headers=auth_headers).json()
        initial_score = dash_before["user"]["score"]
        
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": honeypot_flags[0]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["result"] == "honeypot"
        assert data["points_delta"] == -50
        assert data["points"] == max(0, initial_score - 50)

    def test_honeypot_does_not_unlock_level(self, client, auth_headers, honeypot_flags):
        """Honeypot submission does not unlock next level."""
        reset_rate_limiter()
        
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": honeypot_flags[0]},
            headers=auth_headers,
        )
        assert response.json()["unlocked_next"] is False
        
        dash = client.get("/api/dashboard", headers=auth_headers).json()
        level_1 = next(l for l in dash["levels"] if l["order_index"] == 1)
        level_2 = next(l for l in dash["levels"] if l["order_index"] == 2)
        assert level_1["status"] == "available"
        assert level_2["status"] == "locked"

    def test_all_known_honeypots_trigger_penalty(self, client, honeypot_flags, register_student):
        """Test all known honeypot patterns trigger penalty."""
        reset_rate_limiter()
        
        for i, honeypot in enumerate(honeypot_flags):
            token = register_student(
                email=f"honeypot_tester_{i}@test.ucc",
                student_code=f"HP{i:03d}",
            )
            headers = {"Authorization": f"Bearer {token}"}
            
            response = client.post(
                "/api/levels/1/submit",
                json={"flag": honeypot},
                headers=headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "honeypot", f"Flag {honeypot} should be honeypot"
            assert data["points_delta"] == -50

    def test_honeypot_score_cannot_go_negative(self, client, auth_headers, honeypot_flags):
        """Score should clamp to 0 and not go negative."""
        reset_rate_limiter()
        
        for _ in range(3):
            client.post(
                "/api/levels/1/submit",
                json={"flag": honeypot_flags[0]},
                headers=auth_headers,
            )
        
        dash = client.get("/api/dashboard", headers=auth_headers).json()
        assert dash["user"]["score"] >= 0

    def test_fake_flag_pattern_triggers_honeypot(self, client, auth_headers):
        """FLAG{FAKE_IN_COOKIE} pattern triggers honeypot penalty."""
        reset_rate_limiter()
        
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{FAKE_IN_COOKIE}"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "honeypot"
        assert data["points_delta"] == -50
