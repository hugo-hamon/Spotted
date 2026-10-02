from dataclasses import dataclass, field
from pathlib import Path
import toml


@dataclass
class EEL:
    open_browser_on_start: bool = False
    port: int = 8000


@dataclass
class Game:
    duration_seconds: int = 120
    uniqueness_budget_ms: int = 150
    generation_attempts: int = 5
    storage_file: str = 'data/scores.json'
    max_records: int = 300


@dataclass
class Config:
    eel: EEL = field(default_factory=EEL)
    game: Game = field(default_factory=Game)


def load_config(config_path):
    data = toml.load(config_path)
    config = Config(EEL(**data.get('eel', {})), Game(**data.get('game', {})))
    for value, low, high in [(config.game.duration_seconds, 10, 600),
                             (config.game.uniqueness_budget_ms, 1, 2000),
                             (config.game.generation_attempts, 1, 20),
                             (config.game.max_records, 1, 2000), (config.eel.port, 1024, 65535)]:
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'Configuration hors limites : {value} (attendu : {low}–{high}).')
    path = Path(config.game.storage_file)
    if not path.is_absolute():
        config.game.storage_file = str(Path(__file__).resolve().parents[1] / path)
    return config
