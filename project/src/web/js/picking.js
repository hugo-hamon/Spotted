/** Pick from the event coordinates, not the renderer's throttled hover cache. */
export function installPicking(element, graph, {select, undo, hover}) {
  const pointers = new Map();
  const canvas = graph.renderer().domElement;
  let hovered = null;

  function pick(event) {
    const box = canvas.getBoundingClientRect();
    const x = (event.clientX - box.left) * graph.width() / box.width;
    const y = (event.clientY - box.top) * graph.height() / box.height;
    if (x < 0 || y < 0 || x > graph.width() || y > graph.height()) return null;
    const camera = graph.camera();
    camera.updateMatrixWorld();
    const projectionScale = graph.height() / (2 * Math.tan(camera.fov * Math.PI / 360));
    const hits = [];
    for (const node of graph.graphData().nodes) {
      const position = camera.position.clone().set(node.x, node.y, node.z).applyMatrix4(camera.matrixWorldInverse);
      const depth = -position.z;
      if (depth <= camera.near || depth >= camera.far) continue;
      const p = graph.graph2ScreenCoords(node.x, node.y, node.z);
      const value = graph.nodeVal();
      const radius = graph.nodeRelSize() * Math.cbrt(typeof value === 'function' ? value(node) : value) * projectionScale / depth;
      const distance = Math.hypot(p.x - x, p.y - y);
      const tolerance = Math.max(event.pointerType === 'touch' ? 24 : 18, radius + 6);
      if (distance <= tolerance) hits.push({id: node.id, depth, distance, inside: distance <= radius});
    }
    // A visible sphere wins over another node's enlarged hit area. For actual
    // overlaps choose the front sphere; otherwise choose the nearest centre.
    hits.sort((a, b) => Number(b.inside) - Number(a.inside)
      || (a.inside && b.inside ? a.depth - b.depth : a.distance - b.distance));
    return hits[0]?.id ?? null;
  }

  function showHover(id) {
    if (hovered === id) return;
    hovered = id;
    canvas.style.cursor = id === null ? 'grab' : 'pointer';
    hover(id);
  }

  element.addEventListener('pointerdown', event => {
    if (event.button === 2) {
      // Right click is undo, so it must not also pan the camera.
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    if (event.button !== 0) return;
    const gesture = {x: event.clientX, y: event.clientY, node: pick(event), nodes: graph.graphData().nodes, dragged: false};
    pointers.set(event.pointerId, gesture);
    if (pointers.size > 1) pointers.forEach(p => { p.dragged = true; });
  }, true);

  window.addEventListener('pointermove', event => {
    const gesture = pointers.get(event.pointerId);
    if (!gesture) return;
    if (Math.hypot(event.clientX - gesture.x, event.clientY - gesture.y) > 7) gesture.dragged = true;
  }, true);

  element.addEventListener('pointermove', event => {
    if (!pointers.size) showHover(pick(event));
  });
  element.addEventListener('pointerleave', () => showHover(null));

  window.addEventListener('pointerup', event => {
    const gesture = pointers.get(event.pointerId);
    pointers.delete(event.pointerId);
    if (!gesture || event.button !== 0 || gesture.nodes !== graph.graphData().nodes) return;
    const moved = Math.hypot(event.clientX - gesture.x, event.clientY - gesture.y);
    if (!gesture.dragged && moved <= 7 && gesture.node !== null) select(gesture.node);
    showHover(null);
  }, true);
  window.addEventListener('pointercancel', event => {
    pointers.delete(event.pointerId);
    showHover(null);
  }, true);
  element.addEventListener('wheel', () => pointers.forEach(p => { p.dragged = true; }), {passive: true});
  element.addEventListener('contextmenu', event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    // A touch long-press may also produce this event: don't select on release.
    pointers.forEach(p => { p.dragged = true; });
    undo();
  }, true);
}
