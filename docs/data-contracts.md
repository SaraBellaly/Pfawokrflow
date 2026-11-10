# Contrats de données

> Implémentation de référence : [`packages/core/models.py`](../packages/core/models.py) (Pydantic v2). Vocabulaire : voir [glossary.md](glossary.md).
>
> En cas d'écart entre ce document et le code, **le code fait foi pour les types** et **ce document fait foi pour l'intention**. Tout écart est un bug à corriger.

## 1. Conventions générales

| Convention | Règle |
|---|---|
| Mode de validation | Strict (`strict=True`) : pas de conversion implicite. Par exemple, `"12"` n'est pas accepté pour un entier en Python. En JSON, les dates et les montants sont fournis sous forme de chaînes. |
| Champs inconnus | Refusés (`extra="forbid"`) |
| Noms de champs | Anglais, `snake_case` |
| Identifiants | Chaîne de 1 à 64 caractères `[A-Za-z0-9_.-]` (pas d'espace ni de `|`) |
| Dates | ISO 8601 **avec fuseau obligatoire**, normalisées en UTC et sérialisées avec `Z` (ex. `2026-10-05T08:30:00Z`) |
| Montants | `Decimal`, strictement positifs, 2 décimales au plus, sérialisés en chaîne (`"50000.00"`) |
| Devise | `EUR` uniquement (Q10) |
| Pays | ISO 3166-1 alpha-2 en majuscules (`FR`) |
| Confiance | Nombre décimal entre 0,0 et 1,0 inclus |
| Enums | Sérialisés par leur valeur (`"awaiting_documents"`) |

## 2. Paramètres de cadrage

Ils sont définis comme constantes dans `models.py`. Ce sont des propositions **provisoires** (Q2, Q3, Q4 et Q6 de `open-questions.md`), non validées.

| Constante | Valeur | Borne |
|---|---|---|
| `HIGH_AMOUNT_THRESHOLD_EUR` | `50000.00` | Montant **strictement supérieur** : `sensitive`. **Égal** : n'escalade pas. |
| `CONFIDENCE_THRESHOLD` | `0.80` | Confiance **strictement inférieure** : champ illisible, pièce `unreadable`. Confiance égale : lisible. |
| `MAX_REMINDERS` | `2` | `reminder_count` ≥ 2 avec une pièce encore manquante : `sensitive` |
| `ALLOWED_COUNTRIES` | FR, BE, MA, TN | Autre pays : `sensitive` |
| `GENESIS_HASH` | 64 × `0` | `previous_hash` du premier événement |

## 3. `Client`

Identité minimale du client. Le type de client (entreprise et/ou particulier) est à trancher (Q11), donc les champs propres aux entreprises sont optionnels.

| Champ | Type | Défaut | Contrainte |
|---|---|---|---|
| `client_id` | Identifiant | requis | |
| `legal_name` | str | requis | Raison sociale ou nom complet, 1 à 200 caractères |
| `registration_number` | str \| null | `null` | ≤ 64 caractères |
| `legal_representative` | str \| null | `null` | Nom complet du représentant légal, 1 à 200 caractères. Caractère optionnel **provisoire** (Q11). |
| `country` | CountryCode | requis | `^[A-Z]{2}$` |

## 4. `ExtractedField`

| Champ | Type | Défaut | Contrainte |
|---|---|---|---|
| `name` | str | requis | `snake_case`, voir la liste ci-dessous |
| `value` | str \| null | `null` | Toujours une chaîne (montants `"12500.00"`, dates `"AAAA-MM-JJ"`). `null` si rien n'a été extrait. |
| `confidence` | float | requis | 0,0 ≤ x ≤ 1,0 |

Un champ est **lisible** si `confidence` ≥ 0,80 et que `value` n'est pas `null`.

### Champs obligatoires par type de pièce

Ce sont les champs que l'extraction doit produire. Le seuil de confiance s'applique-t-il à ces seuls champs ou à tous les champs extraits ? C'est à trancher (Q18).

| `PieceType` | Champs obligatoires (`MANDATORY_FIELDS`) |
|---|---|
| `identity_document` | `full_name`, `document_number`, `birth_date`, `expiry_date`, `nationality` |
| `balance_sheet` | `company_name`, `fiscal_year`, `revenue`, `net_income`, `total_equity`, `total_debt` |
| `quote` | `supplier_name`, `client_name`, `quote_number`, `quote_date`, `total_amount_excl_tax`, `total_amount_incl_tax` |
| `proof_of_address` | `holder_name`, `address`, `issue_date` |

## 5. `Piece`

| Champ | Type | Défaut | Contrainte |
|---|---|---|---|
| `piece_id` | Identifiant | requis | Unique dans le dossier |
| `piece_type` | `PieceType` | requis | |
| `file_name` | str \| null | `null` | `null` si la pièce est manquante |
| `mime_type` | str \| null | `null` | |
| `received_at` | datetime UTC \| null | `null` | `null` si la pièce est manquante |
| `ocr_status` | `OcrStatus` | `pending` | Voir le glossaire |
| `ocr_text` | str \| null | `null` | Texte brut produit par l'OCR |
| `extracted_fields` | liste de `ExtractedField` | `[]` | Noms uniques |
| `is_missing` | bool | `false` | `true` pour l'emplacement d'une pièce obligatoire constatée manquante |

**Invariant** : si `is_missing` vaut `true`, alors `file_name`, `received_at` et `ocr_text` sont `null`, `ocr_status` vaut `pending` et `extracted_fields` est vide.

**Règle de statut OCR** : une pièce dont au moins un champ extrait a une confiance strictement inférieure à 0,80, ou une valeur `null`, est `unreadable` (champs concernés : Q18).

## 6. `Decision`

| Champ | Type | Défaut | Contrainte |
|---|---|---|---|
| `decision_id` | Identifiant | requis | |
| `decision_type` | `DecisionType` | requis | |
| `author_type` | `AuthorType` | requis | |
| `author_id` | str | requis | Nom de l'agent (ex. `routing-agent`) ou identifiant du validateur |
| `justification` | str | requis | 1 à 4 000 caractères, en français |
| `routing` | `RoutingDecision` \| null | `null` | Renseigné pour les décisions de l'agent |
| `triggered_rules` | liste de str | `[]` | Valeurs dans R1 à R7 et R9 (`routing-rules.md`). R8 est hors MVP et refusée. |
| `decided_at` | datetime UTC | requis | |

**Invariant de droits** :

| `author_type` | `decision_type` autorisés |
|---|---|
| `agent` | `auto_approve`, `escalate` (Q7, provisoire), `request_documents` |
| `human` | `human_approve`, `human_reject`, `request_documents` |

`request_documents` est accepté pour les deux auteurs tant que Q15 n'est pas tranchée.

## 7. `Dossier`

| Champ | Type | Défaut | Contrainte |
|---|---|---|---|
| `dossier_id` | Identifiant | requis | |
| `client_id` | Identifiant | requis | Référence vers `Client.client_id` |
| `status` | `DossierStatus` | `submitted` | |
| `created_at` | datetime UTC | requis | Date de soumission |
| `updated_at` | datetime UTC | requis | ≥ `created_at` |
| `requested_amount` | Decimal | requis | > 0, 2 décimales au plus |
| `currency` | `Currency` | `EUR` | |
| `pieces` | liste de `Piece` | `[]` | `piece_id` uniques |
| `reminder_count` | int | `0` | ≥ 0 |
| `final_decision` | `Decision` \| null | `null` | Voir les invariants |

**Invariants** :
- `status = approved` exige `final_decision.decision_type` dans {`auto_approve`, `human_approve`}.
- `status = rejected` exige `final_decision.decision_type = human_reject`.

## 8. `AuditEvent`

Il est **immuable** (`frozen=True`). Le calcul du hash est décrit dans [audit-chain.md](audit-chain.md).

| Champ | Type | Défaut | Contrainte |
|---|---|---|---|
| `event_id` | Identifiant | requis | Unique |
| `dossier_id` | Identifiant | requis | |
| `sequence` | int | requis | ≥ 0. Rang dans la chaîne, consécutif à partir de 0. La portée de la chaîne (par dossier ou globale) est à trancher (Q14). |
| `event_type` | `AuditEventType` | requis | |
| `payload` | objet JSON | `{}` | Valeurs autorisées : chaîne, entier, booléen, `null`, liste, objet. **Pas de flottant** (les montants et scores sont mis en chaîne). |
| `occurred_at` | datetime UTC | requis | |
| `previous_hash` | hex SHA-256 | requis | `GENESIS_HASH` si et seulement si `sequence = 0` |
| `current_hash` | hex SHA-256 | requis | 64 caractères `[0-9a-f]` |

Le payload ne contient **aucune donnée personnelle en clair** : uniquement des identifiants, des statuts, des montants et des empreintes (Q9, provisoire).

## 9. Format des fixtures

Voir [fixtures/dossiers/README.md](../fixtures/dossiers/README.md). Un fichier de fixture contient un `Client`, un `Dossier` tel que soumis, et un bloc `expected` dont `routing` vaut `"simple"`, `"sensitive"` ou `null` (dossier en `awaiting_documents`).
