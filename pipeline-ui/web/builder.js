/* Pipeline builder — canvas, parameter inspector, run driver and result charts. */
(() => {
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const NODE_W = 250;

let CATALOG = {};          // type -> spec
let CATALOG_LIST = [];
let DEFAULT_GRAPH = null;
let SAMPLE_INFO = {};
let graph = { nodes: [], edges: [] };
let selectedId = null;
let seq = 0;
let currentRun = null;
let pollTimer = null;
let logCursor = 0;

/* ------------------------------------------------------------------ utils */
const uid = () => 'n' + (++seq);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const commas = n => (typeof n === 'number' ? n.toLocaleString() : n);

function fmtNum(v, d = 3) {
  const f = Number(v);
  if (!isFinite(f)) return '—';
  if (f !== 0 && (Math.abs(f) < 1e-3 || Math.abs(f) >= 1e5)) return f.toExponential(2);
  return f.toFixed(d);
}
function fmtBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(2) + ' MB';
}

/* ------------------------------------------------------------------- boot */
async function boot() {
  const res = await fetch('/api/catalog');
  const data = await res.json();
  CATALOG_LIST = data.nodes;
  CATALOG = Object.fromEntries(data.nodes.map(n => [n.type, n]));
  DEFAULT_GRAPH = data.default_graph;
  SAMPLE_INFO = data.sample_info || {};
  buildPalette();
  loadGraph(JSON.parse(JSON.stringify(DEFAULT_GRAPH)));
  wireChrome();
}

/* ---------------------------------------------------------------- palette */
function buildPalette() {
  const groups = {};
  CATALOG_LIST.forEach(n => (groups[n.group] = groups[n.group] || []).push(n));
  $('#palette-list').innerHTML = Object.entries(groups).map(([g, items]) => `
    <div class="pgroup"><h3>${esc(g)}</h3>
      ${items.map(n => `
        <div class="pitem" draggable="true" data-type="${n.type}">
          <div class="pchip" style="background:${n.color}">${esc(n.icon)}</div>
          <div><b>${esc(n.name)}</b><span>${esc(n.summary)}</span></div>
        </div>`).join('')}
    </div>`).join('');

  $$('.pitem').forEach(el => {
    el.addEventListener('dragstart', e => {
      e.dataTransfer.setData('text/plain', el.dataset.type);
      e.dataTransfer.effectAllowed = 'copy';
    });
    // Clicking is the quick path: drop the block below the selected one and wire it up.
    el.addEventListener('click', () => appendBlock(el.dataset.type));
  });
}

function appendBlock(type) {
  const from = graph.nodes.find(n => n.id === selectedId);
  let x = 40, y = 60;
  if (from) {
    x = from.x + 290;
    y = from.y;
    while (graph.nodes.some(n => Math.abs(n.x - x) < 40 && Math.abs(n.y - y) < 60)) y += 140;
  } else if (graph.nodes.length) {
    const last = graph.nodes[graph.nodes.length - 1];
    x = last.x; y = last.y + 140;
  }
  const node = addNode(type, x, y);
  if (from && CATALOG[from.type].outputs.length && CATALOG[type].inputs.length) {
    addEdge(from.id, node.id);
  }
  const el = $(`.node[data-id="${node.id}"]`);
  if (el) el.scrollIntoView({ block: 'nearest', inline: 'nearest' });
}

/* ------------------------------------------------------------------ graph */
function loadGraph(g) {
  graph = g;
  seq = 0;
  graph.nodes.forEach(n => {
    const m = /^n(\d+)$/.exec(n.id);
    if (m) seq = Math.max(seq, +m[1]);
    n.params = n.params || {};
  });
  selectedId = null;
  render();
  renderInspector();
}

function addNode(type, x, y) {
  const node = { id: uid(), type, x: Math.max(10, x), y: Math.max(10, y), params: {} };
  graph.nodes.push(node);
  selectedId = node.id;
  render();
  renderInspector();
  return node;
}

function removeNode(id) {
  graph.nodes = graph.nodes.filter(n => n.id !== id);
  graph.edges = graph.edges.filter(e => e.from !== id && e.to !== id);
  if (selectedId === id) selectedId = null;
  render();
  renderInspector();
}

function addEdge(from, to) {
  if (from === to) return;
  if (graph.edges.some(e => e.from === from && e.to === to)) return;
  graph.edges.push({ from, to });
  if (hasCycle()) { graph.edges.pop(); flash('That connection would create a loop.'); return; }
  render();
}

function hasCycle() {
  const adj = {}; graph.nodes.forEach(n => adj[n.id] = []);
  graph.edges.forEach(e => adj[e.from] && adj[e.from].push(e.to));
  const state = {};
  const walk = id => {
    if (state[id] === 1) return true;
    if (state[id] === 2) return false;
    state[id] = 1;
    for (const nxt of adj[id] || []) if (walk(nxt)) return true;
    state[id] = 2; return false;
  };
  return graph.nodes.some(n => walk(n.id));
}

function paramsOf(node) {
  const spec = CATALOG[node.type];
  const out = {};
  spec.params.forEach(p => out[p.key] = (node.params[p.key] !== undefined ? node.params[p.key] : p.default));
  return out;
}

/* ----------------------------------------------------------------- render */
function render() {
  const host = $('#nodes');
  host.innerHTML = graph.nodes.map(n => nodeHtml(n)).join('');
  $('#empty-hint').classList.toggle('hidden', graph.nodes.length > 0);
  $('#graph-summary').textContent =
    `${graph.nodes.length} block${graph.nodes.length === 1 ? '' : 's'}, ${graph.edges.length} connection${graph.edges.length === 1 ? '' : 's'}`;
  drawEdges();
  wireNodes();
}

function summaryPills(node) {
  const spec = CATALOG[node.type], p = paramsOf(node);
  const pick = spec.params.slice(0, 3);
  return pick.map(f => {
    let v = p[f.key];
    if (f.type === 'bool') v = v ? 'on' : 'off';
    if (Array.isArray(v)) v = v.length + ' selected';
    if (v === '' || v === null || v === undefined) v = '—';
    const short = String(v).length > 16 ? String(v).slice(0, 15) + '…' : v;
    return `<span class="pill">${esc(f.label)} <b>${esc(short)}</b></span>`;
  }).join('');
}

function nodeHtml(n) {
  const spec = CATALOG[n.type];
  if (!spec) return '';
  const sel = n.id === selectedId ? ' selected' : '';
  const st = (currentRun && currentRun.node_status && currentRun.node_status[n.id]) || '';
  return `<div class="node${sel} ${st}" data-id="${n.id}" style="left:${n.x}px;top:${n.y}px">
    ${spec.inputs.length ? `<div class="port in" data-id="${n.id}" data-dir="in" title="input"></div>` : ''}
    ${spec.outputs.length ? `<div class="port out" data-id="${n.id}" data-dir="out" title="drag to connect"></div>` : ''}
    <header style="background:${spec.color}">
      <span class="ic">${esc(spec.icon)}</span><b>${esc(spec.name)}</b>
      <span class="x" data-del="${n.id}" title="delete block">✕</span>
    </header>
    <div class="body">${esc(spec.summary)}<div class="pillrow">${summaryPills(n)}</div></div>
  </div>`;
}

function nodeBox(id) {
  const el = $(`.node[data-id="${id}"]`);
  const n = graph.nodes.find(x => x.id === id);
  if (!n) return null;
  return { x: n.x, y: n.y, w: NODE_W, h: el ? el.offsetHeight : 96 };
}

function drawEdges(live) {
  const svg = $('#edges');
  const paths = graph.edges.map((e, i) => {
    const a = nodeBox(e.from), b = nodeBox(e.to);
    if (!a || !b) return '';
    const x1 = a.x + a.w, y1 = a.y + 23, x2 = b.x, y2 = b.y + 23;
    const dx = Math.max(46, Math.abs(x2 - x1) * 0.45);
    const d = `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
    const flow = currentRun && currentRun.node_status &&
      currentRun.node_status[e.from] === 'done' ? ' flow' : '';
    return `<path class="${flow.trim()}" d="${d}"></path><path class="hit" data-edge="${i}" d="${d}"></path>`;
  }).join('');
  svg.innerHTML = paths + (live || '');
  $$('.edges path.hit').forEach(p => p.addEventListener('click', () => {
    graph.edges.splice(+p.dataset.edge, 1); render();
  }));
}

/* ----------------------------------------------------- canvas interaction */
function wireNodes() {
  $$('.node').forEach(el => {
    el.addEventListener('mousedown', e => {
      if (e.target.classList.contains('port') || e.target.dataset.del) return;
      selectedId = el.dataset.id;
      renderInspector();
      $$('.node').forEach(x => x.classList.toggle('selected', x === el));
      startDrag(e, el);
    });
  });
  $$('.node .x').forEach(x => x.addEventListener('click', e => {
    e.stopPropagation(); removeNode(x.dataset.del);
  }));
  $$('.port.out').forEach(p => p.addEventListener('mousedown', e => {
    e.stopPropagation(); startLink(e, p.dataset.id);
  }));
}

function startDrag(e, el) {
  const node = graph.nodes.find(n => n.id === el.dataset.id);
  const sx = e.clientX, sy = e.clientY, ox = node.x, oy = node.y;
  el.style.cursor = 'grabbing';
  const move = ev => {
    node.x = Math.max(6, ox + ev.clientX - sx);
    node.y = Math.max(6, oy + ev.clientY - sy);
    el.style.left = node.x + 'px'; el.style.top = node.y + 'px';
    drawEdges();
  };
  const up = () => {
    el.style.cursor = '';
    document.removeEventListener('mousemove', move);
    document.removeEventListener('mouseup', up);
  };
  document.addEventListener('mousemove', move);
  document.addEventListener('mouseup', up);
}

function startLink(e, fromId) {
  const canvas = $('#canvas');
  const a = nodeBox(fromId);
  const x1 = a.x + a.w, y1 = a.y + 23;
  $$('.port.out').forEach(p => p.classList.toggle('armed', p.dataset.id === fromId));

  const move = ev => {
    const r = canvas.getBoundingClientRect();
    const x2 = ev.clientX - r.left + canvas.scrollLeft;
    const y2 = ev.clientY - r.top + canvas.scrollTop;
    const dx = Math.max(40, Math.abs(x2 - x1) * 0.45);
    drawEdges(`<path class="live" d="M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}"></path>`);
  };
  const up = ev => {
    document.removeEventListener('mousemove', move);
    document.removeEventListener('mouseup', up);
    $$('.port.out').forEach(p => p.classList.remove('armed'));
    const target = document.elementFromPoint(ev.clientX, ev.clientY);
    const drop = target && (target.closest('.port.in') || target.closest('.node'));
    if (drop) {
      const toId = drop.dataset.id || drop.closest('.node').dataset.id;
      addEdge(fromId, toId);
    } else render();
  };
  document.addEventListener('mousemove', move);
  document.addEventListener('mouseup', up);
}

/* -------------------------------------------------------------- inspector */
function renderInspector() {
  const body = $('#inspector-body');
  const node = graph.nodes.find(n => n.id === selectedId);
  if (!node) {
    body.innerHTML = `<p class="hint">Select a block on the canvas to adjust its parameters.
      Every value here is live — change it and run again.</p>
      <p class="hint"><b>Tip:</b> the graph on the canvas is the published pipeline. Rewire it,
      delete a step, or drop in a new filter to see how the result moves.</p>`;
    return;
  }
  const spec = CATALOG[node.type];
  const vals = paramsOf(node);
  body.innerHTML = `
    <div class="nodehead">
      <div class="pchip" style="background:${spec.color}">${esc(spec.icon)}</div>
      <div><b>${esc(spec.name)}</b><div class="small">${esc(spec.group)}</div></div>
    </div>
    <div class="detail">${esc(spec.detail)}</div>
    ${spec.params.map(p => fieldHtml(p, vals[p.key])).join('')}
    <button class="resetlink" id="reset-params">reset this block to defaults</button>`;

  spec.params.forEach(p => wireField(node, p));
  $('#reset-params').addEventListener('click', () => {
    node.params = {}; render(); renderInspector();
  });
}

function fieldHtml(p, v) {
  const help = `<div class="fhelp">${esc(p.help)}</div>`;
  if (p.type === 'bool') {
    return `<div class="field"><label class="switch">
      <input type="checkbox" data-k="${p.key}" ${v ? 'checked' : ''}> ${esc(p.label)}</label>${help}</div>`;
  }
  if (p.type === 'choice') {
    return `<div class="field"><label>${esc(p.label)}</label>
      <select data-k="${p.key}">${p.options.map(o =>
        `<option value="${esc(o.value)}" ${o.value === v ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}
      </select>${help}</div>`;
  }
  if (p.type === 'multi') {
    const set = new Set(Array.isArray(v) ? v : []);
    return `<div class="field"><label>${esc(p.label)}</label><div class="multi">${p.options.map(o =>
      `<label><input type="checkbox" data-k="${p.key}" value="${esc(o.value)}" ${set.has(o.value) ? 'checked' : ''}>${esc(o.label)}</label>`).join('')}
      </div>${help}</div>`;
  }
  if (p.type === 'number') {
    return `<div class="field"><label>${esc(p.label)}</label>
      <div class="rangerow">
        <input type="range" data-k="${p.key}" data-role="range" min="${p.min}" max="${p.max}" step="${p.step}" value="${v}">
        <input type="number" data-k="${p.key}" data-role="num" min="${p.min}" max="${p.max}" step="${p.step}" value="${v}">
      </div>${help}</div>`;
  }
  return `<div class="field"><label>${esc(p.label)}</label>
    <input type="text" data-k="${p.key}" value="${esc(v)}" placeholder="${esc(p.placeholder || '')}">${help}</div>`;
}

function wireField(node, p) {
  const set = val => { node.params[p.key] = val; render(); };
  if (p.type === 'number') {
    const range = $(`#inspector [data-k="${p.key}"][data-role="range"]`);
    const num = $(`#inspector [data-k="${p.key}"][data-role="num"]`);
    range.addEventListener('input', () => { num.value = range.value; set(Number(range.value)); });
    num.addEventListener('change', () => { range.value = num.value; set(Number(num.value)); });
  } else if (p.type === 'multi') {
    $$(`#inspector [data-k="${p.key}"]`).forEach(cb => cb.addEventListener('change', () =>
      set($$(`#inspector [data-k="${p.key}"]`).filter(x => x.checked).map(x => x.value))));
  } else {
    const el = $(`#inspector [data-k="${p.key}"]`);
    if (!el) return;
    const ev = p.type === 'text' ? 'input' : 'change';
    el.addEventListener(ev, () => set(p.type === 'bool' ? el.checked : el.value));
  }
}

/* ------------------------------------------------------------------- chrome */
function wireChrome() {
  $$('.tab').forEach(t => t.addEventListener('click', () => showView(t.dataset.view)));
  $$('[data-goto]').forEach(b => b.addEventListener('click', () => showView(b.dataset.goto)));

  const canvas = $('#canvas');
  canvas.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
  canvas.addEventListener('drop', e => {
    e.preventDefault();
    const type = e.dataTransfer.getData('text/plain');
    if (!CATALOG[type]) return;
    const r = canvas.getBoundingClientRect();
    addNode(type, e.clientX - r.left + canvas.scrollLeft - NODE_W / 2,
                  e.clientY - r.top + canvas.scrollTop - 20);
  });
  canvas.addEventListener('mousedown', e => {
    if (e.target === canvas || e.target.id === 'nodes' || e.target.id === 'edges') {
      selectedId = null; render(); renderInspector();
    }
  });
  document.addEventListener('keydown', e => {
    if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId &&
        !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) {
      removeNode(selectedId);
    }
  });

  $('#btn-run').addEventListener('click', startRun);
  $('#btn-reset').addEventListener('click', () => loadGraph(JSON.parse(JSON.stringify(DEFAULT_GRAPH))));
  $('#btn-clear').addEventListener('click', () => loadGraph({ nodes: [], edges: [] }));
  $('#btn-tidy').addEventListener('click', tidy);
  $('#btn-export').addEventListener('click', exportGraph);
  $('#btn-toggle-console').addEventListener('click', () => {
    const c = $('#console'); c.classList.toggle('collapsed');
    $('#btn-toggle-console').textContent = c.classList.contains('collapsed') ? 'show' : 'hide';
  });
  $('#site-pick').addEventListener('change', e => $('#site-frame').src = e.target.value);
  $('#btn-site-new').addEventListener('click', () => window.open($('#site-pick').value, '_blank'));
  $('#btn-report-new').addEventListener('click', () => {
    if (currentRun) window.open(`/api/runs/${currentRun.id}/file?path=run_report.html&inline=1`, '_blank');
  });
  $('#btn-report-dl').addEventListener('click', () => {
    if (currentRun) window.location = `/api/runs/${currentRun.id}/file?path=run_report.html`;
  });
  $('#btn-download-all').addEventListener('click', () => {
    if (currentRun) window.location = `/api/runs/${currentRun.id}/download`;
  });
  window.addEventListener('resize', () => { if (currentRun && currentRun.results) drawCharts(currentRun.results); });
}

function showView(name) {
  $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === name));
  $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + name));
  if (name === 'results' && currentRun && currentRun.results) drawCharts(currentRun.results);
}

function tidy() {
  const order = topoOrder();
  const perCol = 3;
  order.forEach((id, i) => {
    const n = graph.nodes.find(x => x.id === id);
    n.x = 40 + Math.floor(i / perCol) * 290;
    n.y = 60 + (i % perCol) * 140;
  });
  render();
}

function topoOrder() {
  const indeg = {}, adj = {};
  graph.nodes.forEach(n => { indeg[n.id] = 0; adj[n.id] = []; });
  graph.edges.forEach(e => { if (adj[e.from]) { adj[e.from].push(e.to); indeg[e.to]++; } });
  const q = graph.nodes.filter(n => !indeg[n.id]).map(n => n.id), out = [];
  while (q.length) {
    const id = q.shift(); out.push(id);
    (adj[id] || []).forEach(nx => { if (--indeg[nx] === 0) q.push(nx); });
  }
  graph.nodes.forEach(n => { if (!out.includes(n.id)) out.push(n.id); });
  return out;
}

function exportGraph() {
  const blob = new Blob([JSON.stringify(graph, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'pipeline_graph.json';
  a.click();
}

function flash(msg) {
  setStatus('error', msg);
  setTimeout(() => { if (!currentRun || currentRun.status !== 'running') setStatus('idle', 'Ready.'); }, 3500);
}

function setStatus(kind, text) {
  $('#status-dot').className = 'dot ' + kind;
  $('#status-text').innerHTML = text;
}

/* ----------------------------------------------------------------- running */
async function startRun() {
  if (!graph.nodes.length) { flash('The canvas is empty — drag some blocks in first.'); return; }
  $('#btn-run').disabled = true;
  $('#console').classList.remove('collapsed');
  $('#console-body').innerHTML = '';
  logCursor = 0;
  currentRun = null;
  setStatus('running', 'Starting…');

  const res = await fetch('/api/run', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ graph, label: 'sample run' }),
  });
  const data = await res.json();
  if (data.error) { $('#btn-run').disabled = false; flash(esc(data.error)); return; }
  poll(data.run_id);
}

function poll(runId) {
  clearTimeout(pollTimer);
  const tick = async () => {
    const res = await fetch(`/api/runs/${runId}?since=${logCursor}`);
    const snap = await res.json();
    snap.id = runId;
    currentRun = Object.assign(currentRun || {}, snap);
    logCursor = snap.log_count;
    appendLogs(snap.logs);
    paintNodeStatus(snap.node_status);
    $('#status-elapsed').textContent = snap.elapsed ? snap.elapsed.toFixed(1) + 's' : '';

    if (snap.status === 'running' || snap.status === 'queued') {
      setStatus('running', 'Running the pipeline…');
      pollTimer = setTimeout(tick, 350);
      return;
    }
    $('#btn-run').disabled = false;
    if (snap.status === 'error') {
      setStatus('error', 'Run failed — see the log below. <b>' + esc(snap.error || '') + '</b>');
    } else {
      setStatus('done', 'Run complete in ' + snap.elapsed.toFixed(1) + 's — open <b>Results</b>, <b>Report</b> or <b>Downloads</b>.');
    }
    if (snap.results) fillResults(snap.results);
  };
  tick();
}

function appendLogs(lines) {
  if (!lines || !lines.length) return;
  const body = $('#console-body');
  body.insertAdjacentHTML('beforeend', lines.map(l =>
    `<div class="logline ${l.level}"><span class="t">${l.t.toFixed(2)}s</span>${esc(l.message)}</div>`).join(''));
  body.scrollTop = body.scrollHeight;
}

function paintNodeStatus(status) {
  if (!status) return;
  $$('.node').forEach(el => {
    el.classList.remove('running', 'done', 'error');
    const s = status[el.dataset.id];
    if (s) el.classList.add(s);
  });
  drawEdges();
}

/* ----------------------------------------------------------------- results */
function fillResults(r) {
  $('#results-empty').classList.add('hidden');
  $('#results-body').classList.remove('hidden');

  const note = $('#provenance-note');
  if (/simulated/i.test(r.data_provenance || '')) {
    note.className = 'callout danger';
    note.innerHTML = `<b>Sample run — the per-sample values in this cohort are simulated.</b>
      Probe identities, genes, coordinates and the per-probe tumour/normal means come from the
      published TCGA-BRCA analysis; the individual sample values were drawn to match those means
      and the spread implied by the published t-statistics. The <i>algorithms</i> below are the real
      ones; the <i>numbers</i> are a demonstration. Point the Load block at the real matrix for real results.`;
  } else {
    note.className = 'callout good';
    note.innerHTML = `<b>Run on user-supplied input files.</b> ${esc(r.data_provenance || '')}`;
  }

  $('#stat-cards').innerHTML = (r.stats || []).map(s => {
    const cls = /significant/i.test(s.label) ? ' red' : (/AUC/i.test(s.label) ? ' green' : '');
    return `<div class="card${cls}"><div class="num">${commas(s.value)}</div>
      <div class="lbl">${esc(s.label)}</div></div>`;
  }).join('');

  $('#table-markers').innerHTML = tableHtml(r.top_markers, r.top_marker_columns);
  $('#table-panel').innerHTML = tableHtml(r.panel, r.panel_columns);

  if (r.enrichment_top && r.enrichment_top.length) {
    $('#enrich-wrap').classList.remove('hidden');
    $('#enrich-null').classList.toggle('hidden', !r.enrichment_null);
    $('#table-enrich').innerHTML = tableHtml(r.enrichment_top,
      ['library', 'term', 'overlap', 'set_size', 'fdr']);
  } else $('#enrich-wrap').classList.add('hidden');

  $('#roc-note').textContent = r.model
    ? `${r.model.model} · ${r.model.cv_folds}-fold CV · AUC ${r.model.roc_auc_mean.toFixed(4)} ± ${r.model.roc_auc_std.toFixed(4)} · ${r.model.feature_selection}`
    : 'No classifier in this graph.';

  drawCharts(r);
  fillFiles(r);

  if (r.report) {
    $('#report-frame').src = `/api/runs/${currentRun.id}/file?path=${encodeURIComponent(r.report)}&inline=1`;
    $('#report-label').innerHTML = `<b>${esc(r.report)}</b> — self-contained HTML, generated by this run.`;
  } else {
    $('#report-label').textContent = 'This graph has no Report block. Drag one in and run again.';
  }
}

function tableHtml(rows, cols) {
  if (!rows || !rows.length) return '<p class="hint">No rows.</p>';
  cols = cols || Object.keys(rows[0]);
  const head = cols.map(c => `<th>${esc(c.replace(/_/g, ' '))}</th>`).join('');
  const body = rows.map(r => '<tr>' + cols.map(c => {
    const v = r[c];
    if (c === 'direction') return `<td class="${String(v).startsWith('hyper') ? 'hyper' : 'hypo'}">${esc(v)}</td>`;
    if (c === 'probe_id') return `<td><code>${esc(v)}</code></td>`;
    if (typeof v === 'number' && !Number.isInteger(v)) return `<td>${fmtNum(v)}</td>`;
    return `<td>${esc(v)}</td>`;
  }).join('') + '</tr>').join('');
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function fillFiles(r) {
  const files = r.files || [];
  $('#btn-download-all').disabled = !files.length;
  if (!files.length) { $('#table-files').innerHTML = '<p class="hint">No files.</p>'; return; }
  $('#table-files').innerHTML = `<table><thead><tr><th>File</th><th>Size</th><th>What it is</th><th></th></tr></thead><tbody>${
    files.map(f => `<tr>
      <td><code>${esc(f.name)}</code></td>
      <td>${fmtBytes(f.size)}</td>
      <td class="small">${esc(describeFile(f.name))}</td>
      <td><a href="/api/runs/${currentRun.id}/file?path=${encodeURIComponent(f.name)}">download</a></td>
    </tr>`).join('')}</tbody></table>`;
}

function describeFile(name) {
  if (name.startsWith('enrichment_')) return 'Over-representation results for one library / direction.';
  return {
    'differential_methylation.tsv': 'Every tested probe with delta-beta, p-value and FDR.',
    'differential_with_mechanics.tsv': 'The same table plus region context and the silencing/activation call.',
    'candidate_biomarker_panel.tsv': 'The ranked marker panel.',
    'classifier_summary.json': 'Cross-validated AUC and per-fold scores.',
    'cv_folds.tsv': 'One row per cross-validation fold.',
    'qc_sample_missingness.tsv': 'Missing-data fraction for every sample.',
    'run_manifest.json': 'The exact block graph and parameter values this run used.',
    'run_log.txt': 'Full run log.',
    'run_report.html': 'The self-contained HTML report.',
  }[name] || '';
}

/* ------------------------------------------------------------------ charts */
function hidpi(c, h) {
  const r = c.getBoundingClientRect(), d = window.devicePixelRatio || 1;
  if (!r.width) return null;           // hidden tab: redrawn by showView() once visible
  c.width = r.width * d; c.height = h * d;
  const x = c.getContext('2d'); x.setTransform(d, 0, 0, d, 0, 0);
  return { x, W: r.width, H: h };
}

function drawCharts(r) {
  drawVolcano(r.volcano);
  drawRoc(r.roc);
  drawMech(r.mechanics_counts);
}

function drawVolcano(v) {
  const c = $('#volcano'); if (!c) return;
  const dims = hidpi(c, 430); if (!dims) return;
  const { x, W, H } = dims, pad = 52;
  x.clearRect(0, 0, W, H);
  if (!v || !v.x || !v.x.length) { emptyChart(x, W, H, 'No differential results in this graph.'); return; }
  const xmax = Math.max(0.2, ...v.x.map(Math.abs)) * 1.08;
  const ymax = Math.max(2, ...v.y) * 1.08;
  const px = t => pad + (t + xmax) / (2 * xmax) * (W - pad - 20);
  const py = t => H - pad - (t / ymax) * (H - pad - 22);

  x.strokeStyle = '#e6ebf1'; x.fillStyle = '#7c8a99'; x.font = '11px sans-serif';
  for (let i = 0; i <= 4; i++) { const val = ymax * i / 4, y = py(val);
    x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 20, y); x.stroke(); x.fillText(val.toFixed(0), 8, y + 3); }
  for (let i = -2; i <= 2; i++) { const val = xmax * i / 2, X = px(val);
    x.beginPath(); x.moveTo(X, 18); x.lineTo(X, H - pad); x.stroke(); x.fillText(val.toFixed(2), X - 13, H - pad + 16); }

  const pts = [];
  for (let i = 0; i < v.x.length; i++) {
    const sig = v.y[i] > 1.301 && Math.abs(v.x[i]) >= 0.2;
    x.fillStyle = sig ? (v.x[i] > 0 ? 'rgba(192,57,43,.55)' : 'rgba(26,122,58,.55)') : 'rgba(154,165,177,.32)';
    const X = px(v.x[i]), Y = py(v.y[i]);
    x.beginPath(); x.arc(X, Y, 2.3, 0, 6.284); x.fill();
    pts.push({ X, Y, probe: v.probe[i], dx: v.x[i], dy: v.y[i] });
  }
  x.fillStyle = '#333'; x.font = '12px sans-serif';
  x.fillText('Δβ  (group A minus group B)', W / 2 - 78, H - 12);
  x.save(); x.translate(15, H / 2 + 60); x.rotate(-Math.PI / 2); x.fillText('−log10(FDR)', 0, 0); x.restore();

  const tip = $('#tip');
  c.onmousemove = ev => {
    const r = c.getBoundingClientRect();
    const mx = ev.clientX - r.left, my = ev.clientY - r.top;
    let best = null, bd = 64;
    for (const p of pts) { const d = (p.X - mx) ** 2 + (p.Y - my) ** 2; if (d < bd) { bd = d; best = p; } }
    if (best) {
      tip.innerHTML = `<b>${esc(best.probe)}</b><br>Δβ ${best.dx.toFixed(3)} · −log10 FDR ${best.dy.toFixed(2)}`;
      tip.style.opacity = 1; tip.style.left = (ev.clientX + 14) + 'px'; tip.style.top = (ev.clientY - 10) + 'px';
    } else tip.style.opacity = 0;
  };
  c.onmouseleave = () => { $('#tip').style.opacity = 0; };
}

function drawRoc(roc) {
  const c = $('#roc'); if (!c) return;
  const dims = hidpi(c, 330); if (!dims) return;
  const { x, W, H } = dims, pad = 46;
  x.clearRect(0, 0, W, H);
  if (!roc || !roc.fpr) { emptyChart(x, W, H, 'No classifier in this graph.'); return; }
  const px = t => pad + t * (W - pad - 18), py = t => H - pad - t * (H - pad - 20);
  x.strokeStyle = '#e6ebf1';
  for (let i = 0; i <= 5; i++) { const y = py(i / 5); x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 18, y); x.stroke(); }
  x.strokeStyle = '#bbb'; x.setLineDash([4, 4]);
  x.beginPath(); x.moveTo(px(0), py(0)); x.lineTo(px(1), py(1)); x.stroke(); x.setLineDash([]);
  x.strokeStyle = '#2e75b6'; x.lineWidth = 2.4; x.beginPath();
  roc.fpr.forEach((f, i) => { const X = px(f), Y = py(roc.tpr[i]); i ? x.lineTo(X, Y) : x.moveTo(X, Y); });
  x.stroke(); x.lineWidth = 1;
  x.fillStyle = '#7c8a99'; x.font = '11px sans-serif';
  x.fillText('0', pad - 4, H - pad + 15); x.fillText('1', W - 24, H - pad + 15);
  x.fillStyle = '#333'; x.font = '12px sans-serif';
  x.fillText('false positive rate', W / 2 - 50, H - 10);
  x.save(); x.translate(15, H / 2 + 48); x.rotate(-Math.PI / 2); x.fillText('true positive rate', 0, 0); x.restore();
}

function drawMech(counts) {
  const c = $('#mech'); if (!c) return;
  const dims = hidpi(c, 330); if (!dims) return;
  const { x, W, H } = dims, pad = 46;
  x.clearRect(0, 0, W, H);
  const entries = Object.entries(counts || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) { emptyChart(x, W, H, 'Add a Direction-of-effect block to see this.'); return; }
  const max = Math.max(...entries.map(e => e[1])) * 1.15;
  const colors = { silencing: '#c0392b', activation: '#1a7a3a', ambiguous: '#9aa5b1' };
  const bw = (W - pad - 24) / entries.length;
  entries.forEach(([k, v], i) => {
    const h = (v / max) * (H - pad - 40);
    const X = pad + i * bw + bw * 0.18, Y = H - pad - h;
    x.fillStyle = colors[k] || '#7d4fbf';
    x.fillRect(X, Y, bw * 0.64, h);
    x.fillStyle = '#1a2733'; x.font = 'bold 13px sans-serif';
    x.fillText(v.toLocaleString(), X, Y - 7);
    x.fillStyle = '#68788a'; x.font = '11.5px sans-serif';
    x.fillText(k, X, H - pad + 16);
  });
  x.strokeStyle = '#d7dde5'; x.beginPath(); x.moveTo(pad, H - pad); x.lineTo(W - 18, H - pad); x.stroke();
}

function emptyChart(x, W, H, msg) {
  x.fillStyle = '#9aabbc'; x.font = '13px sans-serif';
  x.fillText(msg, W / 2 - x.measureText(msg).width / 2, H / 2);
}

boot();
})();
