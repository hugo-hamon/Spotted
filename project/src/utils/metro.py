"""Planar metro maps with one certified motif and varied decoy loops."""
import random
import math
from itertools import combinations
import networkx as nx

STATIONS = ['Gare', 'Musée', 'Jardin', 'Université', 'Marché', 'Mairie', 'Opéra',
            'Bibliothèque', 'Stade', 'Hôpital', 'Port', 'Château', 'École', 'Parc',
            'Place', 'Théâtre', 'Piscine', 'Palais', 'Arènes', 'Les Halles']

def _turn(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def _on_segment(a, b, p):
    return abs(_turn(a,b,p)) < 1e-7 and min(a[0],b[0])-1e-7 <= p[0] <= max(a[0],b[0])+1e-7 and min(a[1],b[1])-1e-7 <= p[1] <= max(a[1],b[1])+1e-7


def _clear_segment(graph, pos, u, v):
    """A straight track may neither cross a track nor pass through a station."""
    a,b = pos[u],pos[v]
    if any(_on_segment(a,b,pos[n]) for n in graph if n not in (u,v)):
        return False
    for c,d in graph.edges:
        if len({u,v,c,d}) < 4:
            continue
        c,d = pos[c],pos[d]
        if _turn(a,b,c)*_turn(a,b,d) < 0 and _turn(c,d,a)*_turn(c,d,b) < 0:
            return False
    return True


def metro_occurrences(graph, target):
    """Exact induced motifs using NetworkX's bounded chordless-cycle search.

    A house is a chordless square plus a roof adjacent to exactly two consecutive
    square vertices. Vertex sets deduplicate all rotations and reflections.
    This avoids running general VF2 for every tentative track change.
    """
    from .graph import EXTENDED_PORTS
    if target in EXTENDED_PORTS:
        return _extended_occurrences(graph, target)
    size = {'triangle':3, 'square':4, 'pentagon':5, 'house':4}[target]
    found = set()
    for cycle in nx.chordless_cycles(graph,length_bound=size):
        if len(cycle) != size:
            continue
        square = set(cycle)
        if target != 'house':
            found.add(frozenset(cycle))
        else:
            for a,b in zip(cycle,cycle[1:]+cycle[:1]):
                for roof in (set(graph[a]) & set(graph[b])) - square:
                    if not (set(graph[roof]) & (square-{a,b})):
                        found.add(frozenset(square | {roof}))
                        if len(found)>=2:
                            return found
        if len(found)>=2:
            return found
    return found


def _extended_occurrences(graph, target):
    """Exact triangle-based candidates; check every required and absent edge."""
    neighbors = {n: set(graph[n]) for n in graph}
    found = set()
    if target == 'wheel':
        for center in graph:
            for rim in combinations(neighbors[center], 4):
                # Four vertices of internal degree two form an induced square.
                if all(len(neighbors[n] & set(rim)) == 2 for n in rim):
                    found.add(frozenset((*rim, center)))
                    if len(found) == 2:
                        return found
        return found
    for triangle in nx.chordless_cycles(graph, length_bound=3):
        triangle = set(triangle)
        outside = set().union(*(neighbors[n] for n in triangle)) - triangle
        for n in outside:
            touching = neighbors[n] & triangle
            if target == 'pendant_triangle' and len(touching) == 1:
                found.add(frozenset(triangle | {n}))
            elif target in ('diamond', 'pendant_diamond') and len(touching) == 2:
                diamond = triangle | {n}
                if target == 'diamond':
                    found.add(frozenset(diamond))
                else:
                    for tip in diamond:
                        if len(neighbors[tip] & diamond) != 2:
                            continue
                        for tail in neighbors[tip] - diamond:
                            if neighbors[tail] & diamond == {tip}:
                                found.add(frozenset(diamond | {tail}))
                                if len(found) >= 2:
                                    return found
            elif target == 'bowtie' and len(touching) == 1:
                center = next(iter(touching))
                for wing in (neighbors[n] & neighbors[center]) - triangle:
                    if neighbors[wing] & triangle == {center}:
                        found.add(frozenset(triangle | {n, wing}))
                        if len(found) >= 2:
                            return found
            if len(found) >= 2:
                return found
    return found


def _plant_extended(graph, pos, corners, target, x, y, rng):
    from .graph import MOTIFS, EXTENDED_PORTS
    # Fit a planar drawing inside a random cell. Rotate its outer attachment
    # towards that cell's top-left corner, so the joining track cannot cross it.
    _, edges, points = MOTIFS[target]
    port = EXTENDED_PORTS[target]
    angle = -3 * math.pi / 4 - math.atan2(points[port][1], points[port][0])
    cosine, sine = math.cos(angle), math.sin(angle)
    ids = {}
    for n, (px, py) in enumerate(points):
        ids[n] = len(pos)
        pos[ids[n]] = [x*100 + 50 + 20*(px*cosine-py*sine),
                       y*100 + 50 + 20*(px*sine+py*cosine), 0]
    for a, b in edges:
        graph.add_edge(ids[a], ids[b], line=rng.randrange(4))
    graph.add_edge(corners[x,y], ids[port], line=y % 4)
    return set(ids.values())


def _diversify(graph, pos, solution, target, level, rng):
    """Shortcuts and diagonals create decoys, never a second exact answer.

    Each trial is checked before commitment. Fixed attempt counts keep work
    bounded; rejecting a candidate leaves the last certified map intact.
    """
    def unique(candidate):
        return metro_occurrences(candidate,target) == {frozenset(solution)}

    # Vary the number of stations around each loop, instead of repeating eight
    # stations around every rectangular cell. Larger levels vary more corridors.
    candidates = [n for n in graph if n not in solution and graph.degree(n)==2]
    rng.shuffle(candidates)
    for n in candidates[:round(len(candidates)*(.5 if level=='medium' else .8))]:
        if graph.degree(n)!=2:
            continue
        a,b = list(graph[n])
        if graph.has_edge(a,b):
            continue
        trial = graph.copy(); line = graph[n][a]['line']; trial.remove_node(n)
        if not _clear_segment(trial,pos,a,b):
            continue
        trial.add_edge(a,b,line=line)
        if unique(trial):
            graph = trial

    # Random planar chords mix triangles, quadrilaterals and longer loops.
    # Collinear extra stations make some visual triangles false friends.
    from itertools import combinations
    candidates = [(a,b) for a,b in combinations(graph,2) if not graph.has_edge(a,b)
                  and not {a,b} <= solution and 45 < math.dist(pos[a],pos[b]) < 180]
    rng.shuffle(candidates)
    added = 0
    for a,b in candidates[:240]:
        if graph.degree(a)>=5 or graph.degree(b)>=5 or not _clear_segment(graph,pos,a,b):
            continue
        trial = graph.copy()
        # Extend a neighbouring line, rather than marking every decoy with a
        # special colour. The target receives no distinct styling in Libre.
        trial.add_edge(a,b,line=rng.choice([data['line'] for _,_,data in graph.edges(a,data=True)]))
        if unique(trial):
            graph = trial; added += 1
            if added >= (7 if level=='medium' else 16):
                break
    return graph, unique


def _finish_decoys(graph, pos, solution, target, level, rng, regions=None):
    """Keep several actual loop sizes after inserting the extra stations."""
    from itertools import combinations
    forbidden = {'triangle':3,'square':4,'pentagon':5}.get(target)
    for size in [3,4,5,6]:
        if size == forbidden or any(len(c)==size for c in nx.chordless_cycles(graph,length_bound=size)):
            continue
        candidates = [(a,b) for a,b in combinations(graph,2) if not graph.has_edge(a,b)
                      and not {a,b} <= solution and graph.degree(a)<5 and graph.degree(b)<5
                      and not (regions and a in regions and b in regions and regions[a] == regions[b])
                      and math.dist(pos[a],pos[b])<180 and nx.shortest_path_length(graph,a,b)==size-1]
        rng.shuffle(candidates)
        for a,b in candidates[:100]:
            if not _clear_segment(graph,pos,a,b):
                continue
            trial = graph.copy()
            trial.add_edge(a,b,line=rng.choice([d['line'] for _,_,d in graph.edges(a,data=True)]))
            if metro_occurrences(trial,target)=={frozenset(solution)}:
                graph=trial
                break
    return graph


def _vary_positions(graph, pos, level, rng):
    """Bend and skew all stations alike, preserving a crossing-free drawing."""
    if level=='easy':
        return
    amplitude = 12 if level=='medium' else 22
    order = list(graph); rng.shuffle(order)
    for n in order:
        original = pos[n]
        for _ in range(4):
            pos[n] = [original[0]+rng.uniform(-amplitude,amplitude), original[1]+rng.uniform(-amplitude,amplitude),0]
            if min(math.dist(pos[n],pos[v]) for v in graph if v!=n) >= 22 and all(_clear_segment(graph,pos,n,v) for v in graph[n]):
                break
        else:
            pos[n] = original
    # A small affine shear breaks the last regular rows without adding crossings.
    shear = rng.uniform(-.16,.16)
    for n in graph:
        pos[n][0] += shear * pos[n][1]


def generate_metro(level, target=None, seed=None):
    from .graph import MOTIFS, EXTENDED_PORTS
    rng = random.Random(seed)
    target = target or rng.choice(['triangle', 'square'] if level == 'easy' else list(MOTIFS))
    if target in EXTENDED_PORTS and level != 'easy':
        from .camouflage import camouflaged_network
        graph, pos, solution, unique, regions = camouflaged_network(level, target, rng)
        return _complete_map(graph,pos,solution,target,level,rng,unique,regions)
    width, height = {'easy': (3, 2), 'medium': (5, 3), 'hard': (6, 4)}[level]
    extended = target in EXTENDED_PORTS
    if extended:
        width, height = {'easy': (2, 2), 'medium': (5, 3), 'hard': (5, 4)}[level]
    graph = nx.Graph()
    pos = {}
    def node(x, y):
        i = len(pos)
        pos[i] = [x*100, y*100, 0]
        graph.add_node(i)
        return i
    corners = {(x,y): node(x,y) for y in range(height) for x in range(width)}
    mids = {}
    for (x,y), a in corners.items():
        for dx,dy in [(1,0),(0,1)]:
            if (x+dx,y+dy) not in corners:
                continue
            b = corners[x+dx,y+dy]
            m = node(x+dx/2,y+dy/2)
            line = y % 4 if dx else (x+2) % 4
            graph.add_edge(a,m,line=line); graph.add_edge(m,b,line=line)
            mids[frozenset((a,b))] = m
    x, y = rng.randrange(width-1), rng.randrange(height-1)
    if extended:
        if level == 'easy':
            # Leave enough room for five motif stations within the 12-node map.
            (u,v), m = next((tuple(edge), mid) for edge, mid in mids.items())
            line = graph[u][m]['line']
            graph.remove_node(m)
            graph.add_edge(u,v,line=line)
        solution = _plant_extended(graph,pos,corners,target,x,y,rng)
    else:
        solution = _plant_cycle(graph,pos,corners,mids,target,x,y)
    unique = (lambda candidate: metro_occurrences(candidate,target) == {frozenset(solution)}) if extended else None
    if level != 'easy':
        graph, unique = _diversify(graph,pos,solution,target,level,rng)
    return _complete_map(graph,pos,solution,target,level,rng,unique)


def _plant_cycle(graph, pos, corners, mids, target, x, y):
    a,b,c,d = [corners[p] for p in [(x,y),(x+1,y),(x+1,y+1),(x,y+1)]]
    # Straight grid corridors become the selected cell's short cycle. All
    # other faces retain at least six edges, so cannot copy the target.
    roof = mids[frozenset((c,d))]
    for u,v in [(a,b),(b,c),(c,d),(d,a)]:
        m = mids[frozenset((u,v))]
        if m == roof and target in ('house','pentagon'):
            pos[m][1] += 30
            continue
        line = graph[u][m]['line']
        graph.remove_node(m)
        graph.add_edge(u,v,line=line)
    solution = {a,b,c,d}
    if target == 'triangle':
        pos[a] = [(pos[a][0]+pos[b][0])/2, pos[a][1], 0]
        for v, attrs in list(graph[b].items()):
            if v != a:
                graph.add_edge(a,v,**attrs)
        graph.remove_node(b)
        solution.remove(b)
    elif target in ('pentagon','house'):
        solution.add(roof)
        if target == 'house':
            graph.add_edge(c,d,line=y % 4)
    return solution


def _complete_map(graph, pos, solution, target, level, rng, unique, regions=None):
    from .graph import Puzzle, LEVELS, EXTENDED_PORTS, motif_view
    # Fill to the same difficulty sizes with stations along existing corridors.
    # With decoys, a subdivision can create another target: certify it first.
    rejected_subdivisions = set()
    while len(graph) < LEVELS[level][0]:
        edges = [(u,v) for u,v in graph.edges if not {u,v} <= solution
                 and not (regions and u in regions and v in regions and regions[u] == regions[v])
                 and frozenset((u,v)) not in rejected_subdivisions]
        rng.shuffle(edges)
        edges.sort(key=lambda e: math.dist(pos[e[0]],pos[e[1]]),reverse=True)
        for u,v in edges:
            if math.dist(pos[u],pos[v]) < (0 if target in EXTENDED_PORTS else 45):
                continue
            m = len(pos)
            trial = graph.copy(); line = graph[u][v]['line']
            trial.remove_edge(u,v)
            trial.add_edge(u,m,line=line); trial.add_edge(m,v,line=line)
            if unique is None or unique(trial):
                pos[m] = [(pos[u][k]+pos[v][k])/2 for k in range(3)]
                graph = trial
                break
            rejected_subdivisions.add(frozenset((u,v)))
        else:
            if target in EXTENDED_PORTS:
                raise ValueError('Aucune subdivision ne conserve le motif unique.')
            # A terminus cannot belong to any biconnected motif. This always
            # completes the requested size if every subdivision is ambiguous.
            u = min(graph,key=lambda n:pos[n][0]); m = len(pos)
            pos[m] = [pos[u][0]-45,pos[u][1],0]
            graph.add_edge(u,m,line=graph.edges[next(iter(graph.edges(u)))]['line'])
    if level != 'easy':
        graph = _finish_decoys(graph,pos,solution,target,level,rng,regions)
    _vary_positions(graph,pos,level,rng)
    if not nx.check_planarity(graph)[0] or metro_occurrences(graph,target) != {frozenset(solution)}:
        raise ValueError('Le plan de métro ne possède pas un motif unique.')
    ids = list(range(len(graph))); rng.shuffle(ids)
    mapping = dict(zip(sorted(graph), ids))
    graph = nx.relabel_nodes(graph, mapping)
    # Reflect the entire map, keeping straight edges and the planar embedding.
    sx, sy = rng.choice([-1,1]), rng.choice([-1,1])
    # Use the wide play area instead of squeezing a square network into its
    # centre. This affine transform treats every region alike and is planar.
    aspect = {'medium': 1.25, 'hard': 1.75}.get(level, 1) if target in EXTENDED_PORTS else 1
    positions = {mapping[n]: [p[0]*sx*aspect, p[1]*sy, 0] for n,p in pos.items() if n in mapping}
    solution = frozenset(mapping[n] for n in solution)
    nodes = [{'id': i, 'element': ['C','O','H','N'][i%4],
              'station': STATIONS[i%len(STATIONS)] + (f' {i//len(STATIONS)+1}' if i>=len(STATIONS) else ''),
              'x': positions[i][0], 'y': positions[i][1], 'z': 0} for i in sorted(graph)]
    view = {'skin': 'metro', 'nodes': nodes,
            'links': [{'source': a, 'target': b, 'line': data['line']} for a,b,data in graph.edges(data=True)],
            'motif': motif_view(target)}
    return Puzzle(graph, target, solution, view, {'family':'metro', 'fallback':False})
