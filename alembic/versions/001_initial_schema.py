"""Schéma initial : tables métier + table d'audit append-only.

Revision ID: 001
Revises: None
Create Date: 2026-11-10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Extension pgvector --
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # -- clients --
    op.create_table(
        "clients",
        sa.Column("client_id", sa.String(64), primary_key=True),
        sa.Column("legal_name", sa.String(200), nullable=False),
        sa.Column("registration_number", sa.String(64)),
        sa.Column("legal_representative", sa.String(200)),
        sa.Column("country", sa.String(2), nullable=False),
    )

    # -- dossiers --
    op.create_table(
        "dossiers",
        sa.Column("dossier_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.String(64), sa.ForeignKey("clients.client_id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="submitted"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("reminder_count", sa.Integer, nullable=False, server_default="0"),
    )

    # -- pieces --
    op.create_table(
        "pieces",
        sa.Column("piece_id", sa.String(64), primary_key=True),
        sa.Column("dossier_id", sa.String(64), sa.ForeignKey("dossiers.dossier_id"), nullable=False),
        sa.Column("piece_type", sa.String(30), nullable=False),
        sa.Column("file_name", sa.String(255)),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("ocr_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ocr_text", sa.Text),
        sa.Column("is_missing", sa.Boolean, nullable=False, server_default="false"),
    )
    op.execute("ALTER TABLE pieces ADD COLUMN embedding vector(1536)")

    # -- extracted_fields --
    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("piece_id", sa.String(64), sa.ForeignKey("pieces.piece_id"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("value", sa.Text),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.UniqueConstraint("piece_id", "name", name="uq_piece_field_name"),
    )

    # -- decisions --
    op.create_table(
        "decisions",
        sa.Column("decision_id", sa.String(64), primary_key=True),
        sa.Column("dossier_id", sa.String(64), sa.ForeignKey("dossiers.dossier_id"), nullable=False, unique=True),
        sa.Column("decision_type", sa.String(30), nullable=False),
        sa.Column("author_type", sa.String(10), nullable=False),
        sa.Column("author_id", sa.String(64), nullable=False),
        sa.Column("justification", sa.Text, nullable=False),
        sa.Column("routing", sa.String(20)),
        sa.Column("triggered_rules", JSONB, nullable=False, server_default="[]"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )

    # -- audit_events (append-only) --
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("dossier_id", sa.String(64), sa.ForeignKey("dossiers.dossier_id"), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("current_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("dossier_id", "sequence", name="uq_audit_chain_sequence"),
    )

    # -- Triggers : interdire UPDATE et DELETE sur audit_events --
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_events_deny_update()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'UPDATE interdit sur la table audit_events (append-only)';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_audit_events_no_update
        BEFORE UPDATE ON audit_events
        FOR EACH ROW
        EXECUTE FUNCTION audit_events_deny_update();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION audit_events_deny_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'DELETE interdit sur la table audit_events (append-only)';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_audit_events_no_delete
        BEFORE DELETE ON audit_events
        FOR EACH ROW
        EXECUTE FUNCTION audit_events_deny_delete();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION audit_events_deny_truncate()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'TRUNCATE interdit sur la table audit_events (append-only)';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_audit_events_no_truncate
        BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT
        EXECUTE FUNCTION audit_events_deny_truncate();
    """)

    # -- Index utiles --
    op.create_index("ix_audit_events_dossier_seq", "audit_events", ["dossier_id", "sequence"])
    op.create_index("ix_dossiers_status", "dossiers", ["status"])
    op.create_index("ix_pieces_dossier", "pieces", ["dossier_id"])


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_truncate ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_delete ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_deny_truncate()")
    op.execute("DROP FUNCTION IF EXISTS audit_events_deny_delete()")
    op.execute("DROP FUNCTION IF EXISTS audit_events_deny_update()")

    op.drop_table("audit_events")
    op.drop_table("decisions")
    op.drop_table("extracted_fields")
    op.drop_table("pieces")
    op.drop_table("dossiers")
    op.drop_table("clients")

    op.execute("DROP EXTENSION IF EXISTS vector")
