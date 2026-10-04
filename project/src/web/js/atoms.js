import { drawMetro } from './metro.js';
// An illustrative atom skin, not a chemically valid molecular model.
export const ATOMS = {
  C: {name: 'Carbone', color: '#475569'},
  O: {name: 'Oxygène', color: '#e94d5d'},
  H: {name: 'Hydrogène', color: '#f5f5f5'},
  N: {name: 'Azote', color: '#497ae6'},
};
const symbols = Object.keys(ATOMS);
export function atomSymbol(node) {
  return Object.hasOwn(ATOMS, node.element) ? node.element : symbols[node.id % symbols.length];
}
export function atomColor(node) { return ATOMS[atomSymbol(node)].color; }
const layers = new WeakMap();

/** Billboard symbols on the existing spheres, without another WebGL library.
 * Projection and hit testing use the same radius. Front spheres occlude labels
 * behind them. The overlay follows rotation, zoom, resizing and theme changes.
 */
export function installAtomLabels(graph, element, options = {}) {
  const canvas = document.createElement('canvas');
  canvas.className = 'atom-labels';
  canvas.setAttribute('aria-hidden', 'true');
  element.append(canvas);
  const ctx = canvas.getContext('2d');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let request;
  function draw() {
    const width = graph.width(), height = graph.height(), ratio = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const camera = graph.camera();
    camera.updateMatrixWorld();
    const scale = height / (2 * Math.tan(camera.fov * Math.PI / 360));
    const nodes = graph.graphData().nodes.map(node => {
      const depth = -camera.position.clone().set(node.x, node.y, node.z).applyMatrix4(camera.matrixWorldInverse).z;
      const p = graph.graph2ScreenCoords(node.x, node.y, node.z);
      const value = graph.nodeVal();
      const radius = graph.nodeRelSize() * Math.cbrt(typeof value === 'function' ? value(node) : value) * scale / depth;
      return {...p, depth, radius, node};
    }).filter(p => p.depth > camera.near && p.depth < camera.far && p.x >= 0 && p.x <= width && p.y >= 0 && p.y <= height)
      .sort((a, b) => a.depth - b.depth);
    const metro = options.skin?.() === 'metro';
    canvas.dataset.skin = metro ? 'metro' : 'atoms';
    if (metro) {
      drawMetro(ctx, graph, options, reducedMotion.matches);
      request = requestAnimationFrame(draw);
      return;
    }
    nodes.forEach((p, index) => {
      if (p.radius < 5 || nodes.slice(0, index).some(front => (options.opacity?.(front.node) ?? 1) > .5 && Math.hypot(front.x-p.x, front.y-p.y) < front.radius + p.radius * .3)) return;
      ctx.globalAlpha = options.opacity?.(p.node) ?? 1;
      if (options.hinted?.(p.node)) {
        ctx.beginPath(); ctx.arc(p.x, p.y, p.radius+5, 0, Math.PI*2);
        ctx.strokeStyle = '#e6a323'; ctx.lineWidth = 3; ctx.stroke();
      }
      const color = graph.nodeColor();
      const fill = typeof color === 'function' ? color(p.node) : color;
      // Bright selected/hovered atoms and hydrogen need dark lettering.
      const rgb = /^#[0-9a-f]{6}$/i.test(fill) ? [1,3,5].map(i => parseInt(fill.slice(i,i+2),16)) : [0,0,0];
      const brightness = rgb[0]*.299 + rgb[1]*.587 + rgb[2]*.114;
      if (metro) {
        ctx.beginPath(); ctx.arc(p.x, p.y, p.radius*.73, 0, Math.PI*2);
        ctx.fillStyle = '#ffffff'; ctx.fill();
      }
      ctx.font = `700 ${Math.max(9, Math.min(32, p.radius * (metro ? .85 : 1.1)))}px system-ui, sans-serif`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = metro || brightness > 150 ? '#17212d' : '#ffffff';
      ctx.fillText(metro ? String(p.node.id+1) : atomSymbol(p.node), p.x, p.y);
      ctx.globalAlpha = 1;
    });
    request = requestAnimationFrame(draw);
  }
  request = requestAnimationFrame(draw);
  layers.set(graph, () => { cancelAnimationFrame(request); canvas.remove(); });
}
export function removeAtomLabels(graph) {
  layers.get(graph)?.(); layers.delete(graph);
}
