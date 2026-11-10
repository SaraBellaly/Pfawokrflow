"""Vérifie que les modules d'infrastructure s'importent sans erreur."""

from __future__ import annotations


def test_import_db_models() -> None:
    from db.models_db import Base, ClientRow, DossierRow, PieceRow, AuditEventRow
    assert Base is not None
    assert ClientRow.__tablename__ == "clients"
    assert DossierRow.__tablename__ == "dossiers"
    assert PieceRow.__tablename__ == "pieces"
    assert AuditEventRow.__tablename__ == "audit_events"


def test_import_audit() -> None:
    from db.audit import compute_audit_hash, canonical_json
    assert callable(compute_audit_hash)
    assert callable(canonical_json)


def test_canonical_json_sort_and_compact() -> None:
    from db.audit import canonical_json
    result = canonical_json({"b": 2, "a": 1})
    assert result == b'{"a":1,"b":2}'


def test_import_api_config() -> None:
    from api.config import DATABASE_URL, REDIS_URL
    assert "postgresql" in DATABASE_URL
    assert "redis" in REDIS_URL
