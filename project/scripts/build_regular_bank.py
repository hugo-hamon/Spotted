"""Rebuild the certified fallback bank. Run as a module from the repo root."""
import json
from pathlib import Path
import random
from project.src.utils.graph import LEVELS, CUBIC_MOTIFS, motif_graph, planted_regular, occurrences, SearchBudgetExceeded


def main():
    rng = random.Random(20261002)
    bank = {}
    for total, _ in LEVELS.values():
        bank[str(total)] = {}
        for target in CUBIC_MOTIFS:
            motif = motif_graph(target)
            records = []
            tried = 0
            while len(records) < 8:
                tried += 1
                if tried > 5000:
                    raise RuntimeError(f'No certified bank for {total}/{target}')
                graph = planted_regular(total, motif, rng)
                if graph is None:
                    continue
                try:
                    copies = occurrences(graph, motif, budget_ms=2000, max_candidates=1000000)
                except SearchBudgetExceeded:
                    continue
                if len(copies) == 1:
                    records.append({'edges': sorted([sorted(edge) for edge in graph.edges()]), 'solution': sorted(copies[0])})
            bank[str(total)][target] = records
            print(total, target, '8 certified graphs;', tried, 'candidates', flush=True)
    path = Path(__file__).resolve().parents[1] / 'src/utils/regular_bank.json'
    path.write_text(json.dumps(bank, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
