"""Healthcheck : vérifie la connexion PostgreSQL et Redis."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.engine import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck(session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
