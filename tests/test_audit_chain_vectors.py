"""Vecteurs de référence de la chaîne d'audit (docs/audit-chain.md §7).

Reconstruit e0 et e1 à partir de leurs champs, selon les règles de canonisation de
docs/audit-chain.md §3, puis compare les SHA-256 obtenus aux valeurs du document.
Exécutable aussi directement : `python tests/test_audit_chain_vectors.py`.
"""

import hashlib
import json
import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "audit-chain.md"
GENESIS = "0" * 64


def canonical(event: dict) -> bytes:
    """Contenu canonique : clés triées, séparateurs sans espace, UTF-8 sans échappement."""
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def documented_hashes() -> list[str]:
    return re.findall(r"`current_hash` = `([0-9a-f]{64})`", DOC.read_text(encoding="utf-8"))


def documented_canonical_lines() -> list[str]:
    return [line for line in DOC.read_text(encoding="utf-8").splitlines() if line.startswith('{"dossier_id"')]


def build_vectors() -> tuple[dict, str, dict, str]:
    # Champs volontairement fournis dans le désordre : le tri doit être fait par la canonisation.
    e0 = {"sequence": 0, "previous_hash": GENESIS, "occurred_at": "2026-10-05T08:30:00.000000Z",
          "event_type": "dossier_submitted", "event_id": "EVT-FICT-0001", "dossier_id": "DOS-FICT-001",
          "payload": {"requested_amount": "18500.00", "currency": "EUR", "client_id": "CLI-FICT-001"}}
    h0 = sha256_hex(canonical(e0))
    e1 = {"sequence": 1, "previous_hash": h0, "occurred_at": "2026-10-05T08:31:12.250000Z",
          "event_type": "routing_decided", "event_id": "EVT-FICT-0002", "dossier_id": "DOS-FICT-001",
          "payload": {"triggered_rules": ["R9"], "routing": "simple"}}
    h1 = sha256_hex(canonical(e1))
    return e0, h0, e1, h1


def test_document_contains_two_vectors() -> None:
    assert len(documented_hashes()) == 2
    assert len(documented_canonical_lines()) == 2


def test_reconstructed_hashes_match_document() -> None:
    _, h0, _, h1 = build_vectors()
    assert [h0, h1] == documented_hashes()


def test_reconstructed_canonical_content_matches_document() -> None:
    e0, _, e1, _ = build_vectors()
    assert [canonical(e0).decode("utf-8"), canonical(e1).decode("utf-8")] == documented_canonical_lines()


def test_chain_link() -> None:
    e0, h0, e1, _ = build_vectors()
    assert e0["previous_hash"] == GENESIS
    assert e1["previous_hash"] == h0


if __name__ == "__main__":
    e0, h0, e1, h1 = build_vectors()
    doc = documented_hashes()
    print("canonique e0 :", canonical(e0).decode("utf-8"))
    print("sha256 e0    :", h0)
    print("doc e0       :", doc[0], "OK" if h0 == doc[0] else "DIFFÉRENT")
    print("canonique e1 :", canonical(e1).decode("utf-8"))
    print("sha256 e1    :", h1)
    print("doc e1       :", doc[1], "OK" if h1 == doc[1] else "DIFFÉRENT")
    print("lien e1.previous_hash == sha256 e0 :", e1["previous_hash"] == h0)
