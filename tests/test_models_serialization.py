"""Tests des contrats de données : sérialisation JSON aller-retour et invariants principaux."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from core.models import (
    GENESIS_HASH,
    AuditEvent,
    AuditEventType,
    AuthorType,
    Client,
    Decision,
    DecisionType,
    Dossier,
    DossierStatus,
    ExtractedField,
    OcrStatus,
    Piece,
    PieceType,
    RoutingDecision,
)

NOW = datetime(2026, 10, 5, 8, 30, tzinfo=timezone.utc)
HASH_A = "a" * 64


def make_client() -> Client:
    return Client(client_id="CLI-FICT-001", legal_name="Menuiserie Alpha (FICTIF) SARL",
                  legal_representative="Yanis FICTIF-ALPHA", country="FR")


def make_field() -> ExtractedField:
    return ExtractedField(name="document_number", value="FICT-ID-000001", confidence=0.93)


def make_piece() -> Piece:
    return Piece(piece_id="PCE-FICT-001-1", piece_type=PieceType.IDENTITY_DOCUMENT,
                 file_name="id.pdf", mime_type="application/pdf", received_at=NOW,
                 ocr_status=OcrStatus.DONE, ocr_text="DOCUMENT FICTIF", extracted_fields=[make_field()])


def make_decision() -> Decision:
    return Decision(decision_id="DEC-FICT-001", decision_type=DecisionType.AUTO_APPROVE,
                    author_type=AuthorType.AGENT, author_id="routing-agent",
                    justification="Aucune règle d'escalade déclenchée.", routing=RoutingDecision.SIMPLE,
                    triggered_rules=["R9"], decided_at=NOW)


def make_dossier() -> Dossier:
    return Dossier(dossier_id="DOS-FICT-001", client_id="CLI-FICT-001", status=DossierStatus.APPROVED,
                   created_at=NOW, updated_at=NOW + timedelta(minutes=2),
                   requested_amount=Decimal("18500.00"), pieces=[make_piece()], final_decision=make_decision())


def make_event(sequence: int = 0, previous_hash: str = GENESIS_HASH) -> AuditEvent:
    return AuditEvent(event_id=f"EVT-FICT-{sequence}", dossier_id="DOS-FICT-001", sequence=sequence,
                      event_type=AuditEventType.DOSSIER_SUBMITTED,
                      payload={"requested_amount": "18500.00", "pieces": 3, "ok": True, "note": None},
                      occurred_at=NOW, previous_hash=previous_hash, current_hash=HASH_A)


FACTORIES = [make_client, make_field, make_piece, make_decision, make_dossier, make_event]


@pytest.mark.parametrize("factory", FACTORIES, ids=lambda f: f.__name__.removeprefix("make_"))
def test_json_round_trip(factory) -> None:
    """Chaque modèle se sérialise en JSON puis se relit à l'identique."""
    instance: BaseModel = factory()
    as_json = instance.model_dump_json()
    assert type(instance).model_validate_json(as_json) == instance


def test_serialization_format() -> None:
    data = make_dossier().model_dump(mode="json")
    assert data["requested_amount"] == "18500.00"      # Decimal -> chaîne
    assert data["created_at"] == "2026-10-05T08:30:00Z"  # UTC avec « Z »
    assert data["status"] == "approved"                 # enum -> valeur
    assert data["currency"] == "EUR"                    # défaut explicite


def test_defaults() -> None:
    d = Dossier(dossier_id="D", client_id="C", created_at=NOW, updated_at=NOW, requested_amount=Decimal("1.00"))
    assert d.status is DossierStatus.SUBMITTED
    assert d.pieces == [] and d.reminder_count == 0 and d.final_decision is None
    p = Piece(piece_id="P", piece_type=PieceType.QUOTE)
    assert p.ocr_status is OcrStatus.PENDING and p.is_missing is False and p.extracted_fields == []


def test_datetime_normalized_to_utc() -> None:
    paris = timezone(timedelta(hours=2))
    d = Dossier.model_validate_json(
        '{"dossier_id":"D","client_id":"C","created_at":"2026-10-05T10:30:00+02:00",'
        '"updated_at":"2026-10-05T10:30:00+02:00","requested_amount":"10.00"}')
    assert d.created_at == datetime(2026, 10, 5, 10, 30, tzinfo=paris)
    assert d.created_at.utcoffset() == timedelta(0)


def test_naive_datetime_rejected() -> None:
    with pytest.raises(ValidationError):
        Dossier.model_validate_json('{"dossier_id":"D","client_id":"C","created_at":"2026-10-05T10:30:00",'
                                    '"updated_at":"2026-10-05T10:30:00","requested_amount":"10.00"}')


def test_strict_and_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        Client.model_validate({**make_client().model_dump(), "unknown": 1})
    with pytest.raises(ValidationError):
        Dossier.model_validate_json('{"dossier_id":"D","client_id":"C","created_at":"2026-10-05T08:00:00Z",'
                                    '"updated_at":"2026-10-05T08:00:00Z","requested_amount":"10.00",'
                                    '"status":"inconnu"}')


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_bounds(confidence: float) -> None:
    with pytest.raises(ValidationError):
        ExtractedField(name="x", value="v", confidence=confidence)


def test_auto_reject_does_not_exist() -> None:
    assert "auto_reject" not in {d.value for d in DecisionType}


@pytest.mark.parametrize("decision_type", [DecisionType.HUMAN_APPROVE, DecisionType.HUMAN_REJECT])
def test_agent_cannot_take_human_decisions(decision_type: DecisionType) -> None:
    with pytest.raises(ValidationError):
        Decision(**{**make_decision().model_dump(), "decision_type": decision_type})


def test_human_cannot_auto_approve() -> None:
    with pytest.raises(ValidationError):
        Decision(**{**make_decision().model_dump(), "author_type": AuthorType.HUMAN})


@pytest.mark.parametrize("rule", ["R42", "R8"])  # R8 : hors MVP
def test_unknown_or_out_of_scope_rule_rejected(rule: str) -> None:
    with pytest.raises(ValidationError):
        Decision(**{**make_decision().model_dump(), "triggered_rules": [rule]})


def test_missing_piece_invariant() -> None:
    Piece(piece_id="P", piece_type=PieceType.QUOTE, is_missing=True)
    with pytest.raises(ValidationError):
        Piece(piece_id="P", piece_type=PieceType.QUOTE, is_missing=True, file_name="devis.pdf")


def test_approved_requires_matching_decision() -> None:
    with pytest.raises(ValidationError):
        Dossier(dossier_id="D", client_id="C", status=DossierStatus.APPROVED, created_at=NOW,
                updated_at=NOW, requested_amount=Decimal("10.00"))


def test_audit_event_is_frozen() -> None:
    event = make_event()
    with pytest.raises(ValidationError):
        event.payload = {}  # type: ignore[misc]


def test_audit_genesis_rule() -> None:
    with pytest.raises(ValidationError):
        make_event(sequence=0, previous_hash=HASH_A)
    with pytest.raises(ValidationError):
        make_event(sequence=1, previous_hash=GENESIS_HASH)
    make_event(sequence=1, previous_hash=HASH_A)


def test_audit_payload_rejects_floats() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(**{**make_event().model_dump(), "payload": {"score": 0.92}})
    with pytest.raises(ValidationError):
        AuditEvent(**{**make_event().model_dump(), "payload": {"nested": [{"x": 1.5}]}})


def test_audit_hash_format() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(**{**make_event().model_dump(), "current_hash": "A" * 64})  # majuscules refusées
