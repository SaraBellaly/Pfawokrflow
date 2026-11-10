"""Tâches Celery (stubs semaine 2 — la logique métier viendra en semaine 3+)."""

from __future__ import annotations

from worker.celery_app import celery


@celery.task(name="ocr.process_piece")
def process_piece(dossier_id: str, piece_id: str) -> dict:
    """Lance l'OCR sur une pièce (stub)."""
    return {"dossier_id": dossier_id, "piece_id": piece_id, "status": "stub"}


@celery.task(name="extraction.extract_fields")
def extract_fields(dossier_id: str, piece_id: str) -> dict:
    """Extrait les champs d'une pièce après OCR (stub)."""
    return {"dossier_id": dossier_id, "piece_id": piece_id, "status": "stub"}
