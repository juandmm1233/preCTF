from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError, DockerException, ImageNotFound, NotFound
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import LabSession, Level, User
from app.services.progression import is_level_unlocked

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("starting", "running")


def _http(code: str, message: str, status_code: int) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _user_short(user: User) -> str:
    return user.id.hex[:8]


def _container_name(level: Level, user: User) -> str:
    return f"prectf-n{level.order_index}-{_user_short(user)}"


def _route_file(name: str) -> Path:
    return Path(settings.traefik_dynamic_dir) / f"{name}.yml"


def _write_traefik_route(name: str, host: str) -> None:
    directory = Path(settings.traefik_dynamic_dir)
    directory.mkdir(parents=True, exist_ok=True)
    port = settings.lab_internal_port
    content = (
        "http:\n"
        "  routers:\n"
        f"    {name}:\n"
        f"      rule: Host(`{host}`)\n"
        "      entryPoints:\n"
        "        - web\n"
        f"      service: {name}\n"
        "  services:\n"
        f"    {name}:\n"
        "      loadBalancer:\n"
        "        servers:\n"
        f"          - url: http://{name}:{port}\n"
    )
    _route_file(name).write_text(content, encoding="utf-8")


def _remove_traefik_route(name: str) -> None:
    path = _route_file(name)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("No se pudo borrar la ruta de Traefik %s", path)


def _public_host(level: Level, user: User) -> str:
    return f"n{level.order_index}-{_user_short(user)}.{settings.lab_base_domain}"


def _public_url(level: Level, user: User) -> str:
    host = _public_host(level, user)
    port = settings.lab_public_port
    if port in (80, 443):
        scheme = "https" if port == 443 else "http"
        return f"{scheme}://{host}/index.php"
    return f"http://{host}:{port}/index.php"


def _expected_image_id(client: docker.DockerClient, image: str) -> str | None:
    try:
        return client.images.get(image).id
    except (ImageNotFound, DockerException):
        return None


def _container_uses_image(client: docker.DockerClient, container_id: str, image: str) -> bool:
    if not container_id or not image:
        return False
    try:
        container = client.containers.get(container_id)
        expected = _expected_image_id(client, image)
        if expected is None:
            return False
        return container.image.id == expected
    except (NotFound, DockerException):
        return False


def image_for_level(level: Level) -> str | None:
    if level.order_index == 1 or level.slug == "sqli":
        image = settings.challenge_n1_image.strip()
        return image or None
    return None


def _client() -> docker.DockerClient:
    return docker.DockerClient(base_url=settings.docker_host, timeout=60)


def _ensure_unlocked(db: Session, user: User, level: Level) -> None:
    if not is_level_unlocked(db, user, level):
        _http(
            "LEVEL_LOCKED",
            "Completa el nivel anterior primero.",
            status.HTTP_403_FORBIDDEN,
        )


def _active_session(db: Session, user: User, level: Level) -> LabSession | None:
    return db.scalar(
        select(LabSession)
        .where(
            LabSession.user_id == user.id,
            LabSession.level_id == level.id,
            LabSession.status.in_(ACTIVE_STATUSES),
        )
        .with_for_update()
    )


def _count_active(db: Session) -> int:
    value = db.scalar(
        select(func.count()).select_from(LabSession).where(LabSession.status.in_(ACTIVE_STATUSES))
    )
    return int(value or 0)


def _container_running(client: docker.DockerClient, container_id: str) -> bool:
    if not container_id:
        return False
    try:
        container = client.containers.get(container_id)
        container.reload()
        return container.status == "running"
    except NotFound:
        return False
    except DockerException:
        logger.exception("No se pudo inspeccionar el contenedor %s", container_id)
        return False


def _destroy_container(client: docker.DockerClient, session: LabSession, name: str | None = None) -> None:
    targets = [session.container_id, name]
    seen: set[str] = set()
    for target in targets:
        if not target or target in seen:
            continue
        seen.add(target)
        try:
            container = client.containers.get(target)
            container.remove(force=True)
        except NotFound:
            continue
        except APIError:
            logger.exception("No se pudo eliminar el contenedor %s", target)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(session: LabSession) -> bool:
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= _utc_now()


def _stop_session(db: Session, session: LabSession, level: Level, user: User) -> None:
    try:
        client = _client()
    except DockerException:
        logger.exception("Docker no disponible al detener la sesión %s", session.id)
        session.status = "stopped"
        session.container_id = ""
        db.commit()
        return
    _destroy_container(client, session, _container_name(level, user))
    _remove_traefik_route(_container_name(level, user))
    session.status = "stopped"
    session.container_id = ""
    db.commit()


def _session_to_out(session: LabSession | None, level: Level) -> dict[str, Any]:
    configured = image_for_level(level) is not None
    base = {
        "status": "idle",
        "public_url": None,
        "expires_at": None,
        "has_lab": level.order_index == 1 or configured,
        "message": None,
    }
    if not configured and level.order_index == 1:
        base["message"] = "El instructor aún no configuró CHALLENGE_N1_IMAGE."
    if session is None:
        return base
    if session.status in ACTIVE_STATUSES and not _is_expired(session):
        return {
            "status": session.status,
            "public_url": session.public_url or None,
            "expires_at": session.expires_at,
            "has_lab": True,
            "message": None,
        }
    if session.status == "error":
        return {
            "status": "error",
            "public_url": None,
            "expires_at": None,
            "has_lab": base["has_lab"],
            "message": "No se pudo levantar el laboratorio. Intenta de nuevo o avisa al instructor.",
        }
    return base


def environment_snapshot(db: Session, user: User, level: Level) -> dict[str, Any]:
    session = db.scalar(
        select(LabSession)
        .where(LabSession.user_id == user.id, LabSession.level_id == level.id)
        .order_by(LabSession.started_at.desc())
    )
    if session is not None and session.status in ACTIVE_STATUSES:
        if _is_expired(session):
            _stop_session(db, session, level, user)
            return _session_to_out(None, level)
        try:
            client = _client()
            wanted = image_for_level(level)
            stale = wanted is not None and not _container_uses_image(
                client, session.container_id, wanted
            )
            if not _container_running(client, session.container_id) or stale:
                _stop_session(db, session, level, user)
                return _session_to_out(None, level)
        except DockerException:
            logger.exception("No se pudo verificar el laboratorio en Docker")
    return _session_to_out(session, level)


def start_environment(db: Session, user: User, level: Level) -> dict[str, Any]:
    _ensure_unlocked(db, user, level)
    image = image_for_level(level)
    if image is None:
        if level.order_index == 1:
            _http(
                "LAB_IMAGE_NOT_CONFIGURED",
                "El instructor no ha configurado la imagen del laboratorio (CHALLENGE_N1_IMAGE).",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        _http(
            "LAB_NOT_AVAILABLE",
            "Este nivel aún no tiene laboratorio aislado en preCTF.",
            status.HTTP_404_NOT_FOUND,
        )

    existing = _active_session(db, user, level)
    if existing is not None:
        if _is_expired(existing):
            _stop_session(db, existing, level, user)
        else:
            try:
                client = _client()
            except DockerException:
                _http(
                    "LAB_ORCHESTRATOR_UNAVAILABLE",
                    "No se pudo contactar el orquestador de laboratorios.",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            if _container_running(client, existing.container_id) and _container_uses_image(
                client, existing.container_id, image
            ):
                existing.public_url = _public_url(level, user)
                db.commit()
                return _session_to_out(existing, level)
            _stop_session(db, existing, level, user)

    if _count_active(db) >= settings.prectf_max_lab_sessions:
        _http(
            "LAB_CAPACITY",
            "No hay cupos de laboratorio. Espera o pide a un compañero que apague su instancia.",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        client = _client()
        client.ping()
        client.images.get(image)
    except ImageNotFound:
        _http(
            "LAB_IMAGE_NOT_FOUND",
            "La imagen del laboratorio no está en este host. El instructor debe construirla y etiquetarla.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except DockerException:
        logger.exception("Docker no disponible al iniciar laboratorio")
        _http(
            "LAB_ORCHESTRATOR_UNAVAILABLE",
            "No se pudo contactar el orquestador de laboratorios.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    now = _utc_now()
    expires = now + timedelta(minutes=settings.lab_ttl_minutes)
    name = _container_name(level, user)
    host = _public_host(level, user)
    url = _public_url(level, user)

    session = LabSession(
        user_id=user.id,
        level_id=level.id,
        container_id="",
        status="starting",
        public_url=url,
        started_at=now,
        expires_at=expires,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        _destroy_container(client, session, name)
        env = {
            "DB_HOST": "127.0.0.1",
            "DB_PORT": "3306",
            "DB_USER": "ctf_web",
            "DB_PASS": "ctf_web_pass",
            "DB_ADMIN_USER": "ctf_admin",
            "DB_ADMIN_PASS": "ctf_admin_pass",
            "DB_NAME": "ctf_login",
            "PRECTF_FLAG_N1": settings.prectf_flag_n1,
        }
        container = client.containers.run(
            image=image,
            name=name,
            detach=True,
            network=settings.challenge_network,
            environment=env,
            mem_limit="512m",
            nano_cpus=1_000_000_000,
            pids_limit=512,
            security_opt=["no-new-privileges:true"],
            labels={
                "prectf.managed": "true",
                "prectf.level": str(level.id),
                "prectf.user": str(user.id),
            },
        )
        _write_traefik_route(name, host)
    except OSError:
        logger.exception("No se pudo publicar la ruta del laboratorio en Traefik")
        _destroy_container(client, session, name)
        session.status = "error"
        db.commit()
        _http(
            "LAB_START_FAILED",
            "El laboratorio arrancó pero no se pudo publicar su URL.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except APIError:
        logger.exception("Error al crear el contenedor de laboratorio")
        session.status = "error"
        db.commit()
        _http(
            "LAB_START_FAILED",
            "Docker rechazó el arranque del laboratorio. Revisa la imagen y la red prectf_challenges.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except DockerException:
        logger.exception("Error de Docker al crear el laboratorio")
        session.status = "error"
        db.commit()
        _http(
            "LAB_ORCHESTRATOR_UNAVAILABLE",
            "No se pudo contactar el orquestador de laboratorios.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    session.container_id = container.id[:64]
    session.status = "running"
    db.commit()
    db.refresh(session)
    return _session_to_out(session, level)


def stop_environment(db: Session, user: User, level: Level) -> dict[str, Any]:
    _ensure_unlocked(db, user, level)
    session = _active_session(db, user, level)
    if session is None:
        return _session_to_out(None, level)
    _stop_session(db, session, level, user)
    return _session_to_out(None, level)


def reap_expired_sessions() -> None:
    db = SessionLocal()
    try:
        now = _utc_now()
        rows = list(
            db.scalars(
                select(LabSession).where(
                    LabSession.status.in_(ACTIVE_STATUSES),
                    LabSession.expires_at <= now,
                )
            ).all()
        )
        if not rows:
            return
        try:
            client = _client()
        except DockerException:
            logger.exception("Reaper: Docker no disponible")
            return
        for row in rows:
            level = db.get(Level, row.level_id)
            user = db.get(User, row.user_id)
            name = _container_name(level, user) if level and user else None
            if name:
                _remove_traefik_route(name)
            _destroy_container(client, row, name)
            row.status = "stopped"
            row.container_id = ""
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Reaper de laboratorios falló")
    finally:
        db.close()
