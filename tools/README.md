# tools/

## `gen_fixtures.py` : générateur des fixtures fictives

Il produit, dans `fixtures/` :
- `dossiers/DOS-FICT-NNN.json` : un dossier de test fictif par fichier (23 actuellement) ;
- `dossiers/_sensitive_list.json` : la liste sensible fictive (règle R1) ;
- `open-questions/QNN-FICT-NNN.json` : les fixtures-questions, sans routage attendu (1 actuellement, pour Q12).

Il ne touche pas aux fichiers `README.md`. Les fichiers sont écrits en UTF-8 avec des fins de ligne LF. La sortie est déterministe : deux exécutions produisent exactement les mêmes octets.

### Utilisation (depuis la racine du dépôt)

```bash
python tools/gen_fixtures.py --check   # vérifie que les fichiers sont à jour, sans rien écrire
python tools/gen_fixtures.py           # régénère les fichiers
python tools/gen_fixtures.py --out DIR # écrit dans un autre répertoire racine que fixtures/ (comparaison, essais)
```

`--check` renvoie le code 1 et liste les fichiers en écart, ou en trop, si les fixtures du dépôt ne correspondent plus au script.

### Règles

- Ce script est la **source** des fixtures. Pour modifier une fixture, on modifie le script, on le relance, puis on lance `pytest`.
- Si une fixture est retirée du script, le fichier correspondant n'est **pas** supprimé automatiquement. Le script affiche un avertissement et c'est à vous de le supprimer.
- Données fictives uniquement (voir `fixtures/dossiers/README.md`).
- Seule la bibliothèque standard Python est utilisée.
