/* Native desktop Figma Plugin API helpers. No network, file writes or auto-run. */
async function loadNeulis(figma, texts = []) {
  const styles = ['Regular', 'Medium', 'Bold'];
  const available = await figma.listAvailableFontsAsync();
  for (const style of styles) {
    if (!available.some(f => f.fontName.family === 'Neulis Alt' && f.fontName.style === style)) {
      throw new Error('Neulis Alt unavailable in this environment: ' + style);
    }
  }
  const current = texts.flatMap(t => t.getStyledTextSegments(['fontName']).map(s => s.fontName));
  for (const font of current) {
    if (font.family !== 'Neulis Alt' || !styles.includes(font.style)) {
      throw new Error('Unexpected source font; inspect source before editing');
    }
  }
  for (const style of styles) await figma.loadFontAsync({ family: 'Neulis Alt', style });
  return { environment: 'figma-desktop', loaded_styles: styles,
    missing_fonts: texts.some(t => t.hasMissingFont), evidence: 'loadFontAsync succeeded: ' + new Date().toISOString() };
}

async function setText(figma, node, value, rule, width) {
  if (node.type !== 'TEXT' || !Number.isFinite(width) || width <= 0) throw new Error('TEXT and fixed width required');
  if (!['Regular', 'Medium', 'Bold'].includes(rule.font_style)) throw new Error('Unsupported Neulis style');
  for (const s of node.getStyledTextSegments(['fontName'])) await figma.loadFontAsync(s.fontName);
  await figma.loadFontAsync({ family: 'Neulis Alt', style: rule.font_style });
  node.fontName = { family: 'Neulis Alt', style: rule.font_style };
  node.fontSize = rule.font_size;
  node.lineHeight = { unit: 'PERCENT', value: rule.line_height_percent || 150 };
  node.paragraphSpacing = 0;
  node.characters = value;
  node.resize(width, Math.max(1, node.height));
  // resize can reset HEIGHT: this assignment deliberately comes last.
  node.textAutoResize = 'HEIGHT';
  if (node.parent && node.parent.layoutMode && node.parent.layoutMode !== 'NONE' && node.layoutPositioning !== 'ABSOLUTE') {
    node.layoutSizingVertical = 'HUG';
  }
  node.visible = true; // Ancestors must still be inspected separately.
  return node.id;
}

function replaceContent(sourceRoot, copyRoot, oldContent, newContent, protectedIds = []) {
  if (sourceRoot === copyRoot || sourceRoot.id === copyRoot.id) throw new Error('Original source cannot be edited');
  if (oldContent === copyRoot || oldContent.parent !== copyRoot || oldContent.type !== 'FRAME') {
    throw new Error('Expected a dedicated content FRAME; direct TEXT children use setText');
  }
  const descendants = [oldContent, ...oldContent.findAll(() => true)].map(n => n.id);
  if (protectedIds.some(id => descendants.includes(id))) throw new Error('Content contains protected header or logo');
  const index = copyRoot.children.indexOf(oldContent);
  copyRoot.insertChild(index, newContent);
  oldContent.remove();
  return { createdNodeIds: [newContent.id, ...newContent.findAll(() => true).map(n => n.id)], removedNodeIds: descendants };
}

function fixPosterSize(poster) {
  poster.resize(700, 937);
  poster.layoutSizingVertical = 'FIXED';
  poster.primaryAxisSizingMode = 'FIXED';
}

function captureFrame(frame, roles, fontCheck) {
  const origin = frame.absoluteBoundingBox;
  const relative = node => {
    const b = node.absoluteBoundingBox;
    if (!b || !origin) return null;
    return { x: b.x - origin.x, y: b.y - origin.y, width: b.width, height: b.height };
  };
  const visible = node => {
    for (let n = node; n && n.type !== 'DOCUMENT'; n = n.parent) {
      if (n.visible === false || n.opacity === 0) return false;
    }
    return true;
  };
  const inside = (a, b) => a && b && b.x >= a.x - .5 && b.y >= a.y - .5 &&
    b.x + b.width <= a.x + a.width + .5 && b.y + b.height <= a.y + a.height + .5;
  const clipped = node => {
    for (let p = node.parent; p && p.type !== 'DOCUMENT'; p = p.parent) {
      if (p.clipsContent && !inside(p.absoluteBoundingBox, node.absoluteBoundingBox)) return true;
    }
    return false;
  };
  const children = frame.findAll(() => true);
  const all = new Map([frame, ...children].map(n => [n.id, n]));
  const texts = children.filter(n => n.type === 'TEXT');
  const inventory = texts.map(t => ({ node_id: t.id, text: t.characters, effective_visible: visible(t),
    missing_font: t.hasMissingFont, clipped: clipped(t), bounds: relative(t), auto_resize: t.textAutoResize,
    paragraph_spacing: t.paragraphSpacing,
    font_runs: t.getStyledTextSegments(['fontName', 'fontSize', 'lineHeight']).map(s => ({
      family: s.fontName.family, style: s.fontName.style, font_size: s.fontSize,
      line_height_px: s.lineHeight.unit === 'PIXELS' ? s.lineHeight.value :
        s.lineHeight.unit === 'PERCENT' ? s.fontSize * s.lineHeight.value / 100 : null
    })) }));
  const slots = {};
  for (const [key, id] of Object.entries(roles.slots)) {
    const n = inventory.find(t => t.node_id === id);
    if (!n) throw new Error('Missing slot ' + key);
    const run = n.font_runs[0];
    const uniform = n.font_runs.every(r => r.font_size === run.font_size && r.line_height_px === run.line_height_px);
    const lines = uniform && n.auto_resize === 'HEIGHT' && n.paragraph_spacing === 0 && run.line_height_px
      ? Math.round(n.bounds.height / run.line_height_px) : null;
    slots[key] = { node_id: id, lines, family: run.family, style: run.style,
      overflow: n.clipped || !inside({x:0,y:0,width:frame.width,height:frame.height}, n.bounds) };
  }
  const node = id => { if (!all.has(id)) throw new Error('Role outside target frame: ' + id); return all.get(id); };
  const logo = node(roles.logo);
  const result = { node_id: frame.id, inspected_at: new Date().toISOString(), evidence: roles.evidence,
    layout: roles.layout, canvas: {x:0,y:0,width:frame.width,height:frame.height},
    overflow: inventory.some(t => t.clipped || !inside({x:0,y:0,width:frame.width,height:frame.height},t.bounds)),
    font_check: fontCheck, font_runs: inventory.flatMap(t => t.font_runs), text_node_count: inventory.length,
    text_nodes: inventory, slots, header: roles.header,
    logo: {node_id:logo.id,effective_visible:visible(logo),bounds:relative(logo)},
    elements: (roles.elements || []).map(e => { const n=node(e.container_node_id); return {...e,bounds:relative(n),effective_visible:visible(n),
      ...(e.artwork_node_id ? {artwork_visible:visible(node(e.artwork_node_id)),artwork_bounds:relative(node(e.artwork_node_id))} : {})}; }) };
  if (roles.asset) {
    const n = node(roles.asset.node_id);
    result.asset = { node_id: n.id, bounds: relative(n), effective_visible: visible(n), clipped: clipped(n),
      ref: roles.asset.ref, source_ref: roles.asset.source_ref };
  }
  if (roles.content) result.content_bounds = relative(node(roles.content));
  if (roles.poster) { const n=node(roles.poster); result.poster_bounds=relative(n);result.poster_size_mode=n.layoutSizingVertical; }
  // Do not fabricate visual_review. Add it only after looking at the final screenshot.
  return result;
}
if (typeof module !== 'undefined') module.exports = {loadNeulis,setText,replaceContent,fixPosterSize,captureFrame};
