"""
Pytest configuration and fixtures for preCTF backend tests.
Uses SQLite in-memory for isolated, fast testing.
"""
import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-tests"
os.environ["TOKEN_SECRET"] = "test-token-secret-for-tests"
os.environ["INSTRUCTOR_KEY"] = "test-instructor-key"
os.environ["ADMIN_EMAIL"] = "instructor@ucc.local"
os.environ["ADMIN_PASSWORD"] = "CambiaEstaClave!"
os.environ["ADMIN_CODE"] = "DOCENTE"
os.environ["ADMIN_NAME"] = "Instructor preCTF"
os.environ["PRECTF_FLAG_N1"] = "FLAG{PRECTF_N1_SQLI}"
os.environ["PRECTF_FLAG_N2"] = "FLAG{PRECTF_N2_COOKIE}"
os.environ["PRECTF_FLAG_N3"] = "FLAG{PRECTF_N3_LFI}"
os.environ["PRECTF_FLAG_N4"] = "FLAG{PRECTF_N4_CONFIG}"
os.environ["PRECTF_FLAG_N5"] = "FLAG{PRECTF_N5_CMDI}"
os.environ["PRECTF_FLAG_N6"] = "FLAG{PRECTF_N6_HASH}"
os.environ["PRECTF_FLAG_N7"] = "FLAG{PRECTF_N7_UPLOAD}"
os.environ["PRECTF_FLAG_N8"] = "FLAG{PRECTF_N8_SSH}"
os.environ["CHALLENGE_N1_IMAGE"] = "prectf-challenge-n1:local"
os.environ["DOCKER_HOST"] = "tcp://localhost:2375"
os.environ["TRAEFIK_DYNAMIC_DIR"] = "/tmp/traefik-test"

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.core.security import hash_flag, hash_password
from app.main import app
from app.models import AccessToken, Honeypot, Level, User


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="function")
def test_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="function")
def test_session(test_session_factory) -> Generator[Session, None, None]:
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_engine, test_session_factory) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(test_session: Session) -> Session:
    """Seed the database with levels, honeypots, and admin user."""
    settings = get_settings()

    levels_data = [
        {"id": 1, "order_index": 1, "slug": "sqli", "title": "Autenticación rota", "vector_name": "SQL Injection", "lab_endpoint": "/index.php", "points": 50, "hint_cost": 10, "description": "Level 1", "hint_text": "Hint 1", "tutorial_content": "", "is_bonus": False},
        {"id": 2, "order_index": 2, "slug": "cookie-bac", "title": "Control de acceso", "vector_name": "Cookie tampering", "lab_endpoint": "/admin.php", "points": 75, "hint_cost": 15, "description": "Level 2", "hint_text": "Hint 2", "tutorial_content": "", "is_bonus": False},
        {"id": 3, "order_index": 3, "slug": "lfi", "title": "Lectura de archivos", "vector_name": "LFI", "lab_endpoint": "/download.php", "points": 60, "hint_cost": 15, "description": "Level 3", "hint_text": "Hint 3", "tutorial_content": "", "is_bonus": False},
        {"id": 4, "order_index": 4, "slug": "config-leak", "title": "Divulgación de config", "vector_name": "Info disclosure", "lab_endpoint": "/download.php", "points": 70, "hint_cost": 15, "description": "Level 4", "hint_text": "Hint 4", "tutorial_content": "", "is_bonus": False},
        {"id": 5, "order_index": 5, "slug": "cmdi", "title": "Diagnóstico", "vector_name": "Command Injection", "lab_endpoint": "/network.php", "points": 80, "hint_cost": 20, "description": "Level 5", "hint_text": "Hint 5", "tutorial_content": "", "is_bonus": False},
        {"id": 6, "order_index": 6, "slug": "weak-hash", "title": "Secretos con hash débil", "vector_name": "Hash débil", "lab_endpoint": "tabla secrets", "points": 100, "hint_cost": 20, "description": "Level 6", "hint_text": "Hint 6", "tutorial_content": "", "is_bonus": False},
        {"id": 7, "order_index": 7, "slug": "upload", "title": "Subida sin frontera", "vector_name": "File upload", "lab_endpoint": "/upload.php", "points": 120, "hint_cost": 25, "description": "Level 7", "hint_text": "Hint 7", "tutorial_content": "", "is_bonus": False},
        {"id": 8, "order_index": 8, "slug": "ssh-creds", "title": "Acceso remoto", "vector_name": "SSH débiles", "lab_endpoint": "contenedor ssh", "points": 150, "hint_cost": 25, "description": "Level 8", "hint_text": "Hint 8", "tutorial_content": "", "is_bonus": False},
    ]

    for spec in levels_data:
        flag = settings.flag_for_level(spec["order_index"])
        test_session.add(Level(**spec, flag_hash=hash_flag(flag)))

    honeypots_data = [
        {"label": "secrets-table-1", "value": "FLAG{HONEYPOT_DO_NOT_SUBMIT_01}", "penalty": 50},
        {"label": "secrets-table-2", "value": "FLAG{HONEYPOT_TRAP_SOC_02}", "penalty": 50},
    ]
    for hp in honeypots_data:
        test_session.add(Honeypot(label=hp["label"], flag_hash=hash_flag(hp["value"]), penalty=hp["penalty"]))

    admin = User(
        email="instructor@ucc.local",
        student_code="DOCENTE",
        full_name="Instructor preCTF",
        password_hash=hash_password("CambiaEstaClave!"),
        is_admin=True,
    )
    test_session.add(admin)
    test_session.commit()
    return test_session


@pytest.fixture
def seeded_client(test_engine, test_session_factory, seeded_db) -> Generator[TestClient, None, None]:
    """Client with seeded database."""
    def override_get_db() -> Generator[Session, None, None]:
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def student_token(seeded_client: TestClient) -> str:
    """Register a student and return their JWT token."""
    response = seeded_client.post("/api/auth/register", json={
        "email": "student@test.local",
        "student_code": "STU001",
        "full_name": "Test Student",
        "password": "testpassword123",
    })
    assert response.status_code == 201
    return response.json()["access_token"]


@pytest.fixture
def instructor_token(seeded_client: TestClient) -> str:
    """Login as instructor and return JWT token."""
    response = seeded_client.post("/api/auth/login", json={
        "identifier": "instructor@ucc.local",
        "password": "CambiaEstaClave!",
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for environment tests without actual Docker daemon."""
    with patch("app.services.environments._client") as mock_client:
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        client_instance.ping.return_value = True

        mock_image = MagicMock()
        mock_image.id = "sha256:abc123"
        client_instance.images.get.return_value = mock_image

        mock_container = MagicMock()
        mock_container.id = "container123abc"
        mock_container.status = "running"
        mock_container.image.id = "sha256:abc123"
        mock_container.reload = MagicMock()
        mock_container.remove = MagicMock()
        client_instance.containers.run.return_value = mock_container
        client_instance.containers.get.return_value = mock_container

        yield client_instance


@pytest.fixture
def mock_traefik_dir(tmp_path):
    """Provide a temporary directory for Traefik routes."""
    traefik_dir = tmp_path / "traefik"
    traefik_dir.mkdir()
    with patch.dict(os.environ, {"TRAEFIK_DYNAMIC_DIR": str(traefik_dir)}):
        get_settings.cache_clear()
        yield traefik_dir
