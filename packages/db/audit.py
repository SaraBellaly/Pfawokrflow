"""Calcul du hash d'audit conforme à docs/audit-chain.md §3."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _format_utc(dt: datetime) -> str:
    """Format ISO 8601 UTC avec exactement 6 chiffres de microsecondes et suffixe Z."""
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond:06d}Z"


def canonical_json(obj: dict[str, Any]) -> bytes:
    """Sérialise un dict en JSON canonique (clés triées, pas d'espaces, UTF-8)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_audit_hash(
    *,
    dossier_id: str,
    event_id: str,
    event_type: str,
    occurred_at: datetime,
    payload: dict[str, Any],
    previous_hash: str,
    sequence: int,
) -> str:
    """Calcule le current_hash SHA-256 d'un événement d'audit."""
    obj = {
        "dossier_id": dossier_id,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": _format_utc(occurred_at),
        "payload": payload,
        "previous_hash": previous_hash,
        "sequence": sequence,
    }
    return hashlib.sha256(canonical_json(obj)).hexdigest()
