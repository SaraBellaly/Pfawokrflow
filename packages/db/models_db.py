"""Modèles SQLAlchemy (ORM) correspondant aux contrats de données Pydantic.

La table ``audit_events`` est en insertion seule : des triggers PostgreSQL
empêchent tout UPDATE et DELETE (voir la migration initiale).
"""

from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ClientRow(Base):
    __tablename__ = "clients"

    client_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(64))
    legal_representative: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(2), nullable=False)

    dossiers: Mapped[list[DossierRow]] = relationship(back_populates="client")


class DossierRow(Base):
    __tablename__ = "dossiers"

    dossier_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.client_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    reminder_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    client: Mapped[ClientRow] = relationship(back_populates="dossiers")
    pieces: Mapped[list[PieceRow]] = relationship(back_populates="dossier", cascade="all, delete-orphan")
    decision: Mapped[DecisionRow | None] = relationship(back_populates="dossier", uselist=False)


class PieceRow(Base):
    __tablename__ = "pieces"

    piece_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossiers.dossier_id"), nullable=False)
    piece_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ocr_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    ocr_text: Mapped[str | None] = mapped_column(Text)
    is_missing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    dossier: Mapped[DossierRow] = relationship(back_populates="pieces")
    extracted_fields: Mapped[list[ExtractedFieldRow]] = relationship(
        back_populates="piece", cascade="all, delete-orphan"
    )

    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))


class ExtractedFieldRow(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    piece_id: Mapped[str] = mapped_column(ForeignKey("pieces.piece_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)

    piece: Mapped[PieceRow] = relationship(back_populates="extracted_fields")

    __table_args__ = (UniqueConstraint("piece_id", "name", name="uq_piece_field_name"),)


class DecisionRow(Base):
    __tablename__ = "decisions"

    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossiers.dossier_id"), nullable=False, unique=True)
    decision_type: Mapped[str] = mapped_column(String(30), nullable=False)
    author_type: Mapped[str] = mapped_column(String(10), nullable=False)
    author_id: Mapped[str] = mapped_column(String(64), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    routing: Mapped[str | None] = mapped_column(String(20))
    triggered_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    dossier: Mapped[DossierRow] = relationship(back_populates="decision")


class AuditEventRow(Base):
    """Table d'audit en insertion seule (append-only).

    Les triggers PostgreSQL empêchent UPDATE et DELETE.
    """

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossiers.dossier_id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("dossier_id", "sequence", name="uq_audit_chain_sequence"),
    )
