# Benchmark de génération et d’unicité

Mesuré le 2 octobre 2026 avec Python 3.12 / NetworkX 3.7. Temps indicatifs sur la machine de développement, avec graphes 3-réguliers et niveau Facile simplifié (12 sommets, triangle ou carré).

Commande : `.venv/bin/python -m project.benchmarks.benchmark`

180 générations : 20 graines par famille et niveau, budget de recherche de 150 ms, cinq candidats maximum. Temps total incluant le placement 3D, hors transport Eel et rendu navigateur. Le jeu utilise uniquement la famille régulière par défaut ; les autres lignes servent à comparer les générateurs.

| Fond demandé | Sommets | Médiane totale | Maximum total | Maximum recherche | Secours / 20 |
|---|---:|---:|---:|---:|---:|
| regular | 12 | 18.43 ms | 22.77 ms | 8.54 ms | 9 |
| erdos | 12 | 15.57 ms | 22.2 ms | 2.71 ms | 20 |
| blocks | 12 | 15.44 ms | 20.12 ms | 6.21 ms | 19 |
| regular | 36 | 108.14 ms | 127.1 ms | 29.34 ms | 9 |
| erdos | 36 | 98.78 ms | 100.84 ms | 1.49 ms | 20 |
| blocks | 36 | 92.12 ms | 103.78 ms | 1.6 ms | 20 |
| regular | 60 | 257.15 ms | 293.42 ms | 27.86 ms | 11 |
| erdos | 60 | 256.65 ms | 276.26 ms | 2.31 ms | 20 |
| blocks | 60 | 241.47 ms | 272.42 ms | 2.01 ms | 20 |

Les graphes du jeu sont 3-réguliers et biconnexes, avec respectivement 18, 54 et 90 arêtes. Le motif est implanté sans modifier le degré de ses sommets. Si les essais aléatoires échouent, le secours tire dans une banque de 96 graphes réguliers dont l’unicité a été vérifiée. Sur les 60 générations régulières, 29 ont utilisé ce secours. Les fonds Erdős–Rényi et par blocs ne satisfont souvent pas la biconnexité ; le secours produit alors également un graphe régulier.

## Cas dégénérés

Recherche négative d’un pentagone dans un graphe biparti complet :

| Sommets | Temps | Résultat |
|---:|---:|---|
| 20 | 59.42 ms | Absence prouvée |
| 40 | 150.15 ms | Budget épuisé, résultat inconnu |
| 80 | 150.16 ms | Budget épuisé, résultat inconnu |
| 120 | 150.28 ms | Budget épuisé, résultat inconnu |

Le budget est coopératif, contrôlé à chaque branche VF2 et entre candidats. L’appariement des degrés est lui-même limité à 200 essais par candidat. Une opération en cours peut légèrement dépasser la limite. Aucun résultat incomplet n’est accepté comme unique. Le placement en O(n²) par itération est effectué après la recherche ; les niveaux sont limités à 60 sommets.

Les tests comparent les solutions à un VF2 indépendant sur le graphe complet pour chaque combinaison motif × famille × niveau ainsi que pour les 96 graphes de secours. Ils contrôlent le degré trois et la biconnexité.
