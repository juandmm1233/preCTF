"""Tests for level progression: sequential flags, out-of-order rejection, honeypots, hints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestSequentialFlags:
    """Tests for sequential flag submission (levels 1-8)."""

    def test_submit_correct_flag_level_1(self, seeded_client: TestClient, student_token: str) -> None:
        """Submitting correct flag for level 1 returns ok=True, correct result."""
        response = seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{PRECTF_N1_SQLI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["result"] == "correct"
        assert data["points_delta"] == 50
        assert data["unlocked_next"] is True

    def test_submit_wrong_flag(self, seeded_client: TestClient, student_token: str) -> None:
        """Submitting wrong flag returns ok=False, incorrect result."""
        response = seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{WRONG_FLAG}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["result"] == "incorrect"
        assert data["points_delta"] == 0

    def test_submit_out_of_order_returns_403(self, seeded_client: TestClient, student_token: str) -> None:
        """Submitting flag for level 2 before completing level 1 returns 403 LEVEL_LOCKED."""
        response = seeded_client.post(
            "/api/levels/2/submit",
            json={"flag": "FLAG{PRECTF_N2_COOKIE}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "LEVEL_LOCKED"

    def test_complete_levels_in_sequence(self, seeded_client: TestClient, student_token: str) -> None:
        """Completing levels in order 1->2->3 works correctly."""
        flags = [
            ("FLAG{PRECTF_N1_SQLI}", 50),
            ("FLAG{PRECTF_N2_COOKIE}", 75),
            ("FLAG{PRECTF_N3_LFI}", 60),
        ]
        total_points = 0
        for i, (flag, points) in enumerate(flags, start=1):
            response = seeded_client.post(
                f"/api/levels/{i}/submit",
                json={"flag": flag},
                headers={"Authorization": f"Bearer {student_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["result"] == "correct"
            total_points += points
            assert data["points"] == total_points

    def test_all_8_levels_sequential(self, seeded_client: TestClient, student_token: str) -> None:
        """Complete all 8 levels in sequence, last level issues token."""
        flags = [
            "FLAG{PRECTF_N1_SQLI}",
            "FLAG{PRECTF_N2_COOKIE}",
            "FLAG{PRECTF_N3_LFI}",
            "FLAG{PRECTF_N4_CONFIG}",
            "FLAG{PRECTF_N5_CMDI}",
            "FLAG{PRECTF_N6_HASH}",
            "FLAG{PRECTF_N7_UPLOAD}",
            "FLAG{PRECTF_N8_SSH}",
        ]
        for i, flag in enumerate(flags, start=1):
            response = seeded_client.post(
                f"/api/levels/{i}/submit",
                json={"flag": flag},
                headers={"Authorization": f"Bearer {student_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["result"] == "correct"
            if i == 8:
                assert data["token"] is not None
                assert data["unlocked_next"] is False
            else:
                assert data["unlocked_next"] is True

    def test_resubmit_completed_level(self, seeded_client: TestClient, student_token: str) -> None:
        """Resubmitting flag for already completed level returns already_completed."""
        seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{PRECTF_N1_SQLI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{PRECTF_N1_SQLI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "already_completed"
        assert data["points_delta"] == 0


class TestHoneypots:
    """Tests for honeypot flags that deduct points."""

    def test_honeypot_flag_deducts_points(self, seeded_client: TestClient, student_token: str) -> None:
        """Submitting a honeypot flag deducts 50 points."""
        seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{PRECTF_N1_SQLI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.post(
            "/api/levels/2/submit",
            json={"flag": "FLAG{HONEYPOT_DO_NOT_SUBMIT_01}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["result"] == "honeypot"
        assert data["points_delta"] == -50

    def test_honeypot_does_not_unlock_level(self, seeded_client: TestClient, student_token: str) -> None:
        """Honeypot does not unlock the next level."""
        seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{PRECTF_N1_SQLI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.post(
            "/api/levels/2/submit",
            json={"flag": "FLAG{HONEYPOT_DO_NOT_SUBMIT_01}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        data = response.json()
        assert data["unlocked_next"] is False
        response = seeded_client.post(
            "/api/levels/3/submit",
            json={"flag": "FLAG{PRECTF_N3_LFI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403


class TestHints:
    """Tests for hint system: points deducted once only."""

    def test_first_hint_deducts_points(self, seeded_client: TestClient, student_token: str) -> None:
        """First hint request deducts hint_cost points."""
        response = seeded_client.post(
            "/api/levels/1/hint",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["already_used"] is False
        assert data["points_delta"] == -10

    def test_second_hint_no_deduction(self, seeded_client: TestClient, student_token: str) -> None:
        """Second hint request does not deduct points again."""
        seeded_client.post(
            "/api/levels/1/hint",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.post(
            "/api/levels/1/hint",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["already_used"] is True
        assert data["points_delta"] == 0

    def test_hint_locked_level_fails(self, seeded_client: TestClient, student_token: str) -> None:
        """Requesting hint for locked level returns 403."""
        response = seeded_client.post(
            "/api/levels/2/hint",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "LEVEL_LOCKED"


class TestGetLevel:
    """Tests for GET /api/levels/{id}."""

    def test_get_unlocked_level(self, seeded_client: TestClient, student_token: str) -> None:
        """GET level 1 (unlocked) returns level details."""
        response = seeded_client.get(
            "/api/levels/1",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Autenticación rota"
        assert data["status"] == "available"

    def test_get_locked_level_fails(self, seeded_client: TestClient, student_token: str) -> None:
        """GET locked level returns 403 LEVEL_LOCKED."""
        response = seeded_client.get(
            "/api/levels/2",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "LEVEL_LOCKED"

    def test_get_nonexistent_level(self, seeded_client: TestClient, student_token: str) -> None:
        """GET nonexistent level returns 404 LEVEL_NOT_FOUND."""
        response = seeded_client.get(
            "/api/levels/999",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "LEVEL_NOT_FOUND"

    def test_level_response_no_flag_plaintext(self, seeded_client: TestClient, student_token: str) -> None:
        """API never returns flag plaintext in level response."""
        response = seeded_client.get(
            "/api/levels/1",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        data = response.json()
        assert "flag" not in data
        assert "flag_hash" not in data
        response_text = str(data)
        assert "FLAG{" not in response_text


class TestRateLimit:
    """Tests for rate limiting on flag submissions."""

    def test_rate_limit_30_per_minute(self, seeded_client: TestClient, student_token: str) -> None:
        """After 30 submissions, rate limit kicks in with 429."""
        from collections import defaultdict
        import app.services.rate_limit as rate_limit_module
        original_attempts = rate_limit_module._attempts
        rate_limit_module._attempts = defaultdict(list)
        try:
            for i in range(30):
                response = seeded_client.post(
                    "/api/levels/1/submit",
                    json={"flag": f"FLAG{{ATTEMPT_{i}}}"},
                    headers={"Authorization": f"Bearer {student_token}"}
                )
                assert response.status_code == 200

            response = seeded_client.post(
                "/api/levels/1/submit",
                json={"flag": "FLAG{ATTEMPT_31}"},
                headers={"Authorization": f"Bearer {student_token}"}
            )
            assert response.status_code == 429
            assert response.json()["detail"]["code"] == "RATE_LIMIT"
        finally:
            rate_limit_module._attempts = original_attempts
