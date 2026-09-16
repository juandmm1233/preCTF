"""Tests for admin endpoints: verify-token with datetime fix."""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AccessToken, User


class TestVerifyToken:
    """Tests for GET /api/admin/verify-token endpoint."""

    def test_verify_token_with_instructor_key(self, seeded_client: TestClient) -> None:
        """Admin can verify token using X-Instructor-Key header."""
        response = seeded_client.get(
            "/api/admin/verify-token",
            params={"token": "invalid-token-format"},
            headers={"X-Instructor-Key": "test-instructor-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_verify_token_with_jwt(self, seeded_client: TestClient, instructor_token: str) -> None:
        """Admin can verify token using JWT bearer auth."""
        response = seeded_client.get(
            "/api/admin/verify-token",
            params={"token": "some-token.signature"},
            headers={"Authorization": f"Bearer {instructor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_verify_token_student_forbidden(self, seeded_client: TestClient, student_token: str) -> None:
        """Non-admin user gets 403 FORBIDDEN."""
        response = seeded_client.get(
            "/api/admin/verify-token",
            params={"token": "some-token"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"

    def test_verify_token_unauthenticated(self, seeded_client: TestClient) -> None:
        """No auth returns 401 UNAUTHENTICATED."""
        response = seeded_client.get(
            "/api/admin/verify-token",
            params={"token": "some-token"}
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "UNAUTHENTICATED"

    def test_verify_valid_token(self, seeded_client: TestClient, student_token: str, seeded_db: Session) -> None:
        """Verifying a valid issued token returns correct info."""
        for i in range(8):
            seeded_client.post(
                f"/api/levels/{i+1}/submit",
                json={"flag": f"FLAG{{PRECTF_N{i+1}_{'SQLI' if i==0 else 'COOKIE' if i==1 else 'LFI' if i==2 else 'CONFIG' if i==3 else 'CMDI' if i==4 else 'HASH' if i==5 else 'UPLOAD' if i==6 else 'SSH'}}}"},
                headers={"Authorization": f"Bearer {student_token}"}
            )

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

        seeded_client2 = seeded_client
        reg_resp = seeded_client2.post("/api/auth/register", json={
            "email": "tokenuser@test.local",
            "student_code": "TOK001",
            "full_name": "Token User",
            "password": "testpassword123",
        })
        token2 = reg_resp.json()["access_token"]

        for i, flag in enumerate(flags, start=1):
            seeded_client2.post(
                f"/api/levels/{i}/submit",
                json={"flag": flag},
                headers={"Authorization": f"Bearer {token2}"}
            )

        dash_resp = seeded_client2.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token2}"}
        )
        access_token = dash_resp.json().get("access_token")
        if access_token:
            verify_resp = seeded_client2.get(
                "/api/admin/verify-token",
                params={"token": access_token},
                headers={"X-Instructor-Key": "test-instructor-key"}
            )
            assert verify_resp.status_code == 200
            data = verify_resp.json()
            assert data["valid"] is True
            assert data["email"] == "tokenuser@test.local"


class TestNaiveVsAwareDatetime:
    """Tests for the datetime timezone bug fix in verify-token."""

    def test_naive_datetime_no_typeerror(self, seeded_client: TestClient, seeded_db: Session) -> None:
        """expires_at with naive datetime does not throw TypeError."""
        from app.core.security import hash_password
        import hmac

        user = User(
            email="naivetest@test.local",
            student_code="NAIVE01",
            full_name="Naive Test",
            password_hash=hash_password("testpassword123"),
            is_admin=False,
        )
        seeded_db.add(user)
        seeded_db.commit()
        seeded_db.refresh(user)

        payload = f"PRECTF-UCC-2024-{str(user.id).replace('-', '')[:8].upper()}-ABCD1234"
        from app.core.config import get_settings
        settings = get_settings()
        signature = hmac.new(
            settings.token_secret.encode("utf-8"),
            payload.encode("utf-8"),
            "sha256",
        ).hexdigest()[:16]
        token_str = f"{payload}.{signature}"

        naive_expires = datetime.now() + timedelta(days=180)
        access_token = AccessToken(
            user_id=user.id,
            token=token_str,
            hmac_signature=signature,
            issued_at=datetime.now(timezone.utc),
            expires_at=naive_expires,
        )
        seeded_db.add(access_token)
        seeded_db.commit()

        response = seeded_client.get(
            "/api/admin/verify-token",
            params={"token": token_str},
            headers={"X-Instructor-Key": "test-instructor-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["expired"] is False

    def test_aware_datetime_works(self, seeded_client: TestClient, seeded_db: Session) -> None:
        """expires_at with timezone-aware datetime works correctly."""
        from app.core.security import hash_password
        import hmac

        user = User(
            email="awaretest@test.local",
            student_code="AWARE01",
            full_name="Aware Test",
            password_hash=hash_password("testpassword123"),
            is_admin=False,
        )
        seeded_db.add(user)
        seeded_db.commit()
        seeded_db.refresh(user)

        payload = f"PRECTF-UCC-2024-{str(user.id).replace('-', '')[:8].upper()}-EFGH5678"
        from app.core.config import get_settings
        settings = get_settings()
        signature = hmac.new(
            settings.token_secret.encode("utf-8"),
            payload.encode("utf-8"),
            "sha256",
        ).hexdigest()[:16]
        token_str = f"{payload}.{signature}"

        aware_expires = datetime.now(timezone.utc) + timedelta(days=180)
        access_token = AccessToken(
            user_id=user.id,
            token=token_str,
            hmac_signature=signature,
            issued_at=datetime.now(timezone.utc),
            expires_at=aware_expires,
        )
        seeded_db.add(access_token)
        seeded_db.commit()

        response = seeded_client.get(
            "/api/admin/verify-token",
            params={"token": token_str},
            headers={"X-Instructor-Key": "test-instructor-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["expired"] is False

    def test_expired_token_detected(self, seeded_client: TestClient, seeded_db: Session) -> None:
        """Expired token (past expires_at) is correctly detected."""
        from app.core.security import hash_password
        import hmac

        user = User(
            email="expiredtest@test.local",
            student_code="EXPIR01",
            full_name="Expired Test",
            password_hash=hash_password("testpassword123"),
            is_admin=False,
        )
        seeded_db.add(user)
        seeded_db.commit()
        seeded_db.refresh(user)

        payload = f"PRECTF-UCC-2024-{str(user.id).replace('-', '')[:8].upper()}-IJKL9012"
        from app.core.config import get_settings
        settings = get_settings()
        signature = hmac.new(
            settings.token_secret.encode("utf-8"),
            payload.encode("utf-8"),
            "sha256",
        ).hexdigest()[:16]
        token_str = f"{payload}.{signature}"

        past_expires = datetime.now(timezone.utc) - timedelta(days=1)
        access_token = AccessToken(
            user_id=user.id,
            token=token_str,
            hmac_signature=signature,
            issued_at=datetime.now(timezone.utc) - timedelta(days=181),
            expires_at=past_expires,
        )
        seeded_db.add(access_token)
        seeded_db.commit()

        response = seeded_client.get(
            "/api/admin/verify-token",
            params={"token": token_str},
            headers={"X-Instructor-Key": "test-instructor-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["expired"] is True
