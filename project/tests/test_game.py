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

    def test_wrong_selection_count_is_explained_without_scoring(self):
        self.start('free')
        solution = list(self.s['puzzle'].solution)
        other = next(n for n in self.s['puzzle'].graph if n not in solution)
        too_few = self.game.validate(self.s['id'],1,solution[:-1])
        self.assertIn('Il manque encore 1 point',too_few['message'])
        too_many = self.game.validate(self.s['id'],1,solution+[other])
        self.assertIn('1 point en trop',too_many['message'])
        self.assertIn('Reclique',too_many['message'])
        self.assertFalse(too_many['correct'])
        self.assertEqual(too_many['score'],0)
        self.assertTrue(self.game.validate(self.s['id'],1,solution)['correct'])

    def test_metro_rounds_and_skin_lock(self):
        state = self.game.start('free','easy','metro')
        self.s = self.game.sessions[state['session']]
        self.assertEqual(state['puzzle']['skin'],'metro')
        self.solve()
        result = self.game.next(self.s['id'],1,'atoms')
        self.assertEqual(result['score'],1)
        self.assertNotIn('skin',result['puzzle'])
        result = self.game.next(self.s['id'],2,'metro')
        self.assertEqual(result['puzzle']['skin'],'metro')
        state = self.game.start('timed','easy','metro')
        with self.assertRaises(ValueError): self.game.next(state['session'],1,'atoms')
        self.assertEqual(self.game.sessions[state['session']]['round'],1)
        with self.assertRaises(ValueError): self.game.start('free','easy','bad')

    def test_new_motifs_guidance_validation_and_snapshots(self):
        from project.src.utils.graph import EXTENDED_PORTS, generate_puzzle
        from project.src.utils.metro import generate_metro
        for skin, generate in [('atoms', generate_puzzle), ('metro', generate_metro)]:
            for target in EXTENDED_PORTS:
                puzzle = generate('medium',target=target,seed=19)
                for mode in ('guided','free','timed'):
                    with self.subTest(skin=skin,target=target,mode=mode), patch.object(self.game,'puzzle',return_value=puzzle):
                        state = self.game.start(mode,'medium',skin)
                        session = self.game.sessions[state['session']]
                        if mode != 'timed':
                            for _ in range(3):
                                hint = self.game.hint(state['session'],1)
                            self.assertEqual(set(hint['hint_nodes']),puzzle.solution)
                        if mode == 'guided':
                            self.assertEqual(set(state['guided_nodes']),puzzle.solution)
                        result = self.game.validate(state['session'],1,list(puzzle.solution))
                        self.assertTrue(result['correct'])
                        self.assertEqual(result['score'],1)
                        self.assertEqual(session['best']['puzzle']['motif'],puzzle.view['motif'])

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

    def test_guidance_and_progressive_hints_are_scoped_to_round_and_mode(self):
        for mode in ('guided', 'free'):
            state = self.start(mode)
            self.assertIsNone(state['remaining'])
            self.assertEqual(state['hint_nodes'], [])
            if mode == 'guided':
                self.assertEqual(set(state['guided_nodes']), self.s['puzzle'].solution)
            else:
                self.assertNotIn('guided_nodes', state)
            for level, count in ((1, 1), (2, 2), (3, len(self.s['puzzle'].solution)), (3, len(self.s['puzzle'].solution))):
                hint = self.game.hint(self.s['id'], 1)
                self.assertEqual(hint['hint_level'], level)
                self.assertEqual(len(hint['hint_nodes']), count)
                self.assertLessEqual(set(hint['hint_nodes']), self.s['puzzle'].solution)
                if level == 2:
                    self.assertTrue(self.s['puzzle'].graph.has_edge(*hint['hint_nodes']))
                self.assertEqual(hint['score'], 0)
            self.solve()
            with self.assertRaises(ValueError): self.game.hint(self.s['id'], 1)
            state = self.game.next(self.s['id'], 1)
            self.assertEqual(state['hint_level'], 0)
            self.assertEqual(state['hint_nodes'], [])
            with self.assertRaises(ValueError): self.game.hint(self.s['id'], 1)
            self.game.finish(self.s['id'])
            with self.assertRaises(ValueError): self.game.hint(self.s['id'], 2)
        state = self.start('timed')
        self.assertNotIn('guided_nodes', state)
        self.assertNotIn('hint_nodes', state)
        with self.assertRaises(ValueError): self.game.hint(self.s['id'], 1)
        self.assertEqual(self.s['hint_level'], 0)

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
