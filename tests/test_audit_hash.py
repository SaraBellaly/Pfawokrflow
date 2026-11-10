"""Vérifie que compute_audit_hash reproduit les deux vecteurs de docs/audit-chain.md §7."""

from __future__ import annotations

from datetime import datetime, timezone

from db.audit import compute_audit_hash


def test_event_0_hash() -> None:
    h = compute_audit_hash(
        dossier_id="DOS-FICT-001",
        event_id="EVT-FICT-0001",
        event_type="dossier_submitted",
        occurred_at=datetime(2026, 10, 5, 8, 30, 0, 0, tzinfo=timezone.utc),
        payload={
            "client_id": "CLI-FICT-001",
            "currency": "EUR",
            "requested_amount": "18500.00",
        },
        previous_hash="0" * 64,
        sequence=0,
    )
    assert h == "bde888c35a69680c02f2a47e032ceb92eeeddef53b81edee8125ab2b0c9a1912"


def test_event_1_hash() -> None:
    h = compute_audit_hash(
        dossier_id="DOS-FICT-001",
        event_id="EVT-FICT-0002",
        event_type="routing_decided",
        occurred_at=datetime(2026, 10, 5, 8, 31, 12, 250000, tzinfo=timezone.utc),
        payload={
            "routing": "simple",
            "triggered_rules": ["R9"],
        },
        previous_hash="bde888c35a69680c02f2a47e032ceb92eeeddef53b81edee8125ab2b0c9a1912",
        sequence=1,
    )
    assert h == "102e05e1911828ae763f5965b914d0550cc2ab51db55f0674074591cba7ef364"
