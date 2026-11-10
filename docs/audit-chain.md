# Spécification de la chaîne d'audit

> Modèle : `AuditEvent` dans [data-contracts.md](data-contracts.md). Vocabulaire : voir [glossary.md](glossary.md).

## 1. Principe

Les événements forment une **chaîne** : chaque événement contient le hash de l'événement précédent. Modifier, supprimer, insérer ou réordonner un événement casse la chaîne de façon détectable.

**Portée de la chaîne : à trancher (Q14).** Une chaîne peut couvrir un seul dossier ou tous les dossiers. Cette spécification fonctionne dans les deux cas : on y parle de « la chaîne » et les points qui dépendent de la portée sont signalés. Le contenu haché (§3) est le même dans les deux cas.

## 2. Algorithme

- Fonction de hachage : **SHA-256** (FIPS 180-4).
- Sortie : 64 caractères hexadécimaux **minuscules**.
- `current_hash = hex(SHA-256(contenu_canonique))`

## 3. Contenu haché (format canonique)

Le contenu haché (Q8, provisoire) est un **objet JSON canonique** formé des 7 champs suivants. `current_hash` en est exclu.

| Champ | Type JSON | Format |
|---|---|---|
| `dossier_id` | chaîne | tel quel |
| `event_id` | chaîne | tel quel |
| `event_type` | chaîne | valeur de l'enum (ex. `"routing_decided"`) |
| `occurred_at` | chaîne | `AAAA-MM-JJTHH:MM:SS.ffffffZ` : UTC, **toujours 6 chiffres** de microsecondes, suffixe `Z` |
| `payload` | objet | voir les règles ci-dessous |
| `previous_hash` | chaîne | 64 caractères hexadécimaux minuscules |
| `sequence` | nombre entier | sans zéro de tête |

Règles de sérialisation :

1. **Ordre des champs** : clés triées par ordre lexicographique des points de code Unicode, **à tous les niveaux**, y compris dans `payload`. Pour les champs ci-dessus, l'ordre obtenu est `dossier_id`, `event_id`, `event_type`, `occurred_at`, `payload`, `previous_hash`, `sequence`.
2. **Séparateurs** : `,` entre éléments et `:` entre clé et valeur, **sans aucun espace** ni retour à la ligne.
3. **Encodage** : UTF-8, sans BOM. Les caractères non ASCII sont écrits tels quels (pas d'échappement `\uXXXX`). Seuls les échappements JSON obligatoires sont appliqués (`"`, `\` et les caractères de contrôle).
4. **Types autorisés dans `payload`** : chaîne, entier, booléen, `null`, liste (ordre conservé), objet. **Les flottants sont interdits** car leur représentation n'est pas déterministe d'un langage à l'autre : montants et scores sont mis en chaîne (`"18500.00"`, `"0.92"`). Le modèle Pydantic refuse les flottants.
5. **Chaînes** : elles sont hachées telles que stockées, sans normalisation au moment du hachage. Les producteurs doivent stocker les chaînes en Unicode NFC.

Équivalent Python de référence (implémentation prévue en semaine 2) :

```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
```

## 4. Règle du premier événement

- Le premier événement d'une chaîne a `sequence = 0` et `previous_hash = "000…000"` (64 zéros, constante `GENESIS_HASH`).
- Aucun autre événement ne peut avoir `previous_hash = GENESIS_HASH` (contrôlé par le modèle).
- *Selon Q14* : si la chaîne est par dossier, le premier événement est le `dossier_submitted` de ce dossier. Si elle est globale, c'est le tout premier événement du système, quel que soit son type.

## 5. Ajout d'un événement

1. Lire le dernier événement de la chaîne (rang `n`, hash `h_n`) **sous verrou** : une seule écriture à la fois par chaîne, c'est-à-dire par dossier ou pour tout le système selon Q14.
2. Construire le nouvel événement avec `sequence = n + 1` et `previous_hash = h_n`.
3. Calculer `current_hash` sur le contenu canonique.
4. Insérer l'événement (insertion seule).

## 6. Procédure de vérification

Pour une chaîne :

1. Charger tous ses événements et les trier par `sequence` croissant.
2. Vérifier que les rangs sont exactement 0, 1, 2, … sans trou ni doublon.
3. Vérifier que l'événement 0 a `previous_hash = GENESIS_HASH` (et, pour une chaîne par dossier, qu'il est de type `dossier_submitted`).
4. Pour chaque événement `i` :
   - recalculer `SHA-256(contenu_canonique(i))` et le comparer à `current_hash(i)` ;
   - pour `i > 0`, vérifier que `previous_hash(i) = current_hash(i-1)`.
5. Toute différence rend la chaîne **invalide**. Le rapport indique le premier rang fautif et la nature de l'erreur (hash recalculé différent, lien rompu, rang manquant).

La vérification ne détecte pas la suppression des **derniers** événements (troncature). Une parade possible, hors MVP, est d'ancrer périodiquement le dernier hash à l'extérieur (Q14).

## 7. Exemple de référence (valeurs réelles)

Ces deux hash ont été recalculés le 2026-11-10 par une commande indépendante du script qui les a produits, et ils sont identiques. L'exemple est valable quelle que soit la réponse à Q14.

Événement 0 : contenu canonique (une seule ligne) :

```
{"dossier_id":"DOS-FICT-001","event_id":"EVT-FICT-0001","event_type":"dossier_submitted","occurred_at":"2026-10-05T08:30:00.000000Z","payload":{"client_id":"CLI-FICT-001","currency":"EUR","requested_amount":"18500.00"},"previous_hash":"0000000000000000000000000000000000000000000000000000000000000000","sequence":0}
```

`current_hash` = `bde888c35a69680c02f2a47e032ceb92eeeddef53b81edee8125ab2b0c9a1912`

Événement 1 :

```
{"dossier_id":"DOS-FICT-001","event_id":"EVT-FICT-0002","event_type":"routing_decided","occurred_at":"2026-10-05T08:31:12.250000Z","payload":{"routing":"simple","triggered_rules":["R9"]},"previous_hash":"bde888c35a69680c02f2a47e032ceb92eeeddef53b81edee8125ab2b0c9a1912","sequence":1}
```

`current_hash` = `102e05e1911828ae763f5965b914d0550cc2ab51db55f0674074591cba7ef364`

L'implémentation de la semaine 2 devra reproduire exactement ces deux valeurs (test de non-régression).

## 8. Interdictions

| Interdit | Mise en œuvre prévue (S2) |
|---|---|
| **Modifier** un événement (n'importe quel champ) | Table en insertion seule : `REVOKE UPDATE` et trigger PostgreSQL qui lève une erreur sur `UPDATE` |
| **Supprimer** un événement | `REVOKE DELETE` et trigger sur `DELETE` / `TRUNCATE` |
| Insérer un événement avec un rang déjà utilisé | Contrainte d'unicité sur le rang dans la chaîne : `UNIQUE (dossier_id, sequence)` pour une chaîne par dossier, `UNIQUE (sequence)` pour une chaîne globale (Q14) |
| Mettre des flottants ou des données personnelles en clair dans `payload` | Validation du modèle et revue de code |
| « Corriger » une erreur en réécrivant l'historique | On ajoute un **nouvel** événement correctif qui référence l'`event_id` erroné dans son payload |

Côté application, `AuditEvent` est `frozen=True` : toute affectation lève une erreur.
