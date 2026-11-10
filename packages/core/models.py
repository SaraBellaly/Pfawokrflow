"""Contrats de données (modèles Pydantic v2) du MVP Funding Workflow Automation.

Ce module ne contient AUCUNE logique métier (pas de routage, pas d'appel LLM,
pas de calcul de hash) : uniquement les structures, les enums et les invariants
de cohérence interne de chaque modèle.

Référence fonctionnelle : docs/data-contracts.md (vocabulaire : docs/glossary.md).
Les paramètres ci-dessous sont des propositions par défaut à confirmer :
voir docs/open-questions.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# ---------------------------------------------------------------------------
# Paramètres de cadrage (valeurs par défaut, cf. docs/open-questions.md)
# ---------------------------------------------------------------------------

#: Montant au-delà duquel un dossier est sensible (strictement supérieur). Q2.
HIGH_AMOUNT_THRESHOLD_EUR: Decimal = Decimal("50000.00")

#: Confiance minimale d'un champ obligatoire. Strictement inférieure => illisible. Q4.
CONFIDENCE_THRESHOLD: float = 0.80

#: Nombre de relances sans réponse avant escalade humaine. Q3.
MAX_REMINDERS: int = 2

#: Pays acceptés au MVP (ISO 3166-1 alpha-2). Q6.
ALLOWED_COUNTRIES: frozenset[str] = frozenset({"FR", "BE", "MA", "TN"})

#: Valeur de `previous_hash` du premier événement d'une chaîne (64 zéros).
GENESIS_HASH: str = "0" * 64

#: Identifiants des règles actives de docs/routing-rules.md.
#: R8 (pièce d'identité expirée) est hors MVP : identifiant réservé, refusé ici.
ROUTING_RULE_IDS: frozenset[str] = frozenset({"R1", "R2", "R3", "R4", "R5", "R6", "R7", "R9"})

# ---------------------------------------------------------------------------
# Types utilitaires
# ---------------------------------------------------------------------------


def _to_utc(value: datetime) -> datetime:
    """Normalise toute date avec fuseau en UTC (sérialisée avec le suffixe « Z »)."""
    return value.astimezone(timezone.utc)


#: Date-heure obligatoirement avec fuseau, normalisée en UTC.
UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]

#: Identifiant textuel non vide, sans espace ni « | ».
Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")]

#: Empreinte SHA-256 en hexadécimal minuscule.
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

#: Code pays ISO 3166-1 alpha-2.
CountryCode = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]

#: Montant monétaire positif, 2 décimales max.
Amount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class StrictModel(BaseModel):
    """Base commune : typage strict, champs inconnus refusés, validation à l'affectation."""

    model_config = ConfigDict(strict=True, extra="forbid", validate_assignment=True)


# ---------------------------------------------------------------------------
# Enums (valeurs = vocabulaire de docs/glossary.md)
# ---------------------------------------------------------------------------


class DossierStatus(str, Enum):
    """Cycle de vie d'un dossier."""

    SUBMITTED = "submitted"
    OCR_IN_PROGRESS = "ocr_in_progress"
    EXTRACTION_IN_PROGRESS = "extraction_in_progress"
    AWAITING_DOCUMENTS = "awaiting_documents"
    UNDER_REVIEW = "under_review"
    PENDING_HUMAN_REVIEW = "pending_human_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PieceType(str, Enum):
    """Types de pièces justificatives gérés au MVP."""

    IDENTITY_DOCUMENT = "identity_document"
    BALANCE_SHEET = "balance_sheet"
    QUOTE = "quote"
    PROOF_OF_ADDRESS = "proof_of_address"  # optionnel, non bloquant (Q1)


#: Pièces obligatoires : leur absence déclenche les règles R4/R5.
MANDATORY_PIECE_TYPES: frozenset[PieceType] = frozenset(
    {PieceType.IDENTITY_DOCUMENT, PieceType.BALANCE_SHEET, PieceType.QUOTE}
)

#: Champs que l'extraction doit produire pour chaque type de pièce.
#: Le périmètre exact du seuil de confiance (ces champs ou tous les champs) est à trancher (Q18).
MANDATORY_FIELDS: dict[PieceType, tuple[str, ...]] = {
    PieceType.IDENTITY_DOCUMENT: ("full_name", "document_number", "birth_date", "expiry_date", "nationality"),
    PieceType.BALANCE_SHEET: ("company_name", "fiscal_year", "revenue", "net_income", "total_equity", "total_debt"),
    PieceType.QUOTE: ("supplier_name", "client_name", "quote_number", "quote_date",
                      "total_amount_excl_tax", "total_amount_incl_tax"),
    PieceType.PROOF_OF_ADDRESS: ("holder_name", "address", "issue_date"),
}


class OcrStatus(str, Enum):
    """État de l'OCR d'une pièce."""

    PENDING = "pending"        # pas encore traitée (ou pièce manquante)
    DONE = "done"              # texte obtenu, champs extraits lisibles
    FAILED = "failed"          # échec technique (fichier corrompu, format non supporté)
    UNREADABLE = "unreadable"  # texte obtenu mais au moins un champ extrait < seuil (périmètre : Q18)


class RoutingDecision(str, Enum):
    """Résultat du routage. L'absence de routage (dossier en attente) est `None`."""

    SIMPLE = "simple"
    SENSITIVE = "sensitive"


class DecisionType(str, Enum):
    """Types de décision. L'agent ne peut produire que AUTO_APPROVE ou ESCALATE (Q7)."""

    AUTO_APPROVE = "auto_approve"
    ESCALATE = "escalate"
    HUMAN_APPROVE = "human_approve"
    HUMAN_REJECT = "human_reject"
    REQUEST_DOCUMENTS = "request_documents"  # auteur non tranché (Q15) : accepté pour agent et humain


class AuthorType(str, Enum):
    """Auteur d'une décision."""

    AGENT = "agent"
    HUMAN = "human"


#: Q7 (provisoire) : l'agent n'approuve qu'avec auto_approve et ne rejette jamais.
#: request_documents : auteur non tranché (Q15), donc accepté pour les deux auteurs.
AGENT_DECISION_TYPES: frozenset[DecisionType] = frozenset(
    {DecisionType.AUTO_APPROVE, DecisionType.ESCALATE, DecisionType.REQUEST_DOCUMENTS}
)
HUMAN_DECISION_TYPES: frozenset[DecisionType] = frozenset(
    {DecisionType.HUMAN_APPROVE, DecisionType.HUMAN_REJECT, DecisionType.REQUEST_DOCUMENTS}
)


class AuditEventType(str, Enum):
    """Types d'événements du journal d'audit (liste fermée)."""

    DOSSIER_SUBMITTED = "dossier_submitted"
    PIECE_RECEIVED = "piece_received"
    OCR_COMPLETED = "ocr_completed"
    OCR_FAILED = "ocr_failed"
    FIELDS_EXTRACTED = "fields_extracted"
    MISSING_PIECE_DETECTED = "missing_piece_detected"
    CLIENT_REMINDER_SENT = "client_reminder_sent"
    ROUTING_DECIDED = "routing_decided"
    ESCALATED_TO_HUMAN = "escalated_to_human"
    DECISION_RECORDED = "decision_recorded"
    STATUS_CHANGED = "status_changed"


class Currency(str, Enum):
    """Devises acceptées (EUR uniquement au MVP, Q10)."""

    EUR = "EUR"


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------


class Client(StrictModel):
    """Client demandeur. Identité minimale uniquement.

    Champs conformes à docs/data-contracts.md §3. Le caractère optionnel de
    `legal_representative` est provisoire tant que Q11 n'est pas tranchée.
    """

    client_id: Identifier
    legal_name: str = Field(min_length=1, max_length=200, description="Raison sociale ou nom complet")
    registration_number: str | None = Field(default=None, max_length=64, description="N° d'immatriculation")
    legal_representative: str | None = Field(default=None, min_length=1, max_length=200,
                                             description="Nom complet du représentant légal (entreprise)")
    country: CountryCode


class ExtractedField(StrictModel):
    """Champ extrait d'une pièce, avec son score de confiance.

    `value` vaut None si l'extraction n'a rien produit. Toutes les valeurs sont des
    chaînes (montants : "12500.00", dates : "AAAA-MM-JJ") pour éviter toute perte.
    """

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    value: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class Piece(StrictModel):
    """Pièce justificative d'un dossier (reçue ou constatée manquante)."""

    piece_id: Identifier
    piece_type: PieceType
    file_name: str | None = None
    mime_type: str | None = None
    received_at: UtcDatetime | None = None
    ocr_status: OcrStatus = OcrStatus.PENDING
    ocr_text: str | None = None
    extracted_fields: list[ExtractedField] = Field(default_factory=list)
    is_missing: bool = False

    @model_validator(mode="after")
    def _check_missing_consistency(self) -> Piece:
        if self.is_missing:
            if self.file_name is not None or self.received_at is not None:
                raise ValueError("une pièce manquante n'a ni fichier ni date de réception")
            if self.ocr_status is not OcrStatus.PENDING or self.ocr_text is not None or self.extracted_fields:
                raise ValueError("une pièce manquante ne peut pas avoir de résultat OCR/extraction")
        names = [f.name for f in self.extracted_fields]
        if len(names) != len(set(names)):
            raise ValueError("noms de champs extraits en double")
        return self


class Decision(StrictModel):
    """Décision prise sur un dossier, par un agent ou un humain."""

    decision_id: Identifier
    decision_type: DecisionType
    author_type: AuthorType
    author_id: str = Field(min_length=1, max_length=64, description="Nom de l'agent ou identifiant du validateur")
    justification: str = Field(min_length=1, max_length=4000)
    routing: RoutingDecision | None = None
    triggered_rules: list[str] = Field(default_factory=list, description="Ex. ['R3'] (docs/routing-rules.md), R8 exclue")
    decided_at: UtcDatetime

    @field_validator("triggered_rules")
    @classmethod
    def _check_rule_ids(cls, value: list[str]) -> list[str]:
        for rule in value:
            if rule not in ROUTING_RULE_IDS:
                raise ValueError(f"règle inconnue : {rule}")
        return value

    @model_validator(mode="after")
    def _check_author_rights(self) -> Decision:
        allowed = AGENT_DECISION_TYPES if self.author_type is AuthorType.AGENT else HUMAN_DECISION_TYPES
        if self.decision_type not in allowed:
            raise ValueError(f"{self.author_type.value} ne peut pas produire {self.decision_type.value}")
        return self


class Dossier(StrictModel):
    """Demande de financement."""

    dossier_id: Identifier
    client_id: Identifier
    status: DossierStatus = DossierStatus.SUBMITTED
    created_at: UtcDatetime
    updated_at: UtcDatetime
    requested_amount: Amount
    currency: Currency = Currency.EUR
    pieces: list[Piece] = Field(default_factory=list)
    reminder_count: int = Field(default=0, ge=0)
    final_decision: Decision | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Dossier:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at doit être postérieur ou égal à created_at")
        ids = [p.piece_id for p in self.pieces]
        if len(ids) != len(set(ids)):
            raise ValueError("piece_id en double dans le dossier")
        decision = self.final_decision
        if self.status is DossierStatus.APPROVED and (
            decision is None or decision.decision_type not in {DecisionType.AUTO_APPROVE, DecisionType.HUMAN_APPROVE}
        ):
            raise ValueError("un dossier approved exige une décision auto_approve ou human_approve")
        if self.status is DossierStatus.REJECTED and (
            decision is None or decision.decision_type is not DecisionType.HUMAN_REJECT
        ):
            raise ValueError("un dossier rejected exige une décision human_reject")
        return self


def _check_json_value(value: Any, path: str = "payload") -> None:
    """Refuse tout ce qui n'est pas canonisable de façon déterministe (cf. audit-chain.md)."""
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise ValueError(f"{path} : les flottants sont interdits (utiliser une chaîne)")
    if isinstance(value, list):
        for i, item in enumerate(value):
            _check_json_value(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} : les clés doivent être des chaînes")
            _check_json_value(item, f"{path}.{key}")
        return
    raise ValueError(f"{path} : type non autorisé ({type(value).__name__})")


class AuditEvent(StrictModel):
    """Événement du journal d'audit, immuable et chaîné par hash (docs/audit-chain.md)."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    event_id: Identifier
    dossier_id: Identifier
    sequence: int = Field(ge=0, description="Rang dans la chaîne, à partir de 0 (portée de la chaîne : Q14)")
    event_type: AuditEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: UtcDatetime
    previous_hash: Sha256Hex
    current_hash: Sha256Hex

    @field_validator("payload")
    @classmethod
    def _check_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        _check_json_value(value)
        return value

    @model_validator(mode="after")
    def _check_genesis(self) -> AuditEvent:
        if (self.sequence == 0) != (self.previous_hash == GENESIS_HASH):
            raise ValueError("seul l'événement de rang 0 a previous_hash = GENESIS_HASH")
        return self
