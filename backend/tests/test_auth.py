"""
Test authentication: register, login, JWT validation.
"""

import pytest


class TestRegister:
    """Tests for POST /api/auth/register."""

    def test_register_student_success(self, client):
        """Student registration with valid data returns 201 and JWT."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "alice@student.ucc",
                "student_code": "ALI001",
                "full_name": "Alice García",
                "password": "MySecurePass99!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email_fails(self, client):
        """Duplicate email returns 409 ALREADY_REGISTERED."""
        payload = {
            "email": "bob@student.ucc",
            "student_code": "BOB001",
            "full_name": "Bob López",
            "password": "StrongPass123!",
        }
        client.post("/api/auth/register", json=payload)
        
        response = client.post(
            "/api/auth/register",
            json={
                "email": "bob@student.ucc",
                "student_code": "BOB002",
                "full_name": "Bob Duplicate",
                "password": "AnotherPass456!",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "ALREADY_REGISTERED"

    def test_register_duplicate_student_code_fails(self, client):
        """Duplicate student_code returns 409."""
        client.post(
            "/api/auth/register",
            json={
                "email": "carol@student.ucc",
                "student_code": "CAR001",
                "full_name": "Carol Ruiz",
                "password": "SecurePass789!",
            },
        )
        
        response = client.post(
            "/api/auth/register",
            json={
                "email": "carol2@student.ucc",
                "student_code": "CAR001",
                "full_name": "Carol Duplicate Code",
                "password": "AnotherPass123!",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "ALREADY_REGISTERED"

    def test_register_invalid_email_fails(self, client):
        """Invalid email format returns 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "notanemail",
                "student_code": "INV001",
                "full_name": "Invalid Email",
                "password": "SomePassword123!",
            },
        )
        assert response.status_code == 422

    def test_register_short_password_fails(self, client):
        """Password < 8 chars returns 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "short@student.ucc",
                "student_code": "SHO001",
                "full_name": "Short Password",
                "password": "short",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/auth/login."""

    def test_login_with_email_success(self, client):
        """Login with email returns JWT."""
        client.post(
            "/api/auth/register",
            json={
                "email": "david@student.ucc",
                "student_code": "DAV001",
                "full_name": "David Moreno",
                "password": "DavidPass123!",
            },
        )
        
        response = client.post(
            "/api/auth/login",
            json={"identifier": "david@student.ucc", "password": "DavidPass123!"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_with_student_code_success(self, client):
        """Login with student_code instead of email."""
        client.post(
            "/api/auth/register",
            json={
                "email": "elena@student.ucc",
                "student_code": "ELE001",
                "full_name": "Elena Sánchez",
                "password": "ElenaPass456!",
            },
        )
        
        response = client.post(
            "/api/auth/login",
            json={"identifier": "ELE001", "password": "ElenaPass456!"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_invalid_password_fails(self, client):
        """Wrong password returns 401 INVALID_CREDENTIALS."""
        client.post(
            "/api/auth/register",
            json={
                "email": "fran@student.ucc",
                "student_code": "FRA001",
                "full_name": "Fran Torres",
                "password": "FranPass789!",
            },
        )
        
        response = client.post(
            "/api/auth/login",
            json={"identifier": "fran@student.ucc", "password": "WrongPassword!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    def test_login_nonexistent_user_fails(self, client):
        """Nonexistent user returns 401."""
        response = client.post(
            "/api/auth/login",
            json={"identifier": "ghost@student.ucc", "password": "AnyPassword123!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    def test_login_instructor_from_env(self, client_with_admin):
        """Login as instructor seeded from .env.example values."""
        response = client_with_admin.post(
            "/api/auth/login",
            json={
                "identifier": "instructor@ucc.local",
                "password": "CambiaEstaClave!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestMe:
    """Tests for GET /api/auth/me."""

    def test_me_returns_user_info(self, client, auth_headers):
        """GET /api/auth/me returns current user info."""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "student_code" in data
        assert "score" in data
        assert data["is_admin"] is False

    def test_me_without_token_fails(self, client):
        """GET /api/auth/me without token returns 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token_fails(self, client):
        """GET /api/auth/me with invalid token returns 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401
