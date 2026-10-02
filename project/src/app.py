from pathlib import Path
import logging
import eel
from gevent.threadpool import ThreadPool
from .config import load_config
from .game import GameService


class App:
    def __init__(self, config_path):
        self.config = load_config(config_path)
        self.game = GameService(self.config.game)
        # Serial worker: costly generation never blocks Eel or races score writes.
        self.pool = ThreadPool(1)

    def run(self):
        eel.init(str(Path(__file__).parent / 'web'))
        for name in dir(self):
            if name.startswith('eel_'):
                eel.expose(getattr(self, name))
        eel.start('index.html', mode='firefox', host='localhost', port=self.config.eel.port,
                  open_browser=self.config.eel.open_browser_on_start, shutdown_delay=3)

    def call(self, fn, *args):
        try:
            return self.pool.spawn(fn, *args).get()
        except (ValueError, TypeError, OSError) as error:
            logging.exception('Spotted request failed')
            return {'error': str(error)}

    def eel_settings(self):
        return {'duration': self.config.game.duration_seconds}

    def eel_start(self, mode, level):
        return self.call(self.game.start, mode, level)

    def eel_next(self, token, round_id):
        return self.call(self.game.next, token, round_id)

    def eel_validate(self, token, round_id, nodes):
        return self.call(self.game.validate, token, round_id, nodes)

    def eel_finish(self, token):
        return self.call(self.game.finish, token)

    def eel_save(self, token, name):
        return self.call(self.game.save, token, name)

    def eel_records(self):
        return self.call(self.game.records.read)
