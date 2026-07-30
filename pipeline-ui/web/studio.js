/* Methylation Studio (v3).
 *
 * Plain language on the surface, the v2 checks underneath: the same readiness
 * gate runs before every launch and a `fail` still blocks.
 *
 * The middle opens on the published study - its real report and its real
 * numbers - so nothing is ever a blank screen. That view is labelled as the
 * published study everywhere it appears, and is replaced by your own run the
 * moment one finishes.
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
  reference: null,     // the published study
  dash: null,          // whatever the Results tab is currently showing
  showing: 'reference',// 'reference' | 'run'
  preset: 'standard',
  thresholds: {},
  useExample: true,    // the example cohort is selected on load, so every
                       // run button works the moment the page opens
  runId: null,
  snap: null,
  logCursor: 0,
  timer: null,
  ticker: null,
  filter: '',
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

function say(el, kind, html) { el.className = 'status show ' + kind; el.innerHTML = html; }
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
  renderWorkspace(state.setup.workspace, state.setup.readiness, true);
  wire();
  await refreshHistory();
  renderTiers();

  // Fill the middle before anything has been run.
  try {
    state.reference = await api.get('/api/v3/reference');
    showReference();
  } catch (err) {
    $('#dash-title').textContent = 'Could not load the published study';
    $('#dash-sub').textContent = err.message;
  }
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

  $('#use-example').addEventListener('click', selectExample);

  $$('.tab').forEach(t => t.addEventListener('click', () => {
    $$('.tab').forEach(x => x.classList.toggle('active', x === t));
    $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + t.dataset.view));
    if (t.dataset.view === 'results' && state.dash) drawCharts(state.dash);
  }));

  $('#p-cancel').addEventListener('click', cancel);
  $('#show-tests').addEventListener('change', refreshHistory);
  $('#report-open').addEventListener('click', () => {
    const src = $('#report-frame').getAttribute('src');
    if (src) window.open(src, '_blank');
  });
  $('#report-print').addEventListener('click', () => {
    const f = $('#report-frame');
    if (f.contentWindow) f.contentWindow.print();
  });
  $('#download-all').addEventListener('click', () => {
    if (state.runId) window.location = `/api/v3/runs/${state.runId}/download`;
  });
  $('#tsearch').addEventListener('input', e => {
    state.filter = e.target.value.toLowerCase();
    if (state.dash) renderTable(state.dash);
  });
  $('#report-variant').addEventListener('change', e => {
    $('#report-frame').src = e.target.value;
  });
  window.addEventListener('resize', () => { if (state.dash) drawCharts(state.dash); });
}

const fileUrl = (id, name, inline) =>
  `/api/v3/runs/${id}/file?path=${encodeURIComponent(name)}${inline ? '&inline=1' : ''}`;

/* ------------------------------------------------------- data selection */
function selectExample() {
  state.useExample = true;
  $('#use-example').classList.add('on');
  say($('#data-status'), 'ok',
    '<b>Using the example data.</b> 130 breast samples, tumour against normal tissue. ' +
    'The individual values in it are simulated, so treat anything it finds as a demonstration ' +
    'of the method rather than a finding.');
  renderTiers();
}

async function upload(files) {
  if (!files.length) return;
  const status = $('#data-status');
  say(status, 'warn', `Reading ${files.length} file${files.length === 1 ? '' : 's'}…`);
  let last = null;
  for (const f of files) {
    if (f.size > 100 * 1024 * 1024) {
      say(status, 'bad', `<b>${esc(f.name)} is ${(f.size / 1048576).toFixed(0)} MB.</b>
        The browser limit is 100 MB. Put a file that big on this machine and point the
        pipeline at it directly.`);
      continue;
    }
    try {
        last = await fetch('/api/v3/upload', {
        method: 'POST', headers: { 'X-Filename': f.name }, body: f,
      }).then(r => r.json());
    } catch (err) { say(status, 'bad', esc(err.message)); return; }
  }
  if (last && last.workspace) {
    state.useExample = false;
    $('#use-example').classList.remove('on');
    renderWorkspace(last.workspace, last.readiness, false, last.ingest);
  }
}

/* What had to be translated to fit the pipeline. Shown, never silent: which
 * group became the comparison side decides the sign of every difference. */
function ingestHtml(ing) {
  if (!ing) return '';
  const g = (ing.mapping || {}).groups;
  const cols = (ing.mapping || {}).columns;
  const bits = [];
  if (g) {
    bits.push(`<div class="ingrow"><b>Comparing ${esc(g.case)} against ${esc(g.reference)}.</b>
      A positive difference means more methylation in <b>${esc(g.case)}</b>.
      <small>${esc(g.why)}</small></div>`);
  }
  if (cols) {
    bits.push(`<div class="ingrow">Reading <code>${esc(cols.sample_barcode || '—')}</code>
      as the sample name and <code>${esc(cols.sample_class || '—')}</code> as the group.
      <small>Your files are not modified — a translated copy is used for the run.</small></div>`);
  }
  (ing.warnings || []).forEach(w => bits.push(`<div class="ingrow warnrow">${esc(w)}</div>`));
  return bits.length ? `<div class="ingest">${bits.join('')}</div>` : '';
}

function renderWorkspace(ws, readiness, initial, ingest) {
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
      selectExample();
    });
    state.useExample = false;
    $('#use-example').classList.remove('on');
    say($('#data-status'), readiness.ready ? 'ok' : 'warn',
        esc(readiness.message) + ingestHtml(ingest));
  } else if (initial || state.useExample) {
    selectExample();
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
  }));
  renderAdvanced();
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

function renderAdvanced() {
  const tcfg = state.setup.thresholds || {};
  $('#advanced').innerHTML = Object.entries(tcfg).map(([key, spec]) => {
    const v = state.thresholds[key] !== undefined ? state.thresholds[key] : spec.default;
    if (spec.type === 'bool') {
      return `<div class="ctrl"><label class="checkline">
        <input type="checkbox" data-bool="${key}" ${v ? 'checked' : ''}>
        <span>${esc(spec.label || key)}</span></label>
        <div class="expl">${esc(PLAIN[key] || '')}</div></div>`;
    }
    return `<div class="ctrl">
      <label>${esc(spec.label || key)} <span class="val" data-val="${key}">${v}</span></label>
      <input type="range" data-range="${key}" min="${spec.min}" max="${spec.max}"
             step="${spec.step}" value="${v}">
      <div class="expl">${esc(PLAIN[key] || '')}</div>
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

async function measure(key) {
  const el = $(`[data-measured="${key}"]`);
  if (!el) return;
  try {
    const q = new URLSearchParams({ key, value: state.thresholds[key] });
    if (state.runId) q.set('run', state.runId);
    const j = await api.get(`/api/v2/studies/brca_sim/threshold-effect?${q}`);
    el.textContent = j.available ? j.text : '';
  } catch (_) { el.textContent = ''; }
}

/* ------------------------------------------------------------------ run */
function dataReady() {
  if (state.useExample) return true;
  const ws = state.setup && state.setup.workspace;
  return !!(ws && ws.roles && ws.roles.matrix && ws.roles.manifest);
}

function renderTiers() {
  const tiers = state.setup.tiers || {};
  const testDone = (state.history || []).some(r => r.mode === 'demo' && r.status === 'done');
  const order = [['demo', '▶', true], ['full', '★', false], ['plan', '✓', false]];
  $('#tiers').innerHTML = order.map(([mode, ico, primary]) => {
    const t = tiers[mode] || {};
    const needsTest = mode === 'full' && !testDone;
    // Every button stays clickable. A button that does nothing when you press
    // it is indistinguishable from a broken one, so pressing always gets you
    // an answer - and for the locked case, a one-press way out of it.
    return `<button class="tierbtn ${primary ? 'primary' : ''} ${needsTest ? 'needs' : ''}"
              data-tier="${mode}">
      <span class="ico">${ico}</span>
      <span><b>${esc(t.label || mode)}</b><span>${esc(t.blurb || '')}</span></span>
      ${needsTest ? '<span class="lock">quick test first</span>' : ''}</button>`;
  }).join('');
  $$('[data-tier]').forEach(b => b.addEventListener('click', () => launch(b.dataset.tier)));
}

async function launch(mode) {
  const status = $('#run-status');

  if (!dataReady()) {
    say(status, 'warn',
      `<b>Pick your data first.</b> Press <b>Example data</b> at the top, or drop in your own
       methylation table and sample list.`);
    return;
  }
  const testDone = (state.history || []).some(r => r.mode === 'demo' && r.status === 'done');
  if (mode === 'full' && !testDone) {
    say(status, 'warn',
      `<b>Run the quick test first.</b> It runs all 11 steps on a few samples so a full run
       does not fail an hour in on something a one-minute test would have caught.
       <button class="inlinebtn" id="do-test">Run the quick test now</button>`);
    $('#do-test').addEventListener('click', () => launch('demo'));
    return;
  }

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
    say(status, 'bad', `<b>Cannot run yet.</b> ${esc(err.message)}`);
  }
}

function startTicker() {
  clearInterval(state.ticker);
  state.ticker = setInterval(() => {
    const s = state.snap;
    if (!s || !['running', 'queued'].includes(s.status)) return;
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
  } catch (err) { say($('#run-status'), 'bad', esc(err.message)); return; }
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
  renderTiers();
}

function renderProgress(snap) {
  const p = snap.progress || {};
  const live = ['running', 'queued'].includes(snap.status);
  $('#p-step').textContent = `Step ${p.index || 0} of ${p.total || 0}`;
  $('#p-name').textContent = p.current ? p.current.friendly
    : (snap.status === 'done' ? 'Finished' : snap.status === 'error' ? 'Stopped early'
      : snap.status === 'cancelled' ? 'Stopped' : 'Starting…');
  $('#p-plain').textContent = p.current ? (p.current.plain || '') : '';
  $('#p-elapsed').textContent = secs(p.elapsed) || '0s';
  $('#p-elapsed').nextElementSibling.textContent = live ? 'running for' : 'took';
  if (!live) {
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
    const failed = (snap.steps || []).find(s => s.state === 'failed');
    el.className = 'banner bad';
    el.innerHTML = `<b>It stopped at "${esc(failed ? failed.friendly : 'a step')}".</b>
      ${esc(snap.error || '')}<div class="more">Nothing was overwritten. Earlier runs are
      untouched, and the technical log says exactly where it stopped.</div>`;
    return;
  }
  if (['running', 'queued'].includes(snap.status)) {
    el.className = 'banner test';
    el.innerHTML = `<b>Running.</b> Results and the report appear here as soon as it finishes.`;
    return;
  }
  if (snap.mode === 'demo') {
    el.className = 'banner test';
    el.innerHTML = `<b>That was a quick test on ${snap.n_per_class || 3} samples per group.</b>
      It proves all 11 steps run end to end. The numbers are not a result — press
      <b>Full analysis</b> for that.`;
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
    ${(v.reasons || []).length ? `<div class="more">${esc(v.reasons[0])}</div>` : ''}
    <div class="more">${esc(v.caveat || '')}</div>`;
}

/* ------------------------------------------------- what the middle shows */
function renderSourcePick() {
  const hasRun = !!state.runId && state.snap && !['running', 'queued'].includes(state.snap.status);
  $('#sourcepick').innerHTML = `
    <button class="src ${state.showing === 'run' ? 'on' : ''}" data-src="run" ${hasRun ? '' : 'disabled'}>
      ${hasRun ? esc(state.snap.label || 'Your run') : 'Your run'}</button>
    <button class="src ${state.showing === 'reference' ? 'on' : ''}" data-src="reference">
      Published study</button>`;
  $$('[data-src]').forEach(b => b.addEventListener('click', () => {
    if (b.disabled) return;
    if (b.dataset.src === 'reference') showReference();
    else if (state.snap) settle(state.snap);
  }));
}

function showReference() {
  const ref = state.reference;
  if (!ref) return;
  state.showing = 'reference';
  state.dash = ref;
  renderDash(ref);
  $('#report-variant').innerHTML = (ref.report_alt || [])
    .map(o => `<option value="${esc(o.url)}">${esc(o.label)}</option>`).join('');
  $('#report-variant').hidden = false;
  $('#report-frame').src = ref.report_url;
  $('#report-label').innerHTML = `<b>Published study report</b> — the completed breast analysis.`;
  $('#files-label').textContent =
    'Downloads come from runs you start here. The published study is read-only.';
  $('#filetable').innerHTML =
    '<p class="sub pad">No run selected. Start a run and its files appear here.</p>';
  $('#download-all').disabled = true;
  renderSourcePick();
}

async function settle(snap) {
  state.showing = 'run';
  const files = snap.artifacts || snap.files || [];
  $('#download-all').disabled = !files.length;
  $('#files-label').textContent = files.length
    ? `${files.length} files from ${snap.label || snap.id}. Only steps that finished are listed.`
    : 'Nothing to download — no step produced a file.';
  $('#filetable').innerHTML = files.length ? `<table><thead><tr>
      <th>File</th><th>Size</th><th>What it is</th><th></th></tr></thead><tbody>${
    files.map(f => `<tr><td><code>${esc(f.name)}</code></td><td>${bytes(f.size)}</td>
      <td>${esc(describe(f.name))}</td>
      <td><a href="${fileUrl(snap.id, f.name)}">download</a></td></tr>`).join('')}
    </tbody></table>` : '<p class="sub pad">No files.</p>';

  $('#report-variant').hidden = true;
  if (snap.has_report) {
    $('#report-frame').src = fileUrl(snap.id, 'run_report.html', true);
    $('#report-label').innerHTML = `<b>${esc(snap.label || snap.id)}</b> — ${
      esc(snap.tier_label || snap.mode)}, generated by this run.`;
  } else {
    $('#report-frame').removeAttribute('src');
    $('#report-label').innerHTML = `<b>No report from this run.</b> The report step did not
      finish. An older report is not shown in its place — it would not describe this run.`;
  }

  try {
    state.dash = await api.get(`/api/v3/runs/${snap.id}/results`);
    renderDash(state.dash);
  } catch (_) {
    state.dash = null;
    $('#dash-title').textContent = snap.label || snap.id;
    $('#dash-sub').textContent = 'This run produced no results to chart.';
    $('#cards').innerHTML = '';
    $('#movers').innerHTML = '<p class="sub">Nothing to show.</p>';
  }
  Object.keys(state.setup.thresholds || {}).forEach(measure);
  renderSourcePick();
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
    // Always fetch everything: the Full-analysis gate asks whether a quick test
    // has ever passed, and that must not depend on a display filter.
    const j = await api.get('/api/v3/history?include_tests=1');
    state.history = j.runs;
    const shown = inc ? j.runs : j.runs.filter(r => !r.is_test);
    const box = $('#history');
    if (!shown.length) {
      box.innerHTML = `<p class="sub">${inc ? 'Nothing yet.'
        : 'No full runs yet — tick the box to see test runs.'}</p>`;
      return;
    }
    box.innerHTML = shown.map(r => `
      <button class="hrun ${r.id === state.runId ? 'on' : ''}" data-open="${esc(r.id)}">
        <b>${esc(r.label)}</b>
        <span class="badge ${r.status === 'error' ? 'bad' : (r.is_test ? 'test' : 'full')}">${
          r.status === 'error' ? 'failed' : (r.is_test ? 'test' : 'full')}</span>
        <div class="meta">${esc(r.when)} · ${esc(secs(r.elapsed) || '')}${
          r.has_report ? ' · report saved' : ''}</div>
      </button>`).join('');
    $$('[data-open]').forEach(b => b.addEventListener('click', () => openRun(b.dataset.open)));
  } catch (err) {
    $('#history').innerHTML = `<p class="sub">${esc(err.message)}</p>`;
  }
}

async function openRun(runId) {
  clearTimeout(state.timer);
  state.runId = runId;
  state.logCursor = 0;
  $('#logbody').innerHTML = '';
  $('#progress').hidden = false;
  await poll();
  refreshHistory();
}

/* ====================================================== RESULTS DASHBOARD */

function renderDash(d) {
  $('#dash-title').textContent = d.title || '';
  $('#dash-sub').textContent = d.subtitle || '';
  $('#dash-note').innerHTML = d.caveat
    ? `<span class="chip">Published study</span> ${esc(d.caveat)}` : '';

  $('#cards').innerHTML = (d.cards || []).map(c => `
    <div class="card ${c.tone || ''}">
      <div class="num">${c.kind === 'auc' && typeof c.value === 'number'
        ? c.value.toFixed(3) : num(c.value)}</div>
      <div class="lbl">${esc(c.label)}</div>
      ${c.note ? `<div class="cnote">${esc(c.note)}</div>` : ''}
    </div>`).join('');

  $('#box-volcano').hidden = !(d.volcano && d.volcano.x && d.volcano.x.length);
  $('#box-cohort').hidden = !(d.cohort && d.cohort.subtypes &&
    Object.keys(d.cohort.subtypes).length);
  if (!$('#box-cohort').hidden) renderCohort(d.cohort);

  const m = d.model || {};
  $('#val-sub').textContent = m.roc_auc_mean != null
    ? `A score of 1.0 is perfect, 0.5 is a coin flip. Each dot is one round of testing on ` +
      `samples the model had not seen.`
    : 'This run did not include the prediction test.';
  $('#val-note').textContent = m.roc_auc_mean != null
    ? `${String(m.model || '').replace(/_/g, ' ')} · ${m.cv_folds || '?'} rounds · average ` +
      `${m.roc_auc_mean.toFixed(3)}${m.roc_auc_std != null ? ' ± ' + m.roc_auc_std.toFixed(3) : ''}` +
      `${m.nested ? ' · nested cross-validation' : ''}`
    : '';

  renderMovers(d);
  renderTable(d);
  drawCharts(d);
}

function renderCohort(c) {
  const subs = c.subtypes || {};
  const total = Object.values(subs).reduce((a, b) => a + b, 0) || 1;
  $('#cohortbars').innerHTML = Object.entries(subs)
    .sort((a, b) => b[1] - a[1]).map(([k, v]) => `
    <div class="crow"><span class="ck">${esc(k)}</span>
      <span class="cbar"><i style="width:${(v / total * 100).toFixed(1)}%"></i></span>
      <span class="cv">${num(v)}</span></div>`).join('') +
    `<p class="sub" style="margin-top:8px">${num(c.tumor)} tumour · ${num(c.normal)} normal
     tissue${c.age && c.age.tumor_median ? ` · median age ${c.age.tumor_median}` : ''}</p>`;
}

function renderMovers(d) {
  const rows = d.movers || [];
  if (!rows.length) { $('#movers').innerHTML = '<p class="sub">Nothing to show.</p>'; return; }
  const max = Math.max(...rows.map(r => Math.abs(r.delta))) || 1;
  $('#movers').innerHTML = rows.map(r => {
    const pct = Math.abs(r.delta) / max * 50;   // half-width each side of centre
    const up = r.delta > 0;
    return `<div class="mrow" title="${esc(r.probe)} · ${r.delta > 0 ? '+' : ''}${r.delta}">
      <span class="mgene">${esc(r.gene.split(',')[0])}</span>
      <span class="mtrack">
        <i class="mbar ${up ? 'up' : 'down'}"
           style="${up ? 'left:50%' : `right:50%`};width:${pct}%"></i>
        <i class="mzero"></i>
      </span>
      <span class="mval ${up ? 'up' : 'down'}">${up ? '+' : ''}${r.delta.toFixed(2)}</span>
    </div>`;
  }).join('');
}

function renderTable(d) {
  const t = d.table || {};
  let rows = t.rows || [];
  if (state.filter) {
    rows = rows.filter(r => Object.values(r).some(v =>
      String(v).toLowerCase().includes(state.filter)));
  }
  if (!rows.length) {
    $('#tbl-markers').innerHTML = `<p class="sub pad">${state.filter
      ? 'Nothing matches “' + esc(state.filter) + '”.' : 'Nothing to show.'}</p>`;
    return;
  }
  const cols = t.columns && t.columns.length ? t.columns : Object.keys(rows[0]);
  const nice = c => ({
    probe_id: 'site', gene: 'gene', chrom: 'chromosome', delta_beta: 'difference',
    abs_delta_beta: 'size of difference', fdr: 'confidence (FDR)', direction: 'change',
  }[c] || c.replace(/_/g, ' '));
  $('#tbl-markers').innerHTML = `<table><thead><tr>${
    cols.map(c => `<th>${esc(nice(c))}</th>`).join('')}</tr></thead><tbody>${
    rows.slice(0, 200).map(r => '<tr>' + cols.map(c => {
      const v = r[c];
      if (c === 'direction') {
        const up = String(v).startsWith('hyper');
        return `<td class="${up ? 'hyper' : 'hypo'}">${up ? 'gained' : 'lost'} methylation</td>`;
      }
      if (c === 'probe_id') return `<td><code>${esc(v)}</code></td>`;
      if (typeof v === 'number' && !Number.isInteger(v)) {
        return `<td>${Math.abs(v) < 1e-3 && v !== 0 ? v.toExponential(1) : v.toFixed(3)}</td>`;
      }
      return `<td>${esc(v)}</td>`;
    }).join('') + '</tr>').join('')}</tbody></table>
    ${rows.length > 200 ? `<p class="sub pad">Showing the first 200 of ${num(rows.length)}.</p>` : ''}`;
}

/* --------------------------------------------------------------- canvas */
function ctx2(id, h) {
  const c = document.getElementById(id);
  if (!c) return null;
  const r = c.getBoundingClientRect();
  if (!r.width) return null;                 // hidden tab; redrawn when shown
  const d = window.devicePixelRatio || 1;
  c.width = r.width * d; c.height = h * d;
  const x = c.getContext('2d');
  x.setTransform(d, 0, 0, d, 0, 0);
  x.clearRect(0, 0, r.width, h);
  return { x, W: r.width, H: h };
}

/* Canvas palette. Same rule as the stylesheet: the only colours are the ones
 * that say which way the methylation went. Axes, grids, validation dots and
 * cohort bars encode no direction, so they are grey. */
const INK = '#0d0d0d', MUTED = '#6b6b6b', GRID = '#ececec', FAINT = '#d4d4d4';
const RED = '#c0392b', GREEN = '#1a7a3a', NEUTRAL = '#bdbdbd';

function drawCharts(d) {
  donut(d.direction);
  folds(d.folds, d.model);
  if (d.volcano) volcano(d.volcano);
}

function donut(counts) {
  const d = ctx2('donut', 230); if (!d) return;
  const { x, W, H } = d;
  const label = { silencing: 'switched off', activation: 'switched on', ambiguous: 'unclear' };
  const colour = { silencing: RED, activation: GREEN, ambiguous: NEUTRAL };
  const e = Object.entries(counts || {}).filter(([, v]) => v != null && v > 0);
  if (!e.length) {
    x.fillStyle = MUTED; x.font = '13px sans-serif';
    x.fillText('No effect call in this run.', 20, H / 2);
    $('#donut-legend').innerHTML = '';
    return;
  }
  const total = e.reduce((a, b) => a + b[1], 0);
  const cx = Math.min(120, W / 3), cy = H / 2, R = Math.min(88, H / 2 - 12), r0 = R * 0.58;
  let a0 = -Math.PI / 2;
  e.forEach(([k, v]) => {
    const a1 = a0 + (v / total) * Math.PI * 2;
    x.beginPath();
    x.arc(cx, cy, R, a0, a1); x.arc(cx, cy, r0, a1, a0, true); x.closePath();
    x.fillStyle = colour[k] || '#7d4fbf'; x.fill();
    a0 = a1;
  });
  x.fillStyle = INK; x.font = 'bold 19px sans-serif'; x.textAlign = 'center';
  x.fillText(total >= 1000 ? (total / 1000).toFixed(0) + 'k' : String(total), cx, cy + 2);
  x.font = '11px sans-serif'; x.fillStyle = MUTED;
  x.fillText('sites', cx, cy + 17);
  x.textAlign = 'left';
  $('#donut-legend').innerHTML = e.map(([k, v]) => `
    <div class="dl"><i style="background:${colour[k] || '#7d4fbf'}"></i>
      <span><b>${num(v)}</b> ${esc(label[k] || k)}
        <small>${(v / total * 100).toFixed(0)}%</small></span></div>`).join('');
}

function folds(list, model) {
  const d = ctx2('folds', 230); if (!d) return;
  const { x, W, H } = d;
  const pad = 40;
  if (!list || !list.length) {
    if (model && model.roc_auc_mean != null) {
      // No per-round scores recorded, but the average is real - show that alone.
      x.fillStyle = INK; x.font = 'bold 44px sans-serif'; x.textAlign = 'center';
      x.fillText(model.roc_auc_mean.toFixed(3), W / 2, H / 2);
      x.fillStyle = MUTED; x.font = '12px sans-serif';
      x.fillText('average score across ' + (model.cv_folds || '?') + ' rounds', W / 2, H / 2 + 22);
      x.textAlign = 'left';
      return;
    }
    x.fillStyle = MUTED; x.font = '13px sans-serif';
    x.fillText('No prediction test in this run.', 20, H / 2);
    return;
  }
  const lo = Math.min(0.5, ...list) - 0.02, hi = 1.002;
  const py = v => H - pad - ((v - lo) / (hi - lo)) * (H - pad - 26);
  x.strokeStyle = GRID;
  [0.5, 0.75, 0.9, 1.0].filter(v => v >= lo).forEach(v => {
    const y = py(v);
    x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 14, y); x.stroke();
    x.fillStyle = MUTED; x.font = '10.5px sans-serif';
    x.fillText(v.toFixed(2), 8, y + 3);
  });
  const step = (W - pad - 24) / list.length;
  list.forEach((v, i) => {
    const X = pad + step * (i + 0.5), Y = py(v);
    x.strokeStyle = FAINT; x.beginPath(); x.moveTo(X, H - pad); x.lineTo(X, Y); x.stroke();
    x.fillStyle = INK; x.beginPath(); x.arc(X, Y, 6, 0, 6.284); x.fill();
    x.fillStyle = MUTED; x.font = '10.5px sans-serif'; x.textAlign = 'center';
    x.fillText('round ' + (i + 1), X, H - pad + 15);
    x.textAlign = 'left';
  });
  if (model && model.roc_auc_mean != null) {
    const y = py(model.roc_auc_mean);
    x.strokeStyle = MUTED; x.setLineDash([5, 4]);
    x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 14, y); x.stroke(); x.setLineDash([]);
  }
}

function volcano(v) {
  const d = ctx2('volcano', 360); if (!d) return;
  const { x, W, H } = d, pad = 54;
  if (!v || !v.x || !v.x.length) return;
  const xm = Math.max(0.2, ...v.x.map(Math.abs)) * 1.08;
  const ym = Math.max(2, ...v.y) * 1.08;
  const px = t => pad + (t + xm) / (2 * xm) * (W - pad - 20);
  const py = t => H - pad - (t / ym) * (H - pad - 24);
  x.strokeStyle = GRID; x.fillStyle = MUTED; x.font = '11px sans-serif';
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
    x.fillStyle = sig ? (v.x[i] > 0 ? 'rgba(192,57,43,.62)' : 'rgba(26,122,58,.62)')
      : 'rgba(154,165,177,.28)';
    x.beginPath(); x.arc(px(v.x[i]), py(v.y[i]), 2.4, 0, 6.284); x.fill();
  }
  x.fillStyle = '#3f3f3f'; x.font = '12px sans-serif';
  x.fillText('size of the difference', W / 2 - 62, H - 12);
  x.save(); x.translate(16, H / 2 + 46); x.rotate(-Math.PI / 2);
  x.fillText('confidence', 0, 0); x.restore();
}

boot();
})();
