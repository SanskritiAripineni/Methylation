/* Methylation Studio (v3).
 *
 * Plain language on the surface, the v2 checks underneath: the same readiness
 * gate runs before every launch and a `fail` still blocks. What changes here
 * is how much someone has to read.
 *
 * Things this file will not do: invent a time estimate, show a report from a
 * run that did not write one, or call a test run a result.
 */
(() => {
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = n => (typeof n === 'number' ? n.toLocaleString() : n);

const state = {
  setup: null,
  preset: 'standard',
  thresholds: {},
  useExample: false,
  runId: null,
  snap: null,
  logCursor: 0,
  timer: null,
  ticker: null,
  results: null,
};

const api = {
  async get(u) {
    const r = await fetch(u);
    const j = await r.json().catch(() => ({ error: r.statusText }));
    if (!r.ok) throw new Error(j.error || r.statusText);
    return j;
  },
  async post(u, b) {
    const r = await fetch(u, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(b || {}) });
    const j = await r.json().catch(() => ({ error: r.statusText }));
    if (!r.ok) throw new Error(j.error || r.statusText);
    return j;
  },
};

const secs = s => {
  if (s == null) return null;
  s = Math.round(s);
  if (s < 60) return s + 's';
  const m = Math.floor(s / 60);
  if (m < 60) return m + 'm ' + (s % 60) + 's';
  return Math.floor(m / 60) + 'h ' + (m % 60) + 'm';
};
const bytes = b => b < 1024 ? b + ' B'
  : b < 1048576 ? (b / 1024).toFixed(0) + ' KB' : (b / 1048576).toFixed(1) + ' MB';

const HELP = {
  volcano: 'Each dot is one spot on the DNA. Further left or right means a bigger difference ' +
    'between your two groups. Higher up means we are more confident it is real. The coloured ' +
    'dots in the top corners are the interesting ones.',
  roc: 'A test of whether the shortlist can actually tell your two groups apart. The line ' +
    'bulges towards the top-left when it works. The dashed diagonal is a coin flip. AUC of ' +
    '1.0 is perfect, 0.5 is useless.',
  mech: 'Methylation in the wrong place usually switches a gene off; losing it can switch one ' +
    'on. This counts how many of the changed sites fall into each case. "Unclear" means the ' +
    'site is not in a position where the effect is predictable.',
};

function tipOn(el, text) {
  if (!text) return;
  const tip = $('#tip');
  el.addEventListener('mouseenter', () => {
    tip.textContent = text;
    tip.style.opacity = 1;
    const r = el.getBoundingClientRect();
    tip.style.left = Math.min(window.innerWidth - 350, r.left) + 'px';
    tip.style.top = (r.bottom + 8) + 'px';
  });
  el.addEventListener('mouseleave', () => { tip.style.opacity = 0; });
}

function say(el, kind, html) {
  el.className = 'status show ' + kind;
  el.innerHTML = html;
}
function hide(el) { el.className = 'status'; }

/* ------------------------------------------------------------------ boot */
async function boot() {
  try {
    state.setup = await api.get('/api/v3/setup');
  } catch (err) {
    document.body.insertAdjacentHTML('afterbegin',
      `<div class="banner bad" style="display:block">Could not start: ${esc(err.message)}</div>`);
    return;
  }
  $('#example-blurb').textContent = state.setup.example.blurb;
  applyPreset('standard');
  renderPresets();
  renderTiers();
  renderWorkspace(state.setup.workspace, state.setup.readiness);
  wire();
  await refreshHistory();
}

function wire() {
  const drop = $('#drop');
  const pick = $('#filepick');
  drop.addEventListener('click', e => { if (e.target.id !== 'browse') pick.click(); });
  $('#browse').addEventListener('click', e => { e.stopPropagation(); pick.click(); });
  pick.addEventListener('change', () => upload(Array.from(pick.files)));
  ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => {
    e.preventDefault(); drop.classList.add('over');
  }));
  ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => {
    e.preventDefault(); drop.classList.remove('over');
  }));
  drop.addEventListener('drop', e => upload(Array.from(e.dataTransfer.files)));

  $('#use-example').addEventListener('click', () => {
    state.useExample = true;
    $('#use-example').classList.add('on');
    say($('#data-status'), 'ok',
      '<b>Using the example data.</b> 130 breast samples, tumour against normal tissue. ' +
      'The individual values in it are simulated, so treat anything it finds as a demonstration.');
    renderTiers();
  });

  $$('.tab').forEach(t => t.addEventListener('click', () => {
    $$('.tab').forEach(x => x.classList.toggle('active', x === t));
    $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + t.dataset.view));
    if (t.dataset.view === 'results' && state.results) drawAll(state.results);
  }));

  $('#p-cancel').addEventListener('click', cancel);
  $('#show-tests').addEventListener('change', refreshHistory);
  $('#report-open').addEventListener('click', () => {
    if (state.runId) window.open(fileUrl(state.runId, 'run_report.html', true), '_blank');
  });
  $('#report-print').addEventListener('click', () => {
    const f = $('#report-frame');
    if (f.contentWindow) f.contentWindow.print();
  });
  $('#download-all').addEventListener('click', () => {
    if (state.runId) window.location = `/api/v3/runs/${state.runId}/download`;
  });
  $$('.q').forEach(b => tipOn(b, HELP[b.dataset.q]));
  window.addEventListener('resize', () => { if (state.results) drawAll(state.results); });
}

const fileUrl = (id, name, inline) =>
  `/api/v3/runs/${id}/file?path=${encodeURIComponent(name)}${inline ? '&inline=1' : ''}`;

/* ------------------------------------------------------------- uploading */
async function upload(files) {
  if (!files.length) return;
  const status = $('#data-status');
  say(status, 'warn', `Reading ${files.length} file${files.length === 1 ? '' : 's'}…`);
  let last = null;
  for (const f of files) {
    if (f.size > 100 * 1024 * 1024) {
      say(status, 'bad', `<b>${esc(f.name)} is ${(f.size / 1048576).toFixed(0)} MB.</b>
        The browser limit is 100 MB. For a file that big, use the advanced console and point
        it at the file where it already sits.`);
      continue;
    }
    try {
      last = await fetch('/api/v3/upload', {
        method: 'POST', headers: { 'X-Filename': f.name }, body: f,
      }).then(r => r.json());
    } catch (err) {
      say(status, 'bad', esc(err.message));
      return;
    }
  }
  if (last && last.workspace) {
    state.useExample = false;
    $('#use-example').classList.remove('on');
    renderWorkspace(last.workspace, last.readiness);
  }
}

function renderWorkspace(ws, readiness) {
  const list = $('#filelist');
  list.innerHTML = (ws.files || []).map(f => `
    <div class="fileitem ${f.ok ? '' : 'bad'}">
      <span class="fmark">${f.ok ? '✓' : '!'}</span>
      <span>
        <span class="frole">${esc(f.ok ? f.label : 'Problem')}</span>
        <div class="fname">${esc(f.name)}</div>
        <div class="fdetail">${esc(f.detail)}</div>
      </span>
    </div>`).join('');
  if (ws.files && ws.files.length) {
    list.insertAdjacentHTML('beforeend',
      `<button class="btn small" id="clear-files" style="justify-self:start">Remove these files</button>`);
    $('#clear-files').addEventListener('click', async () => {
      const j = await api.post('/api/v3/workspace/clear');
      renderWorkspace(j.workspace, j.readiness);
      hide($('#data-status'));
    });
  }
  const status = $('#data-status');
  if (ws.files && ws.files.length) {
    say(status, readiness.ready ? 'ok' : 'warn', esc(readiness.message));
  } else if (!state.useExample) {
    hide(status);
  }
  renderTiers();
}

/* -------------------------------------------------------------- settings */
function applyPreset(id) {
  const p = (state.setup.presets || []).find(x => x.id === id);
  if (!p) return;
  state.preset = id;
  state.thresholds = { ...p.values };
}

function renderPresets() {
  $('#presets').innerHTML = (state.setup.presets || []).map(p => `
    <button class="preset ${p.id === state.preset ? 'on' : ''}" data-preset="${esc(p.id)}">
      <span class="radio"></span>
      <span><b>${esc(p.label)}</b>${p.recommended ? ' <span class="tag">RECOMMENDED</span>' : ''}
        <span>${esc(p.blurb)}</span></span>
    </button>`).join('');
  $$('[data-preset]').forEach(b => b.addEventListener('click', () => {
    applyPreset(b.dataset.preset);
    renderPresets();
    renderAdvanced();
    renderTiers();
  }));
  renderAdvanced();
}

function renderAdvanced() {
  const tcfg = state.setup.thresholds || {};
  $('#advanced').innerHTML = Object.entries(tcfg).map(([key, spec]) => {
    const v = state.thresholds[key] !== undefined ? state.thresholds[key] : spec.default;
    if (spec.type === 'bool') {
      return `<div class="ctrl"><label class="checkline">
        <input type="checkbox" data-bool="${key}" ${v ? 'checked' : ''}>
        <span>${esc(spec.label || key)}</span></label>
        <div class="expl">${esc(plainFor(key))}</div></div>`;
    }
    return `<div class="ctrl">
      <label>${esc(spec.label || key)} <span class="val" data-val="${key}">${v}</span></label>
      <input type="range" data-range="${key}" min="${spec.min}" max="${spec.max}"
             step="${spec.step}" value="${v}">
      <div class="expl">${esc(plainFor(key))}</div>
      <div class="measured" data-measured="${key}"></div>
    </div>`;
  }).join('');

  $$('[data-range]').forEach(r => {
    r.addEventListener('input', () => {
      $(`[data-val="${r.dataset.range}"]`).textContent = r.value;
    });
    r.addEventListener('change', () => {
      state.thresholds[r.dataset.range] = Number(r.value);
      state.preset = 'custom';
      renderPresets();
      measure(r.dataset.range);
    });
  });
  $$('[data-bool]').forEach(c => c.addEventListener('change', () => {
    state.thresholds[c.dataset.bool] = c.checked;
    state.preset = 'custom';
    renderPresets();
  }));
  Object.keys(tcfg).forEach(measure);
}

const PLAIN = {
  delta_beta_min: 'How big a difference has to be before it counts. Higher means fewer, ' +
    'stronger results.',
  fdr_max: 'How much luck you are willing to tolerate. Lower means fewer false alarms.',
  sample_call_rate_min: 'Throw out samples with too much missing data. Higher is stricter.',
  probe_call_rate_min: 'Throw out DNA sites measured in too few samples.',
  min_samples_per_class: 'The smallest group size the analysis will accept. Below about 5 per ' +
    'group there is very little chance of finding anything real.',
  panel_size: 'How many of the top sites go into the shortlist.',
  exclude_sex_chromosomes: 'X and Y behave differently between sexes and can drown out ' +
    'everything else. Normally left on.',
};
const plainFor = key => PLAIN[key] || '';

async function measure(key) {
  const el = $(`[data-measured="${key}"]`);
  if (!el) return;
  const v = state.thresholds[key];
  try {
    const q = new URLSearchParams({ key, value: v });
    if (state.runId) q.set('run', state.runId);
    const j = await api.get(`/api/v2/studies/brca_sim/threshold-effect?${q}`);
    el.textContent = j.available ? j.text : '';
  } catch (_) { el.textContent = ''; }
}

/* ------------------------------------------------------------------ run */
function canRun() {
  if (state.useExample) return true;
  const ws = state.setup && state.setup.workspace;
  return !!(ws && ws.roles && ws.roles.matrix && ws.roles.manifest);
}

function renderTiers() {
  const tiers = state.setup.tiers || {};
  const testDone = (state.history || []).some(r => r.mode === 'demo' && r.status === 'done');
  const ready = canRun();
  const order = [
    ['demo', '▶', true],
    ['full', '★', false],
    ['plan', '✓', false],
  ];
  $('#tiers').innerHTML = order.map(([mode, ico, primary]) => {
    const t = tiers[mode] || {};
    const locked = mode === 'full' && !testDone;
    const disabled = !ready || locked;
    const lock = locked
      ? '<span class="lock">Run the quick test first</span>'
      : (!ready ? '<span class="lock">Pick your data first</span>' : '');
    return `<button class="tierbtn ${primary ? 'primary' : ''}" data-tier="${mode}"
              ${disabled ? 'disabled' : ''}>
      <span class="ico">${ico}</span>
      <span><b>${esc(t.label || mode)}</b><span>${esc(t.blurb || '')}</span></span>
      ${lock}</button>`;
  }).join('');
  $$('[data-tier]').forEach(b => b.addEventListener('click', () => launch(b.dataset.tier)));
}

async function launch(mode) {
  const status = $('#run-status');
  say(status, 'warn', 'Checking your files…');
  try {
    const j = await api.post('/api/v3/runs', {
      study: 'brca_sim', mode,
      use_example: state.useExample,
      thresholds: state.thresholds,
      n_per_class: 3,
      name: mode === 'full' ? 'Full analysis' : (mode === 'demo' ? 'Quick test' : 'File check'),
    });
    hide(status);
    state.logCursor = 0;
    $('#logbody').innerHTML = '';
    state.runId = j.run_id;
    $('#progress').hidden = false;
    startTicker();
    poll();
  } catch (err) {
    // The gate refused. Show its own sentence — it is written to be actionable.
    say(status, 'bad', `<b>Cannot run yet.</b> ${esc(err.message)}`);
  }
}

function startTicker() {
  clearInterval(state.ticker);
  state.ticker = setInterval(() => {
    const s = state.snap;
    if (!s || !['running', 'queued'].includes(s.status)) return;
    // Tick the clock between polls so it never looks frozen.
    const p = s.progress || {};
    const shown = (p.elapsed || 0) + (Date.now() - (state.polledAt || Date.now())) / 1000;
    $('#p-elapsed').textContent = secs(shown);
    if (p.remaining != null) {
      $('#p-left').textContent = secs(Math.max(0, p.remaining - (shown - (p.elapsed || 0))));
    }
  }, 1000);
}

async function poll() {
  if (!state.runId) return;
  let snap;
  try {
    snap = await api.get(`/api/v3/runs/${state.runId}?since=${state.logCursor}`);
  } catch (err) {
    say($('#run-status'), 'bad', esc(err.message));
    return;
  }
  state.snap = snap;
  state.polledAt = Date.now();
  state.logCursor = snap.log_count || state.logCursor;
  appendLog(snap.logs);
  renderProgress(snap);
  renderBanner(snap);

  if (['running', 'queued'].includes(snap.status)) {
    state.timer = setTimeout(poll, 2000);
    return;
  }
  clearInterval(state.ticker);
  await settle(snap);
  await refreshHistory();
}

function renderProgress(snap) {
  const p = snap.progress || {};
  $('#p-step').textContent = `Step ${p.index || 0} of ${p.total || 0}`;
  $('#p-name').textContent = p.current ? p.current.friendly
    : (snap.status === 'done' ? 'Finished' : snap.status === 'error' ? 'Stopped early'
      : snap.status === 'cancelled' ? 'Stopped' : 'Starting…');
  $('#p-plain').textContent = p.current ? (p.current.plain || '') : '';
  const live = ['running', 'queued'].includes(snap.status);
  $('#p-elapsed').textContent = secs(p.elapsed) || '0s';
  $('#p-elapsed').nextElementSibling.textContent = live ? 'running for' : 'took';
  if (!live) {
    // Finished. "No estimate yet" would be a true sentence in the wrong place.
    $('#p-left').textContent = snap.status === 'done' ? 'done' : snap.status;
    $('#p-left').title = '';
  } else {
    $('#p-left').textContent = p.remaining != null ? secs(p.remaining) : '—';
    $('#p-left').title = p.remaining != null ? (p.remaining_basis || '') : (p.remaining_note || '');
  }
  $('#p-fill').style.width = (p.percent || 0) + '%';
  $('#p-track').innerHTML = (snap.steps || []).map(s =>
    `<span class="tick ${esc(s.state)}" title="${esc(s.friendly)}${
      s.seconds != null ? ' — ' + secs(s.seconds) : ''}"></span>`).join('');
  $('#p-cancel').disabled = !live;
  $('#p-cancel').textContent = live ? 'Stop' : 'Done';
}

function appendLog(lines) {
  if (!lines || !lines.length) return;
  const b = $('#logbody');
  b.insertAdjacentHTML('beforeend', lines.map(l =>
    `<div class="l-${esc(l.level)}"><span class="t">${(l.t || 0).toFixed(1)}s</span>${
      esc(l.message)}</div>`).join(''));
  b.scrollTop = b.scrollHeight;
}

function renderBanner(snap) {
  const el = $('#banner');
  const v = snap.verdict || {};
  el.hidden = false;
  if (snap.status === 'error') {
    el.className = 'banner bad';
    el.innerHTML = `<b>It stopped at "${esc((snap.steps || []).find(s => s.state === 'failed')
      ? snap.steps.find(s => s.state === 'failed').friendly : 'a step')}".</b>
      ${esc(snap.error || '')}<div class="more">Nothing was overwritten. Earlier runs are
      untouched, and the technical log above says exactly where it stopped.</div>`;
    return;
  }
  if (snap.mode === 'demo') {
    el.className = 'banner test';
    el.innerHTML = `<b>This was a quick test on ${snap.n_per_class || 3} samples per group.</b>
      It proves the whole thing runs. The numbers are not a result — press
      <b>Full analysis</b> for that.
      ${(snap.demo_adjustments || []).length
        ? `<div class="more">${esc(snap.demo_adjustments[0].param)} was adjusted for the small
           sample count, because the run would otherwise finish with nothing in it.</div>` : ''}`;
    return;
  }
  if (snap.mode === 'plan') {
    el.className = 'banner test';
    el.innerHTML = `<b>Files checked. Nothing was analysed.</b>
      Every file and setting was resolved and written to <code>commands.txt</code>.`;
    return;
  }
  const limited = v.level === 'research-only';
  el.className = 'banner ' + (limited ? 'test' : 'ok');
  el.innerHTML = `<b>${limited ? 'Finished — read with care.' : 'Finished.'}</b>
    ${esc(v.summary || '')}
    ${(v.reasons || []).length ? `<div class="more">${esc(v.reasons[0])}${
      v.reasons.length > 1 ? ` (+${v.reasons.length - 1} more in the advanced console)` : ''}</div>` : ''}
    <div class="more">${esc(v.caveat || '')}</div>`;
}

async function settle(snap) {
  const files = snap.artifacts || snap.files || [];
  $('#download-all').disabled = !files.length;
  $('#files-label').textContent = files.length
    ? `${files.length} files from ${snap.label || snap.id}. Only steps that finished are listed here.`
    : 'Nothing to download — no step produced a file.';
  $('#filetable').innerHTML = files.length ? `<table><thead><tr>
      <th>File</th><th>Size</th><th>What it is</th><th></th></tr></thead><tbody>${
    files.map(f => `<tr><td><code>${esc(f.name)}</code></td><td>${bytes(f.size)}</td>
      <td>${esc(describe(f.name))}</td>
      <td><a href="${fileUrl(snap.id, f.name)}">download</a></td></tr>`).join('')}
    </tbody></table>` : '<p class="sub pad">No files.</p>';

  if (snap.has_report) {
    $('#report-frame').src = fileUrl(snap.id, 'run_report.html', true);
    $('#report-empty').hidden = true;
    $('#report-label').innerHTML = `Report from <b>${esc(snap.label || snap.id)}</b>
      · ${esc(snap.tier_label || snap.mode)}`;
    $('#report-open').disabled = false;
    $('#report-print').disabled = false;
  } else {
    $('#report-frame').removeAttribute('src');
    $('#report-empty').hidden = false;
    $('#report-empty').querySelector('h3').textContent = 'No report from this run';
    $('#report-empty').querySelector('p').textContent =
      'The report step did not finish, so there is nothing to show. An older report is not ' +
      'shown in its place — it would not describe this run.';
    $('#report-label').textContent = 'No report from this run.';
    $('#report-open').disabled = true;
    $('#report-print').disabled = true;
  }

  try {
    state.results = await api.get(`/api/v3/runs/${snap.id}/results`);
    $('#results-empty').hidden = true;
    $('#results-body').hidden = false;
    fillResults(state.results);
  } catch (_) {
    state.results = null;
    $('#results-empty').hidden = false;
    $('#results-body').hidden = true;
  }
  Object.keys(state.setup.thresholds || {}).forEach(measure);
}

function describe(name) {
  if (name.startsWith('enrichment_')) return 'Pathways the hit genes fall into.';
  if (name.startsWith('demo_sample_')) return 'The subset this test run used.';
  return {
    'differential_methylation.tsv': 'Every site tested, with its difference and p-value.',
    'differential_with_mechanics.tsv': 'The same, plus gene context and likely effect.',
    'candidate_biomarker_panel.tsv': 'The shortlist of top sites.',
    'classifier_summary.json': 'How well the shortlist told the groups apart.',
    'cv_folds.tsv': 'Score from each cross-validation round.',
    'qc_sample_missingness.tsv': 'How much data was missing per sample.',
    'run_manifest.json': 'Exactly which settings this run used.',
    'run_record.json': 'The full record, including the checks and the verdict.',
    'run_log.txt': 'The complete log.',
    'run_report.html': 'The report.',
    'commands.txt': 'What a real run would do, resolved but not executed.',
  }[name] || '';
}

async function cancel() {
  if (!state.runId) return;
  try {
    const j = await api.post(`/api/v3/runs/${state.runId}/cancel`);
    say($('#run-status'), 'warn', esc(j.outcome));
  } catch (err) { say($('#run-status'), 'bad', esc(err.message)); }
}

/* -------------------------------------------------------------- history */
async function refreshHistory() {
  const inc = $('#show-tests').checked;
  try {
    const j = await api.get(`/api/v3/history?include_tests=${inc ? 1 : 0}`);
    state.history = j.runs;
    renderTiers();
    const box = $('#history');
    if (!j.runs.length) { box.innerHTML = '<p class="sub">Nothing yet.</p>'; return; }
    box.innerHTML = j.runs.map(r => `
      <button class="hrun ${r.id === state.runId ? 'on' : ''}" data-open="${esc(r.id)}">
        <b>${esc(r.label)}</b>
        <span class="badge ${r.status === 'error' ? 'bad' : (r.is_test ? 'test' : 'full')}">${
          r.status === 'error' ? 'failed' : (r.is_test ? 'test' : 'full')}</span>
        <div class="meta">${esc(r.when)} · ${esc(secs(r.elapsed) || '')}${
          r.has_report ? ' · report saved' : ''}</div>
      </button>`).join('');
    $$('[data-open]').forEach(b => b.addEventListener('click', () => open(b.dataset.open)));
  } catch (err) {
    $('#history').innerHTML = `<p class="sub">${esc(err.message)}</p>`;
  }
}

async function open(runId) {
  clearTimeout(state.timer);
  state.runId = runId;
  state.logCursor = 0;
  $('#logbody').innerHTML = '';
  $('#progress').hidden = false;
  await poll();
  refreshHistory();
}

/* --------------------------------------------------------------- charts */
function fillResults(r) {
  $('#cards').innerHTML = (r.stats || []).map(s => {
    const cls = /significant|passing/i.test(s.label) ? ' red' : (/AUC/i.test(s.label) ? ' green' : '');
    return `<div class="card${cls}"><div class="num">${num(s.value)}</div>
      <div class="lbl">${esc(s.label)}</div></div>`;
  }).join('');
  $('#roc-note').textContent = r.model
    ? `${r.model.model.replace(/_/g, ' ')} · ${r.model.cv_folds}-fold · AUC ${
      r.model.roc_auc_mean.toFixed(3)} ± ${r.model.roc_auc_std.toFixed(3)}`
    : 'No classifier in this run.';
  $('#tbl-markers').innerHTML = table(r.top_markers, r.top_marker_columns);
  $('#tbl-panel').innerHTML = table(r.panel, r.panel_columns);
  drawAll(r);
}

function table(rows, cols) {
  if (!rows || !rows.length) return '<p class="sub pad">Nothing to show.</p>';
  cols = cols || Object.keys(rows[0]);
  const nice = c => c.replace(/_/g, ' ').replace('delta beta', 'difference')
    .replace('fdr', 'confidence (FDR)').replace('probe id', 'site');
  return `<table><thead><tr>${cols.map(c => `<th>${esc(nice(c))}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(row => '<tr>' + cols.map(c => {
      const v = row[c];
      if (c === 'direction') return `<td class="${String(v).startsWith('hyper') ? 'hyper' : 'hypo'}">${
        esc(String(v).replace('hyper', 'more methylated').replace('hypo', 'less methylated'))}</td>`;
      if (c === 'probe_id') return `<td><code>${esc(v)}</code></td>`;
      if (typeof v === 'number' && !Number.isInteger(v)) {
        return `<td>${Math.abs(v) < 1e-3 && v !== 0 ? v.toExponential(2) : v.toFixed(3)}</td>`;
      }
      return `<td>${esc(v)}</td>`;
    }).join('') + '</tr>').join('')}</tbody></table>`;
}

function ctx(id, h) {
  const c = $('#' + id);
  if (!c) return null;
  const r = c.getBoundingClientRect();
  if (!r.width) return null;              // hidden tab; redrawn when shown
  const d = window.devicePixelRatio || 1;
  c.width = r.width * d; c.height = h * d;
  const x = c.getContext('2d');
  x.setTransform(d, 0, 0, d, 0, 0);
  x.clearRect(0, 0, r.width, h);
  return { x, W: r.width, H: h };
}

function drawAll(r) { volcano(r.volcano); roc(r.roc); mech(r.mechanics_counts); }

function blank(x, W, H, msg) {
  x.fillStyle = '#9aabbc'; x.font = '13px sans-serif';
  x.fillText(msg, W / 2 - x.measureText(msg).width / 2, H / 2);
}

function volcano(v) {
  const d = ctx('volcano', 380); if (!d) return;
  const { x, W, H } = d, pad = 54;
  if (!v || !v.x || !v.x.length) return blank(x, W, H, 'No comparison in this run.');
  const xm = Math.max(0.2, ...v.x.map(Math.abs)) * 1.08;
  const ym = Math.max(2, ...v.y) * 1.08;
  const px = t => pad + (t + xm) / (2 * xm) * (W - pad - 20);
  const py = t => H - pad - (t / ym) * (H - pad - 24);
  x.strokeStyle = '#eef2f7'; x.fillStyle = '#8494a5'; x.font = '11px sans-serif';
  for (let i = 0; i <= 4; i++) {
    const val = ym * i / 4, y = py(val);
    x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 20, y); x.stroke();
    x.fillText(val.toFixed(0), 10, y + 3);
  }
  for (let i = -2; i <= 2; i++) {
    const val = xm * i / 2, X = px(val);
    x.beginPath(); x.moveTo(X, 18); x.lineTo(X, H - pad); x.stroke();
    x.fillText(val.toFixed(2), X - 13, H - pad + 17);
  }
  for (let i = 0; i < v.x.length; i++) {
    const sig = v.y[i] > 1.301 && Math.abs(v.x[i]) >= 0.2;
    x.fillStyle = sig ? (v.x[i] > 0 ? 'rgba(192,57,43,.55)' : 'rgba(26,122,58,.55)')
      : 'rgba(154,165,177,.3)';
    x.beginPath(); x.arc(px(v.x[i]), py(v.y[i]), 2.4, 0, 6.284); x.fill();
  }
  x.fillStyle = '#3b4756'; x.font = '12px sans-serif';
  x.fillText('size of the difference', W / 2 - 62, H - 12);
  x.save(); x.translate(16, H / 2 + 46); x.rotate(-Math.PI / 2);
  x.fillText('confidence', 0, 0); x.restore();
}

function roc(r) {
  const d = ctx('roc', 300); if (!d) return;
  const { x, W, H } = d, pad = 46;
  if (!r || !r.fpr) return blank(x, W, H, 'No prediction test in this run.');
  const px = t => pad + t * (W - pad - 18), py = t => H - pad - t * (H - pad - 20);
  x.strokeStyle = '#eef2f7';
  for (let i = 0; i <= 5; i++) {
    const y = py(i / 5); x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 18, y); x.stroke();
  }
  x.strokeStyle = '#c9d3de'; x.setLineDash([4, 4]);
  x.beginPath(); x.moveTo(px(0), py(0)); x.lineTo(px(1), py(1)); x.stroke(); x.setLineDash([]);
  x.strokeStyle = '#2e75b6'; x.lineWidth = 2.6; x.beginPath();
  r.fpr.forEach((f, i) => { const X = px(f), Y = py(r.tpr[i]); i ? x.lineTo(X, Y) : x.moveTo(X, Y); });
  x.stroke(); x.lineWidth = 1;
  x.fillStyle = '#3b4756'; x.font = '12px sans-serif';
  x.fillText('false alarms', W / 2 - 36, H - 11);
  x.save(); x.translate(16, H / 2 + 40); x.rotate(-Math.PI / 2);
  x.fillText('correct calls', 0, 0); x.restore();
}

function mech(counts) {
  const d = ctx('mech', 300); if (!d) return;
  const { x, W, H } = d, pad = 46;
  const label = { silencing: 'switched off', activation: 'switched on', ambiguous: 'unclear' };
  const colour = { silencing: '#c0392b', activation: '#1a7a3a', ambiguous: '#9aa5b1' };
  const e = Object.entries(counts || {}).sort((a, b) => b[1] - a[1]);
  if (!e.length) return blank(x, W, H, 'No effect call in this run.');
  const max = Math.max(...e.map(v => v[1])) * 1.2 || 1;
  const bw = (W - pad - 24) / e.length;
  e.forEach(([k, v], i) => {
    const h = (v / max) * (H - pad - 44);
    const X = pad + i * bw + bw * 0.18, Y = H - pad - h;
    x.fillStyle = colour[k] || '#7d4fbf';
    x.fillRect(X, Y, bw * 0.64, h);
    x.fillStyle = '#16212c'; x.font = 'bold 14px sans-serif';
    x.fillText(v.toLocaleString(), X, Y - 8);
    x.fillStyle = '#67788a'; x.font = '12px sans-serif';
    x.fillText(label[k] || k, X, H - pad + 17);
  });
  x.strokeStyle = '#dde4ec';
  x.beginPath(); x.moveTo(pad, H - pad); x.lineTo(W - 18, H - pad); x.stroke();
}

boot();
})();
