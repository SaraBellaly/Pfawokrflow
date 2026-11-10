"""Point d'entrée FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from api.routers import health

app = FastAPI(
    title="Funding Workflow Automation",
    version="0.2.0",
    description="API de traitement des demandes de financement",
)

app.include_router(health.router)
