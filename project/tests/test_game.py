from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from project.src.config import Game, load_config
from project.src.game import GameService
from project.src.storage import Records


class GameTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = 100.
        self.path = Path(self.directory.name)/'scores.json'
        self.game = GameService(Game(duration_seconds=10, storage_file=str(self.path)),clock=lambda:self.now)

    def start(self,mode='timed'):
        state=self.game.start(mode,'easy')
        self.s=self.game.sessions[state['session']]
        return state

    def solve(self):
        return self.game.validate(self.s['id'],self.s['round'],list(self.s['puzzle'].solution))

    def test_validation_score_duplicate_and_stale_round(self):
        state=self.start()
        self.assertNotIn('solution',state['puzzle'])
        self.assertFalse(self.game.validate(self.s['id'],1,[])['correct'])
        self.assertFalse(self.game.validate(self.s['id'],1,[True]*3)['correct'])
        self.now+=2
        self.assertEqual(self.solve()['score'],1)
        self.assertEqual(self.solve()['score'],1)
        self.game.next(self.s['id'],1)
        with self.assertRaises(ValueError): self.game.validate(self.s['id'],1,[])
        self.now+=1
        self.assertEqual(self.solve()['score'],2)
        self.assertEqual(self.s['best']['seconds'],1)

    def test_server_deadline_and_early_finish(self):
        self.start()
        self.now+=10
        self.assertTrue(self.solve()['finished'])
        self.assertEqual(self.s['score'],0)
        self.assertNotIn('puzzle',self.game.next(self.s['id'],1))
        self.start('free'); self.now+=10000
        self.assertTrue(self.solve()['correct'])
        self.game.finish(self.s['id'])
        self.assertTrue(self.game.next(self.s['id'],1)['finished'])

    def test_skip_penalty_is_authoritative_and_applied_once(self):
        self.game.config.duration_seconds = 45
        self.start()
        self.now += 5
        state = self.game.next(self.s['id'], 1)
        self.assertEqual(state['remaining'], 30)
        self.assertEqual(state['penalty_seconds'], 10)
        self.assertEqual(state['score'], 0)
        self.assertEqual(state['round'], 2)
        with self.assertRaises(ValueError):
            self.game.next(self.s['id'], 1)
        self.assertEqual(self.s['penalty_seconds'], 10)
        self.now += 2.5
        result = self.solve()
        self.assertEqual(result['seconds'], 2.5)
        state = self.game.next(self.s['id'], 2)
        self.assertEqual(state['penalty_seconds'], 10)
        self.assertEqual(state['remaining'], 27.5)
        self.assertEqual(state['score'], 1)

    def test_skip_ends_session_when_ten_seconds_or_less_remain(self):
        for elapsed in [0, 1, 9]:
            self.start()
            self.now += elapsed
            with patch.object(self.game, 'puzzle') as generate:
                result = self.game.next(self.s['id'], 1)
                generate.assert_not_called()
            self.assertTrue(result['finished'])
            self.assertEqual(result['remaining'], 0)
            self.assertNotIn('puzzle', result)
            self.assertEqual(self.game.next(self.s['id'], 1)['penalty_seconds'], 10)

    def test_free_mode_and_failed_generation_have_no_penalty(self):
        self.start('free')
        state = self.game.next(self.s['id'], 1)
        self.assertIsNone(state['remaining'])
        self.assertEqual(state['penalty_seconds'], 0)
        self.game.config.duration_seconds = 45
        self.start()
        with patch.object(self.game, 'puzzle', side_effect=ValueError('Generation failed')):
            with self.assertRaises(ValueError):
                self.game.next(self.s['id'], 1)
        self.assertEqual(self.s['round'], 1)
        self.assertEqual(self.s['penalty_seconds'], 0)

    def test_save_reload_idempotency_and_best_snapshot(self):
        self.start(); self.now+=1.25; self.solve()
        with self.assertRaises(ValueError): self.game.save(self.s['id'],'Alice')
        self.game.finish(self.s['id'])
        with self.assertRaises(ValueError): self.game.save(self.s['id'],'  ')
        self.game.save(self.s['id'],'  Alice  ')
        self.game.save(self.s['id'],'Bob')
        records=Records(self.path).read()
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['name'],'Alice')
        self.assertEqual(records[0]['best']['seconds'],1.25)
        self.assertEqual(set(records[0]['best']['selected']),self.s['puzzle'].solution)
        self.assertEqual(records[0]['duration'],10)

    def test_empty_game_not_saved_and_invalid_start(self):
        self.start(); self.game.finish(self.s['id'])
        with self.assertRaises(ValueError): self.game.save(self.s['id'],'Test')
        with self.assertRaises(ValueError): self.game.start('oops','easy')
        with self.assertRaises(ValueError): self.game.start('free','oops')
        with self.assertRaises(ValueError): self.game.finish('unknown')

    def test_corrupt_storage_is_preserved_and_history_capped(self):
        self.path.write_text('{broken')
        self.start(); self.solve(); self.game.finish(self.s['id'])
        with self.assertRaises(ValueError): self.game.save(self.s['id'],'Test')
        self.assertEqual(self.path.read_text(),'{broken')
        self.path.unlink()
        self.game.records.limit=1
        self.game.save(self.s['id'],'One')
        self.start(); self.solve(); self.game.finish(self.s['id']); self.game.save(self.s['id'],'Two')
        self.assertEqual([r['name'] for r in self.game.records.read()],['Two'])

    def test_config_defaults_and_bounds(self):
        path=Path(self.directory.name)/'test.toml'
        path.write_text('[eel]\nopen_browser_on_start = false\n')
        self.assertEqual(load_config(path).game.duration_seconds,120)
        path.write_text('[game]\nduration_seconds=0\n')
        with self.assertRaises(ValueError): load_config(path)


if __name__=='__main__': unittest.main()
