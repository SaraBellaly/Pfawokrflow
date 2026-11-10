# Glossaire : vocabulaire commun

Ce document est la **source unique** du vocabulaire. Les autres documents (`scope.md`, `routing-rules.md`, `data-contracts.md` et `audit-chain.md`) ainsi que le code (`packages/core/models.py`) utilisent exactement ces termes. Pour changer une valeur, on modifie d'abord ce glossaire, puis le code et les autres documents.

Les valeurs entre `backticks` sont les valeurs techniques (en anglais). Les libellés sont en français.

## Statuts de dossier : `DossierStatus`

| Valeur | Libellé | Signification |
|---|---|---|
| `submitted` | Soumis | Dossier reçu, aucun traitement commencé |
| `ocr_in_progress` | OCR en cours | Lecture des pièces en cours |
| `extraction_in_progress` | Extraction en cours | Extraction des champs en cours |
| `awaiting_documents` | En attente de pièces | Pièce obligatoire manquante, relance client en cours. **Aucun routage n'est calculé.** |
| `under_review` | En analyse | Pièces complètes, règles de routage en cours d'évaluation |
| `pending_human_review` | En attente de validation humaine | Dossier routé `sensitive`, dans la file du validateur humain |
| `approved` | Approuvé | Décision finale positive (`auto_approve` ou `human_approve`) |
| `rejected` | Rejeté | Décision finale négative (`human_reject` uniquement) |

## Types de pièce : `PieceType`

| Valeur | Libellé | Obligatoire |
|---|---|---|
| `identity_document` | Pièce d'identité du représentant légal | Oui |
| `balance_sheet` | Bilan comptable (dernier exercice) | Oui |
| `quote` | Devis de l'investissement financé | Oui |
| `proof_of_address` | Justificatif de domicile / siège | Non (optionnel, non bloquant, Q1) |

## Statuts OCR : `OcrStatus`

| Valeur | Signification |
|---|---|
| `pending` | Pas encore traitée (ou pièce manquante) |
| `done` | Texte obtenu, tous les champs obligatoires ont une confiance **≥ 0,80** |
| `failed` | Échec technique : aucun texte exploitable |
| `unreadable` | Texte obtenu mais au moins un champ extrait a une confiance **strictement inférieure à 0,80** (champs concernés : Q18, à trancher) |

## Routage : `RoutingDecision`

| Valeur | Libellé | Effet |
|---|---|---|
| `simple` | Dossier simple | Décision automatique `auto_approve` |
| `sensitive` | Dossier sensible | Décision `escalate`, puis validation humaine |
| *(absent / `null`)* | Pas de routage | Dossier en `awaiting_documents`. Le routage sera calculé plus tard. |

## Types de décision : `DecisionType`

| Valeur | Auteur autorisé | Signification |
|---|---|---|
| `auto_approve` | agent | Approbation automatique d'un dossier `simple` |
| `escalate` | agent | Transmission d'un dossier `sensitive` au validateur humain |
| `human_approve` | humain | Approbation par le validateur |
| `human_reject` | humain | Rejet par le validateur (l'agent ne rejette jamais, Q7) |
| `request_documents` | agent ou humain (non tranché, Q15) | Demande de pièces complémentaires |

La relance automatique pour pièce manquante est tracée par les événements `missing_piece_detected` et `client_reminder_sent`. Doit-elle aussi produire une `Decision` `request_documents` ? C'est à trancher (Q15).

## Auteur : `AuthorType`

`agent` (un composant automatique, identifié par son nom) ou `human` (un validateur, identifié par son identifiant).

## Événements d'audit : `AuditEventType`

| Valeur | Émis quand |
|---|---|
| `dossier_submitted` | Le dossier est créé |
| `piece_received` | Une pièce est attachée au dossier |
| `ocr_completed` | L'OCR d'une pièce se termine (`done` ou `unreadable`) |
| `ocr_failed` | L'OCR d'une pièce échoue techniquement (`failed`) |
| `fields_extracted` | Les champs d'une pièce sont extraits |
| `missing_piece_detected` | Une pièce obligatoire manquante est détectée |
| `client_reminder_sent` | Une relance client est émise (simulée au MVP) |
| `routing_decided` | Le routage est calculé |
| `escalated_to_human` | Le dossier entre dans la file du validateur |
| `decision_recorded` | Une décision (agent ou humain) est enregistrée |
| `status_changed` | Le statut du dossier change |

## Autres termes

- **Champ obligatoire** : champ que l'extraction doit produire pour un type de pièce (`MANDATORY_FIELDS`, voir `data-contracts.md` §4). Les champs soumis au seuil de confiance (ceux-ci seulement, ou tous) restent à trancher (Q18).
- **Liste sensible** : liste **fictive** de clients à escalader systématiquement (`fixtures/dossiers/_sensitive_list.json`). Au MVP, elle remplace un vrai contrôle KYC/AML.
- **Relance** : message au client demandant une pièce manquante. Au MVP, la relance est simulée (aucun email réel). Le compteur `reminder_count` est incrémenté.
- **Comparaison de noms** : la méthode (égalité stricte ou normalisation) est à trancher (Q16).
- **Chaîne d'audit** : suite d'`AuditEvent` chaînés par SHA-256 (voir `audit-chain.md`). Sa portée (par dossier ou globale) est à trancher (Q14).
