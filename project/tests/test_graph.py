import unittest
import math
from itertools import combinations
import networkx as nx
from project.src.utils.graph import MOTIFS, LEVELS, CUBIC_MOTIFS, EXTENDED_PORTS, generate_puzzle, occurrences, motif_graph, SearchBudgetExceeded, certified_bank


class GraphTests(unittest.TestCase):
    def test_metro_planarity_geometry_uniqueness_and_sizes(self):
        from project.src.utils.metro import generate_metro
        def orient(a,b,c):
            return (b['x']-a['x'])*(c['y']-a['y'])-(b['y']-a['y'])*(c['x']-a['x'])
        def on_segment(a,b,c):
            return abs(orient(a,b,c)) < 1e-7 and min(a['x'],b['x'])<=c['x']<=max(a['x'],b['x']) and min(a['y'],b['y'])<=c['y']<=max(a['y'],b['y'])
        for level in LEVELS:
            for target in MOTIFS:
                for seed in range(6):
                    with self.subTest(level=level,target=target,seed=seed):
                        p = generate_metro(level,target,seed)
                        self.assertTrue(nx.check_planarity(p.graph)[0])
                        self.assertTrue(nx.is_connected(p.graph))
                        self.assertEqual(len(p.graph),LEVELS[level][0])
                        self.assertTrue(all(n['z']==0 and n['station'] for n in p.view['nodes']))
                        matcher = nx.algorithms.isomorphism.GraphMatcher(p.graph,motif_graph(target))
                        self.assertEqual({frozenset(m) for m in matcher.subgraph_isomorphisms_iter()}, {p.solution})
                        if level != 'easy':
                            loop_sizes = {len(c) for c in nx.chordless_cycles(p.graph,length_bound=7)}
                            self.assertGreaterEqual(len(loop_sizes),3)
                        pos = {n['id']:n for n in p.view['nodes']}
                        for (a,b),(c,d) in combinations(p.graph.edges,2):
                            if len({a,b,c,d}) < 4: continue
                            a,b,c,d = [pos[i] for i in (a,b,c,d)]
                            self.assertFalse(orient(a,b,c)*orient(a,b,d)<0 and orient(c,d,a)*orient(c,d,b)<0)
                            self.assertFalse(any((on_segment(a,b,c),on_segment(a,b,d),on_segment(c,d,a),on_segment(c,d,b))))


    def test_metro_cycle_search_agrees_with_independent_vf2(self):
        from project.src.utils.metro import metro_occurrences
        for seed in range(20):
            graph = nx.gnp_random_graph(9,.35,seed=seed)
            for target in MOTIFS:
                matcher = nx.algorithms.isomorphism.GraphMatcher(graph,motif_graph(target))
                expected = {frozenset(m) for m in matcher.subgraph_isomorphisms_iter()}
                actual = metro_occurrences(graph,target)
                self.assertEqual(len(actual),min(2,len(expected)))
                self.assertLessEqual(actual,expected)

    def test_unique_connected_puzzles_all_families_levels_and_motifs(self):
        for level in LEVELS:
            for target in MOTIFS:
                for family in ['regular', 'erdos', 'blocks']:
                    with self.subTest(level=level, target=target, family=family):
                        puzzle = generate_puzzle(level, target, family, seed=17, budget_ms=30)
                        self.assertTrue(nx.is_connected(puzzle.graph))
                        self.assertEqual(len(puzzle.graph), LEVELS[level][0])
                        # Independent full VF2 matcher, deduplicating automorphisms.
                        matcher = nx.algorithms.isomorphism.GraphMatcher(puzzle.graph, motif_graph(target))
                        copies = {frozenset(m) for m in matcher.subgraph_isomorphisms_iter()}
                        self.assertEqual(copies, {puzzle.solution})
                        self.assertEqual(len(puzzle.view['nodes']),len(puzzle.graph))
                        self.assertEqual({n['element'] for n in puzzle.view['nodes']}, {'C','O','H','N'})
                        if target in CUBIC_MOTIFS:
                            self.assertTrue(nx.is_biconnected(puzzle.graph))
                            if family == 'regular' or puzzle.diagnostics['fallback']:
                                self.assertEqual({d for _, d in puzzle.graph.degree()}, {3})
                                self.assertEqual(puzzle.graph.number_of_edges(), len(puzzle.graph) * 3 // 2)

    def test_requested_motifs_have_exact_edges_and_complete_previews(self):
        requested = [
            [(0,1),(0,2),(1,2),(2,3)],
            [(0,1),(0,2),(0,3),(1,3),(2,3)],
            [(0,1),(0,2),(1,2),(2,3),(2,4),(3,4)],
            [(0,1),(0,2),(0,4),(1,4),(1,3),(2,4),(2,3),(3,4)],
            [(0,1),(0,2),(1,2),(1,3),(2,3),(3,4)],
        ]
        for key, edges in zip(EXTENDED_PORTS, requested):
            self.assertEqual(MOTIFS[key][1], edges)
            self.assertEqual(set(motif_graph(key)), set(range(len(MOTIFS[key][2]))))

    def test_extended_fallback_all_sizes_and_seeds(self):
        import random
        from project.src.utils.graph import extended_fallback
        for total, _ in LEVELS.values():
            for target in EXTENDED_PORTS:
                for seed in range(12):
                    # Medium/hard now share the same camouflaged fallback
                    # across families; each family is exercised above too.
                    for family in (('regular', 'erdos', 'blocks') if total == 12 else ('regular',)):
                        graph, solution = extended_fallback(total,target,family,random.Random(seed))
                        self.assertTrue(nx.is_connected(graph))
                        self.assertEqual(len(graph),total)
                        matcher = nx.algorithms.isomorphism.GraphMatcher(graph,motif_graph(target))
                        self.assertEqual({frozenset(m) for m in matcher.subgraph_isomorphisms_iter()}, {solution})

    def test_extended_motifs_have_disjoint_lookalikes_at_similar_scale(self):
        from statistics import median
        from project.src.utils.metro import generate_metro
        for target in EXTENDED_PORTS:
            motif = motif_graph(target)
            patterns = []
            for a,b in motif.edges:
                missing = motif.copy(); missing.remove_edge(a,b)
                if nx.is_connected(missing):
                    patterns.append(missing)
                divided = motif.copy(); divided.remove_edge(a,b)
                divided.add_edges_from([(a,len(motif)),(len(motif),b)])
                patterns.append(divided)
            for level in ('medium','hard'):
                for seed in (3,7,11):
                    with self.subTest(target=target,level=level,seed=seed):
                        p = generate_metro(level,target,seed)
                        # Count independent, disjoint near matches in the final
                        # graph, without relying on generator region metadata.
                        used = set(p.solution)
                        decoys = 0
                        for pattern in patterns:
                            matcher = nx.algorithms.isomorphism.GraphMatcher(p.graph.subgraph(set(p.graph)-used),pattern)
                            for mapping in matcher.subgraph_isomorphisms_iter():
                                if not used.intersection(mapping):
                                    used.update(mapping)
                                    decoys += 1
                        self.assertGreaterEqual(decoys,2 if level == 'medium' else 4)
                        pos = {n['id']:(n['x'],n['y']) for n in p.view['nodes']}
                        inside = [math.dist(pos[a],pos[b]) for a,b in p.graph.edges if {a,b} <= p.solution]
                        outside = [math.dist(pos[a],pos[b]) for a,b in p.graph.edges if not {a,b} <= p.solution]
                        self.assertGreater(median(inside)/median(outside),.55)
                        self.assertLessEqual(p.graph.number_of_edges(),len(p.graph)*2)

    def test_pendant_decoys_can_be_connected_without_an_extra_answer(self):
        from project.src.utils.metro import generate_metro
        for level, seed in [('medium',19),('hard',119),('hard',3530265750)]:
            p = generate_metro(level,'pendant_diamond',seed)
            self.assertTrue(nx.is_connected(p.graph))
            matcher = nx.algorithms.isomorphism.GraphMatcher(p.graph,motif_graph(p.target))
            self.assertEqual({frozenset(m) for m in matcher.subgraph_isomorphisms_iter()},{p.solution})

    def test_entire_fallback_bank_with_independent_matcher(self):
        for total, motifs in certified_bank().items():
            for target, rows in motifs.items():
                self.assertEqual(len(rows), 8)
                for index, row in enumerate(rows):
                    with self.subTest(total=total, target=target, index=index):
                        graph = nx.Graph(row['edges'])
                        self.assertEqual(len(graph), int(total))
                        self.assertEqual({d for _, d in graph.degree()}, {3})
                        self.assertTrue(nx.is_biconnected(graph))
                        matcher = nx.algorithms.isomorphism.GraphMatcher(graph, motif_graph(target))
                        copies = {frozenset(m) for m in matcher.subgraph_isomorphisms_iter()}
                        self.assertEqual(copies, {frozenset(row['solution'])})


    def test_easy_is_small_and_only_offers_simple_motifs(self):
        for seed in range(12):
            puzzle = generate_puzzle('easy', seed=seed)
            self.assertEqual(len(puzzle.graph), 12)
            self.assertEqual(puzzle.graph.number_of_edges(), 18)
            self.assertIn(puzzle.target, ('triangle', 'square'))
            nodes = puzzle.view['nodes']
            depth = max(n['z'] for n in nodes) - min(n['z'] for n in nodes)
            width = max(n['x'] for n in nodes) - min(n['x'] for n in nodes)
            self.assertGreater(depth, width * .3)
            self.assertGreater(min(math.dist([a[k] for k in ('x', 'y', 'z')], [b[k] for k in ('x', 'y', 'z')])
                                   for a, b in combinations(nodes, 2)), 20)

    def test_automorphisms_and_induced_semantics(self):
        triangle = nx.cycle_graph(3)
        self.assertEqual(len(occurrences(triangle, triangle)), 1)
        self.assertEqual(len(occurrences(nx.complete_graph(4), triangle)), 2)
        self.assertEqual(occurrences(nx.complete_graph(4), nx.cycle_graph(4)), [])

    def test_block_optimization_agrees_with_exhaustive(self):
        for seed in range(5):
            graph = nx.gnp_random_graph(9,.3,seed=seed)
            for key in MOTIFS:
                motif = motif_graph(key)
                brute = {frozenset(nodes) for nodes in combinations(graph,len(motif)) if nx.is_isomorphic(graph.subgraph(nodes),motif)}
                found = occurrences(graph,motif,1000)
                self.assertEqual(len(found),min(2,len(brute)))
                self.assertTrue(set(found)<=brute)

    def test_budget_never_accepts_unchecked_candidate(self):
        with self.assertRaises(SearchBudgetExceeded):
            occurrences(nx.complete_graph(20), motif_graph('pentagon'), 0)
        for target in MOTIFS:
            puzzle = generate_puzzle('hard',target,seed=42,budget_ms=0)
            self.assertTrue(puzzle.diagnostics['fallback'])
            self.assertEqual(occurrences(puzzle.graph,motif_graph(target)), [puzzle.solution])

    def test_reproducible_generation_and_coordinates(self):
        a=generate_puzzle(seed=123,budget_ms=0)
        b=generate_puzzle(seed=123,budget_ms=0)
        self.assertEqual(a.view,b.view)
        self.assertTrue(all(abs(node[axis])<1000 for node in a.view['nodes'] for axis in ('x','y','z')))


if __name__ == '__main__':
    unittest.main()
