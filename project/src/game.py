from datetime import datetime, timezone
import secrets
import time
import networkx as nx
from .utils.graph import LEVELS, generate_puzzle, motif_graph
from .storage import Records


class GameService:
    def __init__(self, config, clock=time.monotonic):
        self.config, self.clock = config, clock
        self.sessions = {}
        self.records = Records(config.storage_file, config.max_records)

    def remaining(self, session):
        return max(0, self.config.duration_seconds - (self.clock() - session['started']) - session['penalty_seconds']) if session['mode'] == 'timed' else None

    def state(self, s):
        return {'session': s['id'], 'round': s['round'], 'score': s['score'], 'remaining': self.remaining(s), 'finished': s['finished'], 'solved': s['solved'], 'penalty_seconds': s['penalty_seconds']}

    def session(self, token):
        s = self.sessions.get(token)
        if s is None:
            raise ValueError('Cette partie a expiré. Lance une nouvelle partie.')
        if s['mode'] == 'timed' and self.remaining(s) <= 0:
            s['finished'] = True
        return s

    def puzzle(self, level):
        return generate_puzzle(level, budget_ms=self.config.uniqueness_budget_ms, attempts=self.config.generation_attempts)

    def start(self, mode, level):
        if mode not in ('free', 'timed') or level not in LEVELS:
            raise ValueError('Mode ou difficulté inconnu.')
        puzzle = self.puzzle(level)
        now = self.clock()
        self.sessions = {k: s for k, s in self.sessions.items() if now - s['started'] < 3600}
        if len(self.sessions) >= 100:
            self.sessions.pop(next(iter(self.sessions)))
        token = secrets.token_urlsafe(18)
        s = dict(id=token, mode=mode, level=level, started=now, round_started=now, puzzle=puzzle,
                 round=1, score=0, solved=False, finished=False, best=None, saved=False, penalty_seconds=0)
        self.sessions[token] = s
        return {**self.state(s), 'puzzle': puzzle.view}

    def next(self, token, round_id):
        s = self.session(token)
        if s['finished']:
            return self.state(s)
        if round_id != s['round']:
            raise ValueError('Ce défi a déjà changé.')
        # Automatic advancement after a correct answer is free. Every unsolved
        # timed round costs 10 seconds, even when called directly through Eel.
        penalty = 10 if s['mode'] == 'timed' and not s['solved'] else 0
        if penalty and self.remaining(s) <= penalty:
            s['penalty_seconds'] += penalty
            s['finished'] = True
            return self.state(s)
        puzzle = self.puzzle(s['level'])
        # Commit together after generation, so a failed request can be retried
        # without paying twice for the same round.
        s['penalty_seconds'] += penalty
        s['puzzle'] = puzzle
        s['round'] += 1
        s['round_started'] = self.clock()
        s['solved'] = False
        self.session(token)
        return {**self.state(s), 'puzzle': s['puzzle'].view}

    def validate(self, token, round_id, nodes):
        s = self.session(token)
        if s['finished'] or s['solved']:
            return self.state(s)
        if round_id != s['round']:
            raise ValueError('Ce défi a déjà changé.')
        puzzle = s['puzzle']
        motif = motif_graph(puzzle.target)
        if not isinstance(nodes, list) or len(nodes) != len(motif) or any(type(n) is not int for n in nodes) or len(set(nodes)) != len(nodes) or not set(nodes) <= set(puzzle.graph):
            return {**self.state(s), 'correct': False, 'message': f'Sélectionne exactement {len(motif)} points.'}
        if not nx.is_isomorphic(puzzle.graph.subgraph(nodes), motif):
            return {**self.state(s), 'correct': False, 'message': 'Pas encore ! Vérifie les liaisons entre tes points.'}
        elapsed = round(self.clock() - s['round_started'], 3)
        s['score'] += 1
        s['solved'] = True
        if s['best'] is None or elapsed < s['best']['seconds']:
            s['best'] = {'seconds': elapsed, 'puzzle': puzzle.view, 'selected': nodes}
        return {**self.state(s), 'correct': True, 'seconds': elapsed}

    def finish(self, token):
        s = self.session(token)
        s['finished'] = True
        return {**self.state(s), 'best_seconds': s['best']['seconds'] if s['best'] else None}

    def save(self, token, name):
        s = self.session(token)
        if not s['finished'] or not s['best']:
            raise ValueError('Termine une partie avec au moins un motif trouvé.')
        name = ' '.join(str(name).split())
        if not 1 <= len(name) <= 24 or any(ord(c) < 32 for c in name):
            raise ValueError('Choisis un pseudo de 1 à 24 caractères.')
        self.records.add({'id': s['id'], 'name': name, 'mode': s['mode'], 'level': s['level'],
                          'duration': self.config.duration_seconds, 'score': s['score'], 'best': s['best'],
                          'date': datetime.now(timezone.utc).isoformat()})
        s['saved'] = True
        return {'ok': True}
