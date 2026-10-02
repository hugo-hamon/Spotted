"""Run from repo root: .venv/bin/python -m project.benchmarks.benchmark."""
import csv
from pathlib import Path
import statistics
import time
import networkx as nx
from project.src.utils.graph import generate_puzzle, occurrences, motif_graph, SearchBudgetExceeded, LEVELS


def main():
    rows=[]
    for level,n in [(level, size) for level, (size, _) in LEVELS.items()]:
        for family in ['regular','erdos','blocks']:
            samples=[]; search=[]; fallback=0
            for seed in range(20):
                start=time.perf_counter()
                puzzle=generate_puzzle(level,family=family,seed=seed)
                samples.append((time.perf_counter()-start)*1000)
                search.append(puzzle.diagnostics['search_ms'])
                fallback+=puzzle.diagnostics['fallback']
            rows.append(dict(case=family,nodes=n,samples=20,median_ms=round(statistics.median(samples),2),max_ms=round(max(samples),2),search_max_ms=round(max(search),2),fallbacks=fallback))
    for n in [20,40,80,120]:
        # Large biconnected bipartite blocks contain no odd cycle: deliberately
        # expensive negative instance, unlike dense graphs with quick matches.
        graph=nx.complete_bipartite_graph(n//2,n-n//2)
        start=time.perf_counter(); exceeded=False
        try: occurrences(graph,motif_graph('pentagon'),150)
        except SearchBudgetExceeded: exceeded=True
        elapsed=round((time.perf_counter()-start)*1000,2)
        rows.append(dict(case='bipartite_stress',nodes=n,samples=1,median_ms=elapsed,max_ms=elapsed,search_max_ms=elapsed,fallbacks=int(exceeded)))
    path=Path(__file__).with_name('results.csv')
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    for row in rows: print(row)

if __name__=='__main__': main()
