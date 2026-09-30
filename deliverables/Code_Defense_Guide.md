# Guide de défense du code — Personal Finance Tracker

> Document de préparation personnel (en français) pour l'entretien avec l'évaluateur du cours
> DATA 333. Le code, le rapport et les slides sont en anglais : les noms de fichiers, de
> fonctions et de classes sont donc cités tels quels.

---

## 1. Le projet en 30 secondes

Une application Python qui enregistre des revenus et des dépenses, les classe par catégorie
et les transforme en résumés, tendances, alertes de budget et suivi d'objectifs d'épargne.
Un même « cœur » testé alimente trois interfaces :

| Commande | Ce que ça lance |
|---|---|
| `python main.py cli` | le menu console interactif |
| `python main.py gui` | la fenêtre Tkinter |
| `python main.py demo` | une démonstration automatique sur les données d'exemple |
| `streamlit run finance_tracker/dashboard.py` | le tableau de bord web interactif |

Chiffres clés : 311 transactions fictives sur 6 mois, plus de 150 tests, environ 98 % de
couverture, `ruff` sans erreur.

---

## 2. Chaque module expliqué simplement

L'architecture est en couches : **interfaces → logique → domaine et stockage → fichiers**.
Les interfaces ne contiennent aucune règle métier : elles appellent la logique et se
contentent d'afficher les résultats (le dashboard applique aussi ses filtres avec pandas).

| Fichier | En une phrase | À retenir pour l'oral |
|---|---|---|
| `models.py` | Les « fiches » de base : `Transaction`, `SavingsGoal`, `Budget`. | Ce sont des *dataclasses*. `__post_init__` vérifie chaque valeur dès la création : un montant négatif ou une date invalide lève une exception, donc un objet mal formé ne peut jamais exister. |
| `exceptions.py` | Nos propres types d'erreurs. | Hiérarchie avec une classe de base `FinanceTrackerError` : l'interface peut attraper *toutes* les erreurs de l'application d'un seul coup. |
| `storage.py` | Lire et écrire les fichiers JSON et CSV. | Écriture **atomique** (fichier temporaire puis `replace`). Un JSON corrompu, ou valide mais mal structuré (`{"transactions": null}`), est renommé en `.corrupted-<date>` et l'application redémarre à vide. Une ligne invalide ou un identifiant en double est ignoré et signalé, sans tout faire échouer. |
| `tracker.py` | La classe `FinanceTracker`, le « classeur » qui contient tout. | Une **liste** de transactions, deux **dictionnaires** (budgets et objectifs indexés par nom), un **set** de catégories. Méthodes : ajouter, modifier, supprimer, rechercher, filtrer, totaux, sauvegarder et charger. |
| `analytics.py` | Les calculs avec pandas. | `pivot_table` pour le résumé mensuel, `groupby().agg()` pour les catégories, `rolling(3).mean()` pour la moyenne glissante, `pct_change()` pour la variation d'un mois sur l'autre. Chaque fonction gère le cas « aucune donnée ». |
| `alerts.py` | Les alertes de budget et les jalons d'épargne. | Seuils en constantes (`WARNING_THRESHOLD = 0.80`, `EXCEEDED_THRESHOLD = 1.00`). Une chaîne `if / elif / else` classe l'utilisation du budget. |
| `visualize.py` | Les graphiques matplotlib (PNG). | Utilise `Figure` directement, sans `pyplot` : ça marche sans écran (mode démo, tests) et les mêmes figures s'affichent dans Tkinter. |
| `config.py` | Tous les chemins du projet. | Calculés avec `pathlib` à partir de l'emplacement du fichier : aucun chemin absolu codé en dur. |
| `cli.py` | Le menu console. | Boucle `while`. Un **dictionnaire** associe chaque touche à une méthode. Des boucles de validation redemandent la saisie tant qu'elle est invalide. Les fonctions `input` et `print` sont *injectables*, ce qui permet de tester des sessions complètes. |
| `gui_tkinter.py` | L'application de bureau. | Classe `FinanceApp` (hérite de `ttk.Frame`) avec 4 onglets, un `Treeview` triable et des graphiques intégrés. Gère les écrans HiDPI. |
| `dashboard.py` | Le tableau de bord Streamlit. | Filtres dans la barre latérale, KPI, graphiques Plotly interactifs, import et export de CSV. Il réutilise `analytics.py`. |
| `main.py` | Le point d'entrée. | `argparse` choisit le mode ; `run_demo()` exécute tout sans interaction. |
| `tools/` | Scripts annexes. | Générateur de données (graine 42), captures d'écran réelles, construction du rapport, des slides et du document CodeStepByStep. |

---

## 3. Chaque concept du cours avec une analogie de la vie courante

| Concept | Où dans le code | Analogie |
|---|---|---|
| **Entrées / sorties** | `cli.py` : `ask()`, `prompt_amount()`, tableaux alignés | Un guichet de banque : le client donne une information, le guichetier répond avec un reçu clair. |
| **Structures de décision** | `alerts.budget_level()`, `main.main()` | Un feu tricolore : vert sous 80 %, orange entre 80 et 100 %, rouge au-delà. |
| **Boucles** | menu `while` dans `ConsoleApp.run()`, validation dans `prompt_amount()` | Un distributeur qui redemande le code PIN tant qu'il est faux. |
| **Fonctions** | `parse_amount()`, les fonctions de `analytics` | Une recette de cuisine : on l'écrit une fois et on la réutilise à chaque repas. |
| **Gestion de fichiers** | `storage.py` (`json`, `csv`, `pathlib`, `with open`) | Un classeur de bureau : on range les feuilles et on les retrouve le lendemain. |
| **Exceptions** | `exceptions.py`, `load_json()` avec `try / except / else`, `_atomic_write()` avec `try / except / finally` | L'airbag d'une voiture : quand un problème survient, il amortit le choc au lieu de laisser tout s'écraser. |
| **Listes** | `FinanceTracker.transactions` | Un relevé bancaire : les opérations dans l'ordre, et deux cafés identiques peuvent s'y trouver. |
| **Dictionnaires** | `budgets`, `goals`, `ConsoleApp.menu` | Un répertoire téléphonique : on cherche par nom et on trouve tout de suite. |
| **Sets** | `categories`, `VALID_KINDS`, colonnes manquantes d'un CSV | Une liste d'invités sans doublons : ajouter deux fois « Alice » ne change rien. |
| **POO (classes)** | `Transaction`, `FinanceTracker`, `FinanceApp` | Le plan d'une maison (la classe) et les maisons construites (les objets), chacune avec ses pièces (attributs) et ses usages (méthodes). |
| **pandas** | `analytics.py` | Un tableur Excel automatisé : un seul `groupby` fait ce qu'on ferait à la main avec des filtres et des sous-totaux. |

Astuce pour l'oral : chaque concept est marqué dans le code par un commentaire
`# Concept: ...`. Un `grep -rn "# Concept:" finance_tracker` les liste tous.

---

## 4. Les 15 questions probables de l'évaluateur (avec réponses)

**1. Pourquoi avoir utilisé des dataclasses plutôt que des dictionnaires ?**
Une dataclass garantit la présence de tous les champs et permet de valider les données dans
`__post_init__`. Elle ajoute aussi des méthodes (`signed_amount`, `to_dict`). Avec un
dictionnaire, une faute de frappe dans une clé passerait inaperçue.

**2. Pourquoi une liste pour les transactions, mais un dictionnaire pour les budgets ?**
Les transactions ont un ordre et peuvent se ressembler : une liste convient. Un budget se
cherche par catégorie : un dictionnaire donne l'accès direct en O(1) et empêche d'avoir deux
budgets pour la même catégorie.

**3. À quoi sert le set de catégories ?**
À garantir l'unicité automatiquement. De plus, `normalize_category()` transforme « food »,
« Food » et « FOOD » en « Food », donc ces variantes ne créent pas trois catégories.

**4. Que se passe-t-il si le fichier JSON est corrompu ?**
`load_json()` attrape `json.JSONDecodeError`, renomme le fichier en
`data.json.corrupted-<horodatage>` (aucune donnée n'est perdue), ajoute un avertissement et
renvoie un état vide. L'application démarre normalement. Le test
`test_corrupted_json_is_backed_up` le prouve.

**5. Et si un seul enregistrement est invalide ?**
La boucle de chargement a un `try/except` *par* enregistrement : la ligne fautive est ignorée
et signalée (« Skipped CSV line 3: ... »), et les autres sont chargées.

**6. Pourquoi une écriture « atomique » ?**
Si le programme plante au milieu d'une sauvegarde, un fichier écrit directement serait à
moitié vide. On écrit donc dans un fichier temporaire, puis `Path.replace()` le substitue en
une seule opération. Le bloc `finally` supprime le fichier temporaire en cas d'erreur.

**7. Pourquoi JSON *et* CSV ?**
Le JSON conserve tout l'état, y compris les données imbriquées (budgets, objectifs). Le CSV
est un tableau plat, idéal pour Excel ou pandas, mais il ne contient que les transactions.

**8. Comment fonctionnent les alertes de budget ?**
Pour le mois choisi, on calcule `dépensé / limite`. À partir de 0,80 le niveau est WARNING, à
partir de 1,00 il est EXCEEDED. Les alertes sont triées de la plus grave à la moins grave.
Dans la CLI et la GUI, une alerte s'affiche dès qu'une dépense franchit un seuil.

**9. Explique le résumé mensuel avec pandas.**
`df.pivot_table(index="month", columns="kind", values="amount", aggfunc="sum")` donne une
ligne par mois et une colonne par type (revenu ou dépense). On en déduit `net` et le taux
d'épargne, avec une protection contre la division par zéro quand il n'y a pas de revenu.

**10. Qu'est-ce que la moyenne glissante et pourquoi l'utiliser ?**
`rolling(window=3).mean()` fait la moyenne des 3 derniers mois. Elle lisse un pic ponctuel
(comme juillet, +28 %) pour montrer la vraie tendance. `pct_change()` donne la variation
d'un mois à l'autre.

**11. Comment as-tu testé un programme interactif ?**
`ConsoleApp` reçoit ses fonctions `input_func` et `output_func` en paramètre. Les tests lui
passent une liste de réponses préparées et vérifient ce qui est affiché. Des sessions
complètes sont testées, y compris les saisies invalides. La GUI a un smoke test sur un vrai
écran, et le dashboard est testé avec l'`AppTest` de Streamlit.

**12. Quel a été ton bug le plus intéressant ?**
Les montants du type « $1,850 / $3,000 » s'affichaient sans leurs `$` et en italique :
matplotlib, comme le Markdown de Streamlit, interprète le texte entre deux `$` comme une
formule LaTeX. Les tests unitaires ne l'ont pas vu ; c'est la capture d'écran qui l'a révélé.
Corrigé en échappant `\$`, avec un test de non-régression.

**13. Pourquoi l'ordre des `except` compte-t-il ?**
Notre `StorageError` hérite de `OSError`. Dans `load_csv`, un `except OSError` générique
attrapait donc notre propre erreur et masquait le vrai message. Python teste les `except`
dans l'ordre, et un parent attrape ses enfants : on a ajouté `except StorageError: raise`
avant.

**14. Pourquoi l'interface ne contient-elle aucune logique métier ?**
Pour réutiliser et tester. Les trois interfaces appellent les mêmes fonctions
(`FinanceTracker`, `analytics`, `alerts`, `visualize`) : les chiffres sont identiques partout,
et la logique est testée sans écran. Ajouter le dashboard n'a demandé aucune modification du
cœur.

**15. Que pourrais-tu améliorer ?**
Des transactions récurrentes automatiques (loyer, abonnements), l'import de relevés bancaires
(OFX), une base SQLite pour de gros historiques, et des prévisions de dépenses (régression
linéaire sur les totaux mensuels).

---

## 5. Démonstration express si l'évaluateur demande « montre-moi »

```bash
python main.py demo                           # tout en une commande
pytest -q                                     # plus de 150 tests verts
grep -rn "# Concept:" finance_tracker | head  # les concepts étiquetés
python main.py cli                            # taper "abc" comme montant → message + nouvelle demande
```

Fichiers à ouvrir si on te demande du code précis :
- `storage.py` → `load_json` (exceptions et fichiers) ;
- `analytics.py` → `monthly_summary` (pandas) ;
- `cli.py` → `prompt_amount` (boucle et validation) ;
- `tracker.py` → `__init__` (liste, dictionnaires, set).
