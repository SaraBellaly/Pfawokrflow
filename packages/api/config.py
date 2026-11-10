"""Configuration centralisée (variables d'environnement)."""

from __future__ import annotations

import os


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://funding:funding_dev@localhost:5432/funding",
)

DATABASE_URL_SYNC: str = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://funding:funding_dev@localhost:5432/funding",
)

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "cloud")
