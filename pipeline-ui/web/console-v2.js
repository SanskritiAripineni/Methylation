/* console-v2 — sidebar launcher.
 *
 * Standalone: loads no part of builder.js (a closed IIFE with no exports).
 * Every number and label on screen comes from a server response. Nothing here
 * computes an estimate, infers a verdict, or fills in a threshold the config
 * did not supply.
 */
(() => {
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const STUDY = 'brca_sim';

const state = {
  mode: 'explore',          // sidebar mode
  tier: 'demo',
  source: 'bundled',
  study: null,              // study config from the server
  thresholds: {},           // user overrides only; blanks mean "use the config default"
  preview: null,
  run: null,                // the live snapshot
  runId: null,
  logCursor: 0,
  follow: true,
  pollTimer: null,
  paths: { matrix: '', manifest: '', annotation: '' },
};

const api = {
  async get(url) {
    const r = await fetch(url);
    const j = await r.json().catch(() => ({ error: r.statusText }));
    if (!r.ok) throw new Error(j.error || r.statusText);
    return j;
  },
  async post(url, body) {
    const r = await fetch(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const j = await r.json().catch(() => ({ error: r.statusText }));
    if (!r.ok) throw new Error(j.error || r.statusText);
    return j;
  },
};

const fmtSecs = s => {
  if (s == null) return null;
  if (s < 60) return s.toFixed(1) + 's';
  const m = Math.floor(s / 60);
  return m + 'm ' + Math.round(s - m * 60) + 's';
};
const fmtBytes = b => b < 1024 ? b + ' B'
  : b < 1048576 ? (b / 1024).toFixed(1) + ' KB' : (b / 1048576).toFixed(2) + ' MB';

/* ------------------------------------------------------------------- tips */
function wireTip(el, text) {
  if (!text) return;
  const tip = $('#tip');
  el.addEventListener('mouseenter', e => {
    tip.textContent = text;
    tip.style.opacity = 1;
    const r = el.getBoundingClientRect();
    tip.style.left = Math.min(window.innerWidth - 360, r.left) + 'px';
    tip.style.top = (r.bottom + 6) + 'px';
  });
  el.addEventListener('mouseleave', () => { tip.style.opacity = 0; });
}

/* ------------------------------------------------------------------- boot */
async function boot() {
  wireChrome();
  try {
    state.study = await api.get(`/api/v2/studies/${STUDY}`);
  } catch (err) {
    $('#thresholds').innerHTML = `<p class="hint">Could not load the study config: ${esc(err.message)}</p>`;
    return;
  }
  $('#brand-sub').textContent = state.study.label;
  renderSource();
  renderThresholds();
  renderNotApplicable();
  renderRepro();
  renderVerdict(null);
  await refreshRuns();

  // Re-attach if something is already executing server-side. The picker is
  // realigned FROM this, never the other way round.
  try {
    const active = await api.get('/api/v2/active');
    if (active.active) attach(active.active);
  } catch (_) { /* nothing running */ }
}

function wireChrome() {
  $$('.mode').forEach(b => b.addEventListener('click', () => {
    state.mode = b.dataset.mode;
    $$('.mode').forEach(x => x.classList.toggle('active', x === b));
    $('#pane-explore').classList.toggle('active', state.mode === 'explore');
    $('#pane-new').classList.toggle('active', state.mode === 'new');
  }));

  $$('.tile').forEach(t => t.addEventListener('click', () => {
    if (t.disabled) return;
    state.source = t.dataset.source;
    $$('.tile').forEach(x => x.classList.toggle('selected', x === t));
    renderSource();
    // A gate computed against a different source is not a gate for this one.
    invalidatePreview();
  }));

  $$('.tierbtn').forEach(b => b.addEventListener('click', () => {
    if (b.classList.contains('locked')) return;
    state.tier = b.dataset.mode;
    $$('.tierbtn').forEach(x => x.classList.toggle('active', x === b));
    $('#demo-n-wrap').style.display = state.tier === 'demo' ? 'flex' : 'none';
    state.preview = null;
    $('#checks').innerHTML = '<p class="hint">Tier changed — run the readiness check again.</p>';
    updateStartGate();
  }));
  $('#demo-n-wrap').style.display = 'flex';

  $('#btn-inspect').addEventListener('click', inspect);
  $('#btn-check').addEventListener('click', check);
  $('#btn-start').addEventListener('click', start);
  $('#btn-cancel').addEventListener('click', cancel);
  $('#show-rehearsals').addEventListener('change', refreshRuns);

  $$('.mtab').forEach(t => t.addEventListener('click', () => {
    $$('.mtab').forEach(x => x.classList.toggle('active', x === t));
    $$('.mview').forEach(v => v.classList.toggle('active', v.id === 'view-' + t.dataset.view));
  }));

  const log = $('#logbody');
  log.addEventListener('scroll', () => {
    state.follow = log.scrollHeight - log.scrollTop - log.clientHeight < 30;
    $('#log-follow').textContent = state.follow ? 'following' : 'paused — scroll to the bottom to resume';
  });

  $('#btn-report-new').addEventListener('click', () => {
    if (state.runId) window.open(reportUrl(state.runId), '_blank');
  });
  $('#btn-download').addEventListener('click', () => {
    if (state.runId) window.location = `/api/v2/runs/${state.runId}/download`;
  });
}

const reportUrl = id => `/api/v2/runs/${id}/file?path=run_report.html&inline=1`;

/* --------------------------------------------------------- source panel */
function renderSource() {
  const box = $('#sourcepanel');
  const d = state.study ? state.study.data : {};
  if (state.source === 'bundled') {
    box.innerHTML = `<div class="box">
      <b>${esc(state.study.label)}</b>
      <p class="hint">${esc(d.provenance || '')}</p>
      <p class="hint mono">${esc(d.matrix_path)}<br>${esc(d.manifest_path)}</p>
    </div>`;
  } else if (state.source === 'local') {
    box.innerHTML = `<div class="box">
      <div class="field"><label>Beta-value matrix (TSV / TSV.gz)</label>
        <input type="text" id="p-matrix" value="${esc(state.paths.matrix || d.matrix_path || '')}"></div>
      <div class="field"><label>Sample table (TSV)</label>
        <input type="text" id="p-manifest" value="${esc(state.paths.manifest || d.manifest_path || '')}"></div>
      <div class="field"><label>Probe annotation (TSV) <span class="sub">optional</span></label>
        <input type="text" id="p-annotation" value="${esc(state.paths.annotation || d.annotation_path || '')}"></div>
      <p class="hint">Read where they already sit. Nothing is copied or uploaded.</p>
    </div>`;
    ['matrix', 'manifest', 'annotation'].forEach(k => {
      state.paths[k] = $('#p-' + k).value.trim();
      $('#p-' + k).addEventListener('input', e => {
        state.paths[k] = e.target.value.trim();
        invalidatePreview();
      });
    });
  } else if (state.source === 'upload') {
    box.innerHTML = `<div class="box">
      <input type="file" id="upl" accept=".tsv,.csv,.txt">
      <p class="hint">Sample tables and small matrices only, parsed server-side. Anything over
        100 MB is refused — use <b>Local path</b>, which reads the file where it sits instead of
        pushing it through the browser so the server can read its header.</p>
      <div id="upl-out"></div>
    </div>`;
    $('#upl').addEventListener('change', uploadInspect);
  } else if (state.source === 'repeat') {
    box.innerHTML = `<div class="box"><p class="hint">Loading earlier runs…</p></div>`;
    api.get('/api/v2/runs?include_rehearsals=1').then(j => {
      if (!j.runs.length) {
        box.innerHTML = `<div class="box"><p class="hint">No earlier runs this session.
          Runs are held in memory, so restarting the server clears them.</p></div>`;
        return;
      }
      box.innerHTML = `<div class="box">
        <div class="field"><label>Reuse settings from</label>
          <select id="repeat-pick" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:8px">
            ${j.runs.map(r => `<option value="${esc(r.id)}">${esc(r.id)} — ${esc(r.label)}</option>`).join('')}
          </select></div>
        <div id="repeat-note"></div></div>`;
      const load = async () => {
        const id = $('#repeat-pick').value;
        try {
          const rec = await api.get(`/api/v2/runs/${id}/record`);
          const t = rec.thresholds || {};
          const has = Object.keys(t).length > 0;
          $('#repeat-note').innerHTML = has
            ? `<p class="hint">Recorded settings applied: ${Object.entries(t)
                 .map(([k, v]) => `${esc(k)}=${esc(v)}`).join(', ')}.<br>
                 <b>Thresholds only.</b> Input paths are not reused — a demo's recorded matrix
                 points at that run's own subset file, which is not the cohort you want.</p>`
            : `<p class="hint"><b>That run recorded no settings.</b> "Repeat" would silently mean
                 "run with today's defaults", which is not the same thing.</p>`;
          if (has) { state.thresholds = { ...t }; renderThresholds(); }
        } catch (err) {
          $('#repeat-note').innerHTML = `<p class="hint">${esc(err.message)}</p>`;
        }
      };
      $('#repeat-pick').addEventListener('change', load);
      load();
    });
  } else {
    box.innerHTML = '';
  }
  updateStartGate();
}

async function uploadInspect(e) {
  const file = e.target.files[0];
  if (!file) return;
  const out = $('#upl-out');
  if (file.size > 100 * 1024 * 1024) {
    out.innerHTML = `<p class="hint">That file is ${(file.size / 1048576).toFixed(0)} MB.
      Uploads are capped at 100 MB — use the <b>Local path</b> field.</p>`;
    return;
  }
  out.innerHTML = '<p class="hint">Parsing server-side…</p>';
  const r = await fetch('/api/v2/uploads/inspect', {
    method: 'POST', headers: { 'X-Filename': file.name }, body: file,
  });
  const j = await r.json();
  if (!r.ok) { out.innerHTML = `<p class="hint">${esc(j.error)}</p>`; return; }
  const t = j.table || {};
  out.innerHTML = `<p class="hint">${esc(file.name)} — ${t.n_columns || 0} columns,
    ${(t.n_rows || 0).toLocaleString()} rows, ${esc(t.separator || '')}-separated.<br>
    ${esc((t.columns || []).slice(0, 6).join(', '))}</p>`;
}

/* --------------------------------------------------------- capabilities */
const MARK = { ok: '✓', warn: '○', fail: '✗', na: '—', fail_soft: '✗' };

async function inspect() {
  const box = $('#capabilities');
  box.innerHTML = '<p class="hint">Reading the files…</p>';
  try {
    const j = await api.post('/api/v2/inputs/inspect', {
      study: STUDY,
      matrix_path: state.source === 'local' ? state.paths.matrix : null,
      manifest_path: state.source === 'local' ? state.paths.manifest : null,
      annotation_path: state.source === 'local' ? state.paths.annotation : null,
    });
    box.innerHTML = j.capabilities.map(c => `
      <div class="caprow" data-tip="${esc(c.consequence)}">
        <span class="capmark ${c.state === 'fail_soft' ? 'fail' : c.state}">${MARK[c.state] || '?'}</span>
        <span class="cl"><b>${esc(c.label)}</b>${c.required ? ' <span class="sub">· required</span>' : ''}
          <div class="cd">${esc(c.detail)}</div></span>
      </div>`).join('');
    $$('.caprow', box).forEach(el => wireTip(el, el.dataset.tip));
  } catch (err) {
    box.innerHTML = `<p class="hint">${esc(err.message)}</p>`;
  }
}

/* ----------------------------------------------------------- thresholds */
function renderThresholds() {
  const host = $('#thresholds');
  const tcfg = state.study.thresholds || {};
  host.innerHTML = Object.entries(tcfg).map(([key, spec]) => {
    const val = state.thresholds[key] !== undefined ? state.thresholds[key] : spec.default;
    if (spec.type === 'bool') {
      return `<div class="thr" data-key="${key}">
        <label class="checkline"><input type="checkbox" data-bool="${key}" ${val ? 'checked' : ''}>
          <b>${esc(spec.label || key)}</b></label>
        ${whyHtml(spec)}
      </div>`;
    }
    const dir = spec.direction === 'lower_is_stricter' ? 'lower is stricter'
      : spec.direction === 'higher_is_stricter' ? 'higher is stricter' : '';
    return `<div class="thr" data-key="${key}">
      <div class="thead"><b>${esc(spec.label || key)}</b><span class="dir">${esc(dir)}</span></div>
      <div class="anchors">${(spec.anchors || []).map(a => `
        <button class="anchor ${Number(a.value) === Number(val) ? 'on' : ''}"
                data-anchor="${key}" data-value="${a.value}" title="${esc(a.note || '')}">
          <b>${a.value}</b>${esc(a.label || '')}</button>`).join('')}</div>
      <div class="valrow">
        <input type="number" data-num="${key}" value="${val}"
               min="${spec.min ?? ''}" max="${spec.max ?? ''}" step="${spec.step ?? 'any'}">
        <span class="effect" data-effect="${key}"></span>
      </div>
      ${whyHtml(spec)}
    </div>`;
  }).join('');

  $$('[data-anchor]', host).forEach(b => b.addEventListener('click', () => {
    setThreshold(b.dataset.anchor, Number(b.dataset.value));
  }));
  $$('[data-num]', host).forEach(i => i.addEventListener('change', () => {
    setThreshold(i.dataset.num, Number(i.value));
  }));
  $$('[data-bool]', host).forEach(i => i.addEventListener('change', () => {
    state.thresholds[i.dataset.bool] = i.checked;
    invalidatePreview();
  }));
  Object.keys(tcfg).forEach(refreshEffect);
}

function whyHtml(spec) {
  if (!spec.convention) return '';
  const label = spec.default !== undefined ? `Why ${spec.default}?` : 'Why?';
  return `<details class="disclosure"><summary>${esc(label)}</summary>
    <div class="why">${esc(spec.convention)}</div></details>`;
}

function setThreshold(key, value) {
  state.thresholds[key] = value;
  renderThresholds();
  invalidatePreview();
}

function invalidatePreview() {
  state.preview = null;
  $('#checks').innerHTML = '<p class="hint">Settings changed — run the readiness check again.</p>';
  updateStartGate();
}

async function refreshEffect(key) {
  const el = $(`[data-effect="${key}"]`);
  if (!el) return;
  const spec = (state.study.thresholds || {})[key] || {};
  const val = state.thresholds[key] !== undefined ? state.thresholds[key] : spec.default;
  el.textContent = '';
  el.classList.remove('refused');
  try {
    const q = new URLSearchParams({ key, value: val });
    if (state.runId) q.set('run', state.runId);
    const j = await api.get(`/api/v2/studies/${STUDY}/threshold-effect?${q}`);
    if (j.available) {
      el.textContent = j.text;
    } else {
      el.textContent = j.reason || '';
      el.classList.add('refused');
    }
  } catch (_) { /* leave blank rather than invent a number */ }
}

function renderNotApplicable() {
  const na = state.study.not_applicable || {};
  $('#na-count').textContent = `(${Object.keys(na).length})`;
  $('#not-applicable').innerHTML = Object.entries(na).map(([k, v]) => `
    <div class="na"><b>${esc(v.label || k)}</b>
      <p>${esc(v.reason || '')}</p>
      <p><i>Consequence:</i> ${esc(v.consequence || '')}</p></div>`).join('');
}

function renderRepro() {
  const r = state.study.reproducibility || {};
  const pk = Object.entries(r.packages || {})
    .map(([k, v]) => `${k} ${v || '—'}`).join(' · ');
  $('#repro').innerHTML = [
    `python ${esc(r.python || '?')} · ${esc(r.platform || '')}`,
    esc(pk),
    `git ${esc(r.git_commit || 'unknown')}${r.git_dirty ? ' (uncommitted changes)' : ''}`,
    `array type: ${esc(r.array_type || 'n/a')} — ${esc(r.array_type_note || '')}`,
    `annotation version: ${esc(r.annotation_version || 'n/a')} — ${esc(r.annotation_version_note || '')}`,
  ].join('<br>');
}

/* -------------------------------------------------------------- readiness */
async function check() {
  const box = $('#checks');
  box.innerHTML = '<p class="hint">Checking…</p>';
  const q = new URLSearchParams({
    mode: state.tier,
    thresholds: JSON.stringify(state.thresholds),
    n_per_class: $('#demo-n').value,
    paths: JSON.stringify(runPaths()),
  });
  try {
    const p = await api.get(`/api/v2/studies/${STUDY}/preview?${q}`);
    state.preview = p;
    box.innerHTML = p.checks.map(c => `
      <div class="check ${c.state}">
        <b>${esc(c.label)}</b>
        <div class="cdetail">${esc(c.detail)}</div>
        ${c.fix ? `<div class="cfix">${esc(c.fix)}</div>` : ''}
      </div>`).join('');
    renderStepPlan(p);
    renderEstimateNote(p);
    lockTiers(p);
    updateStartGate();
  } catch (err) {
    box.innerHTML = `<div class="check fail"><b>Readiness check failed</b>
      <div class="cdetail">${esc(err.message)}</div></div>`;
    state.preview = null;
    updateStartGate();
  }
}

function lockTiers(p) {
  const gate = (p.checks || []).find(c => c.id === 'demo_gate');
  const btn = $('.tierbtn[data-mode="full"]');
  const locked = state.tier === 'full' && gate && gate.state === 'fail';
  btn.classList.toggle('locked', !!locked);
  btn.title = locked ? gate.detail : '';
}

/* A source that can be inspected but not launched disables Start, with the
 * reason on screen — never a silent fallback to the bundled cohort. */
function sourceBlock() {
  if (state.source === 'upload') {
    return 'Uploads are inspect-only: they show you what a table provides, but a run is not ' +
      'pointed at one. Use Local path, which reads the file where it sits.';
  }
  if (state.source === 'fastq') {
    return 'Raw FASTQ needs alignment and methylation calling (Bismark) first — a separate pipeline.';
  }
  if (state.source === 'local' && !(state.paths.matrix && state.paths.manifest)) {
    return 'Local path needs both a matrix and a sample table. Empty fields would silently ' +
      'fall back to the bundled cohort.';
  }
  return null;
}

function runPaths() {
  return state.source === 'local' ? { ...state.paths } : {};
}

function updateStartGate() {
  const p = state.preview;
  const btn = $('#btn-start');
  const note = $('#start-note');
  const blocked = sourceBlock();
  if (blocked) {
    btn.disabled = true;
    btn.textContent = 'Start';
    note.textContent = blocked;
    return;
  }
  if (!p) {
    btn.disabled = true;
    note.textContent = 'Run the readiness check first.';
    return;
  }
  // ONLY fail blocks. A warning that fires on every project must never make
  // Start permanently unpressable.
  btn.disabled = !p.can_start;
  btn.textContent = p.can_start ? `Start ${state.tier} run` : 'Blocked';
  note.textContent = p.can_start
    ? (p.warn_count
      ? `${p.warn_count} warning${p.warn_count === 1 ? '' : 's'} — shown above, not blocking.`
      : 'All checks clear.')
    : `Blocked by: ${p.blocking.join(', ')}. Warnings do not block; these are failures.`;
}

function renderEstimateNote(p) {
  const e = p.estimates || {};
  $('#estimate-note').innerHTML = e.total_seconds == null
    ? `<b>No time estimate.</b> This project has no completed <b>${esc(p.mode)}</b> run to measure,
       and a modelled guess would be a number nobody stands behind.`
    : `Estimated <b>${esc(fmtSecs(e.total_seconds))}</b> — ${esc(e.basis)}.
       Demo and full timings are never mixed.`;
}

function renderStepPlan(p) {
  $('#stepcards').innerHTML = (p.steps || []).map(s => `
    <div class="stepcard ${s.runs ? '' : 'skipped'}">
      <span class="sdot"></span>
      <span><span class="sname">${esc(s.name)}</span>
        <div class="smeta">${s.runs ? 'will run' : 'skipped — ' + esc(s.reason || 'no reason recorded')}
          ${s.caveat ? '· ' + esc(s.caveat) : ''}</div></span>
      <span class="stime">${s.estimate_seconds != null ? esc(fmtSecs(s.estimate_seconds)) : '—'}</span>
    </div>`).join('');
}

/* ---------------------------------------------------------------- launch */
async function start() {
  const btn = $('#btn-start');
  btn.disabled = true;
  try {
    const j = await api.post('/api/v2/runs', {
      study: STUDY,
      mode: state.tier,
      n_per_class: Number($('#demo-n').value),
      name: $('#run-name').value.trim(),
      source_label: $('#source-label').value.trim(),
      thresholds: state.thresholds,
      paths: runPaths(),
    });
    $('#logbody').innerHTML = '';
    state.logCursor = 0;
    attach(j.run_id);
    $$('.mtab').forEach(t => t.classList.toggle('active', t.dataset.view === 'steps'));
    $$('.mview').forEach(v => v.classList.toggle('active', v.id === 'view-steps'));
  } catch (err) {
    $('#start-note').textContent = err.message;
    btn.disabled = false;
  }
}

function attach(runId) {
  state.runId = runId;
  state.logCursor = 0;
  clearTimeout(state.pollTimer);
  poll();
}

async function poll() {
  if (!state.runId) return;
  let snap;
  try {
    snap = await api.get(`/api/v2/runs/${state.runId}?since=${state.logCursor}`);
  } catch (err) {
    $('#run-title').textContent = err.message;
    return;
  }
  state.run = snap;
  state.logCursor = snap.log_count;
  appendLog(snap.logs);
  renderRunSteps(snap);
  renderVerdict(snap);
  renderRunBar(snap);

  const live = snap.status === 'running' || snap.status === 'queued';
  $('#btn-cancel').disabled = !live;
  if (live) {
    state.pollTimer = setTimeout(poll, 3000);
    return;
  }
  $('#btn-start').disabled = false;
  await finishRun(snap);
  refreshRuns();
}

function renderRunBar(snap) {
  // The label comes from the run record, not from the sidebar picker: if the
  // two can drift, a report renders one cohort's title over another's rows.
  const pill = `<span class="pill ${snap.mode}">${esc(snap.mode)}</span>`;
  $('#run-title').innerHTML = `<b>${esc(snap.label || snap.id)}</b> ${pill}
    <span class="rid mono">${esc(snap.id)}</span>` +
    (snap.waiting_behind ? ` <span class="hint">waiting behind ${esc(snap.waiting_behind)}</span>` : '');
  // Wall clock, not the sum of finished steps.
  $('#run-elapsed').textContent = fmtSecs(snap.elapsed_wall) || '';
  if (snap.cancel_outcome) $('#start-note').textContent = snap.cancel_outcome;
}

function renderRunSteps(snap) {
  const est = (state.preview && state.preview.estimates && state.preview.estimates.per_step) || {};
  $('#stepcards').innerHTML = (snap.steps || []).map(s => {
    const meta = s.state === 'skipped' || s.state === 'failed'
      ? esc(s.reason || 'no reason recorded')
      : (s.caveat ? esc(s.caveat) : s.state);
    const time = s.seconds != null ? fmtSecs(s.seconds)
      : (est[s.name] != null ? '~' + fmtSecs(est[s.name]) : '—');
    return `<div class="stepcard ${s.state}">
      <span class="sdot"></span>
      <span><span class="sname">${esc(s.name)}</span><div class="smeta">${meta}</div></span>
      <span class="stime">${esc(time)}</span>
    </div>`;
  }).join('');
  if (snap.demo_adjustments && snap.demo_adjustments.length) {
    $('#stepcards').insertAdjacentHTML('afterbegin', snap.demo_adjustments.map(a => `
      <div class="check warn"><b>Demo adjustment · ${esc(a.param)} ${a.from} → ${a.to}</b>
        <div class="cdetail">${esc(a.why)}</div></div>`).join(''));
  }
}

function appendLog(lines) {
  if (!lines || !lines.length) return;
  const body = $('#logbody');
  if (body.querySelector('.muted')) body.innerHTML = '';
  body.insertAdjacentHTML('beforeend', lines.map(l =>
    `<div class="l-${esc(l.level)}"><span class="t">${l.t.toFixed(2)}s</span>${esc(l.message)}</div>`
  ).join(''));
  if (state.follow) body.scrollTop = body.scrollHeight;
}

async function finishRun(snap) {
  const files = snap.artifacts || [];
  $('#btn-download').disabled = !files.length;
  $('#filetable').innerHTML = files.length
    ? `<table><thead><tr><th>File</th><th>Size</th><th></th></tr></thead><tbody>${
      files.map(f => `<tr><td><code>${esc(f.name)}</code></td><td>${fmtBytes(f.size)}</td>
        <td><a href="/api/v2/runs/${esc(snap.id)}/file?path=${encodeURIComponent(f.name)}">download</a></td>
      </tr>`).join('')}</tbody></table>`
    : '<p class="hint pad">No artifact was collected — no producing step succeeded.</p>';

  if (snap.has_report) {
    $('#report-frame').src = reportUrl(snap.id);
    $('#report-label').innerHTML = `<b>run_report.html</b> — written by this run
      (${esc(snap.id)}), by the report generator this project already had.`;
    $('#btn-report-new').disabled = false;
  } else {
    $('#report-frame').removeAttribute('src');
    $('#report-label').textContent =
      'No report: the report step did not succeed in this run. Nothing older is shown in its place.';
    $('#btn-report-new').disabled = true;
  }
  Object.keys(state.study.thresholds || {}).forEach(refreshEffect);
}

async function cancel() {
  if (!state.runId) return;
  try {
    const j = await api.post(`/api/v2/runs/${state.runId}/cancel`);
    $('#start-note').textContent = j.outcome;
  } catch (err) {
    $('#start-note').textContent = err.message;
  }
}

/* --------------------------------------------------------------- verdict */
function renderVerdict(snap) {
  const v = snap && snap.verdict;
  const el = $('#verdict-level');
  if (!v) {
    el.className = 'vlevel';
    el.textContent = 'no run selected';
    $('#verdict-summary').textContent = 'Pick a run on the left, or launch a new one.';
    $('#verdict-reasons').innerHTML = '';
    $('#verdict-caveat').textContent = (state.study && state.study.standing_caveat) || '';
    return;
  }
  el.className = 'vlevel ' + v.level;
  el.textContent = v.level;
  $('#verdict-summary').textContent = v.summary;
  $('#verdict-reasons').innerHTML = (v.reasons || []).map(r => `<li>${esc(r)}</li>`).join('');
  $('#verdict-caveat').textContent = v.caveat || '';
}

/* -------------------------------------------------------------- run list */
async function refreshRuns() {
  const includeRehearsals = $('#show-rehearsals').checked;
  const box = $('#run-list');
  try {
    const j = await api.get(`/api/v2/runs?include_rehearsals=${includeRehearsals ? 1 : 0}`);
    if (!j.runs.length) {
      box.innerHTML = `<p class="hint">${includeRehearsals
        ? 'No runs yet this session.'
        : 'No full runs yet. Rehearsals are hidden — tick the box above to see them.'}</p>`;
      return;
    }
    box.innerHTML = j.runs.map(r => `
      <button class="run ${r.id === state.runId ? 'on' : ''}" data-run="${esc(r.id)}">
        <span class="rlabel">${esc(r.label)}</span>
        <span class="pill ${esc(r.mode)}">${esc(r.mode)}</span>
        ${r.status === 'error' ? '<span class="pill err">failed</span>' : ''}
        <div class="rid">${esc(r.id)} · ${esc(r.verdict)} · ${esc(fmtSecs(r.elapsed) || '')}</div>
      </button>`).join('');
    $$('[data-run]', box).forEach(b => b.addEventListener('click', () => select(b.dataset.run)));
  } catch (err) {
    box.innerHTML = `<p class="hint">${esc(err.message)}</p>`;
  }
}

async function select(runId) {
  state.runId = runId;
  state.logCursor = 0;
  $('#logbody').innerHTML = '';
  clearTimeout(state.pollTimer);
  await poll();
  await renderProvenance(runId);
  refreshRuns();
}

async function renderProvenance(runId) {
  const box = $('#provenance');
  try {
    const rec = await api.get(`/api/v2/runs/${runId}/record`);
    const rows = [
      ['run id', rec.run_id],
      ['tier', rec.mode],
      ['label', rec.label],
      ['source label', rec.source_label || '—'],
      ['status', rec.status + (rec.error ? ' — ' + rec.error : '')],
      ['verdict', rec.verdict && rec.verdict.level],
      ['validated by', rec.validated_by || (rec.mode === 'full' ? 'nothing' : 'n/a')],
      ['data provenance', rec.data_provenance || '—'],
      ['samples per class', rec.n_per_class == null ? 'full cohort' : rec.n_per_class],
      ['normalization', 'upstream — not a choice this pipeline makes'],
      ...Object.entries(rec.thresholds || {}).map(([k, v]) => [k, String(v)]),
    ];
    box.innerHTML = rows.map(([k, v]) =>
      `<div class="prow"><span class="pk">${esc(k)}</span><span class="pv">${esc(v)}</span></div>`).join('');
  } catch (err) {
    box.innerHTML = `<p class="hint">${esc(err.message)}</p>`;
  }
}

boot();
})();
