from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness check (verifies DB connectivity)")
async def readiness(session: DbSession) -> dict:
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
