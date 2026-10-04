export const METRO_COLORS = ['#b458c8', '#3485bd', '#db7541', '#2b9c80'];

/** Flat, screen-space metro symbols; the shared camera supplies pan and zoom. */
export function drawMetro(ctx, graph, options, reducedMotion) {
  const data = graph.graphData(), width = graph.width(), height = graph.height();
  const dark = document.documentElement.dataset.theme === 'dark';
  const ink = dark ? '#f0e8f7' : '#342d40';
  const nodes = new Map(data.nodes.map(n => [n.id, {...graph.graph2ScreenCoords(n.x,n.y,0), node:n}]));
  const endpoint = n => typeof n === 'object' ? n.id : n;
  const colorOf = (accessor, datum) => typeof accessor === 'function' ? accessor(datum) : accessor;
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const tracks = [];
  for (const link of data.links) {
    const a = nodes.get(endpoint(link.source)), b = nodes.get(endpoint(link.target));
    if (!a || !b) continue;
    ctx.strokeStyle = colorOf(graph.linkColor(), link);
    ctx.lineWidth = colorOf(graph.linkWidth(), link) > 3 ? 6 : 4;
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
    tracks.push({a,b,link});
  }
  if (options.animate?.() !== false) tracks.filter((_,i)=>i%5===0).slice(0,8).forEach(({a,b},i) => {
    const progress = ((reducedMotion ? 0 : performance.now()/7000)+i*.31)%2;
    const t = progress>1 ? 2-progress : progress;
    const x = a.x+(b.x-a.x)*t, y = a.y+(b.y-a.y)*t;
    if ([...nodes.values()].some(n=>Math.hypot(n.x-x,n.y-y)<23)) return;
    ctx.save(); ctx.translate(x,y); ctx.rotate(Math.atan2(b.y-a.y,b.x-a.x));
    ctx.fillStyle = '#ffdb75'; ctx.strokeStyle = '#60472d'; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.roundRect(-12,-5,24,10,3); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#374966'; ctx.fillRect(-7,-3,4,6); ctx.fillRect(1,-3,4,6);
    ctx.restore();
  });
  const labels = [];
  for (const {x,y,node} of nodes.values()) {
    if (x < -30 || y < -30 || x > width+30 || y > height+30) continue;
    const opacity = options.opacity?.(node) ?? 1;
    ctx.globalAlpha = opacity;
    const fill = colorOf(graph.nodeColor(),node);
    // A little station sign: rounded tile, M symbol, and entrance steps.
    ctx.fillStyle = dark ? '#2b2435' : '#fff';
    ctx.strokeStyle = /^#/.test(fill) ? fill : ink; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.roundRect(x-11,y-11,22,22,5); ctx.fill(); ctx.stroke();
    ctx.fillStyle = ctx.strokeStyle; ctx.font = '800 14px system-ui';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('M',x,y);
    ctx.beginPath(); ctx.moveTo(x-6,y+13); ctx.lineTo(x+6,y+13); ctx.stroke();
    if (options.hinted?.(node)) {
      ctx.strokeStyle = '#e6a323'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.roundRect(x-16,y-16,32,32,8); ctx.stroke();
    }
    // Names on a metro plan are more recognisable than numbered spheres. Avoid
    // covering another station or a previously placed name on smaller screens.
    ctx.font = '600 11px system-ui'; ctx.textAlign = 'left';
    const name = node.station || `Station ${node.id+1}`, w = ctx.measureText(name).width;
    const placements = [[x+17,y-8],[x+17,y+18],[x-w-17,y-8],[x-w/2,y-24]];
    const position = placements.find(([tx,ty])=> tx>2 && tx+w<width-2 && ty>10 && ty<height-10
      && ![...nodes.values()].some(n=> n.node.id!==node.id && n.x>tx-15 && n.x<tx+w+15 && Math.abs(n.y-ty)<20)
      && !labels.some(r=>tx<r.x+r.w+4 && tx+w+4>r.x && Math.abs(ty-r.y)<16));
    if (position) {
      const [tx,ty] = position; labels.push({x:tx,y:ty,w});
      ctx.lineWidth = 4; ctx.strokeStyle = graph.backgroundColor(); ctx.strokeText(name,tx,ty);
      ctx.fillStyle = ink; ctx.fillText(name,tx,ty);
    }
    ctx.globalAlpha = 1;
  }
}
