"""Tests for authentication endpoints: register, login, /me."""
import pytest
from fastapi.testclient import TestClient


class TestRegister:
    """Tests for POST /api/auth/register."""

    def test_register_creates_user(self, seeded_client: TestClient) -> None:
        """Registering a new student returns 201 and JWT token."""
        response = seeded_client.post("/api/auth/register", json={
            "email": "newstudent@test.local",
            "student_code": "NEW001",
            "full_name": "New Student",
            "password": "securepassword123",
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email_fails(self, seeded_client: TestClient) -> None:
        """Registering with existing email returns 409 ALREADY_REGISTERED."""
        seeded_client.post("/api/auth/register", json={
            "email": "dup@test.local",
            "student_code": "DUP001",
            "full_name": "Dup Student",
            "password": "securepassword123",
        })
        response = seeded_client.post("/api/auth/register", json={
            "email": "dup@test.local",
            "student_code": "DUP002",
            "full_name": "Dup Student 2",
            "password": "securepassword123",
        })
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "ALREADY_REGISTERED"

    def test_register_duplicate_student_code_fails(self, seeded_client: TestClient) -> None:
        """Registering with existing student code returns 409."""
        seeded_client.post("/api/auth/register", json={
            "email": "first@test.local",
            "student_code": "SAMECODE",
            "full_name": "First Student",
            "password": "securepassword123",
        })
        response = seeded_client.post("/api/auth/register", json={
            "email": "second@test.local",
            "student_code": "SAMECODE",
            "full_name": "Second Student",
            "password": "securepassword123",
        })
        assert response.status_code == 409

    def test_register_invalid_email_fails(self, seeded_client: TestClient) -> None:
        """Registering with invalid email returns 422."""
        response = seeded_client.post("/api/auth/register", json={
            "email": "notanemail",
            "student_code": "STU001",
            "full_name": "Test Student",
            "password": "securepassword123",
        })
        assert response.status_code == 422

    def test_register_short_password_fails(self, seeded_client: TestClient) -> None:
        """Registering with password < 8 chars returns 422."""
        response = seeded_client.post("/api/auth/register", json={
            "email": "short@test.local",
            "student_code": "SHORT01",
            "full_name": "Short Pass",
            "password": "short",
        })
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/auth/login."""

    def test_login_with_email(self, seeded_client: TestClient, student_token: str) -> None:
        """Login with email returns JWT token."""
        response = seeded_client.post("/api/auth/login", json={
            "identifier": "student@test.local",
            "password": "testpassword123",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_with_student_code(self, seeded_client: TestClient, student_token: str) -> None:
        """Login with student code returns JWT token."""
        response = seeded_client.post("/api/auth/login", json={
            "identifier": "STU001",
            "password": "testpassword123",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_instructor(self, seeded_client: TestClient) -> None:
        """Instructor can login with email and password."""
        response = seeded_client.post("/api/auth/login", json={
            "identifier": "instructor@ucc.local",
            "password": "CambiaEstaClave!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, seeded_client: TestClient) -> None:
        """Login with wrong password returns 401 INVALID_CREDENTIALS."""
        response = seeded_client.post("/api/auth/login", json={
            "identifier": "instructor@ucc.local",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    def test_login_nonexistent_user(self, seeded_client: TestClient) -> None:
        """Login with nonexistent user returns 401."""
        response = seeded_client.post("/api/auth/login", json={
            "identifier": "nonexistent@test.local",
            "password": "somepassword",
        })
        assert response.status_code == 401


class TestMe:
    """Tests for GET /api/auth/me."""

    def test_me_returns_user_info(self, seeded_client: TestClient, student_token: str) -> None:
        """GET /me with valid token returns user info."""
        response = seeded_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "student@test.local"
        assert data["student_code"] == "STU001"
        assert data["full_name"] == "Test Student"
        assert data["is_admin"] is False

    def test_me_instructor_is_admin(self, seeded_client: TestClient, instructor_token: str) -> None:
        """Instructor user has is_admin=True."""
        response = seeded_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {instructor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True

    def test_me_without_token_fails(self, seeded_client: TestClient) -> None:
        """GET /me without token returns 401 UNAUTHENTICATED."""
        response = seeded_client.get("/api/auth/me")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "UNAUTHENTICATED"

    def test_me_invalid_token_fails(self, seeded_client: TestClient) -> None:
        """GET /me with invalid token returns 401 INVALID_TOKEN."""
        response = seeded_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "INVALID_TOKEN"
