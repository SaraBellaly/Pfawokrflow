# Questions ouvertes

Décisions métier à trancher par l'équipe. **Aucune de ces questions n'est validée.**

**Statuts** :
- **Provisoire** (Q1 à Q10) : la proposition par défaut est appliquée dans les documents, le code et les fixtures pour pouvoir avancer. Elle **n'est pas validée** et peut être remplacée par l'équipe.
- **À trancher** (Q11 à Q18) : la proposition par défaut n'est **pas appliquée**. Aucun code ni aucune fixture n'en dépend. La colonne « État actuel » décrit comment le dépôt reste neutre.

Si une réponse change, il faut mettre à jour : `glossary.md` (si le vocabulaire change), `routing-rules.md`, `packages/core/models.py` (constantes), puis `tools/gen_fixtures.py` et les fixtures régénérées.

## Q1 à Q10 : provisoires (appliquées, non validées)

| # | Question | Proposition par défaut | Impact |
|---|---|---|---|
| Q1 | Faut-il un 4e type de pièce, et lequel ? | `proof_of_address`, optionnel et non bloquant. Obligatoires : identité, bilan, devis. | `PieceType`, R4 |
| Q2 | Quel seuil pour un « montant élevé » ? | > 50 000,00 € (strictement supérieur). L'égalité n'escalade pas. | R3, `HIGH_AMOUNT_THRESHOLD_EUR` |
| Q3 | Que faire d'un dossier avec une pièce manquante ? | `awaiting_documents`, sans routage (`null`), avec relance simulée. Escalade (`sensitive`) après 2 relances sans réponse. | R4, R5, `MAX_REMINDERS` |
| Q4 | Quel seuil de confiance pour l'OCR et l'extraction ? | Confiance < 0,80 (strictement) : pièce `unreadable`, escalade. 0,80 est lisible. | R6, `CONFIDENCE_THRESHOLD` |
| Q5 | Quelle tolérance pour une incohérence entre bilan et devis ? | Escalade si le devis TTC dépasse 30 % du CA, ou si les raisons sociales (client, bilan, devis) diffèrent. Les deux autres cas envisagés (montant demandé > devis, nom de la pièce d'identité ≠ représentant légal) sont **hors MVP** (`scope.md` §3). | R7 |
| Q6 | Quels pays sont acceptés ? | FR, BE, MA, TN. Les autres sont escaladés. | R2, `ALLOWED_COUNTRIES` |
| Q7 | L'agent peut-il rejeter automatiquement ? | Non. L'agent approuve seulement par `auto_approve`, escalade par `escalate`, et ne rejette jamais. `auto_reject` n'existe pas dans l'enum. Le cas de `request_documents` relève de Q15. | `DecisionType`, `Decision` |
| Q8 | Que hache-t-on dans l'audit : le payload complet ou son empreinte ? | JSON canonique complet (clés triées, UTF-8, sans espace). | `audit-chain.md` |
| Q9 | Comment concilier un journal immuable et le droit à l'effacement (RGPD) ? | Aucune donnée personnelle en clair dans le payload : uniquement des identifiants, des statuts, des montants et des empreintes. | `AuditEvent.payload` |
| Q10 | Quelles devises ? | EUR uniquement. | `Currency` |

## Q11 à Q18 : à trancher (non appliquées)

| # | Question | Proposition par défaut (non appliquée) | État actuel du dépôt |
|---|---|---|---|
| Q11 | Faut-il accepter les clients particuliers ? | Non au MVP : entreprises uniquement. | Aucun test ne l'encode. `Client` est conforme à `data-contracts.md` §3. **Champ provisoire** : `Client.legal_representative` (optionnel, `null` par défaut) est provisoire en attendant Q11. Les fixtures sont des entreprises parce que le bilan est une pièce obligatoire (Q1). |
| Q12 | Faut-il escalader immédiatement un dossier incomplet qui déclenche déjà R1, R2 ou R3, ou d'abord attendre les pièces ? | Escalade immédiate. | Non tranché : ni le code ni les tests ne fixent d'ordre d'évaluation (les tests ne vérifient que des implications valables dans les deux options). Fixture-question `fixtures/open-questions/Q12-FICT-001.json` (ancienne DOS-FICT-024) : elle décrit les deux options, **sans routage attendu ni assertion de routage**. |
| Q13 | Une pièce d'identité expirée doit-elle être escaladée ? | Oui, `sensitive`. | Règle R8 **hors MVP** (`scope.md` §3), refusée par le code. DOS-FICT-025 retirée. Aucune fixture n'a de pièce expirée. |
| Q14 | Faut-il une chaîne d'audit par dossier ou une chaîne globale ? | Par dossier. Ancrage externe du dernier hash hors MVP. | Neutre : `audit-chain.md` décrit « une chaîne » valable dans les deux cas. Les points qui dépendent de la portée sont signalés. |
| Q15 | Qui peut produire `request_documents` (agent, humain, les deux) ? La relance automatique doit-elle être une `Decision` ? | Validateur humain uniquement. La relance automatique est tracée par des événements, pas par une `Decision`. | Non tranché : le modèle **accepte `request_documents` pour les deux auteurs** (agent et humain). Aucun test ne fixe l'auteur. |
| Q16 | Comment comparer les noms (R1, R7 a) ? | Normalisation : sans accents, majuscules, ponctuation remplacée par des espaces, espaces réduits, formes juridiques conservées. | Non tranché : aucune règle de comparaison n'est codée ni testée (le test de R1 ne vérifie que la correspondance par `client_id`). DOS-FICT-018 teste un nom identique, caractère pour caractère, et n'est liée à aucune règle de comparaison. |
| Q17 | Quel délai entre deux relances ? | Sans objet au MVP (relances simulées). À définir avant tout envoi réel. | Non utilisé. |
| Q18 | Faut-il appliquer le seuil de confiance à tous les champs extraits ou aux seuls champs obligatoires ? | Champs obligatoires uniquement. | Neutre : les fixtures ne contiennent que les champs de `MANDATORY_FIELDS`, donc les deux options donnent le même résultat. |
