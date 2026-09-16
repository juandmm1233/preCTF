"""Tests for lab environment endpoints: start/get/stop with mocked Docker."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient


class TestEnvironmentStart:
    """Tests for POST /api/levels/{id}/environment/start."""

    def test_start_environment_unlocked_level(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Starting environment for unlocked level 1 returns running status."""
        response = seeded_client.post(
            "/api/levels/1/environment/start",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["has_lab"] is True
        assert data["public_url"] is not None

    def test_start_environment_locked_level_forbidden(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Starting environment for locked level returns 403 LEVEL_LOCKED."""
        response = seeded_client.post(
            "/api/levels/2/environment/start",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "LEVEL_LOCKED"

    def test_start_environment_after_unlock(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """After completing level 1, can start environment for level 2."""
        seeded_client.post(
            "/api/levels/1/submit",
            json={"flag": "FLAG{PRECTF_N1_SQLI}"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.post(
            "/api/levels/2/environment/start",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_start_environment_unauthenticated(self, seeded_client: TestClient) -> None:
        """Starting environment without auth returns 401."""
        response = seeded_client.post("/api/levels/1/environment/start")
        assert response.status_code == 401

    def test_start_environment_nonexistent_level(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Starting environment for nonexistent level returns 404."""
        response = seeded_client.post(
            "/api/levels/999/environment/start",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 404


class TestEnvironmentGet:
    """Tests for GET /api/levels/{id}/environment."""

    def test_get_environment_idle(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Getting environment before starting returns idle status."""
        response = seeded_client.get(
            "/api/levels/1/environment",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["public_url"] is None

    def test_get_environment_after_start(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Getting environment after starting returns running status."""
        seeded_client.post(
            "/api/levels/1/environment/start",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.get(
            "/api/levels/1/environment",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["public_url"] is not None

    def test_get_environment_has_activity_path(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Environment response includes activity_path."""
        response = seeded_client.get(
            "/api/levels/1/environment",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "activity_path" in data


class TestEnvironmentStop:
    """Tests for POST /api/levels/{id}/environment/stop."""

    def test_stop_environment(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Stopping running environment returns idle status."""
        seeded_client.post(
            "/api/levels/1/environment/start",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        response = seeded_client.post(
            "/api/levels/1/environment/stop",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["public_url"] is None

    def test_stop_idempotent(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Stopping an already stopped environment is safe/idempotent."""
        response = seeded_client.post(
            "/api/levels/1/environment/stop",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"

        response = seeded_client.post(
            "/api/levels/1/environment/stop",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"

    def test_stop_locked_level_forbidden(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Stopping environment for locked level returns 403."""
        response = seeded_client.post(
            "/api/levels/2/environment/stop",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403


class TestDockerUnavailable:
    """Tests for graceful handling when Docker is unavailable."""

    def test_start_docker_unavailable(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_traefik_dir
    ) -> None:
        """Starting environment when Docker is unavailable returns 503."""
        from docker.errors import DockerException
        with patch("app.services.environments._client") as mock_client:
            mock_client.side_effect = DockerException("Docker not available")

            response = seeded_client.post(
                "/api/levels/1/environment/start",
                headers={"Authorization": f"Bearer {student_token}"}
            )
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "LAB_ORCHESTRATOR_UNAVAILABLE"

    def test_get_environment_docker_unavailable(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_traefik_dir
    ) -> None:
        """Getting environment when Docker is unavailable still works (returns idle)."""
        from docker.errors import DockerException
        with patch("app.services.environments._client") as mock_client:
            mock_client.side_effect = DockerException("Docker not available")

            response = seeded_client.get(
                "/api/levels/1/environment",
                headers={"Authorization": f"Bearer {student_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "idle"


class TestImageNotConfigured:
    """Tests for when lab image is not configured."""

    def test_start_no_image_configured(
        self,
        seeded_client: TestClient,
        student_token: str,
        mock_docker_client,
        mock_traefik_dir
    ) -> None:
        """Starting environment when image not configured returns 503."""
        with patch("app.services.environments.image_for_level") as mock_image:
            mock_image.return_value = None

            response = seeded_client.post(
                "/api/levels/1/environment/start",
                headers={"Authorization": f"Bearer {student_token}"}
            )
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "LAB_IMAGE_NOT_CONFIGURED"
