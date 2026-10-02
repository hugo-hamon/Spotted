"""Start Spotted from any working directory."""
import argparse
import logging
from pathlib import Path
from src.app import App

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(prog='Spotted', description='Repère les motifs cachés dans un graphe en 3D.')
    parser.add_argument('--config', '-c', default='default', help='Chemin TOML ou nom dans project/config (default, launch).')
    args = parser.parse_args()
    candidates = [Path(args.config), ROOT / 'config' / args.config, ROOT / 'config' / f'{args.config}.toml']
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        parser.error(f'Configuration introuvable : {args.config}')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = App(str(path))
    print(f'Spotted : http://localhost:{app.config.eel.port}', flush=True)
    app.run()


if __name__ == '__main__':
    main()
