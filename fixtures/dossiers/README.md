# Fixtures : dossiers de test fictifs

> **Toutes les données de ce dossier sont fictives.** Les noms de personnes portent le suffixe `FICTIF-…` et les entreprises la mention `(FICTIF)`. Les numéros commencent par `FICT-` et les adresses sont imaginaires. Chaque fichier contient `"_fictitious": true`. N'ajoutez jamais de données réelles ou dérivées de personnes réelles.

## Contenu

| Fichier | Rôle |
|---|---|
| `DOS-FICT-001.json` … `DOS-FICT-026.json` | Un dossier de test par fichier (23 fichiers ; les numéros 021, 024 et 025 sont retirés) |
| `_sensitive_list.json` | Liste sensible fictive (règle R1), avec une entrée leurre |

Ces fichiers sont **générés** par [`tools/gen_fixtures.py`](../../tools/gen_fixtures.py). Ne les modifiez pas à la main : modifiez le script, puis lancez `python tools/gen_fixtures.py`. Pour vérifier qu'ils sont à jour : `python tools/gen_fixtures.py --check`.

## Format d'une fixture

```jsonc
{
  "_fictitious": true,
  "_notice": "…",
  "fixture_id": "DOS-FICT-001",
  "scenario": "complete_simple",          // voir le tableau ci-dessous
  "description": "…",                      // en français
  "client":  { /* Client (data-contracts.md §3) */ },
  "dossier": { /* Dossier tel que soumis : status "submitted", pièces en ocr_status "pending" */ },
  "expected": {
    "pieces": [{                           // une entrée par pièce soumise
      "piece_id": "PCE-FICT-001-1",
      "piece_type": "identity_document",
      "ocr_status": "done",                // done | unreadable | failed
      "ocr_text": "…",                     // texte OCR attendu (simulé), null si failed
      "extracted_fields": [ /* ExtractedField : name, value, confidence simulée */ ]
    }],
    "missing_pieces": ["quote"],           // types obligatoires absents ([] sinon)
    "routing": "simple",                   // "simple" | "sensitive" | null (= awaiting_documents)
    "status": "approved",                  // statut attendu après traitement
    "decision_type": "auto_approve",       // auto_approve | escalate | null
    "triggered_rules": ["R9"]              // règles de docs/routing-rules.md
  }
}
```

Correspondance obligatoire (vérifiée par `tests/test_fixtures.py`) :

| `routing` | `status` | `decision_type` | `triggered_rules` |
|---|---|---|---|
| `"simple"` | `approved` | `auto_approve` | `["R9"]` |
| `"sensitive"` | `pending_human_review` | `escalate` | une ou plusieurs règles parmi R1, R2, R3, R5, R6, R7 |
| `null` | `awaiting_documents` | `null` | `["R4"]` |

Les scores de `confidence` sont **simulés**. Ils permettent de tester le routage de façon déterministe sans LLM. Les montants de TVA (20 %) sont arbitraires.

## Répartition

| Scénario | Fixtures | Routage attendu |
|---|---|---|
| `complete_simple` | 001 à 006 (005 avec le justificatif de domicile optionnel) | `simple` |
| `missing_piece` | 007 (devis), 008 (bilan, 1 relance), 009 (identité) | `null` (attente) |
| `missing_piece_after_reminders` | 010 (devis manquant après 2 relances) | `sensitive` (R5) |
| `unreadable_field` | 011 (confiance 0,42), 012 (confiance 0,79), 013 (OCR en échec) | `sensitive` (R6) |
| `high_amount` | 014 (50 000,01 €), 015, 016 | `sensitive` (R3) |
| `sensitive_list` | 017 (par `client_id`), 018 (nom identique, caractère pour caractère, à une entrée sans `client_id` ; liée à aucune règle de comparaison, Q16) | `sensitive` (R1) |
| `inconsistency` | 019 (raison sociale différente), 020 (devis > 30 % du CA) | `sensitive` (R7) |
| `edge_amount_equal_threshold` | 022 (50 000,00 € exactement) | `simple` |
| `edge_country_out_of_scope` | 023 (CA) | `sensitive` (R2) |
| `edge_confidence_equal_threshold` | 026 (confiance 0,80 exactement) | `simple` |

Total : **23 dossiers**, dont 8 `simple`, 12 `sensitive` et 3 `null`.

### Fixtures retirées

| Numéro | Ancien cas | Raison du retrait |
|---|---|---|
| 021 | Montant demandé supérieur au devis (ancien R7 c) | Règle hors MVP (non validée par l'équipe) |
| 024 | Pièce manquante et montant élevé | Le résultat dépend de Q12 (à trancher). Remplacée par la fixture-question `../open-questions/Q12-FICT-001.json` |
| 025 | Pièce d'identité expirée (ancien R8) | Règle hors MVP (non validée par l'équipe) |

## Fixtures-questions (`fixtures/open-questions/`)

Ces fixtures illustrent un cas dont le résultat dépend d'une question non tranchée. Elles ont le même format qu'un dossier, mais :
- `expected` ne contient **ni** `routing`, **ni** `status`, **ni** `decision_type`, **ni** `triggered_rules` ;
- un bloc `open_question` donne l'identifiant de la question, son texte et les options possibles.

Les tests vérifient seulement qu'elles se chargent : **aucune assertion de routage**.

| Fichier | Question |
|---|---|
| `Q12-FICT-001.json` | Q12 : bilan manquant et montant élevé (90 000 €). Faut-il une escalade immédiate ou attendre les pièces d'abord ? |

Voir la colonne « État actuel » de `docs/open-questions.md` pour la façon dont le dépôt reste neutre sur Q11 à Q18.
