# Périmètre du MVP (6 semaines)

> Vocabulaire : voir [glossary.md](glossary.md). Questions non tranchées : voir [open-questions.md](open-questions.md).

## 1. Objectif

Démontrer, sur des dossiers **fictifs**, un parcours de bout en bout traçable :

```
soumission → OCR → extraction → contrôle des pièces manquantes → routage → décision (auto ou humaine) → journal d'audit
```

Chaque étape produit au moins un événement d'audit chaîné. La qualité est mesurée par rapport aux fixtures de `fixtures/dossiers/`.

## 2. Dans le périmètre

| Étape | Contenu MVP | Statuts concernés |
|---|---|---|
| Soumission | Upload via l'API (FastAPI) d'un dossier : client, montant, pièces | `submitted` |
| OCR | OCR des pièces avec un modèle local (Ollama). Statut `done`, `failed` ou `unreadable` par pièce | `ocr_in_progress` |
| Extraction | Extraction des champs obligatoires par type de pièce, avec un score de confiance | `extraction_in_progress` |
| Contrôle des pièces | Détection des pièces obligatoires manquantes et relance **simulée** (au plus 2) | `awaiting_documents` |
| Routage | Application des règles R1 à R7 et R9 de [routing-rules.md](routing-rules.md) | `under_review` |
| Décision automatique | `auto_approve` pour un dossier `simple` | `approved` |
| Décision humaine | Console minimale : liste des dossiers `sensitive`, détail, boutons approuver / rejeter (« demander des pièces » dépend de Q15) | `pending_human_review`, `approved`, `rejected` |
| Journal d'audit | Événements immuables chaînés par SHA-256, avec une commande de vérification | tous |
| Évaluation | Exécution du pipeline sur les **23 fixtures** fictives et comparaison avec les valeurs attendues | n/a |

### Pièces gérées

| Type | Obligatoire |
|---|---|
| `identity_document` | Oui |
| `balance_sheet` | Oui |
| `quote` | Oui |
| `proof_of_address` | Non (optionnel, voir Q1) |

### Clients

Le type de client (entreprises seulement ou aussi particuliers) est **à trancher** (Q11). Les fixtures actuelles sont des entreprises, car le bilan est une pièce obligatoire. Pays autorisés : FR, BE, MA, TN (Q6, provisoire). Devise : EUR (Q10, provisoire).

## 3. Hors MVP

| Élément | Raison |
|---|---|
| **Scoring avancé** (modèle statistique, ratios multiples pondérés, historique bancaire) | Il faut des données d'entraînement réalistes, que nous n'avons pas (données fictives uniquement). Le MVP se limite à des contrôles de cohérence simples (règle R7). |
| **Génération réelle de contrat** | Elle demande des modèles juridiques validés et une signature électronique. Au MVP, l'approbation produit seulement une décision `auto_approve` / `human_approve` tracée. |
| **Décaissement réel** | Il exige une intégration bancaire et des garanties de sécurité hors de portée d'un MVP de 6 semaines. Il présente aussi un risque en cas d'erreur. |
| **Envoi réel d'emails** | Il présente un risque d'envoi à de vraies adresses et demande une infrastructure SMTP et la gestion des désinscriptions. Au MVP, les relances sont simulées et tracées (`client_reminder_sent`). |
| **Ingestion email complète** (parsing de boîte mail, pièces jointes, fils) | Elle est complexe (formats, MIME, spam, rattachement au bon dossier) et apporte peu à la démonstration du parcours. Au MVP, la soumission se fait uniquement par upload. |
| **RAG avancé** sur la politique de crédit (KYC/AML complet) | Il demande un corpus réglementaire validé et une évaluation dédiée. Au MVP, la conformité se limite à la liste sensible fictive (R1) et à la liste des pays (R2). pgvector est mis en place mais non exploité en profondeur. |
| **Incohérence « montant demandé supérieur au devis TTC »** (ancien R7 c) | Non validé par l'équipe. |
| **Incohérence « nom sur la pièce d'identité différent du représentant légal »** (ancien R7 d) | Non validé par l'équipe. |
| **Escalade pour pièce d'identité expirée** (ancienne règle R8, voir Q13) | Non validé par l'équipe. |
| **Multi-devises** | Il faudrait gérer les taux de change et leur traçabilité. Voir Q10. |
| **Authentification forte / gestion fine des rôles** | Une authentification basique de la console suffit pour une démonstration sur données fictives. |
| **Rejet automatique par l'agent** | C'est un choix de prudence : tout rejet est humain (Q7). |

## 4. Planning indicatif

| Semaine | Livrable |
|---|---|
| S1 | Cadrage : documents, contrats de données, fixtures (ce dépôt) |
| S2 | Schéma PostgreSQL, API de soumission, journal d'audit et vérification de la chaîne |
| S3 | OCR et extraction (Ollama), évaluation sur les fixtures |
| S4 | Contrôle des pièces, relances simulées, routage (LangGraph) |
| S5 | Console de validation humaine (React), décisions humaines |
| S6 | Évaluation de bout en bout, durcissement, démonstration |

## 5. Critères de réussite du MVP

- 100 % des 23 fixtures traversent le pipeline sans erreur technique.
- La décision de routage correspond à `expected.routing` pour toutes les fixtures (les règles sont déterministes une fois les champs extraits).
- La chaîne d'audit de chaque dossier traité se vérifie sans erreur.
- Aucune donnée réelle n'est présente dans le dépôt ni dans la base.
