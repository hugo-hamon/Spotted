import { installPicking } from './picking.js';
const $ = id => document.getElementById(id);
function readPalette() {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(['scene', 'node', 'selected', 'edge', 'hover'].map(key => [key, style.getPropertyValue(`--graph-${key}`).trim()]));
}
let palette = readPalette();
let GREEN = palette.selected, PURPLE = palette.node;
const labels = {easy: 'Facile', medium: 'Moyen', hard: 'Difficile'};
const selected = new Set();
let state = null, puzzle = null, graph, busy = false, deadline = null, duration = 120, records = [], hovered = null, replayGraph = null;
let activeMode = 'free', activeLevel = 'easy';
let replaySelected = new Set();
const seconds = n => `${Number(n).toFixed(1).replace('.', ',')} s`;
const endpoint = x => typeof x === 'object' ? x.id : x;
const selectedLink = l => selected.has(endpoint(l.source)) && selected.has(endpoint(l.target));
// Fit projected positions, rather than a bounding sphere that leaves wide margins.
function frameGraph(view = graph) {
  const nodes = view.graphData().nodes;
  if (!nodes.length) return;
  const bounds = ['x', 'y', 'z'].map(axis => [Math.min(...nodes.map(n => n[axis])), Math.max(...nodes.map(n => n[axis]))]);
  const [x, y, z] = bounds.map(([low, high]) => (low + high) / 2);
  const vertical = Math.tan(view.camera().fov * Math.PI / 360);
  const horizontal = vertical * view.width() / view.height();
  const distance = Math.max(...nodes.map(n => n.z - z + Math.max(
    (Math.abs(n.x - x) + 7) / (horizontal * .87),
    (Math.abs(n.y - y) + 7) / (vertical * .86)
  )));
  view.controls().reset();
  view.camera().up.set(0, 1, 0);
  view.cameraPosition({x, y, z: z + distance}, {x, y, z}, 0);
  view.controls().update();
}

async function api(name, ...args) {
  const response = await Promise.race([eel[`eel_${name}`](...args)(), new Promise((_, reject) => setTimeout(() => reject(new Error('Connexion interrompue. Réessaie ou recharge la page.')), 15000))]);
  if (response?.error) throw new Error(response.error);
  return response;
}
function status(message, success = false) { $('status').textContent = message; $('status').classList.toggle('success', success); }
async function action(fn) {
  if (busy) return;
  busy = true; controls();
  try { await fn(); } catch (error) { status(error.message); }
  finally { busy = false; $('loading').hidden = true; controls(); }
}
function controls() {
  const locked = busy || !state || state.finished;
  $('validate').hidden = activeMode === 'timed';
  $('validate').disabled = locked || state?.solved || selected.size !== puzzle?.motif.points.length;
  $('clear').disabled = locked || state?.solved || selected.size === 0;
  $('next').disabled = locked;
  $('next').textContent = state?.solved ? 'Suivant' : activeMode === 'timed' ? 'Passer (−10 s)' : 'Nouveau';
  $('finish').disabled = locked;
  $('start').disabled = busy;
  const timed = state && !state.finished && activeMode === 'timed';
  $('mode').disabled = busy || timed;
  $('level').disabled = busy || timed;
  $('start').disabled = busy || timed;
  $('save-form').querySelector('button').disabled = busy;
  $('replay').disabled = busy;
}
function svgMarkup(points, edges, highlight = null, width = 180, height = 150) {
  const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
  const minX = Math.min(...xs), minY = Math.min(...ys), dx = Math.max(...xs) - minX || 1, dy = Math.max(...ys) - minY || 1;
  const scale = Math.min((width - 36) / dx, (height - 36) / dy);
  const xy = points.map(([x,y]) => [(width - dx * scale) / 2 + (x-minX)*scale, (height-dy*scale)/2+(y-minY)*scale]);
  const lines = edges.map(([a,b]) => `<line x1="${xy[a][0]}" y1="${xy[a][1]}" x2="${xy[b][0]}" y2="${xy[b][1]}" stroke="${highlight ? highlight.has(a) && highlight.has(b) ? GREEN : palette.edge : PURPLE}" stroke-width="${highlight ? 2 : 4}"/>`).join('');
  const dots = xy.map(([x,y],i) => `<circle cx="${x}" cy="${y}" r="${highlight ? highlight.has(i) ? 5 : 3 : 7}" fill="${highlight?.has(i) ? GREEN : PURPLE}"/>`).join('');
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${highlight ? 'Motif trouvé en vert dans le graphe' : 'Dessin du motif à trouver'}">${lines}${dots}</svg>`;
}
function createGraph(element) {
  const renderer = ForceGraph3D()(element).backgroundColor(palette.scene).showNavInfo(false).nodeLabel(n => `Point ${n.id+1}`)
    .nodeRelSize(4.2).nodeVal(1.2).nodeResolution(16).nodeOpacity(1).linkOpacity(.65).linkWidth(1.3)
    .enableNodeDrag(false).cooldownTicks(0);
  renderer.controls().staticMoving = true;
  return renderer;
}
function fixedData(view) { return {nodes: view.nodes.map(n => ({...n, fx:n.x, fy:n.y, fz:n.z})), links: view.links.map(l => ({...l}))}; }
function paint() {
  graph.nodeColor(n => n.id === hovered ? palette.hover : selected.has(n.id) ? GREEN : PURPLE)
    .linkColor(l => selectedLink(l) ? GREEN : palette.edge).linkWidth(l => selectedLink(l) ? 3.5 : 1.2);
  $('selection').textContent = `${selected.size} / ${puzzle?.motif.points.length || 0} points sélectionnés`;
  controls();
}
function toggle(id) {
  if (busy || !state || state.finished || state.solved) return;
  if (selected.has(id)) selected.delete(id);
  else if (selected.size < puzzle.motif.points.length) selected.add(id);
  else { status('Désélectionne un point pour en choisir un autre.'); return; }
  paint(); status('');
  if (activeMode === 'timed' && selected.size === puzzle.motif.points.length) action(validateSelection);
}
function undoSelection() {
  if (busy || !state || state.finished || state.solved || !selected.size) return;
  selected.delete([...selected].at(-1));
  paint(); status('');
}
function apply(response) {
  state = response;
  $('score').textContent = state.score;
  $('plural').textContent = state.score > 1 ? 's' : '';
  deadline = state.remaining === null ? null : performance.now() + state.remaining * 1000;
  if (response.puzzle && !state.finished) {
    puzzle = response.puzzle; selected.clear(); hovered = null;
    graph.nodeRelSize(activeLevel === 'easy' ? 5.5 : 4.2).graphData(fixedData(puzzle));
    graph.cameraPosition({x:0,y:0,z:420}, {x:0,y:0,z:0}, 0);
    requestAnimationFrame(() => frameGraph(graph));
    $('motif').innerHTML = svgMarkup(puzzle.motif.points, puzzle.motif.edges);
    $('motif-name').textContent = puzzle.motif.name;
    $('motif-count').textContent = `${puzzle.motif.points.length} points · ${puzzle.motif.edges.length} liens`;
    status('');
  }
  paint(); tick();
}
async function start() {
  $('result').close(); $('loading').hidden = false;
  const mode = $('mode').value, level = $('level').value;
  const result = await api('start', mode, level);
  activeMode = mode; activeLevel = level;
  apply(result); renderRecords();
}
async function finish() {
  if (!state) return;
  const response = await api('finish', state.session);
  apply(response);
  $('result-title').textContent = state.score ? `${state.score} motif${state.score > 1 ? 's' : ''} repéré${state.score > 1 ? 's' : ''} !` : 'Aucun motif trouvé';
  $('result-text').textContent = state.score ? `Meilleur temps : ${seconds(response.best_seconds)}` : '';
  $('save-form').hidden = !state.score; $('name').value = ''; $('save-status').textContent = '';
  if (!$('result').open) $('result').showModal();
  status('Partie terminée.');
}
function tick() {
  const left = deadline === null ? null : Math.max(0, Math.ceil((deadline - performance.now()) / 1000));
  $('timer').textContent = left === null ? '∞' : `${Math.floor(left/60)}:${String(left%60).padStart(2,'0')}`;
  $('timer').classList.toggle('urgent', left !== null && left <= 15);
  if (left === 0 && state && !state.finished && !busy) action(finish);
}
function element(tag, text, className) { const el = document.createElement(tag); el.textContent = text; if (className) el.className = className; return el; }
function renderRecords() {
  const level = $('level').value;
  const ranked = records.filter(r => r.mode === 'timed' && r.level === level && r.duration === duration)
    .sort((a,b) => b.score-a.score || a.best.seconds-b.best.seconds).slice(0,10);
  $('ranking-label').textContent = `${labels[level]} · ${duration} s · Top 10`;
  $('scores').replaceChildren();
  if (!ranked.length) $('scores').append(element('div', 'Aucun score enregistré.', 'empty'));
  ranked.forEach((r,i) => {
    const row = element('div', '', 'ranking-row');
    row.append(element('span', String(i+1).padStart(2,'0'), 'rank'), element('strong',r.name), element('span',`${r.score} motif${r.score>1?'s':''}`), element('small', `Record : ${seconds(r.best.seconds)}`));
    $('scores').append(row);
  });
  $('gallery').replaceChildren();
  if (!records.length) $('gallery').append(element('div', 'Aucune partie enregistrée.', 'empty'));
  [...records].reverse().slice(0,30).forEach(r => {
    const best = r.best, view = best.puzzle;
    const card = element('button', '', 'card');
    // Saved nodes are sorted by id; remap anyway so imported records stay coherent.
    const indices = new Map(view.nodes.map((n,i) => [n.id,i]));
    card.innerHTML = svgMarkup(view.nodes.map(n=>[n.x,n.y]), view.links.map(l=>[indices.get(l.source),indices.get(l.target)]), new Set(best.selected.map(id=>indices.get(id))), 300,170);
    const body = element('div','','card-body'), name = element('strong',r.name);
    name.append(element('small',`${view.motif.name} · ${labels[r.level]} · ${r.mode === 'timed' ? 'Chrono' : 'Découverte'}`));
    body.append(name, element('span',seconds(best.seconds),'card-time')); card.append(body);
    card.onclick = () => openReplay(r); $('gallery').append(card);
  });
}
async function refreshRecords() { records = await api('records'); renderRecords(); }
function openReplay(record) {
  $('replay-title').textContent = `${record.name} · ${record.best.puzzle.motif.name} en ${seconds(record.best.seconds)}`;
  $('replay-dialog').showModal();
  if (replayGraph) replayGraph._destructor();
  const chosen = new Set(record.best.selected);
  replaySelected = chosen;
  replayGraph = createGraph($('replay-graph')).nodeColor(n=>chosen.has(n.id)?GREEN:PURPLE)
    .linkColor(l=>chosen.has(endpoint(l.source))&&chosen.has(endpoint(l.target))?GREEN:palette.edge)
    .linkWidth(l=>chosen.has(endpoint(l.source))&&chosen.has(endpoint(l.target))?3.5:1)
    .width($('replay-graph').clientWidth).height($('replay-graph').clientHeight).graphData(fixedData(record.best.puzzle));
  requestAnimationFrame(()=>frameGraph(replayGraph));
}
function updateTheme(theme, remember = false) {
  document.documentElement.dataset.theme = theme;
  if (remember) {
    try { localStorage.setItem('spotted-theme', theme); } catch (_) { /* preference lasts for this page */ }
  }
  palette = readPalette();
  GREEN = palette.selected; PURPLE = palette.node;
  $('theme-toggle').textContent = theme === 'dark' ? '☀ Mode clair' : '☾ Mode sombre';
  $('theme-toggle').setAttribute('aria-pressed', String(theme === 'dark'));
  document.querySelector('meta[name="theme-color"]').content = palette.scene;
  if (graph) {
    graph.backgroundColor(palette.scene);
    if (puzzle) {
      paint();
      $('motif').innerHTML = svgMarkup(puzzle.motif.points, puzzle.motif.edges);
    }
  }
  if (replayGraph) {
    replayGraph.backgroundColor(palette.scene)
      .nodeColor(n => replaySelected.has(n.id) ? GREEN : PURPLE)
      .linkColor(l => replaySelected.has(endpoint(l.source)) && replaySelected.has(endpoint(l.target)) ? GREEN : palette.edge);
  }
  renderRecords();
}
$('theme-toggle').onclick = () => updateTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', true);
updateTheme(document.documentElement.dataset.theme);

$('replay-dialog').addEventListener('close',()=>{ if(replayGraph){replayGraph._destructor(); replayGraph=null;} });
$('close-replay').onclick = () => $('replay-dialog').close();
$('close-result').onclick = () => $('result').close();
$('start').onclick = () => action(start);
$('replay').onclick = () => action(start);
$('clear').onclick = () => { selected.clear(); paint(); status(''); };
$('next').onclick = () => action(async()=>{ $('loading').hidden=false; apply(await api('next',state.session,state.round)); if(state.finished) await finish(); });
async function validateSelection() {
  const result = await api('validate', state.session, state.round, [...selected]);
  apply(result);
  if (result.finished) {
    await finish();
  } else if (result.correct) {
    if (activeMode === 'timed') {
      apply(await api('next', state.session, state.round));
      if (state.finished) { await finish(); return; }
    }
    status(`Repéré en ${seconds(result.seconds)}.`, true);
  } else {
    status(result.message || 'Ce motif a déjà été trouvé.');
  }
}
$('validate').onclick = () => action(validateSelection);
$('finish').onclick = () => action(finish);
$('recenter').onclick = () => frameGraph(graph);
$('mode').onchange = () => { $('start').textContent = $('mode').value === 'timed' ? 'Démarrer' : 'Nouvelle partie'; };
$('level').onchange = renderRecords;
$('save-form').onsubmit = event => {
  event.preventDefault();
  action(async()=>{
    try {
      await api('save',state.session,$('name').value); $('save-form').hidden=true;
      $('save-status').textContent='Partie enregistrée.'; await refreshRecords();
    } catch(error) { $('save-status').textContent=error.message; }
  });
};
for(const tab of ['scores','gallery']) {
  $(`${tab}-tab`).onclick = ()=>{
    for(const name of ['scores','gallery']) { $(`${name}-tab`).setAttribute('aria-selected',name===tab); $(`${name}-panel`).hidden=name!==tab; }
  };
  $(`${tab}-tab`).onkeydown = event => {
    if(['ArrowLeft','ArrowRight'].includes(event.key)) { event.preventDefault(); const other=tab==='scores'?'gallery':'scores'; $(`${other}-tab`).click(); $(`${other}-tab`).focus(); }
  };
}
try {
  graph = createGraph($('graph-network')).enablePointerInteraction(false);
  installPicking($('graph-network'), graph, {
    select: toggle, undo: undoSelection,
    hover: id => { hovered = id; if (puzzle) paint(); }
  });
  const resize = () => {
    graph.width($('graph-network').clientWidth).height($('graph-network').clientHeight);
    if (puzzle) frameGraph();
    if (replayGraph) { replayGraph.width($('replay-graph').clientWidth).height($('replay-graph').clientHeight); frameGraph(replayGraph); }
  };
  new ResizeObserver(resize).observe($('graph-network')); window.addEventListener('resize',resize); resize();
  setInterval(tick,200);
  action(async()=>{ const settings=await api('settings'); duration=settings.duration; await start(); await refreshRecords(); });
} catch(error) { status(`Le rendu 3D n’a pas pu démarrer : ${error.message}. Vérifie que WebGL est activé dans le navigateur.`); }

// Renderer export for browser integration checks; solutions stay on the server.
export { graph };
