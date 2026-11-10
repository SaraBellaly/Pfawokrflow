"""Génère les fixtures fictives de fixtures/dossiers/ et fixtures/open-questions/ (voir tools/README.md).

Usage :
    python tools/gen_fixtures.py            # (ré)écrit les fichiers
    python tools/gen_fixtures.py --check    # compare sans écrire ; code retour 1 si écart
    python tools/gen_fixtures.py --out DIR  # écrit dans un autre répertoire racine (à la place de fixtures/)
"""
import argparse
import json
from decimal import Decimal
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "fixtures"

#: Contenu généré : nom de fichier -> texte (rempli par build() et en fin de script).
GENERATED: dict[str, str] = {}


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"

NOTICE = ("Données entièrement fictives générées pour les tests. Noms, numéros et entreprises "
          "sont inventés (marqués FICTIF/FICT) ; toute ressemblance serait fortuite.")
MANDATORY = {
    "identity_document": ["full_name", "document_number", "birth_date", "expiry_date", "nationality"],
    "balance_sheet": ["company_name", "fiscal_year", "revenue", "net_income", "total_equity", "total_debt"],
    "quote": ["supplier_name", "client_name", "quote_number", "quote_date", "total_amount_excl_tax", "total_amount_incl_tax"],
    "proof_of_address": ["holder_name", "address", "issue_date"],
}
CONFS = [0.97, 0.93, 0.95, 0.91, 0.98, 0.94, 0.96, 0.92, 0.99]


def money(x):
    return f"{Decimal(str(x)).quantize(Decimal('0.01'))}"


def fields(ptype, values, overrides):
    out = []
    for i, name in enumerate(MANDATORY[ptype]):
        value, conf = values[name], CONFS[(i + len(ptype)) % len(CONFS)]
        if name in overrides:
            value, conf = overrides[name]
        out.append({"name": name, "value": value, "confidence": conf})
    return out


def status_of(flds):
    return "done" if all(f["value"] is not None and f["confidence"] >= 0.80 for f in flds) else "unreadable"


def identity(n, rep, birth, expiry, nat, overrides=None, ocr_text=None):
    v = {"full_name": rep, "document_number": f"FICT-ID-{n:06d}", "birth_date": birth,
         "expiry_date": expiry, "nationality": nat}
    text = ocr_text or (
        "CARTE D'IDENTITÉ — DOCUMENT FICTIF (spécimen de test)\n"
        f"Nom complet : {rep}\nN° document : {v['document_number']}\n"
        f"Né(e) le : {birth}\nExpire le : {expiry}\nNationalité : {nat}")
    return "identity_document", text, fields("identity_document", v, overrides or {})


def balance(company, year, revenue, net, equity, debt, overrides=None, ocr_text=None):
    v = {"company_name": company, "fiscal_year": str(year), "revenue": money(revenue),
         "net_income": money(net), "total_equity": money(equity), "total_debt": money(debt)}
    text = ocr_text or (
        f"BILAN COMPTABLE — DOCUMENT FICTIF\nSociété : {company}\nExercice : {year}\n"
        f"Chiffre d'affaires : {v['revenue']} EUR\nRésultat net : {v['net_income']} EUR\n"
        f"Capitaux propres : {v['total_equity']} EUR\nDettes totales : {v['total_debt']} EUR")
    return "balance_sheet", text, fields("balance_sheet", v, overrides or {})


def quote(n, supplier, client_name, qdate, ttc, overrides=None):
    ht = money(Decimal(str(ttc)) / Decimal("1.2"))
    v = {"supplier_name": supplier, "client_name": client_name, "quote_number": f"FICT-DEV-{n:05d}",
         "quote_date": qdate, "total_amount_excl_tax": ht, "total_amount_incl_tax": money(ttc)}
    text = (f"DEVIS N° {v['quote_number']} — DOCUMENT FICTIF\nFournisseur : {supplier}\n"
            f"Client : {client_name}\nDate : {qdate}\nTotal HT : {ht} EUR\nTotal TTC : {v['total_amount_incl_tax']} EUR")
    return "quote", text, fields("quote", v, overrides or {})


def address(holder, addr, date):
    v = {"holder_name": holder, "address": addr, "issue_date": date}
    text = f"JUSTIFICATIF DE DOMICILE — DOCUMENT FICTIF\nTitulaire : {holder}\nAdresse : {addr}\nÉmis le : {date}"
    return "proof_of_address", text, fields("proof_of_address", v, {})


def failed(ptype):
    return ptype, None, []


def build(n, scenario, description, legal_name, rep, country, amount, created, docs,
          routing, rules, missing=(), reminders=0, client_id=None, question=None):
    """Enregistre une fixture. Avec `question`, c'est une fixture-question sans résultat attendu."""
    fid = question["fixture_id"] if question else f"DOS-FICT-{n:03d}"
    cid = client_id or f"CLI-FICT-{n:03d}"
    pieces, exp_pieces = [], []
    for i, (ptype, text, flds) in enumerate(docs, start=1):
        pid = f"PCE-FICT-{n:03d}-{i}"
        pieces.append({"piece_id": pid, "piece_type": ptype, "file_name": f"{fid}_{ptype}.pdf",
                       "mime_type": "application/pdf", "received_at": created, "ocr_status": "pending",
                       "ocr_text": None, "extracted_fields": [], "is_missing": False})
        exp_pieces.append({"piece_id": pid, "piece_type": ptype,
                           "ocr_status": "failed" if text is None else status_of(flds),
                           "ocr_text": text, "extracted_fields": flds})
    if question:
        expected = {"pieces": exp_pieces, "missing_pieces": list(missing)}  # pas de routage attendu
    else:
        if routing is None:
            status, decision = "awaiting_documents", None
        elif routing == "simple":
            status, decision = "approved", "auto_approve"
        else:
            status, decision = "pending_human_review", "escalate"
        expected = {"pieces": exp_pieces, "missing_pieces": list(missing), "routing": routing,
                    "status": status, "decision_type": decision, "triggered_rules": rules}
    data = {
        "_fictitious": True,
        "_notice": NOTICE,
        "fixture_id": fid,
        "scenario": scenario,
        "description": description,
        "client": {"client_id": cid, "legal_name": legal_name,
                   "registration_number": f"FICT-RCS-{n:04d}", "legal_representative": rep, "country": country},
        "dossier": {"dossier_id": fid, "client_id": cid, "status": "submitted", "created_at": created,
                    "updated_at": created, "requested_amount": money(amount), "currency": "EUR",
                    "pieces": pieces, "reminder_count": reminders, "final_decision": None},
        "expected": expected,
    }
    if question:
        data["open_question"] = {k: v for k, v in question.items() if k != "fixture_id"}
        GENERATED[f"open-questions/{fid}.json"] = dump(data)
    else:
        GENERATED[f"dossiers/{fid}.json"] = dump(data)


SUP = "Fournisseur Oméga Équipements (FICTIF) SAS"


def full(n, name, rep, nat, rev, ttc, qdate="2026-09-15", extra=()):
    return [identity(n, rep, "1984-04-12", "2031-03-01", nat),
            balance(name, 2025, rev, Decimal(rev) * Decimal("0.08"), Decimal(rev) * Decimal("0.35"), Decimal(rev) * Decimal("0.25")),
            quote(n, SUP, name, qdate, ttc), *extra]


# --- Dossiers complets simples -------------------------------------------------
simple = [
    (1, "Menuiserie Alpha (FICTIF) SARL", "Yanis FICTIF-ALPHA", "FR", 18500, 210000, 18500),
    (2, "Boulangerie Bêta (FICTIF) SPRL", "Inès FICTIF-BETA", "BE", 9200, 145000, 9600),
    (3, "Atelier Gamma (FICTIF) SARL", "Karim FICTIF-GAMMA", "MA", 32000, 400000, 32000),
    (4, "Transports Delta (FICTIF) SUARL", "Salma FICTIF-DELTA", "TN", 45000, 520000, 47500),
    (6, "Paysages Zêta (FICTIF) SRL", "Léa FICTIF-ZETA", "BE", 12000, 98000, 12400),
]
for n, name, rep, c, amt, rev, ttc in simple:
    build(n, "complete_simple", "Dossier complet, cohérent, sous le seuil : approbation automatique.",
          name, rep, c, amt, f"2026-10-0{n}T08:30:00Z", full(n, name, rep, c, rev, ttc), "simple", ["R9"])
name, rep = "Imprimerie Epsilon (FICTIF) SAS", "Hugo FICTIF-EPSILON"
build(5, "complete_simple", "Dossier complet avec justificatif de domicile optionnel fourni.",
      name, rep, "FR", 27500, "2026-10-05T09:00:00Z",
      full(5, name, rep, "FR", 300000, 27500,
           extra=[address(name, "12 rue Imaginaire, 00000 Villefictive", "2026-08-01")]), "simple", ["R9"])

# --- Pièce manquante (attente) --------------------------------------------------
def without(docs, ptype):
    return [d for d in docs if d[0] != ptype]

for n, name, rep, c, amt, miss, rem in [
    (7, "Garage Êta (FICTIF) SARL", "Malik FICTIF-ETA", "FR", 22000, "quote", 0),
    (8, "Pressing Thêta (FICTIF) SARL", "Nora FICTIF-THETA", "MA", 15000, "balance_sheet", 1),
    (9, "Fromagerie Iota (FICTIF) SAS", "Paul FICTIF-IOTA", "FR", 8000, "identity_document", 0),
]:
    build(n, "missing_piece", f"Pièce obligatoire manquante ({miss}), {rem} relance(s) envoyée(s) : attente, pas de routage.",
          name, rep, c, amt, f"2026-10-{n:02d}T10:00:00Z", without(full(n, name, rep, c, 200000, amt), miss),
          None, ["R4"], missing=[miss], reminders=rem)

name, rep = "Plomberie Kappa (FICTIF) SARL", "Sofia FICTIF-KAPPA"
build(10, "missing_piece_after_reminders", "Devis toujours manquant après 2 relances : escalade.",
      name, rep, "BE", 19000, "2026-10-10T10:00:00Z", without(full(10, name, rep, "BE", 190000, 19000), "quote"),
      "sensitive", ["R5"], missing=["quote"], reminders=2)

# --- Champ illisible ----------------------------------------------------------
name, rep = "Électricité Lambda (FICTIF) SARL", "Omar FICTIF-LAMBDA"
docs = full(11, name, rep, "FR", 230000, 21000)
docs[0] = identity(11, rep, "1979-11-02", "2030-07-15", "FR",
                   overrides={"document_number": ("F?CT-ID-0▒0▒11", 0.42)},
                   ocr_text=("CARTE D'IDENTITÉ — DOCUMENT FICTIF (spécimen de test)\n"
                             f"Nom complet : {rep}\nN° document : F?CT-ID-0▒0▒11\n"
                             "Né(e) le : 1979-11-02\nExpire le : 2030-07-15\nNationalité : FR"))
build(11, "unreadable_field", "Numéro de pièce d'identité illisible (confiance 0,42) : escalade.",
      name, rep, "FR", 21000, "2026-10-11T08:00:00Z", docs, "sensitive", ["R6"])

name, rep = "Céramique Mu (FICTIF) SARL", "Rania FICTIF-MU"
docs = full(12, name, rep, "TN", 260000, 26000)
docs[1] = balance(name, 2025, 260000, 20800, 91000, 65000, overrides={"revenue": ("260000.00", 0.79)})
build(12, "unreadable_field", "Chiffre d'affaires lu avec une confiance de 0,79 (< 0,80, borne stricte) : escalade.",
      name, rep, "TN", 26000, "2026-10-12T08:00:00Z", docs, "sensitive", ["R6"])

name, rep = "Traiteur Nu (FICTIF) SARL", "Lucas FICTIF-NU"
docs = full(13, name, rep, "FR", 180000, 14000)
docs[2] = failed("quote")
build(13, "unreadable_field", "OCR en échec sur le devis (fichier simulé corrompu) : escalade.",
      name, rep, "FR", 14000, "2026-10-13T08:00:00Z", docs, "sensitive", ["R6"])

# --- Montant élevé --------------------------------------------------------------
for n, name, rep, c, amt, rev, ttc, desc in [
    (14, "Logistique Xi (FICTIF) SAS", "Chloé FICTIF-XI", "FR", "50000.01", 600000, 52000, "Montant 50 000,01 € (juste au-dessus du seuil) : escalade."),
    (15, "Agro Omicron (FICTIF) SA", "Adam FICTIF-OMICRON", "MA", 120000, 1500000, 120000, "Montant 120 000 € : escalade."),
    (16, "Bâtiments Pi (FICTIF) SA", "Emma FICTIF-PI", "FR", 250000, 2400000, 260000, "Montant 250 000 € : escalade."),
]:
    build(n, "high_amount", desc, name, rep, c, amt, f"2026-10-{n:02d}T09:15:00Z",
          full(n, name, rep, c, rev, ttc), "sensitive", ["R3"])

# --- Liste sensible fictive -------------------------------------------------------
name, rep = "Import Rhô (FICTIF) SARL", "Jade FICTIF-RHO"
build(17, "sensitive_list", "Client présent sur la liste sensible fictive (correspondance par client_id).",
      name, rep, "FR", 16000, "2026-10-17T11:00:00Z", full(17, name, rep, "FR", 170000, 16000), "sensitive", ["R1"])
# Nom identique caractère pour caractère à une entrée de la liste, sans client_id.
name, rep = "Négoce Sigma (FICTIF) SARL", "Nathan FICTIF-SIGMA"
build(18, "sensitive_list", "Teste un nom identique, caractère pour caractère, à une entrée de la liste "
      "sensible fictive (entrée sans client_id). Cette fixture n'est liée à aucune règle de comparaison "
      "des noms (Q16, non tranchée).",
      name, rep, "BE", 11000, "2026-10-18T11:00:00Z", full(18, name, rep, "BE", 125000, 11000), "sensitive", ["R1"])

# --- Incohérences ---------------------------------------------------------------
name, rep = "Studio Tau (FICTIF) SARL", "Zoé FICTIF-TAU"
docs = full(19, name, rep, "FR", 160000, 13000)
docs[2] = quote(19, SUP, "Studio Tau Bis (FICTIF) SARL", "2026-09-15", 13000)
build(19, "inconsistency", "Raison sociale du devis différente de celle du bilan et du client : escalade.",
      name, rep, "FR", 13000, "2026-10-19T14:00:00Z", docs, "sensitive", ["R7"])

name, rep = "Couture Upsilon (FICTIF) SARL", "Amine FICTIF-UPSILON"
build(20, "inconsistency", "Devis TTC (36 000 €) supérieur à 30 % du chiffre d'affaires (80 000 €) : escalade.",
      name, rep, "TN", 36000, "2026-10-20T14:00:00Z", full(20, name, rep, "TN", 80000, 36000), "sensitive", ["R7"])

# DOS-FICT-021 (montant demandé > devis, ancien R7 c) : retirée, règle hors MVP.

# --- Cas limites -----------------------------------------------------------------
name, rep = "Mécanique Chi (FICTIF) SAS", "Théo FICTIF-CHI"
build(22, "edge_amount_equal_threshold", "Montant exactement égal à 50 000,00 € : pas d'escalade (borne stricte), dossier simple.",
      name, rep, "FR", "50000.00", "2026-10-22T09:00:00Z", full(22, name, rep, "FR", 400000, 50000), "simple", ["R9"])

name, rep = "Érable Psi (FICTIF) Inc.", "Maya FICTIF-PSI"
build(23, "edge_country_out_of_scope", "Client établi dans un pays hors périmètre (CA) : escalade.",
      name, rep, "CA", 17000, "2026-10-23T09:00:00Z", full(23, name, rep, "CA", 190000, 17000), "sensitive", ["R2"])

# DOS-FICT-024 (pièce manquante + montant élevé) : retirée des dossiers, car elle dépend de Q12.
# Elle est remplacée par la fixture-question Q12-FICT-001 ci-dessous, sans routage attendu.
name, rep = "Énergie Oméga (FICTIF) SAS", "Rayan FICTIF-OMEGA"
build(901, "open_question", "Bilan manquant (0 relance) ET montant élevé (90 000 €). Le résultat dépend "
      "de Q12 : aucun routage attendu tant que la question n'est pas tranchée.",
      name, rep, "FR", 90000, "2026-10-24T09:00:00Z",
      without(full(901, name, rep, "FR", 900000, 90000), "balance_sheet"),
      None, [], missing=["balance_sheet"],
      question={"fixture_id": "Q12-FICT-001", "id": "Q12",
                "text": "Un dossier incomplet qui déclenche aussi R1, R2 ou R3 est-il escaladé "
                        "immédiatement ou mis d'abord en attente des pièces ?",
                "options": [
                    {"label": "A : escalade immédiate", "routing": "sensitive",
                     "status": "pending_human_review", "triggered_rules": ["R3"]},
                    {"label": "B : attente des pièces d'abord", "routing": None,
                     "status": "awaiting_documents", "triggered_rules": ["R4"]},
                ]})
# DOS-FICT-025 (pièce d'identité expirée, ancien R8) : retirée, règle hors MVP.

name, rep = "Cartonnerie Bet (FICTIF) SARL", "Samy FICTIF-BET"
docs = full(26, name, rep, "MA", 230000, 23000)
docs[1] = balance(name, 2025, 230000, 18400, 80500, 57500, overrides={"net_income": ("18400.00", 0.80)})
build(26, "edge_confidence_equal_threshold", "Résultat net lu avec une confiance de 0,80 exactement : lisible (borne stricte), dossier simple.",
      name, rep, "MA", 23000, "2026-10-26T09:00:00Z", docs, "simple", ["R9"])

# --- Liste sensible fictive --------------------------------------------------------
sensitive = {
    "_fictitious": True,
    "_notice": NOTICE + " Cette liste remplace, pour les tests, un contrôle KYC/AML réel.",
    "entries": [
        {"entry_id": "SL-FICT-001", "client_id": "CLI-FICT-017", "legal_name": "Import Rhô (FICTIF) SARL",
         "reason": "Signalement fictif : incident de paiement simulé"},
        {"entry_id": "SL-FICT-002", "client_id": None, "legal_name": "Négoce Sigma (FICTIF) SARL",
         "reason": "Signalement fictif : homonymie à vérifier"},
        {"entry_id": "SL-FICT-003", "client_id": "CLI-FICT-900", "legal_name": "Société Leurre (FICTIF) SA",
         "reason": "Entrée leurre : ne correspond à aucune fixture"},
    ],
}
GENERATED["dossiers/_sensitive_list.json"] = dump(sensitive)

#: Motifs des fichiers gérés par ce script (pour repérer les fichiers en trop).
MANAGED_GLOBS = ("dossiers/DOS-FICT-*.json", "dossiers/_sensitive_list.json", "open-questions/*.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère les fixtures fictives.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="répertoire de sortie")
    parser.add_argument("--check", action="store_true", help="compare sans écrire (code 1 si écart)")
    args = parser.parse_args()
    out: Path = args.out

    # Fichiers générés existants (les README et autres fichiers ne sont pas concernés).
    existing = {p.relative_to(out).as_posix() for pattern in MANAGED_GLOBS for p in out.glob(pattern)}
    stale = sorted(existing - GENERATED.keys())

    if args.check:
        diffs = [name for name, text in GENERATED.items()
                 if not (out / name).exists() or (out / name).read_bytes() != text.encode("utf-8")]
        for name in diffs:
            print(f"ÉCART   {name}")
        for name in stale:
            print(f"EN TROP {name}")
        print(f"{len(GENERATED)} fichiers attendus, {len(diffs)} écart(s), {len(stale)} en trop")
        return 1 if diffs or stale else 0

    for name, text in GENERATED.items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_bytes(text.encode("utf-8"))  # UTF-8, fins de ligne LF
    for name in stale:
        print(f"Attention : {name} n'est plus généré ; supprimez-le s'il est obsolète.")
    print(f"{len(GENERATED)} fichiers écrits dans {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
