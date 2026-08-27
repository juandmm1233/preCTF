import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.environments import router as environments_router
from app.api.levels import router as levels_router
from app.core.config import settings
from app.services.environments import reap_expired_sessions

logger = logging.getLogger(__name__)


async def _reap_loop() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            await asyncio.to_thread(reap_expired_sessions)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fallo en el ciclo de limpieza de laboratorios")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(_reap_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="preCTF UCC",
    description="Campo de entrenamiento secuencial previo al laboratorio CTF.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(levels_router, prefix="/api")
app.include_router(environments_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
