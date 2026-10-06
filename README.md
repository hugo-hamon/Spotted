# Spotted

Spotted est un jeu de repérage de motifs dans des graphes, conçu pour la Fête de la science. L'objectif est de retrouver une forme parmi des atomes en 3D ou sur un plan de métro en 2D en sélectionnant les points qui ont exactement les mêmes liens que le modèle.

Avec Python 3.12, depuis la racine du projet, l'installation des dépendances avec pip et le lancement du jeu se font de la manière suivante :

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd project
python run.py --config config/launch.toml
```

Cela ouvre la page [http://localhost:8000](http://localhost:8000) dans Firefox. Le terminal doit rester ouvert pendant le jeu ; `Ctrl+C` arrête le serveur.

Pour jouer, il suffit de choisir un niveau, de préférence **Facile** pour commencer, de faire glisser la scène pour l’explorer, de zoomer avec la molette et de cliquer sur les points du motif. Le mode **Découverte** montre la solution en doré pour apprendre ; le mode **Libre** permet de chercher à son rythme, avec des indices si besoin. Dans ces deux modes, il faut cliquer sur **Valider**, puis sur **Suivant** après une réussite. En mode **Chrono**, il faut cliquer sur **Démarrer**, puis trouver un maximum de motifs avant la fin du temps imparti : la validation et le passage au suivant sont automatiques.
