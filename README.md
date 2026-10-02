# Spotted

Un jeu de repérage de motifs dans des graphes 3D pour la Fête de la science. Les points restent fixes ; on tourne la scène, on sélectionne des points et on valide leur structure. Une partie découverte démarre à l’ouverture.

## Démarrer

Python 3.12 et un navigateur avec WebGL sont nécessaires. Depuis la racine du projet :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python project/run.py --config launch
```

Si l’environnement `.venv` fourni est déjà installé, seule la dernière commande est nécessaire. `launch` ouvre Firefox. Pour ouvrir soi-même un autre navigateur :

```sh
.venv/bin/python project/run.py
```

Puis ouvrir **http://localhost:8000**. Le lancement fonctionne aussi depuis un autre répertoire en donnant le chemin de `run.py`. Après installation, le jeu fonctionne **sans Internet** : moteur 3D, styles et polices système sont locaux. Garder le terminal ouvert pendant l’atelier ; Ctrl+C arrête le serveur.

## Jouer en moins de trois minutes

1. Découverte sans chrono, ou **Défi chrono** puis **Démarrer**.
2. Choisir Facile (12 points), Moyen (36) ou Difficile (60).
3. Faire glisser le graphe pour tourner, utiliser la molette ou pincer pour zoomer.
4. Cliquer sur les points ; les liens entre points sélectionnés deviennent verts. Recliquer désélectionne. Un clic droit dans la scène annule le dernier point encore sélectionné.
5. En découverte : **Valider**, puis **Suivant**. En chrono, sélectionner tous les points du motif déclenche sa validation et le passage au suivant automatiquement. Une mauvaise sélection reste modifiable. **Nouveau** permet de changer de motif en découverte. En chrono, **Passer (−10 s)** retire dix secondes et charge le motif suivant, sans gagner de point. S’il reste dix secondes ou moins, la partie se termine.
6. À la fin du chrono, ou avec **Terminer**, saisir un pseudo pour enregistrer la partie. En découverte, terminer avant de changer de partie pour conserver ses trouvailles.

La règle est celle du **sous-graphe induit** : les points choisis doivent avoir exactement les liens du motif, sans liaison supplémentaire entre eux. Les liens vers les autres points ne comptent pas. Une forme tournée, inclinée ou déformée reste une bonne réponse. Le motif n’est pas nécessairement plan dans la scène 3D.

Le niveau Facile propose uniquement des triangles et des carrés, avec 12 sommets, des points plus gros et un placement aéré en trois dimensions. Les niveaux Moyen et Difficile proposent aussi la maison et le cycle à cinq points. Chaque défi a exactement **un ensemble de points solution**.

Le classement compare seulement les défis chrono de même niveau et même durée. Le nombre de motifs départage les joueurs, puis leur meilleur temps. La galerie conserve le motif le plus vite trouvé de chaque partie enregistrée (découverte comprise) et permet de revoir le graphe en 3D. Les 30 dernières trouvailles sont affichées.

La sélection utilise directement les coordonnées du clic, indépendamment du survol mis en cache par le moteur 3D. La zone cliquable est légèrement élargie (au moins 18 pixels de rayon à la souris, 24 au toucher), en donnant priorité au point visible le plus proche. Un déplacement de plus de 7 pixels est traité comme une rotation, sans sélectionner de sommet. Le clic droit ne déplace plus la caméra. Une sélection déjà validée reste verrouillée jusqu’au défi suivant.

Le bouton **Mode sombre / Mode clair** en haut de l’interface change le thème, y compris la scène 3D et la galerie. Le choix est mémorisé dans ce navigateur. Sans préférence enregistrée, le thème suit celui du système au chargement. Changer de thème ne modifie ni la sélection, ni la caméra, ni le chronomètre.

## Réglages et stockage

Modifier le TOML utilisé au démarrage, puis relancer le serveur :

```toml
[eel]
open_browser_on_start = true
port = 8000

[game]
duration_seconds = 120        # 10 à 600 secondes
uniqueness_budget_ms = 150     # budget de recherche par génération
generation_attempts = 5      # candidats avant le secours garanti
storage_file = "data/scores.json"
max_records = 300             # conservation des dernières parties enregistrées
```

`project/config/default.toml` et `project/config/launch.toml` sont indépendants : modifier celui utilisé. Un chemin de stockage relatif est résolu depuis `project/`. Les scores sont donc par défaut dans **`project/data/scores.json`**, communs aux navigateurs de cet ordinateur, et conservés après redémarrage. Sauvegarde atomique, enregistrement idempotent, fichier endommagé préservé avec erreur affichée. Copier ce fichier pour sauvegarder les résultats ; le déplacer, serveur arrêté, pour recommencer le classement. Les données des visiteurs sont ignorées par Git.

Le chrono, les réponses et la pénalité de passage sont validés côté Python. Un passage automatique après une bonne réponse ne coûte pas dix secondes ; une répétition de la même requête de passage ne cumule pas les pénalités. Un motif ne rapporte qu’un point, même en cas de double clic. Le temps de passage au défi suivant fait partie du chrono global. Les réglages sont verrouillés pendant un défi ; **Terminer** permet de l’interrompre.

## Génération et unicité

`project/src/utils/graph.py` définit la banque de motifs (`MOTIFS`) et les niveaux (`LEVELS`). Le jeu génère désormais des **graphes 3-réguliers** : chaque sommet possède exactement trois voisins, y compris les sommets du motif. Facile : 12 sommets / 18 arêtes ; Moyen : 36 / 54 ; Difficile : 60 / 90.

Le motif est installé sur des sommets du graphe, puis leurs degrés restants et ceux des autres sommets sont complétés par appariement aléatoire. Boucles, arêtes multiples et liens supplémentaires entre sommets du motif sont rejetés. On exige aussi un graphe biconnexe : le motif ne sert plus de centre d’articulation entre des blocs séparés. Le graphe final, et pas seulement son fond, est régulier. Les générations Erdős–Rényi et par blocs restent disponibles dans le code pour les comparaisons ; elles ne sont pas utilisées par défaut dans le jeu.

Le test exact utilise le VF2 de NetworkX (`GraphMatcher.subgraph_isomorphisms_iter`), sur les composantes biconnexes. Les correspondances sont dédupliquées par ensemble de sommets : les rotations et symétries d’un même motif ne constituent pas plusieurs solutions. La recherche s’arrête dès la deuxième occurrence, après 60 000 branches ou à épuisement du budget. Un résultat incomplet n’est **jamais** accepté comme unique.

Après plusieurs rejets ou dépassement du budget, le jeu choisit un graphe dans `project/src/utils/regular_bank.json` : **96 graphes réguliers biconnexes vérifiés**, huit par combinaison taille × motif. Cette banque garantit un secours rapide sans changer la densité ni replacer le motif au milieu de blocs. Tous ses graphes sont vérifiés par un test VF2 indépendant. Pour la reconstruire après modification des tailles ou des motifs :

```sh
.venv/bin/python -m project.scripts.build_regular_bank
```

Les identifiants sont mélangés, puis le placement 3D applique les mêmes forces à tous les sommets, sans connaître la solution. Un léger mélange spatial évite les superpositions ; il ne déplace pas spécifiquement le motif vers le centre ou vers le bord. Les points sont ensuite figés. Le niveau Facile conserve un volume 3D complet et augmente les distances entre les sommets, sans déplacer spécifiquement la solution. Un motif peut naturellement apparaître au centre, mais il n’y est plus placé par la construction du graphe.

Le cadrage utilise les positions projetées pour remplir la scène. Le classement et la galerie restent en dessous. Un fond lavande clair, des touches violettes et des commandes compactes conservent une interface sobre. Un worker dédié effectue les calculs sans bloquer Eel.

Pour étendre la banque de motifs, adapter `MOTIFS`, vérifier que les nouveaux motifs sont compatibles avec le degré trois, reconstruire la banque de secours et relancer les tests.

## Vérifier

Tests Python (aucune dépendance de test supplémentaire) :

```sh
.venv/bin/python -m unittest discover -s project/tests -v
.venv/bin/python -m project.benchmarks.benchmark
```

Le benchmark couvre 180 générations, plus des graphes bipartis dégénérés jusqu’à 120 sommets. Résultats et limites : [rapport](project/benchmarks/README.md), [CSV](project/benchmarks/results.csv).

Test complet dans Chromium, avec son propre serveur et un fichier de scores temporaire :

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python project/tests/browser_smoke.py
```

Il vérifie le rendu 3D, les clics rapides sans survol préalable, les clics proches des points, le tactile, l’annulation au clic droit dans l’ordre de sélection, la distinction entre clic et glissement, la rotation, les positions fixes, la sélection et les arêtes, les réponses incorrectes/correctes, le passage automatique au suivant en chrono et la validation manuelle en découverte, le chrono et les pénalités de passage, la mémorisation du mode sombre et son effet sur le rendu 3D, l’enregistrement, la persistance, la galerie 3D, le rendu mobile et l’absence de requêtes externes. Captures dans `/tmp/spotted-*.png`.

La validation technique ne remplace pas un essai avec les visiteurs : commencer par Facile pour les plus jeunes et ajuster la durée dans le TOML après quelques parties.
