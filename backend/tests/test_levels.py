"""
Test sequential level progression and flag submission.
"""

import pytest

from tests.conftest import reset_rate_limiter


class TestSequentialUnlock:
    """Tests for sequential level unlock logic."""

    def test_level_1_is_unlocked_initially(self, client, auth_headers):
        """Level 1 should be available to a new student."""
        response = client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200
        levels = response.json()["levels"]
        level_1 = next(l for l in levels if l["order_index"] == 1)
        assert level_1["status"] == "available"

    def test_level_2_is_locked_initially(self, client, auth_headers):
        """Level 2 should be locked until level 1 is completed."""
        response = client.get("/api/dashboard", headers=auth_headers)
        levels = response.json()["levels"]
        level_2 = next(l for l in levels if l["order_index"] == 2)
        assert level_2["status"] == "locked"

    def test_submit_locked_level_returns_403(self, client, auth_headers, test_flags):
        """Submitting to a locked level returns 403 LEVEL_LOCKED."""
        reset_rate_limiter()
        response = client.post(
            "/api/levels/2/submit",
            json={"flag": test_flags[2]},
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "LEVEL_LOCKED"

    def test_submit_correct_flag_unlocks_next_level(self, client, auth_headers, test_flags):
        """Completing level 1 should unlock level 2."""
        reset_rate_limiter()
        
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": test_flags[1]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["result"] == "correct"
        assert data["unlocked_next"] is True
        assert data["points_delta"] > 0
        
        dash = client.get("/api/dashboard", headers=auth_headers).json()
        level_2 = next(l for l in dash["levels"] if l["order_index"] == 2)
        assert level_2["status"] == "available"

    def test_complete_all_levels_sequentially(self, client, auth_headers, test_flags):
        """Complete all 8 levels in order, verifying sequential unlock."""
        reset_rate_limiter()
        
        for level_num in range(1, 9):
            response = client.post(
                f"/api/levels/{level_num}/submit",
                json={"flag": test_flags[level_num]},
                headers=auth_headers,
            )
            assert response.status_code == 200, f"Failed on level {level_num}"
            data = response.json()
            assert data["ok"] is True
            assert data["result"] == "correct"
            
            if level_num < 8:
                assert data["unlocked_next"] is True
            else:
                assert data["token"] is not None

    def test_skip_levels_fails(self, client, auth_headers, test_flags):
        """Cannot skip to level 5 without completing 1-4."""
        reset_rate_limiter()
        
        response = client.post(
            "/api/levels/5/submit",
            json={"flag": test_flags[5]},
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "LEVEL_LOCKED"


class TestIncorrectFlags:
    """Tests for incorrect flag submissions."""

    def test_wrong_flag_rejected(self, client, auth_headers):
        """Incorrect flag returns result='incorrect' with no points."""
        reset_rate_limiter()
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{WRONG_FLAG}"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["result"] == "incorrect"
        assert data["points_delta"] == 0
        assert data["unlocked_next"] is False

    def test_wrong_flag_does_not_unlock_level(self, client, auth_headers):
        """Wrong flag submission does not change level status."""
        reset_rate_limiter()
        client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{COMPLETELY_WRONG}"},
            headers=auth_headers,
        )
        
        dash = client.get("/api/dashboard", headers=auth_headers).json()
        level_1 = next(l for l in dash["levels"] if l["order_index"] == 1)
        level_2 = next(l for l in dash["levels"] if l["order_index"] == 2)
        assert level_1["status"] == "available"
        assert level_2["status"] == "locked"

    def test_empty_flag_rejected(self, client, auth_headers):
        """Empty flag string is rejected by validation."""
        reset_rate_limiter()
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestAlreadyCompleted:
    """Tests for re-submitting already completed levels."""

    def test_resubmit_completed_level_returns_already_completed(
        self, client, auth_headers, test_flags
    ):
        """Re-submitting correct flag for completed level returns 'already_completed'."""
        reset_rate_limiter()
        
        client.post(
            "/api/levels/1/submit",
            json={"flag": test_flags[1]},
            headers=auth_headers,
        )
        
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": test_flags[1]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["result"] == "already_completed"
        assert data["points_delta"] == 0


class TestNonexistentLevel:
    """Tests for accessing non-existent levels."""

    def test_submit_nonexistent_level_returns_404(self, client, auth_headers):
        """Submitting to level ID 999 returns 404."""
        reset_rate_limiter()
        response = client.post(
            "/api/levels/999/submit",
            json={"flag": "FLAG{TEST}"},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "LEVEL_NOT_FOUND"
