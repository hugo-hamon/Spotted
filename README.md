# Spotted

Un jeu de repérage de motifs dans des graphes 3D pour la Fête de la science. Les points restent fixes ; on tourne la scène, on sélectionne des points et on valide leur structure. Une partie découverte démarre à l’ouverture.

Les sommets sont représentés par des atomes : carbone (C, gris), oxygène (O, rouge), hydrogène (H, blanc) et azote (N, bleu). Leur symbole reste lisible pendant la rotation de la vue ; une petite légende rappelle les éléments. Cet habillage est illustratif : les liens sont fictifs et les graphes ne représentent pas des molécules chimiquement exactes. Seule la structure compte pour trouver le motif, indépendamment des éléments. Les atomes sont attribués sans tenir compte de la solution, conservés dans les enregistrements et affichés dans la galerie. Les anciennes parties reçoivent aussi un habillage compatible.

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

1. **Découverte** pour apprendre avec le motif montré en doré, **Libre** pour chercher sans aide initiale, ou **Chrono** puis **Démarrer**.
2. Choisir Facile (12 points), Moyen (36) ou Difficile (60).
3. Faire glisser le graphe pour tourner, utiliser la molette ou pincer pour zoomer.
4. Cliquer sur les points ; les liens entre points sélectionnés deviennent verts. Recliquer désélectionne. Un clic droit dans la scène annule le dernier point encore sélectionné.
5. En Découverte ou Libre : **Valider**, puis **Suivant**. Après réussite, le motif reste vert et le reste du graphe devient transparent pour observer sa structure. En chrono, sélectionner tous les points du motif déclenche sa validation et le passage au suivant automatiquement. Une mauvaise sélection reste modifiable. **Nouveau** permet de changer de motif en Découverte ou Libre. En chrono, **Passer (−10 s)** retire dix secondes et charge le motif suivant, sans gagner de point. S’il reste dix secondes ou moins, la partie se termine.
6. À la fin du chrono, ou avec **Terminer**, saisir un pseudo pour enregistrer la partie. En Découverte ou Libre, terminer avant de changer de partie pour conserver ses trouvailles.

**Indice**, uniquement en Découverte et Libre, entoure successivement un point, deux points reliés, puis le motif complet. Les indices ne sélectionnent pas les points à ta place ; ils restent visibles jusqu’au défi suivant. Chaque nouveau défi remet les indices à zéro. En Découverte, le motif entier est déjà doré et les indices indiquent où commencer. Les indices sont également interdits côté serveur en Chrono.

Le sélecteur **Habillage** alterne entre Atomes en 3D et Métro en 2D. En Métro, le jeu génère un nouveau graphe planaire, dessiné sans croisements : lignes colorées, stations nommées avec un pictogramme M et petites rames animées. Glisser déplace le plan ; la rotation est désactivée, le zoom et le clic droit restent disponibles. Le changement d’habillage charge un nouveau défi et efface la sélection et les indices, tout en conservant le score et les trouvailles d’une partie Découverte ou Libre en cours. Il est verrouillé pendant le Chrono. Les classements Métro et Atomes sont séparés, et chaque trouvaille garde son propre habillage dans la galerie. Le choix est mémorisé dans le navigateur. Les rames s’arrêtent après une réussite en Découverte ou Libre ; elles restent statiques si le navigateur demande moins d’animations.

La règle est celle du **sous-graphe induit** : les points choisis doivent avoir exactement les liens du motif, sans liaison supplémentaire entre eux. Les liens vers les autres points ne comptent pas. Une forme tournée, inclinée ou déformée reste une bonne réponse. Le motif n’est pas nécessairement plan dans la scène 3D.

Le niveau Facile propose uniquement des triangles et des carrés, avec 12 sommets, des points plus gros et un placement aéré en trois dimensions. Les niveaux Moyen et Difficile proposent aussi la maison et le cycle à cinq points. Chaque défi a exactement **un ensemble de points solution**.

Le classement compare seulement les défis chrono de même niveau et même durée. Le nombre de motifs départage les joueurs, puis leur meilleur temps. La galerie conserve le motif le plus vite trouvé de chaque partie enregistrée (découverte comprise) et permet de revoir le graphe en 3D. Les 30 dernières trouvailles sont affichées.

Les boutons Nouvelle partie, Nouveau / Suivant et Valider sont agrandis et contrastés, et le motif à trouver dispose d’un cadre plus visible. La sélection n’est plus plafonnée au nombre de points du motif : les points supplémentaires restent sélectionnés, avec un compteur et un message indiquant combien retirer. Reclique sur un point pour le retirer, ou utilise le clic droit pour annuler le dernier choix. En Libre et Découverte, Valider explique aussi les points manquants ou en trop. En Chrono, revenir au bon nombre de points relance automatiquement la vérification, y compris après une annulation au clic droit.

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

`project/src/utils/graph.py` définit la banque de motifs (`MOTIFS`) et les niveaux (`LEVELS`). Pour les quatre motifs d’origine (triangle, carré, maison, 5-cycle), l’habillage Atomes génère des **graphes 3-réguliers** : chaque sommet possède exactement trois voisins, y compris les sommets du motif. Facile : 12 sommets / 18 arêtes ; Moyen : 36 / 54 ; Difficile : 60 / 90.

Le motif est installé sur des sommets du graphe, puis leurs degrés restants et ceux des autres sommets sont complétés par appariement aléatoire. Boucles, arêtes multiples et liens supplémentaires entre sommets du motif sont rejetés. On exige aussi un graphe biconnexe : le motif ne sert plus de centre d’articulation entre des blocs séparés. Le graphe final, et pas seulement son fond, est régulier. Les générations Erdős–Rényi et par blocs restent disponibles dans le code pour les comparaisons ; elles ne sont pas utilisées par défaut dans le jeu.

Le test exact utilise le VF2 de NetworkX (`GraphMatcher.subgraph_isomorphisms_iter`), sur les composantes biconnexes pour les motifs biconnexes, et sur les composantes connexes pour les motifs avec une branche ou une articulation. Les correspondances sont dédupliquées par ensemble de sommets : les rotations et symétries d’un même motif ne constituent pas plusieurs solutions. La recherche s’arrête dès la deuxième occurrence, après 60 000 branches ou à épuisement du budget. Un résultat incomplet n’est **jamais** accepté comme unique.

Après plusieurs rejets ou dépassement du budget, le jeu choisit un graphe dans `project/src/utils/regular_bank.json` : **96 graphes réguliers biconnexes vérifiés**, huit par combinaison taille × motif d’origine. Cette banque garantit un secours rapide sans changer la densité ni replacer le motif au milieu de blocs. Tous ses graphes sont vérifiés par un test VF2 indépendant. Pour la reconstruire après modification des tailles ou des motifs :

```sh
.venv/bin/python -m project.scripts.build_regular_bank
```

Les identifiants sont mélangés, puis le placement 3D applique les mêmes forces à tous les sommets, sans connaître la solution. Un léger mélange spatial évite les superpositions ; il ne déplace pas spécifiquement le motif vers le centre ou vers le bord. Les points sont ensuite figés. Le niveau Facile conserve un volume 3D complet et augmente les distances entre les sommets, sans déplacer spécifiquement la solution. Un motif peut naturellement apparaître au centre, mais il n’y est plus placé par la construction du graphe.

Le cadrage utilise les positions projetées pour remplir la scène. Le classement et la galerie restent en dessous. Un fond lavande clair, des touches violettes et des commandes compactes conservent une interface sobre. Un worker dédié effectue les calculs sans bloquer Eel.

Le métro utilise `project/src/utils/metro.py`. Facile conserve un petit plan lisible. En Moyen et Difficile, des raccourcis, des diagonales et des déplacements des stations créent des boucles variées et des formes proches du motif : il faut compter les stations et vérifier les liens, pas seulement reconnaître une silhouette. Le motif reçoit les mêmes déformations que les autres stations. Les tailles restent 12 / 36 / 60 ; chaque modification topologique conserve une seule solution exacte. La recherche utilise les cycles sans corde de NetworkX, un carré avec toit pour la maison, et des extensions exactes de triangles pour les nouveaux motifs. La roue est un carré induit avec un centre relié aux quatre sommets. Ces recherches sont comparées à VF2 dans les tests. Les essais sont en nombre limité et les subdivisions rejetées ne sont pas retestées en boucle. Les positions et les nouveaux segments sont contrôlés pour conserver un plan sans croisements. Les tests vérifient aussi la diversité des boucles, la planarité et les intersections géométriques. Aucun nouvel habillage ni réglage n’est nécessaire.

Cinq motifs supplémentaires sont proposés en **Moyen et Difficile**, dans les deux habillages : **Cerf-volant** (triangle avec une branche), **Losange** (deux triangles partageant une arête), **Papillon** (deux triangles partageant un sommet), **Roue** (carré avec un centre relié à ses quatre coins) et **Losange à queue**. Facile conserve uniquement triangle et carré.

Ces nouveaux motifs utilisent des degrés variables : certains nécessitent quatre voisins, et un cerf-volant unique est incompatible avec un graphe entièrement 3-régulier.

En Moyen et Difficile, `project/src/utils/camouflage.py` construit un réseau de **6 ou 9 régions de taille comparable**. Une seule contient la réponse ; la plupart des autres reprennent sa silhouette avec un lien manquant ou une station supplémentaire. Quelques formes différentes apportent de la variété. La position de la réponse et les rotations sont aléatoires, avec la même échelle et les mêmes déformations que les leurres. Des liaisons entre régions créent plusieurs itinéraires, plutôt qu’un unique petit îlot ajouté à un réseau de grandes boucles. L’ajout final de stations préserve aussi les leurres : il ne doit pas les faire disparaître en subdivisant leurs liens internes.

Cette construction est utilisée par défaut pour les cinq nouveaux motifs, en Atomes comme en Métro. Les atomes reçoivent ensuite leur placement 3D ; le métro reste plan, avec un format large pour occuper la scène. Chaque liaison et subdivision est vérifiée pour conserver une seule solution induite. Les niveaux restent à 36 et 60 sommets ; Facile et ses deux motifs simples restent inchangés. Les essais Erdős–Rényi et par blocs gardent leur recherche VF2 et utilisent ce même réseau comme secours. Les tests contrôlent l’unicité avec VF2, les croisements, la présence de plusieurs leurres disjoints et l’échelle du motif par rapport au reste du réseau.

Pour étendre la banque, définir les arêtes et les points d’aperçu dans `MOTIFS`, adapter les constructions de secours et la recherche métro, puis relancer les tests. Le script de banque cubique ne concerne que `CUBIC_MOTIFS`.

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

Il vérifie le rendu 3D, les clics rapides sans survol préalable, les clics proches des points, le tactile, l’annulation au clic droit dans l’ordre de sélection, la distinction entre clic et glissement, la rotation, les positions fixes, la sélection et les arêtes, les réponses incorrectes/correctes, le passage automatique au suivant en chrono et la validation manuelle en découverte, le chrono et les pénalités de passage, la mémorisation du mode sombre et son effet sur le rendu 3D, l’enregistrement, la persistance, la galerie 3D, le mode guidé, les indices progressifs, la transparence après réussite, le changement d’habillage, le rendu mobile et l’absence de requêtes externes. Captures dans `/tmp/spotted-*.png`.

La validation technique ne remplace pas un essai avec les visiteurs : commencer par Facile pour les plus jeunes et ajuster la durée dans le TOML après quelques parties.
