// Draws a {label, lines, children} tree as SVG, root on the left and leaves stacked down the right.
function drawTree(root) {
  const NS = 'http://www.w3.org/2000/svg';
  const ROW = 26, COL = 185, PAD = 12;
  let nextRow = 0;
  let maxDepth = 0;

  function place(node, depth) {
    maxDepth = Math.max(maxDepth, depth);
    const kids = node.children.map((child) => place(child, depth + 1));
    const y = kids.length ? (kids[0].y + kids[kids.length - 1].y) / 2 : nextRow++ * ROW;
    return { node, kids, x: depth * COL, y };
  }

  const laidOut = place(root, 0);
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('width', (maxDepth + 1) * COL + PAD * 2);
  svg.setAttribute('height', nextRow * ROW + PAD * 2);
  svg.classList.add('tree');

  function svgEl(tag, attrs, text) {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text) node.textContent = text;
    svg.appendChild(node);
    return node;
  }

  function draw(item) {
    const x = item.x + PAD, y = item.y + PAD + ROW / 2;
    for (const kid of item.kids) {
      const kx = kid.x + PAD, ky = kid.y + PAD + ROW / 2;
      const mid = (x + COL - 20 + kx) / 2;
      svgEl('path', { d: `M${x + COL - 20},${y} C${mid},${y} ${mid},${ky} ${kx},${ky}`, class: 'edge' });
    }
    const leaf = item.kids.length === 0;
    svgEl('rect', { x, y: y - 10, width: COL - 20, height: 20, rx: 5, class: leaf ? 'node leaf' : 'node' });
    svgEl('text', { x: x + 8, y: y + 4 }, item.node.label);
    item.kids.forEach(draw);
  }

  draw(laidOut);
  return svg;
}
