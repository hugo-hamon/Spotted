"""Small, connected puzzles with exactly one induced copy of the target."""
from dataclasses import dataclass
from itertools import combinations
import math
import json
from functools import lru_cache
from pathlib import Path
import random
import time
import networkx as nx


MOTIFS = {
    'triangle': ('Triangle', [(0, 1), (1, 2), (2, 0)], [(0, -1), (1, 1), (-1, 1)]),
    'square': ('Carré', [(0, 1), (1, 2), (2, 3), (3, 0)], [(-1, -1), (1, -1), (1, 1), (-1, 1)]),
    'house': ('Maison', [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4)], [(-1, 0), (1, 0), (1, 1.5), (-1, 1.5), (0, -1.3)]),
    'pentagon': ('Cycle à 5', [(i, (i + 1) % 5) for i in range(5)], [(math.sin(i * 2 * math.pi / 5), -math.cos(i * 2 * math.pi / 5)) for i in range(5)]),
}
LEVELS = {'easy': (12, 3), 'medium': (36, 3), 'hard': (60, 3)}


def motif_graph(key):
    return nx.Graph(MOTIFS[key][1])


def motif_view(key):
    name, edges, points = MOTIFS[key]
    return {'key': key, 'name': name, 'edges': edges, 'points': points}


class SearchBudgetExceeded(Exception):
    pass


def occurrences(graph, motif, budget_ms=150, max_candidates=60000):
    """Return at most two distinct vertex sets (automorphisms count only once).

    All bank motifs are biconnected: a copy belongs to one biconnected block.
    Bound VF2's search branches, using NetworkX's exact induced isomorphism.
    An exhausted budget is UNKNOWN, never a certificate of uniqueness.
    """
    if not nx.is_biconnected(motif):
        raise ValueError('La banque exige des motifs biconnexes.')
    deadline = time.perf_counter() + budget_ms / 1000
    found, checked = set(), 0

    class BoundedMatcher(nx.algorithms.isomorphism.GraphMatcher):
        def syntactic_feasibility(self, a, b):
            nonlocal checked
            checked += 1
            if checked > max_candidates or time.perf_counter() >= deadline:
                raise SearchBudgetExceeded()
            return super().syntactic_feasibility(a, b)

    for block in nx.biconnected_components(graph):
        if time.perf_counter() >= deadline:
            raise SearchBudgetExceeded()
        if len(block) < len(motif):
            continue
        matcher = BoundedMatcher(graph.subgraph(block), motif)
        for mapping in matcher.subgraph_isomorphisms_iter():
            if time.perf_counter() >= deadline:
                raise SearchBudgetExceeded()
            found.add(frozenset(mapping))
            if len(found) == 2:
                return list(found)
    return list(found)


def background(n, family, degree, rng):
    seed = rng.randrange(2**32)
    if family == 'regular':
        g = nx.random_regular_graph(degree if n * degree % 2 == 0 else degree + 1, n, seed=seed)
    elif family == 'blocks':
        inside = min(.8, degree * 1.6 / (n - 1))
        outside = min(.3, degree * .4 / (n - 1))
        g = nx.stochastic_block_model([n // 2, n - n // 2], [[inside, outside], [outside, inside]], seed=seed)
    else:
        g = nx.gnp_random_graph(n, degree / max(1, n - 1), seed=seed)
    components = list(nx.connected_components(g))
    for a, b in zip(components, components[1:]):
        g.add_edge(rng.choice(sorted(a)), rng.choice(sorted(b)))
    return g


def coordinates(graph, rng, spread=0):
    """Deterministic small force layout, without NumPy or browser simulation."""
    positions = {n: [rng.uniform(-100, 100) for _ in range(3)] for n in graph}
    anchors = {n: list(p) for n, p in positions.items()}
    for step in range(100):
        forces = {n: [0., 0., 0.] for n in graph}
        for a, b in combinations(graph, 2):
            delta = [positions[a][i] - positions[b][i] for i in range(3)]
            dist = max(1., math.sqrt(sum(d * d for d in delta)))
            strength = 1900 / (dist * dist)
            for i in range(3):
                force = delta[i] / dist * strength
                forces[a][i] += force
                forces[b][i] -= force
        for a, b in graph.edges():
            delta = [positions[b][i] - positions[a][i] for i in range(3)]
            dist = max(1., math.sqrt(sum(d * d for d in delta)))
            for i in range(3):
                force = delta[i] / dist * (dist - 48) * .035
                forces[a][i] += force
                forces[b][i] -= force
        for n in graph:
            for i in range(3):
                positions[n][i] += max(-5, min(5, forces[n][i] - positions[n][i] * .003))
    # A small amount of spatial variation keeps the layout from collapsing.
    # Every vertex follows the same rules, with no target-dependent position.
    for n in graph:
        positions[n] = [(1 - spread) * p + spread * a
                        for p, a in zip(positions[n], anchors[n])]
    return {n: [p[0] * 1.5, p[1], p[2] * .7] for n, p in positions.items()}


def planted_regular(total, motif, rng):
    """Complete motif degree stubs to a simple cubic graph without a hub.

    Motif vertices use the same degree as every other vertex. Reject loops,
    parallel edges and new chords inside the motif. Conditioning on simplicity
    and biconnectivity prevents a separate motif module joined by bridges.
    """
    motif_size = len(motif)
    for _ in range(200):
        graph = nx.Graph()
        graph.add_nodes_from(range(total))
        graph.add_edges_from(motif.edges())
        stubs = [node for node in graph for _ in range(3 - graph.degree(node))]
        rng.shuffle(stubs)
        for a, b in zip(stubs[::2], stubs[1::2]):
            if a == b or graph.has_edge(a, b) or (a < motif_size and b < motif_size):
                break
            graph.add_edge(a, b)
        else:
            if nx.is_biconnected(graph):
                return graph
    return None


@lru_cache(maxsize=1)
def certified_bank():
    """Offline-verified cubic graphs: bounded fallback, no density change."""
    path = Path(__file__).with_name('regular_bank.json')
    return json.loads(path.read_text(encoding='utf-8'))


def regular_fallback(total, target, rng):
    rows = certified_bank()[str(total)][target]
    record = rng.choice(rows)
    graph = nx.Graph()
    graph.add_nodes_from(range(total))
    graph.add_edges_from(record['edges'])
    return graph, frozenset(record['solution'])


@dataclass
class Puzzle:
    graph: nx.Graph
    target: str
    solution: frozenset
    view: dict
    diagnostics: dict


def generate_puzzle(level='easy', target=None, family=None, seed=None, budget_ms=150, attempts=5):
    rng = random.Random(seed)
    target = target or rng.choice(['triangle', 'square'] if level == 'easy' else list(MOTIFS))
    motif = motif_graph(target)
    total, degree = LEVELS[level]
    family = family or 'regular'
    start = time.perf_counter()
    fallback = True
    solution = frozenset(motif)
    for _ in range(attempts):
        remaining = budget_ms - (time.perf_counter() - start) * 1000
        if remaining <= 0:
            break
        if family == 'regular':
            graph = planted_regular(total, motif, rng)
            if graph is None:
                continue
        else:
            graph = background(total, family, degree, rng)
            graph.remove_edges_from(list(graph.subgraph(motif.nodes()).edges()))
            graph.add_edges_from(motif.edges())
            if not nx.is_biconnected(graph):
                continue
        remaining = budget_ms - (time.perf_counter() - start) * 1000
        try:
            copies = occurrences(graph, motif, remaining)
        except SearchBudgetExceeded:
            break
        if len(copies) == 1:
            fallback = False
            break
    if fallback:
        graph, solution = regular_fallback(total, target, rng)
    search_ms = (time.perf_counter() - start) * 1000
    permutation = list(range(total))
    rng.shuffle(permutation)
    graph = nx.relabel_nodes(graph, dict(enumerate(permutation)))
    solution = frozenset(permutation[i] for i in solution)
    positions = coordinates(graph, rng, {'easy': .15, 'medium': .15, 'hard': .2}[level])
    if level == 'easy':
        # Restore full depth and increase the spacing relative to node radii.
        # All nodes are treated alike; the motif receives no special placement.
        positions = {node: [x * 1.5, y * 1.5, z * 2.2]
                     for node, (x, y, z) in positions.items()}
    # Cosmetic identities are independent of the solution and stored with each
    # snapshot. These cubic graphs do not encode chemical valence or molecules.
    elements = (['C', 'C', 'O', 'H', 'N'] * (total // 5 + 1))[:total]
    rng.shuffle(elements)
    view = {'nodes': [{'id': i, 'element': element, 'x': positions[i][0], 'y': positions[i][1], 'z': positions[i][2]} for i, element in zip(sorted(graph), elements)],
            'links': [{'source': a, 'target': b} for a, b in graph.edges()], 'motif': motif_view(target)}
    return Puzzle(graph, target, solution, view, {'family': family, 'fallback': fallback, 'search_ms': round(search_ms, 3)})
