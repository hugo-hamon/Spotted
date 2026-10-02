import unittest
import math
from itertools import combinations
import networkx as nx
from project.src.utils.graph import MOTIFS, LEVELS, generate_puzzle, occurrences, motif_graph, SearchBudgetExceeded, certified_bank


class GraphTests(unittest.TestCase):
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
                        self.assertTrue(nx.is_biconnected(puzzle.graph))
                        if family == 'regular' or puzzle.diagnostics['fallback']:
                            self.assertEqual({d for _, d in puzzle.graph.degree()}, {3})
                            self.assertEqual(puzzle.graph.number_of_edges(), len(puzzle.graph) * 3 // 2)

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
