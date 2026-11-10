"""Vérifie que les fixtures sont chargeables, fictives et cohérentes avec docs/routing-rules.md.

Ces tests ne réalisent PAS le routage : ils contrôlent que les valeurs attendues des
fixtures respectent les bornes et la correspondance routage / statut / décision.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from core.models import (
    ALLOWED_COUNTRIES,
    CONFIDENCE_THRESHOLD,
    HIGH_AMOUNT_THRESHOLD_EUR,
    MANDATORY_FIELDS,
    MANDATORY_PIECE_TYPES,
    MAX_REMINDERS,
    Client,
    Dossier,
    DossierStatus,
    ExtractedField,
    OcrStatus,
    PieceType,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "dossiers"
FIXTURE_FILES = sorted(FIXTURES_DIR.glob("DOS-FICT-*.json"))
QUESTION_FILES = sorted((FIXTURES_DIR.parent / "open-questions").glob("*.json"))
SENSITIVE_RULES = {"R1", "R2", "R3", "R5", "R6", "R7"}  # R8 hors MVP
REQUIRED_SCENARIOS = {"complete_simple", "missing_piece", "unreadable_field", "high_amount",
                      "sensitive_list", "inconsistency"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


SENSITIVE = load(FIXTURES_DIR / "_sensitive_list.json")


def listed_by_client_id(client: Client) -> bool:
    # Seule la correspondance par identifiant est vérifiée : la comparaison des noms
    # n'est pas tranchée (Q16) et n'est donc pas encodée ici.
    return any(entry["client_id"] == client.client_id for entry in SENSITIVE["entries"])


@pytest.fixture(params=FIXTURE_FILES, ids=lambda p: p.stem)
def fixture(request) -> dict:
    return load(request.param)


def test_fixture_count() -> None:
    assert 20 <= len(FIXTURE_FILES) <= 30


def test_required_scenarios_covered() -> None:
    scenarios = {load(p)["scenario"] for p in FIXTURE_FILES}
    assert REQUIRED_SCENARIOS <= scenarios


def test_sensitive_list_is_fictitious() -> None:
    assert SENSITIVE["_fictitious"] is True


def test_fixture_is_fictitious_and_named(fixture: dict) -> None:
    assert fixture["_fictitious"] is True
    assert fixture["dossier"]["dossier_id"] == fixture["fixture_id"]
    assert "FICTIF" in fixture["client"]["legal_name"].upper()
    assert "FICTIF" in fixture["client"]["legal_representative"].upper()


def test_models_validate(fixture: dict) -> None:
    client = Client.model_validate_json(json.dumps(fixture["client"]))
    dossier = Dossier.model_validate_json(json.dumps(fixture["dossier"]))
    assert dossier.client_id == client.client_id
    assert dossier.status is DossierStatus.SUBMITTED


def test_routing_status_decision_mapping(fixture: dict) -> None:
    exp = fixture["expected"]
    routing, rules = exp["routing"], exp["triggered_rules"]
    assert routing in {"simple", "sensitive", None}
    if routing == "simple":
        assert (exp["status"], exp["decision_type"], rules) == ("approved", "auto_approve", ["R9"])
    elif routing == "sensitive":
        assert (exp["status"], exp["decision_type"]) == ("pending_human_review", "escalate")
        assert rules and set(rules) <= SENSITIVE_RULES
    else:  # null : dossier en attente de pièces
        assert (exp["status"], exp["decision_type"], rules) == ("awaiting_documents", None, ["R4"])
        assert exp["missing_pieces"], "un dossier en attente doit avoir une pièce manquante"


def test_missing_pieces_match_dossier(fixture: dict) -> None:
    submitted = {p["piece_type"] for p in fixture["dossier"]["pieces"]}
    expected_missing = {PieceType(t) for t in fixture["expected"]["missing_pieces"]}
    assert expected_missing == MANDATORY_PIECE_TYPES - {PieceType(t) for t in submitted}


def test_expected_pieces_consistent(fixture: dict) -> None:
    submitted_ids = [p["piece_id"] for p in fixture["dossier"]["pieces"]]
    expected = fixture["expected"]["pieces"]
    assert [p["piece_id"] for p in expected] == submitted_ids
    for piece in expected:
        status = OcrStatus(piece["ocr_status"])
        fields = [ExtractedField.model_validate_json(json.dumps(f)) for f in piece["extracted_fields"]]
        if status is OcrStatus.FAILED:
            assert piece["ocr_text"] is None and fields == []
            continue
        assert piece["ocr_text"] and "FICTIF" in piece["ocr_text"]
        # Les fixtures ne contiennent que les champs de MANDATORY_FIELDS : le résultat est
        # donc le même quelle que soit la réponse à Q18 (périmètre du seuil).
        assert [f.name for f in fields] == list(MANDATORY_FIELDS[PieceType(piece["piece_type"])])
        readable = all(f.value is not None and f.confidence >= CONFIDENCE_THRESHOLD for f in fields)
        # Borne stricte : < 0,80 => unreadable ; = 0,80 => lisible.
        assert status is (OcrStatus.DONE if readable else OcrStatus.UNREADABLE)


def test_threshold_rules_consistent(fixture: dict) -> None:
    """R2 et R3 : si et seulement si leur condition est vraie. R1 : implication par client_id."""
    client = Client.model_validate_json(json.dumps(fixture["client"]))
    amount = Decimal(fixture["dossier"]["requested_amount"])
    rules = set(fixture["expected"]["triggered_rules"])
    assert "R8" not in rules, "R8 est hors MVP"
    if listed_by_client_id(client):
        assert "R1" in rules
    assert ("R2" in rules) == (client.country not in ALLOWED_COUNTRIES)
    assert ("R3" in rules) == (amount > HIGH_AMOUNT_THRESHOLD_EUR)  # 50 000,00 exactement : pas R3


def test_missing_and_unreadable_rules_consistent(fixture: dict) -> None:
    exp = fixture["expected"]
    rules = set(exp["triggered_rules"])
    reminders = fixture["dossier"]["reminder_count"]
    # Implications seulement : aucun ordre d'évaluation entre R1/R2/R3 et R4/R5 n'est encodé (Q12).
    if "R4" in rules:
        assert exp["missing_pieces"] and reminders < MAX_REMINDERS
    if "R5" in rules:
        assert exp["missing_pieces"] and reminders >= MAX_REMINDERS
    if not exp["missing_pieces"]:
        assert not rules & {"R4", "R5"}
        has_bad_piece = any(p["ocr_status"] in {"failed", "unreadable"} for p in exp["pieces"]
                            if PieceType(p["piece_type"]) in MANDATORY_PIECE_TYPES)
        assert ("R6" in rules) == has_bad_piece


# --- Fixtures-questions (fixtures/open-questions/) ------------------------------
# Elles illustrent un cas dont le résultat dépend d'une question non tranchée.
# Aucune assertion de routage : on vérifie seulement qu'elles se chargent.

def test_question_fixtures_exist() -> None:
    assert QUESTION_FILES, "au moins une fixture-question attendue (Q12)"


@pytest.mark.parametrize("path", QUESTION_FILES, ids=lambda p: p.stem)
def test_question_fixture_loads(path: Path) -> None:
    data = load(path)
    assert data["_fictitious"] is True
    client = Client.model_validate_json(json.dumps(data["client"]))
    dossier = Dossier.model_validate_json(json.dumps(data["dossier"]))
    assert dossier.client_id == client.client_id
    assert data["open_question"]["id"].startswith("Q")
