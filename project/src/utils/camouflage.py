"""Build a network from a target and similarly sized, almost-matching regions."""
from itertools import combinations
import math

import networkx as nx


def camouflaged_network(level, target, rng):
    from .graph import MOTIFS, motif_graph
    from .metro import _clear_segment, metro_occurrences

    # Subdivisions keep the silhouette; missing links keep the point count.
    # Filter variants exactly: subdividing a pendant edge can still contain the
    # original motif, and must never be used as a decoy.
    def variants(key):
        base = motif_graph(key)
        points = {i: [x, y] for i, (x, y) in enumerate(MOTIFS[key][2])}
        result = []
        for a, b in base.edges:
            graph = base.copy()
            graph.remove_edge(a, b)
            if nx.is_connected(graph) and not metro_occurrences(graph, target):
                result.append((graph, points))
            graph = base.copy()
            n = len(graph)
            graph.remove_edge(a, b)
            graph.add_edges_from([(a, n), (n, b)])
            if not metro_occurrences(graph, target):
                pos = {**points, n: [(points[a][k]+points[b][k])/2 for k in range(2)]}
                result.append((graph, pos))
        return result

    close = variants(target)
    other = [variant for key in MOTIFS if key != target for variant in variants(key)]
    # A closed diamond is not a diamond-with-tail on its own, but connecting
    # one of its tips immediately creates that target. Such isolated decoys
    # cannot safely become part of the network. Exclude the offending core.
    core = {'pendant_triangle': 'triangle', 'pendant_diamond': 'diamond'}.get(target)
    if core:
        other = [(graph, points) for graph, points in other if not metro_occurrences(graph, core)]
    columns, rows = (3, 2) if level == 'medium' else (3, 3)
    count = columns * rows
    answer_region = rng.randrange(count)
    # Most regions are close decoys; a few different shapes avoid an identical
    # repeated tile pattern. All receive the same scale and transformations.
    alternatives = set(rng.sample([i for i in range(count) if i != answer_region], 1 if level == 'medium' else 2))
    graph, positions, regions = nx.Graph(), {}, {}
    for region in range(count):
        if region == answer_region:
            local = motif_graph(target)
            points = dict(enumerate(MOTIFS[target][2]))
        else:
            local, points = rng.choice(other if region in alternatives else close)
        angle = rng.randrange(4) * math.pi / 2
        cosine, sine = math.cos(angle), math.sin(angle)
        xs, ys = zip(*points.values())
        cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
        scale = 145 / max(max(xs)-min(xs), max(ys)-min(ys))
        mapping = {}
        for node, (x, y) in points.items():
            n = len(positions)
            mapping[node] = n
            x, y = (x-cx)*scale, (y-cy)*scale
            positions[n] = [region % columns * 220 + x*cosine-y*sine,
                            region // columns * 220 + x*sine+y*cosine, 0]
            regions[n] = region
        graph.add_edges_from((mapping[a], mapping[b], {'line': region % 4}) for a, b in local.edges)
        if region == answer_region:
            solution = frozenset(mapping.values())

    def unique(candidate):
        return metro_occurrences(candidate, target) == {solution}

    def connect(a, b):
        if graph.degree(a) >= 5 or graph.degree(b) >= 5 or not _clear_segment(graph, positions, a, b):
            return False
        graph.add_edge(a, b, line=rng.randrange(4))
        if unique(graph):
            return True
        graph.remove_edge(a, b)
        return False

    pairs = [(a, b) for a, b in combinations(graph, 2) if regions[a] != regions[b]]
    # A little variation avoids always attaching the same tips. Long tracks are
    # considered only when closer attachments would make a second solution.
    pairs.sort(key=lambda e: math.dist(positions[e[0]], positions[e[1]]) * rng.uniform(.85, 1.15))
    components = nx.utils.UnionFind(graph)
    for a, b in graph.edges:
        components.union(a, b)
    for a, b in pairs:
        if components[a] != components[b] and connect(a, b):
            components.union(a, b)
    if not nx.is_connected(graph):
        raise ValueError('Les régions du plan ne peuvent pas être reliées.')

    # Multiple routes integrate the answer in the network and create distractor
    # junctions. Do not inflate density merely to make the puzzle harder.
    added = 0
    for a, b in pairs:
        if graph.has_edge(a, b) or math.dist(positions[a], positions[b]) > 310:
            continue
        if connect(a, b):
            added += 1
            if added >= count * 2:
                break
    return graph, positions, solution, unique, regions
