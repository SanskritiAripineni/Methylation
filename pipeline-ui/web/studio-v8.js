/* Methylation Studio (v8).
 *
 * The one idea, inherited from v4: THERE IS A SELECTION, AND EVERYTHING
 * DESCRIBES IT. `state.selection` decides what is on screen, one request
 * answers for all of it, and every load carries the generation it started in,
 * so a response that arrives after the selection has moved on is dropped.
 *
 * WHAT V8 CHANGES, AND THE BUG IT CAME FROM
 *
 * In v7, clicking a finished run in the Runs tab loaded it twice. `openRun()`
 * called `watch()` and `select()` together; `watch()` polled the run, the
 * server answered "done", and the poller's finished-branch called `select()`
 * a second time for the run that was already on screen. Every `select()`
 * began by blanking every panel to "Loading" - so the files, the charts and
 * the numbers appeared, vanished, and came back:
 *
 *     t+0ms    blank        (select #1 from the click)
 *     t+118ms  16 files     (dashboard arrives)
 *     t+120ms  blank        (select #2, from the poller)
 *     t+201ms  16 files     (the same dashboard arrives again)
 *
 * Locally the second blank is 80ms and reads as a flicker. On a host that
 * sleeps between visits it is seconds long, and if that second request is the
 * one that fails, the screen stays empty - showing nothing for a run whose
 * results were on screen a moment earlier.
 *
 * Two changes fix it, and neither weakens the generation guard:
 *
 *   1. A LOADED SELECTION IS KEPT. `state.cache` holds the dashboard for
 *      every selection that has been read. Re-selecting one paints from it
 *      immediately. A finished run and the published study never change, so
 *      there is nothing to be stale about; a run that has just finished is
 *      re-read explicitly with {force:true}.
 *
 *   2. THE POLLER NO LONGER TAKES OVER THE SCREEN FOR A RUN THAT WAS ALREADY
 *      FINISHED WHEN IT WAS CLICKED. It selects only when the run it was
 *      watching has just *become* finished, which is the case that matters -
 *      you pressed go and you want the results.
 *
 * `markLoading()` still exists and still blanks everything, because with
 * nothing on screen yet that is the honest state. It is simply no longer
 * reached for a selection this page has already loaded.
 *
 * The charts live in viz-v4.js and are shared with every version after v4.
 * They are not copied per version - that is how the published study and a run
 * you started drifted apart in the first place.
 */
import * as viz from './viz-v4.js';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* The contract this interface was written against. If the server answers with
 * a different one, say so rather than drawing half a dashboard. */
const EXPECTED_SCHEMA = 4;
const API = '/api/v8';
const SIDEBAR_KEY = 'methylation.v8.sidebar';

const state = {
  setup: null,
  history: [],
  preset: 'standard',
  thresholds: {},
  useExample: true,
  dataSource: 'example',
  localPath: '',

  /* what the middle is showing */
  selection: null,        // {kind:'reference'|'run', id}
  dash: null,             // the dashboard for exactly that selection
  gen: 0,                 // bumped on every selection; late responses are dropped
  filter: '',

  /* Every dashboard this page has read, by selection key. A finished run and
   * the published study are immutable, so a hit here is not stale data - it
   * is the same bytes the server would send back. This is what stops the
   * Runs tab blanking; see the header. */
  cache: new Map(),

  /* where the server keeps runs, and whether that survives a restart */
  storage: null,

  /* the run being watched, which is not the same thing as the selection -
   * you can read an old run while a new one is still going */
  runId: null,
  snap: null,
  pollGen: 0,
  logCursor: 0,
  timer: null,
  ticker: null,
  polledAt: 0,
  sawLive: false,         // did this watch ever see the run actually running?

  /* history refreshes coalesce: one click used to fire four identical ones */
  historyInflight: null,
  historyAgain: false,
};

const selKey = sel => (sel.kind === 'reference' ? 'reference' : `run:${sel.id}`);

const api = {
  async get(u) {
    const r = await fetch(u);
    const j = await r.json().catch(() => ({ error: r.statusText }));
    if (!r.ok) throw new Error(j.error || r.statusText);
    return j;
  },
  async post(u, b) {
    const r = await fetch(u, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(b || {}),
    });
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

function say(el, kind, html) { el.className = 'status show ' + kind; el.innerHTML = html; }
function hide(el) { el.className = 'status'; }
const panel = name => $(`[data-panel="${name}"]`);

function showTab(view) {
  $$('.tab').forEach(x => x.classList.toggle('active', x.dataset.view === view));
  $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + view));
  $$('.toplink').forEach(x => x.classList.toggle('active', x.dataset.targetView === view));
  // Canvases cannot be drawn while their tab is off screen, so redraw the
  // one that just appeared. `state.dash` is now set for anything the page has
  // already read, so switching to Results no longer finds empty canvases.
  if (view === 'results' && state.dash) drawCharts(state.dash);
}

/* ------------------------------------------------------------- sidebar */

/* v7 had two controls for this column - a nav item that swapped pages on a
 * narrow screen and did nothing visible on a wide one, and the column itself,
 * always there, taking 390px whether or not you were setting anything up.
 * There is one control now. Wide: it collapses and the work gets the width.
 * Narrow: it is a drawer over the work, so the tab you were reading is still
 * behind it rather than replaced by it. */
/* The width the drawer breakpoint uses, kept in step with the media query in
 * studio-v8.css. A page can be asked this before it has been laid out, and a
 * width of 0 is not a small screen - it is no answer yet. Guessing "narrow"
 * there hid the sidebar on desktops, so an unknown width reads as wide and
 * the resize below corrects it the moment a real one arrives. */
const BREAKPOINT = 850;
const viewportWidth = () =>
  window.innerWidth || document.documentElement.clientWidth || 0;
const narrow = () => {
  const w = viewportWidth();
  return w > 0 && w <= BREAKPOINT;
};

function setSidebar(open, remember = true) {
  document.body.classList.toggle('sidebar-collapsed', !open);
  document.body.classList.toggle('sidebar-open', open && narrow());
  $('#sidebar-scrim').hidden = !(open && narrow());
  const toggle = $('#sidebar-toggle');
  toggle.setAttribute('aria-expanded', String(open));
  toggle.title = (open ? 'Hide' : 'Show') + ' Upload & Settings';
  if (open) $('#sidebar').scrollTop = 0;
  if (remember) {
    state.sidebarChosen = true;
    try { localStorage.setItem(SIDEBAR_KEY, open ? 'open' : 'closed'); } catch (_) { /* private mode */ }
  }
}

function sidebarIsOpen() {
  return !document.body.classList.contains('sidebar-collapsed');
}

function initSidebar() {
  let saved = null;
  try { saved = localStorage.getItem(SIDEBAR_KEY); } catch (_) { /* private mode */ }
  // Default: open on a wide screen so the three setup steps are the first
  // thing you see, closed on a narrow one where it would cover everything.
  // A choice you made yourself outranks both and is never overwritten.
  state.sidebarChosen = saved === 'open' || saved === 'closed';
  setSidebar(state.sidebarChosen ? saved === 'open' : !narrow(), false);
  window.addEventListener('resize', () => {
    // Re-apply the default when the screen crosses the breakpoint - including
    // the first real width, which may arrive after this function has run.
    const open = state.sidebarChosen ? sidebarIsOpen() : !narrow();
    setSidebar(open, false);
  });
}

/* ------------------------------------------------------------------ boot */
async function boot() {
  try {
    state.setup = await api.get(`${API}/setup`);
  } catch (err) {
    document.body.insertAdjacentHTML('afterbegin',
      `<div class="banner bad" style="display:block">Could not start: ${esc(err.message)}</div>`);
    return;
  }
  try {
    const s = await api.get(`${API}/schema`);
    if (s.schema !== EXPECTED_SCHEMA) {
      $('#banner').hidden = false;
      $('#banner').className = 'banner bad';
      $('#banner').innerHTML = `<b>This page and the server disagree.</b>
        The server builds dashboards to contract ${esc(s.schema)}; this page was written
        for ${EXPECTED_SCHEMA}. Reload after restarting the server.`;
    }
  } catch (_) { /* the check is a courtesy, not a gate */ }

  applyPreset('standard');
  renderPresets();
  renderWorkspace(state.setup.workspace, state.setup.readiness, true);
  wire();
  initSidebar();
  loadSampleResults();
  loadStorageNotice();
  showTab('report');
  await refreshHistory();
  renderTiers();
  await select({ kind: 'reference', id: 'published-study' });
}

/* Whether this instance can keep a run. A list that empties itself between
 * visits looks like the app losing data; on a host with no persistent disk it
 * is the host, and saying so is cheaper than anyone debugging it twice. */
async function loadStorageNotice() {
  const el = $('#storage-note');
  let info;
  try {
    info = await api.get(`${API}/storage`);
  } catch (_) {
    return;                                  // an older server: say nothing
  }
  state.storage = info;
  el.hidden = false;
  el.className = 'storagenote' + (info.durable ? ' durable' : '');
  el.innerHTML = `<span><b>${esc(info.headline)}</b>${esc(info.reason)}</span>`;
}

async function loadSampleResults() {
  const host = $('#brca-attachments');
  const label = $('#brca-results-label');
  const report = $('#brca-open-report');
  const bundle = $('#brca-download-all');
  try {
    const result = await api.get(`${API}/sample-results`);
    if (result.state !== 'ok') throw new Error(result.reason || 'The saved package is unavailable.');
    label.textContent = result.subtitle;
    report.href = result.report_url;
    report.hidden = false;
    bundle.href = result.bundle_url;
    bundle.hidden = false;
    viz.renderDownloads($('#brca-results-files'), result.downloads);
    const count = (result.downloads.items || []).length;
    $('#brca-files-details').querySelector('summary').textContent =
      `Show all ${count} attached result files`;
  } catch (err) {
    host.classList.add('attachment-error');
    label.textContent = `Could not attach the saved files: ${err.message}`;
    viz.paintState($('#brca-results-files'), {
      state: 'unavailable', reason: err.message,
    });
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
  $('#use-upload').addEventListener('click', () => chooseDataSource('upload'));
  $('#use-local').addEventListener('click', () => chooseDataSource('local'));
  $('#repeat-run').addEventListener('click', repeatLatestRun);
  $('#load-local-path').addEventListener('click', loadLocalFolder);
  $('#local-path-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') loadLocalFolder();
  });

  $('#sidebar-toggle').addEventListener('click', () => setSidebar(!sidebarIsOpen()));
  $('#sidebar-close').addEventListener('click', () => setSidebar(false));
  $('#sidebar-scrim').addEventListener('click', () => setSidebar(false));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && narrow() && sidebarIsOpen()) setSidebar(false);
  });

  $$('.tab').forEach(t => t.addEventListener('click', () => showTab(t.dataset.view)));
  $$('.toplink').forEach(t => t.addEventListener('click', () => {
    showTab(t.dataset.targetView);
    // On a narrow screen the drawer is over the tab you just asked for.
    if (narrow()) setSidebar(false);
  }));
  $('#dataset-select').addEventListener('change', e => {
    if (e.target.value === 'reference') {
      select({ kind: 'reference', id: 'published-study' });
      return;
    }
    const id = selectableRunId();
    if (id) select({ kind: 'run', id });
    else e.target.value = 'reference';
  });

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
  $('#report-variant').addEventListener('change', e => {
    $('#report-frame').src = e.target.value;
  });
  $('#download-all').addEventListener('click', () => {
    const d = state.dash && state.dash.downloads;
    if (d && d.bundle_url) window.location = d.bundle_url;
  });
  $('#tsearch').addEventListener('input', e => {
    state.filter = e.target.value;
    if (state.dash) viz.renderTable(panel('table'), state.dash.table, state.filter);
  });
  window.addEventListener('resize', () => { if (state.dash) drawCharts(state.dash); });
}

/* ==========================================================================
 * THE SELECTION - the only thing that decides what the middle shows
 * ======================================================================== */

function selectionUrl(sel) {
  return sel.kind === 'reference'
    ? `${API}/dashboard?source=reference`
    : `${API}/dashboard?source=run&id=${encodeURIComponent(sel.id)}`;
}

/* Load and show one selection. Every call takes a generation; anything that
 * comes back after a newer selection has started is dropped on the floor.
 *
 * A selection this page has already read is drawn from `state.cache` before
 * anything is fetched, so the screen never empties on the way to showing the
 * same numbers again. Pass {force:true} to re-read one anyway - the poller
 * does, for the run that has just finished, because that run's dashboard did
 * not exist when it was last looked at. */
async function select(sel, { force = false } = {}) {
  const gen = ++state.gen;
  const key = selKey(sel);
  const cached = state.cache.get(key);
  state.selection = sel;

  if (cached) {
    state.dash = cached;
    setStale('');
    renderDashboard(cached);
  } else {
    state.dash = null;
    markLoading(sel);
  }
  renderSourcePick();
  syncRunPanel();
  refreshHistory();

  // On screen already, and nobody asked for it to be re-read. A finished run
  // and the published study do not change underneath us, so there is nothing
  // a second request could tell us that this page does not already know.
  if (cached && !force) return;

  showRefreshing(!!cached);
  let dash;
  try {
    dash = await api.get(selectionUrl(sel));
  } catch (err) {
    if (gen !== state.gen) return;          // superseded - stay quiet
    showRefreshing(false);
    // Keep what is on screen. Blanking a real result because a re-check
    // failed is the v7 behaviour this version exists to remove.
    if (cached) {
      setStale(`Could not re-check this selection (${err.message}). Showing what was already loaded.`);
      return;
    }
    state.dash = null;
    showSelectionError(sel, err);
    return;
  }
  if (gen !== state.gen) return;            // superseded - do not draw
  showRefreshing(false);
  if (dash.schema !== EXPECTED_SCHEMA) {
    if (cached) return;                     // the good copy stays up
    showSelectionError(sel, new Error(
      `the server built this to contract ${dash.schema}, this page reads ${EXPECTED_SCHEMA}`));
    return;
  }
  state.cache.set(key, dash);
  state.dash = dash;
  setStale('');
  renderDashboard(dash);
}

/* Re-checking something that is already drawn. This is the whole visible cost
 * of a refresh now - one word in the selection bar, and nothing below moves. */
function showRefreshing(on) {
  $('#sel-refresh').hidden = !on;
}

function setStale(message) {
  const el = $('#sel-stale');
  el.hidden = !message;
  el.textContent = message || '';
}

/* While a selection is in flight, every panel says so. The alternative -
 * leaving the previous run's numbers under the new run's heading - is the
 * exact failure this version exists to remove. */
function markLoading(sel) {
  $('#sel-loading').hidden = false;
  showRefreshing(false);
  setStale('');
  $('#sel-kind').textContent = sel.kind === 'reference' ? 'Published study' : 'Your run';
  $('#sel-kind').className = 'selkind ' + sel.kind;
  $('#sel-title').textContent = sel.kind === 'reference'
    ? 'Published study' : (labelForRun(sel.id) || sel.id);
  $('#sel-sub').textContent = 'Loading…';
  $('#report-label').textContent = 'Loading…';
  $('#files-label').textContent = 'Loading…';
  $('#download-all').disabled = true;
  $('#report-frame').removeAttribute('src');
  $('#report-variant').hidden = true;
  panel('report').classList.add('report-loading');
  panel('report').querySelector('[data-body]').hidden = false;
  panel('report').querySelector('[data-state]').hidden = true;
  $$('[data-panel]').filter(p => p.dataset.panel !== 'report').forEach(p => {
    viz.paintState(p, { state: 'loading', reason: 'Loading…' });
    const note = p.querySelector('[data-state]');
    if (note) {
      note.className = 'pstate loading';
      note.innerHTML = '<span class="pstate-tag">Loading</span><span></span>';
    }
  });
}

function showSelectionError(sel, err) {
  $('#sel-loading').hidden = true;
  showRefreshing(false);
  $('#sel-sub').textContent = '';
  panel('report').classList.remove('report-loading');
  $$('[data-panel]').forEach(p => {
    viz.paintState(p, {
      state: 'unavailable',
      reason: `Could not load this selection: ${err.message}`,
    });
  });
  $('#report-label').textContent = 'Could not load this selection.';
  $('#files-label').textContent = 'Could not load this selection.';
}

function labelForRun(id) {
  const r = (state.history || []).find(x => x.id === id);
  return r ? r.label : null;
}

/* The status panel belongs to the run being watched, the file list belongs to
 * the selection. They are the same run in every normal case; the one case they
 * differ is reading an old run while a new one is still going, and then the
 * status panel stays up because a run in flight is the more urgent of the two. */
function syncRunPanel() {
  const snap = state.snap;
  const live = snap && ['running', 'queued'].includes(snap.status);
  const selectedIsWatched = state.selection && state.selection.kind === 'run'
    && state.selection.id === state.runId;
  $('#progress').hidden = !(snap && (live || selectedIsWatched));
  if (!live) renderRunsBadge(null);
}

/* ------------------------------------------------- drawing the selection */

function renderDashboard(d) {
  const src = d.source;
  $('#sel-loading').hidden = true;
  $('#sel-kind').textContent = src.kind === 'reference' ? 'Published study' : src.tier_label;
  $('#sel-kind').className = 'selkind ' + src.kind;
  $('#sel-title').textContent = src.title;
  $('#sel-sub').textContent = src.subtitle || '';

  /* ---- report ---- */
  const reportHost = panel('report');
  reportHost.classList.remove('report-loading');
  const rep = d.report;
  viz.paintState(reportHost, rep);
  if (rep.state === 'ok' && rep.url) {
    // Assigning .src reloads the iframe even when the URL has not changed,
    // and the report is the largest thing on the page - so a redraw of the
    // same selection would throw away a document that is already rendered
    // and show a white frame while it came back. Only move it if it moved.
    const frame = $('#report-frame');
    if (frame.getAttribute('src') !== rep.url) frame.src = rep.url;
    $('#report-label').innerHTML = `<b>${esc(src.title)}</b> — ${
      src.kind === 'reference'
        ? 'complete original single-page report with all visualizations'
        : 'complete one-page report generated by this run'}.`;
    $('#report-variant').hidden = true;
  } else {
    $('#report-frame').removeAttribute('src');
    $('#report-variant').hidden = true;
    $('#report-label').textContent = rep.reason || 'No completed report for this selection.';
  }

  /* ---- downloads ---- */
  const dl = d.downloads;
  viz.renderDownloads(panel('downloads'), dl);
  $('#download-all').disabled = !(dl.state === 'ok' && dl.bundle_url);
  $('#files-label').textContent = dl.state === 'ok'
    ? `${dl.items.length} files from ${src.title}. Only steps that finished are listed.`
    : `${src.title} — ${dl.reason}`;

  /* ---- results ---- */
  viz.renderCards(panel('cards'), d.cards);
  viz.renderMovers(panel('movers'), d.movers);
  viz.renderCohort(panel('cohort'), d.cohort);
  viz.renderEnrichment(panel('enrichment'), d.enrichment);
  viz.renderTable(panel('table'), d.table, state.filter);
  drawCharts(d);

  renderSourcePick();
}

/* The canvas charts, together, so a resize or a tab switch redraws all of
 * them through the same path they were first drawn through. */
function drawCharts(d) {
  viz.renderDirection(panel('direction'), d.direction, $('#donut'), $('#donut-legend'));
  viz.renderValidation(panel('validation'), d.validation, $('#folds'), $('#val-note'));
  viz.renderRoc(panel('roc'), d.roc, $('#roc'));
  viz.renderVolcano(panel('volcano'), d.volcano, $('#volcano'));
}

function selectableRunId() {
  if (state.selection && state.selection.kind === 'run') return state.selection.id;
  if (state.runId && state.snap && !['running', 'queued'].includes(state.snap.status)) return state.runId;
  const run = (state.history || []).find(r => r.status !== 'error' && (r.has_results || r.has_report));
  return run ? run.id : null;
}

function renderSourcePick() {
  const sel = state.selection || {};
  const selectEl = $('#dataset-select');
  const runOption = selectEl.querySelector('option[value="run"]');
  const runId = selectableRunId();
  const run = (state.history || []).find(r => r.id === runId);
  runOption.disabled = !runId;
  runOption.textContent = runId
    ? `Sample / uploaded analysis — ${(run && run.label) || labelForRun(runId) || 'latest run'}`
    : 'Sample / uploaded analysis — run one first';
  selectEl.value = sel.kind === 'run' && runId ? 'run' : 'reference';
  $('#sourcepick').innerHTML = '';
}

/* ======================================================= data selection */
function selectExample() {
  state.useExample = true;
  chooseDataSource('example', false);
  say($('#data-status'), 'ok',
    '<b>Using the example data.</b> 130 breast samples, tumour against normal tissue. ' +
    'The individual values in it are simulated, so treat anything it finds as a demonstration ' +
    'of the method rather than a finding.');
  renderTiers();
}

function chooseDataSource(mode, clearStatus = true) {
  state.dataSource = mode;
  $$('[data-source]').forEach(b => b.classList.toggle('on', b.dataset.source === mode));
  $('#local-path-panel').hidden = mode !== 'local';
  $('#upload-panel').hidden = mode !== 'upload';
  const labels = { example: 'Example', repeat: 'Earlier run', local: 'Local path', upload: 'Upload' };
  $('#data-source-badge').textContent = labels[mode] || 'Data';
  if (mode === 'example') state.useExample = true;
  if (mode === 'local' || mode === 'upload') state.useExample = false;
  if (clearStatus && (mode === 'local' || mode === 'upload')) hide($('#data-status'));
  renderTiers();
}

async function repeatLatestRun() {
  chooseDataSource('repeat');
  const id = selectableRunId();
  if (!id) {
    say($('#data-status'), 'warn', '<b>No earlier run yet.</b> Start a quick test first.');
    return;
  }
  try {
    const d = await api.get(`${API}/dashboard?source=run&id=${encodeURIComponent(id)}`);
    const used = (d.thresholds && d.thresholds.used) || {};
    if (Object.keys(used).length) {
      state.thresholds = { ...state.thresholds, ...used };
      state.preset = 'custom';
      renderPresets();
    }
    await select({ kind: 'run', id });
    showTab('report');
    say($('#data-status'), 'ok', `<b>Earlier settings loaded.</b> Viewing ${esc(d.source.title)}.`);
  } catch (err) {
    say($('#data-status'), 'bad', `<b>Could not open that run.</b> ${esc(err.message)}`);
  }
}

async function loadLocalFolder() {
  const path = $('#local-path-input').value.trim();
  if (!path) {
    say($('#data-status'), 'warn', '<b>Enter a folder path first.</b>');
    return;
  }
  say($('#data-status'), 'warn', 'Reading the local folder…');
  try {
    const j = await api.post(`${API}/workspace/local`, { path });
    state.localPath = path;
    state.useExample = false;
    chooseDataSource('local', false);
    state.setup.workspace = j.workspace;
    renderWorkspace(j.workspace, j.readiness, false, j.ingest);
  } catch (err) {
    say($('#data-status'), 'bad', `<b>Could not use that folder.</b> ${esc(err.message)}`);
  }
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
      last = await fetch(`${API}/upload`, {
        method: 'POST', headers: { 'X-Filename': f.name }, body: f,
      }).then(r => r.json());
    } catch (err) { say(status, 'bad', esc(err.message)); return; }
  }
  if (last && last.workspace) {
    state.useExample = false;
    chooseDataSource('upload', false);
    state.setup.workspace = last.workspace;
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
      '<button class="btn small" id="clear-files" style="justify-self:start">Remove these files</button>');
    $('#clear-files').addEventListener('click', async () => {
      const j = await api.post(`${API}/workspace/clear`);
      renderWorkspace(j.workspace, j.readiness);
      selectExample();
    });
    state.useExample = false;
    if (state.dataSource === 'example') chooseDataSource('upload', false);
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
    const j = await api.post(`${API}/runs`, {
      study: 'brca_sim', mode,
      use_example: state.useExample,
      thresholds: state.thresholds,
      n_per_class: 3,
      source_label: state.dataSource === 'local'
        ? `local folder: ${state.localPath}`
        : (state.dataSource === 'upload' ? 'uploaded files' : 'example data'),
      name: mode === 'full' ? 'Full analysis' : (mode === 'demo' ? 'Quick test' : 'File check'),
    });
    hide(status);
    // Go where the progress is. Starting a run and being left on a screen
    // that does not change is how people conclude nothing happened.
    showTab('runs');
    watch(j.run_id);
  } catch (err) {
    say(status, 'bad', `<b>Cannot run yet.</b> ${esc(err.message)}`);
  }
}

/* --------------------------------------------------------------- polling */

/* Watching a run is its own generation. v3 started a second poll loop without
 * stopping the first, so two loops wrote to the same state and whichever
 * happened to land last won. */
function watch(runId) {
  clearTimeout(state.timer);
  clearInterval(state.ticker);
  const gen = ++state.pollGen;
  state.runId = runId;
  state.logCursor = 0;
  state.snap = null;
  // Whether this watch ever saw the run actually running is what decides, at
  // the end, if the poller is allowed to take over the screen. Clicking a run
  // that finished last week must not behave like a run that just completed.
  state.sawLive = false;
  $('#logbody').innerHTML = '';
  $('#progress').hidden = false;
  startTicker();
  poll(gen);
}

function startTicker() {
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

async function poll(gen) {
  if (gen !== state.pollGen || !state.runId) return;
  let snap;
  try {
    snap = await api.get(`${API}/runs/${state.runId}?since=${state.logCursor}`);
  } catch (err) {
    if (gen === state.pollGen) say($('#run-status'), 'bad', esc(err.message));
    return;
  }
  if (gen !== state.pollGen) return;        // a newer run is being watched

  const firstSight = !state.snap || state.snap.id !== snap.id;
  state.snap = snap;
  state.polledAt = Date.now();
  state.logCursor = snap.log_count || state.logCursor;
  appendLog(snap.logs);
  renderProgress(snap);
  renderBanner(snap);
  // The list needs one refresh to learn which row is the live one; after that
  // renderProgress moves its bar directly rather than re-fetching every 2s.
  if (firstSight) refreshHistory();

  // A terminal status does not mean the files exist yet - the record, the
  // results and the bundle are written after the last step. Acting on "done"
  // alone races the writes and shows "no results" for a run that has them.
  const live = ['running', 'queued'].includes(snap.status);
  if (live) state.sawLive = true;
  const settling = !live && snap.finalized === false;
  if (live || settling) {
    state.timer = setTimeout(() => poll(gen), settling ? 400 : 2000);
    return;
  }
  clearInterval(state.ticker);
  // Only a run that finished under this watch changes the list; for one that
  // was already finished, the coalescing refresh is enough.
  await (state.sawLive ? refreshHistoryNow() : refreshHistory());
  renderTiers();
  if (gen !== state.pollGen) return;

  // THE v7 BUG, AND THE ONE LINE THAT WAS MISSING.
  //
  // v7 selected here unconditionally. Clicking a run that had finished long
  // ago went: select (blank, load, draw) -> poll answers "done" -> select
  // again (blank, load, draw). The second pass showed nothing new and blanked
  // the screen to get there.
  //
  // There are only two reasons to take over the middle of the screen from
  // here, and neither is true for a run that was already finished when it was
  // clicked - that one is on screen already, put there by openRun().
  const already = state.selection && state.selection.kind === 'run'
    && state.selection.id === snap.id;
  if (state.sawLive) {
    // It finished while we watched. Its dashboard did not exist when this
    // page last read it, so this one must actually be fetched.
    await select({ kind: 'run', id: snap.id }, { force: true });
  } else if (!already) {
    // Finished between two polls, and the screen is still showing something
    // else. Show it - from cache if we have it.
    await select({ kind: 'run', id: snap.id });
  }
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

  // Every step by name, with what it is doing and what it took. The bar alone
  // tells you how far along it is; this tells you what it is actually doing,
  // which is the question people are really asking while they wait.
  const MARK = { done: '✓', running: '▶', failed: '✕', skipped: '–', pending: '' };
  $('#p-steps').innerHTML = (snap.steps || []).map((s, i) => `
    <div class="srow ${esc(s.state)}">
      <span class="smark">${MARK[s.state] || ''}</span>
      <span class="snum">${i + 1}</span>
      <span class="sname"><b>${esc(s.friendly)}</b>
        ${s.plain ? `<span>${esc(s.plain)}</span>` : ''}</span>
      <span class="stime">${s.seconds != null ? esc(secs(s.seconds))
    : (s.state === 'running' ? 'running…' : '')}</span>
    </div>`).join('');

  const bar = $(`.hrun[data-open="${snap.id}"] .hbar i`);
  if (bar) bar.style.width = (p.percent || 0) + '%';

  renderRunsBadge(snap);
}

/* A run you cannot see is a run you assume has stalled. The tab carries how
 * far along it is, so the Runs tab does not have to be the open one. */
function renderRunsBadge(snap) {
  const b = $('#runs-badge');
  const p = (snap && snap.progress) || {};
  const live = snap && ['running', 'queued'].includes(snap.status);
  if (!live) {
    b.hidden = true;
    b.className = 'tabbadge';
    return;
  }
  b.hidden = false;
  b.className = 'tabbadge live';
  b.textContent = `${p.index || 0}/${p.total || 0}`;
  b.title = p.current
    ? `${p.current.friendly}${p.remaining != null ? ' · ' + secs(p.remaining) + ' left' : ''}`
    : 'running';
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
  // "Nothing passed the filters" is an answer, not a breakage. Reporting it as
  // a crash would send someone hunting for a bug that is not there.
  if (snap.status === 'error' && snap.null_result) {
    const st = (snap.results && snap.results.stats) || snap.stats || [];
    const get = k => (st.find(s => s.label === k) || {}).value;
    const n = v2 => (typeof v2 === 'number' ? v2.toLocaleString() : v2);
    el.className = 'banner test';
    el.innerHTML = `<b>No sites passed the filters — that is a result, not a fault.</b>
      Every step up to the shortlist ran. ${get('Probes tested') != null
    ? `${n(get('Probes tested'))} sites were tested and ${n(get('Significant probes') ?? 0)}
           reached the confidence threshold.` : ''}
      Nothing cleared both the confidence and effect-size bars, so there was no shortlist
      to build and the run stopped there.
      <div class="more">If you expected hits: try the <b>Exploratory</b> preset, or lower the
      minimum effect size under "Fine-tune the settings". If you did not, this is your
      answer — these two groups do not differ at these thresholds.</div>`;
    return;
  }
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
    el.innerHTML = '<b>Running.</b> Results and the report appear here as soon as it finishes.';
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

async function cancel() {
  if (!state.runId) return;
  try {
    const j = await api.post(`${API}/runs/${state.runId}/cancel`);
    say($('#run-status'), 'warn', esc(j.outcome));
  } catch (err) { say($('#run-status'), 'bad', esc(err.message)); }
}

/* -------------------------------------------------------------- history */

/* One click on a run fired four identical /history requests in v7 - one from
 * select(), one from the poller's first sight of the run, and two more from
 * the re-select. They coalesce now: a call while one is in flight sets a flag
 * and the answer is re-read once, afterwards, instead of racing. */
function refreshHistory() {
  if (state.historyInflight) {
    state.historyAgain = true;
    return state.historyInflight;
  }
  state.historyInflight = drawHistory().finally(() => {
    state.historyInflight = null;
    if (state.historyAgain) {
      state.historyAgain = false;
      refreshHistory();
    }
  });
  return state.historyInflight;
}

/* When the answer has to be current - a run has just finished and the list
 * must contain it - skip the coalescing and read it now. */
function refreshHistoryNow() {
  state.historyAgain = false;
  return drawHistory();
}

async function drawHistory() {
  const inc = $('#show-tests').checked;
  try {
    // Always fetch everything: the Full-analysis gate asks whether a quick test
    // has ever passed, and that must not depend on a display filter.
    const j = await api.get(`${API}/history?include_tests=1`);
    // History is read from runs/*/run_record.json, and that file is written
    // when a run finishes - so the run happening right now is not in it. Put
    // it at the top from what the poller already knows, or the list claims
    // nothing is running while the bar above it says otherwise.
    const s = state.snap;
    const live = s && ['running', 'queued'].includes(s.status)
      && !j.runs.some(r => r.id === s.id)
      ? [{
        id: s.id, label: s.label || 'Running', mode: s.mode,
        status: s.status, when: 'now', elapsed: null,
        is_test: ['demo', 'plan'].includes(s.mode),
        null_result: false, has_report: false, has_results: false,
      }] : [];
    state.history = live.concat(j.runs);
    renderSourcePick();
    const shown = inc ? state.history : state.history.filter(r => !r.is_test);
    const box = $('#history');
    if (!shown.length) {
      box.innerHTML = `<p class="sub">${inc ? 'Nothing yet.'
        : 'No full runs yet — tick the box to see test runs.'}</p>`;
      return;
    }
    const selId = state.selection && state.selection.kind === 'run' ? state.selection.id : null;
    const liveId = state.snap && ['running', 'queued'].includes(state.snap.status)
      ? state.snap.id : null;
    $('#run-count').textContent = shown.length === j.runs.length
      ? `${shown.length}` : `${shown.length} of ${j.runs.length}`;

    box.innerHTML = shown.map(r => {
      const isLive = r.id === liveId;
      const pc = isLive ? ((state.snap.progress || {}).percent || 0) : null;
      return `<button class="hrun ${r.id === selId ? 'on' : ''} ${isLive ? 'live' : ''}"
        data-open="${esc(r.id)}">
        <span class="hrow">
          <b>${esc(r.label)}</b>
          <span class="badge ${isLive ? 'live' : (r.null_result ? 'test'
    : (r.status === 'error' ? 'bad' : (r.is_test ? 'test' : 'full')))}">${
  isLive ? 'running' : (r.null_result ? 'no hits'
    : (r.status === 'error' ? 'failed' : (r.is_test ? 'test' : 'full')))}</span>
        </span>
        <span class="meta">${esc(r.when)}${
  r.elapsed ? ' · ' + esc(secs(r.elapsed)) : ''}${
  r.has_report ? ' · report' : ''}${
  r.has_results ? ' · results' : ''}</span>
        ${isLive ? `<span class="hbar"><i style="width:${pc}%"></i></span>` : ''}
      </button>`;
    }).join('');
    $$('[data-open]').forEach(b => b.addEventListener('click', () => openRun(b.dataset.open)));
  } catch (err) {
    $('#history').innerHTML = `<p class="sub">${esc(err.message)}</p>`;
  }
}

/* Clicking a run in the list. It selects that run and shows its progress
 * strip - one path, so the header and the charts move together.
 *
 * Order matters, and it is the reverse of v7's. Select first, so the panels
 * are painted (from cache, instantly, if this run has been opened before);
 * then start watching, so the step list and timings fill in underneath a
 * screen that is already showing the right run. v7 started the watch first,
 * which is what gave the poller a chance to re-select from underneath. */
async function openRun(runId) {
  await select({ kind: 'run', id: runId });
  watch(runId);
}

boot();
