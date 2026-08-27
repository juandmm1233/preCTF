"""
Test admin verify-token endpoint: JWT admin or X-Instructor-Key.
"""

import pytest

from tests.conftest import reset_rate_limiter


class TestVerifyToken:
    """Tests for GET /api/admin/verify-token."""

    def test_verify_token_without_auth_fails(self, client):
        """Verify-token without credentials returns 401."""
        response = client.get("/api/admin/verify-token?token=sometoken")
        assert response.status_code == 401

    def test_verify_token_with_instructor_key(self, client_with_admin):
        """Verify-token works with X-Instructor-Key header."""
        response = client_with_admin.get(
            "/api/admin/verify-token?token=invalid-token",
            headers={"X-Instructor-Key": "test-instructor-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_verify_token_with_admin_jwt(self, client_with_admin):
        """Verify-token works with admin JWT."""
        login_response = client_with_admin.post(
            "/api/auth/login",
            json={
                "identifier": "instructor@ucc.local",
                "password": "CambiaEstaClave!",
            },
        )
        admin_token = login_response.json()["access_token"]
        
        response = client_with_admin.get(
            "/api/admin/verify-token?token=invalid-token",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_verify_token_with_non_admin_jwt_fails(self, client, auth_headers):
        """Verify-token with non-admin JWT returns 403."""
        response = client.get(
            "/api/admin/verify-token?token=sometoken",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"

    def test_verify_valid_access_token(self, client_with_admin, test_flags):
        """After completing all levels, verify the issued access token."""
        reset_rate_limiter()
        
        register_response = client_with_admin.post(
            "/api/auth/register",
            json={
                "email": "completer@test.ucc",
                "student_code": "COMP001",
                "full_name": "Complete Student",
                "password": "CompletePass123!",
            },
        )
        student_token = register_response.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}
        
        access_token = None
        for level_num in range(1, 9):
            response = client_with_admin.post(
                f"/api/levels/{level_num}/submit",
                json={"flag": test_flags[level_num]},
                headers=student_headers,
            )
            data = response.json()
            if level_num == 8:
                access_token = data.get("token")
        
        assert access_token is not None, "Access token should be issued after level 8"
        
        verify_response = client_with_admin.get(
            f"/api/admin/verify-token?token={access_token}",
            headers={"X-Instructor-Key": "test-instructor-key"},
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["valid"] is True
        assert verify_data["student_code"] == "COMP001"
        assert verify_data["full_name"] == "Complete Student"
        assert verify_data["expired"] is False

    def test_wrong_instructor_key_fails(self, client_with_admin):
        """Wrong X-Instructor-Key returns 401 (auth header present but invalid)."""
        response = client_with_admin.get(
            "/api/admin/verify-token?token=sometoken",
            headers={"X-Instructor-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_verify_missing_token_param(self, client_with_admin):
        """Missing token query param returns 422."""
        response = client_with_admin.get(
            "/api/admin/verify-token",
            headers={"X-Instructor-Key": "test-instructor-key"},
        )
        assert response.status_code == 422
