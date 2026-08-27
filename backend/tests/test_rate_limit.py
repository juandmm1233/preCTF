"""
Test rate limiting: 30 submits per minute per student.
"""

import pytest

from tests.conftest import reset_rate_limiter


class TestRateLimit:
    """Tests for rate limiting on flag submissions."""

    def test_under_rate_limit_succeeds(self, client, auth_headers):
        """Submissions under the rate limit should succeed."""
        reset_rate_limiter()
        
        for i in range(5):
            response = client.post(
                "/api/levels/1/submit",
                json={"flag": f"FLAG{{WRONG_{i}}}"},
                headers=auth_headers,
            )
            assert response.status_code == 200

    def test_exceeding_30_requests_triggers_rate_limit(self, client, auth_headers):
        """After 30 submissions, the 31st should return 429."""
        reset_rate_limiter()
        
        for i in range(30):
            response = client.post(
                "/api/levels/1/submit",
                json={"flag": f"FLAG{{ATTEMPT_{i}}}"},
                headers=auth_headers,
            )
            assert response.status_code == 200, f"Request {i+1} failed unexpectedly"
        
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{ATTEMPT_31}"},
            headers=auth_headers,
        )
        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "RATE_LIMIT"

    def test_rate_limit_is_per_user(self, client, register_student):
        """Rate limit is per user, not global."""
        reset_rate_limiter()
        
        token1 = register_student(email="user1@test.ucc", student_code="USR001")
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        for i in range(30):
            client.post(
                "/api/levels/1/submit",
                json={"flag": f"FLAG{{USER1_{i}}}"},
                headers=headers1,
            )
        
        response_rate_limited = client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{USER1_31}"},
            headers=headers1,
        )
        assert response_rate_limited.status_code == 429
        
        token2 = register_student(email="user2@test.ucc", student_code="USR002")
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        response_user2 = client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{USER2_FIRST}"},
            headers=headers2,
        )
        assert response_user2.status_code == 200

    def test_rate_limit_error_message(self, client, auth_headers):
        """Rate limit response includes appropriate message."""
        reset_rate_limiter()
        
        for i in range(30):
            client.post(
                "/api/levels/1/submit",
                json={"flag": f"FLAG{{MSG_{i}}}"},
                headers=auth_headers,
            )
        
        response = client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{MSG_31}"},
            headers=auth_headers,
        )
        assert response.status_code == 429
        detail = response.json()["detail"]
        assert detail["code"] == "RATE_LIMIT"
        assert "message" in detail
