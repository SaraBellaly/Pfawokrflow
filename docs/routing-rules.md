# Règles de routage

> Vocabulaire : voir [glossary.md](glossary.md). Les seuils sont des propositions **provisoires**, non validées (voir [open-questions.md](open-questions.md)). Les règles retirées du MVP sont listées dans [scope.md](scope.md) §3.

## 1. Définitions

- **Dossier simple** (`simple`) : aucune règle d'escalade n'est déclenchée et toutes les pièces obligatoires sont présentes et lisibles. L'agent prend une décision `auto_approve` et le dossier passe à `approved`.
- **Dossier sensible** (`sensitive`) : au moins une règle d'escalade est déclenchée. L'agent prend une décision `escalate` et le dossier passe à `pending_human_review`. Seul un humain peut ensuite approuver ou rejeter.
- **Dossier en attente** (pas de routage, `null`) : une pièce obligatoire manque et moins de 2 relances ont été envoyées. Le dossier est en `awaiting_documents` et aucune décision n'est enregistrée.

L'agent ne rejette jamais un dossier (Q7, provisoire). En cas de doute, la règle par défaut est l'escalade.

## 2. Bornes exactes

| Grandeur | Règle | Exemple |
|---|---|---|
| Montant demandé | **Strictement supérieur à 50 000,00 €** : `sensitive` | 50 000,01 € : `sensitive` (DOS-FICT-014) |
| | **Égal à 50 000,00 €** : la règle R3 ne se déclenche pas (le dossier peut être `simple`) | 50 000,00 € : `simple` si rien d'autre (DOS-FICT-022) |
| Confiance d'un champ extrait | **Strictement inférieure à 0,80** : champ illisible, pièce `unreadable` | 0,79 : illisible (DOS-FICT-012) |
| | **Égale ou supérieure à 0,80** : champ lisible | 0,80 : lisible (DOS-FICT-026) |
| Relances | **2 relances** envoyées sans réception de la pièce : `sensitive` | `reminder_count` = 1 : on attend encore |
| Devis / chiffre d'affaires | Devis TTC **strictement supérieur à 30 %** du chiffre d'affaires : incohérence | CA 100 000, devis 30 000,01 : incohérence |

Les champs soumis au seuil de confiance (champs obligatoires seulement, ou tous les champs) restent à trancher (Q18). Les fixtures ne contiennent que les champs obligatoires, donc les deux options donnent le même résultat.

## 3. Ordre d'évaluation

Si plusieurs règles se déclenchent, **toutes** sont listées dans `triggered_rules`.

1. **Contrôles du dossier** (R1, R2 et R3) : ils ne demandent aucune pièce.
2. **Contrôle des pièces** (R4 et R5).
3. **Contrôles sur les pièces** (R6 et R7) : seulement si toutes les pièces obligatoires sont présentes.
4. **Règle par défaut** (R9).

**Point ouvert (Q12, à trancher)** : on ne sait pas encore traiter un dossier **incomplet** qui déclenche aussi R1, R2 ou R3. Il peut être escaladé immédiatement ou mis d'abord en attente des pièces. Aucun ordre d'évaluation n'est codé ni testé. Le cas est illustré par la fixture-question `fixtures/open-questions/Q12-FICT-001.json`, qui décrit les deux options sans routage attendu.

## 4. Règles

### R1 : client sur la liste sensible
- **Condition** : le `client_id` du client figure dans la liste sensible, **ou** son `legal_name` correspond à un nom de la liste.
- **Décision** : `sensitive`, avec une décision `escalate`.
- **Justification** : au MVP, ce contrôle remplace le KYC/AML. Un client signalé doit toujours être examiné par un humain.
- **Note** : la méthode de comparaison des noms reste à trancher (Q16) et n'est pas codée. DOS-FICT-018 teste seulement un nom identique, caractère pour caractère, à une entrée de la liste.

### R2 : pays hors périmètre
- **Condition** : le `country` du client n'est pas dans {FR, BE, MA, TN}.
- **Décision** : `sensitive`, avec une décision `escalate`.
- **Justification** : la politique de crédit et les contrôles de conformité ne sont définis que pour ces pays (Q6, provisoire).

### R3 : montant élevé
- **Condition** : `requested_amount` **strictement supérieur à** 50 000,00 €.
- **Décision** : `sensitive`, avec une décision `escalate`.
- **Justification** : l'exposition financière justifie un double regard humain (Q2, provisoire). Un montant égal au seuil ne déclenche pas la règle.

### R4 : pièce obligatoire manquante, relance possible
- **Condition** : au moins une pièce obligatoire (`identity_document`, `balance_sheet` ou `quote`) est absente **et** `reminder_count` est inférieur à 2. Le cas où R1, R2 ou R3 se déclenche en même temps relève de Q12.
- **Décision** : **pas de routage** (`null`). Le statut passe à `awaiting_documents`, une relance simulée est envoyée et `reminder_count` est incrémenté. Aucune `Decision` n'est créée.
- **Justification** : un dossier incomplet ne peut pas être évalué. On laisse au client la possibilité de compléter son dossier avant de mobiliser un humain (Q3, provisoire).

### R5 : pièce obligatoire manquante après 2 relances
- **Condition** : au moins une pièce obligatoire est absente **et** `reminder_count` est supérieur ou égal à 2.
- **Décision** : `sensitive`, avec une décision `escalate`.
- **Justification** : le client ne répond pas. Un humain décide de la suite, l'agent ne rejette pas (Q7, provisoire).

### R6 : pièce illisible ou OCR en échec
- **Condition** : une pièce obligatoire a l'`ocr_status` `failed` ou `unreadable`, autrement dit au moins un champ extrait a une confiance **strictement inférieure à 0,80** ou une valeur absente.
- **Décision** : `sensitive`, avec une décision `escalate`.
- **Justification** : on ne prend pas de décision automatique sur une donnée incertaine (Q4, provisoire).

### R7 : incohérence entre le bilan et le devis
- **Condition** (une seule suffit) :
  - (a) `Client.legal_name`, `balance_sheet.company_name` et `quote.client_name` ne désignent pas la même entreprise ;
  - (b) le `quote.total_amount_incl_tax` est **strictement supérieur à 30 %** du `balance_sheet.revenue`.
- **Décision** : `sensitive`, avec une décision `escalate`.
- **Justification** : une incohérence peut signaler une erreur, une fraude ou un projet disproportionné par rapport à l'activité. Un humain doit juger (Q5, provisoire).
- **Note** : pour (a), la méthode de comparaison des noms reste à trancher (Q16). DOS-FICT-019 utilise des noms nettement différents.

### R8 : *(identifiant réservé, règle hors MVP)*
L'ancienne règle « pièce d'identité expirée » est retirée du MVP (voir `scope.md` §3 et Q13). Le code refuse `R8` dans `triggered_rules`.

### R9 : règle par défaut, dossier simple
- **Condition** : aucune des règles R1 à R7 n'est déclenchée.
- **Décision** : `simple`, avec une décision `auto_approve` et le statut `approved`.
- **Justification** : le dossier est complet, lisible, cohérent, sous le seuil, et le client n'est pas signalé.

## 5. Tableau récapitulatif

| Règle | Résultat | Statut | Décision |
|---|---|---|---|
| R1, R2, R3, R5, R6, R7 | `sensitive` | `pending_human_review` | `escalate` (agent) |
| R4 | `null` | `awaiting_documents` | aucune |
| R9 | `simple` | `approved` | `auto_approve` (agent) |
