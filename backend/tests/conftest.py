"""
preCTF UCC test configuration.
Uses SQLite in-memory database for fast, isolated tests.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["TOKEN_SECRET"] = "test-token-secret"
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

from functools import lru_cache

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base, get_db
from app.main import app


@lru_cache
def get_test_settings() -> Settings:
    return Settings()


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    """Create all tables and seed data, then drop after test."""
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    from app.seed import seed_honeypots, seed_levels
    seed_levels(db)
    seed_honeypots(db)
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session_with_admin():
    """Create tables and seed with admin user."""
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    from app.seed import seed_admin, seed_honeypots, seed_levels
    seed_levels(db)
    seed_honeypots(db)
    seed_admin(db)
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Test client with fresh database."""
    return TestClient(app)


@pytest.fixture(scope="function")
def client_with_admin(db_session_with_admin):
    """Test client with admin user seeded."""
    return TestClient(app)


@pytest.fixture
def test_flags():
    """Training flags from .env.example for testing."""
    return {
        1: "FLAG{PRECTF_N1_SQLI}",
        2: "FLAG{PRECTF_N2_COOKIE}",
        3: "FLAG{PRECTF_N3_LFI}",
        4: "FLAG{PRECTF_N4_CONFIG}",
        5: "FLAG{PRECTF_N5_CMDI}",
        6: "FLAG{PRECTF_N6_HASH}",
        7: "FLAG{PRECTF_N7_UPLOAD}",
        8: "FLAG{PRECTF_N8_SSH}",
    }


@pytest.fixture
def honeypot_flags():
    """Known honeypot flags that should trigger penalties."""
    return [
        "FLAG{HONEYPOT_DO_NOT_SUBMIT_01}",
        "FLAG{HONEYPOT_TRAP_SOC_02}",
        "FLAG{FAKE_IN_COOKIE}",
    ]


@pytest.fixture
def register_student(client):
    """Helper to register a test student and return token."""
    def _register(
        email: str = "student@test.ucc",
        student_code: str = "TEST001",
        full_name: str = "Test Student",
        password: str = "SecurePass123!",
    ):
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "student_code": student_code,
                "full_name": full_name,
                "password": password,
            },
        )
        return response.json().get("access_token")
    return _register


@pytest.fixture
def auth_headers(register_student):
    """Get authorization headers for a new student."""
    token = register_student()
    return {"Authorization": f"Bearer {token}"}


def reset_rate_limiter():
    """Reset rate limiter between tests."""
    from app.services.rate_limit import _attempts
    _attempts.clear()
