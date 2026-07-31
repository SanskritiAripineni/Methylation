import * as viz from './viz-v4.js';

const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const panel = name => $(`[data-panel="${name}"]`);
let dashboard = null;

if (window.self !== window.top) document.body.classList.add('embedded');

function queryUrl() {
  const q = new URLSearchParams(location.search);
  if (q.get('source') === 'run') {
    const id = q.get('id');
    if (!id) throw new Error('No sample run was selected.');
    return `/api/v6/dashboard?source=run&id=${encodeURIComponent(id)}`;
  }
  return '/api/v6/dashboard?source=reference';
}

function prettyKey(value) {
  return String(value).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function prettyValue(value) {
  if (value == null || value === '') return 'Not recorded';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object') return Object.entries(value).map(([k,v]) => `${prettyKey(k)}: ${v}`).join(' · ');
  return String(value);
}

function renderMethods(d) {
  const used = (d.thresholds && d.thresholds.used) || {};
  const entries = Object.entries(used);
  const base = [
    ['Report source', d.source.kind === 'reference' ? 'Bundled breast published study' : 'Completed sample / uploaded pipeline run'],
    ['Analysis tier', d.source.tier_label || 'Published analysis'],
    ['Dashboard contract', `Schema ${d.schema}`],
  ];
  $('#method-grid').innerHTML = base.concat(entries).map(([k,v]) => `<div class="methoditem"><small>${esc(prettyKey(k))}</small><strong>${esc(prettyValue(v))}</strong></div>`).join('');
}

function renderHeader(d) {
  const src = d.source;
  document.title = `${src.title} · Methylation Studio Report`;
  $('#report-kind').textContent = src.kind === 'reference' ? 'Breast published study · Version 6' : 'Sample / uploaded analysis · Version 6';
  $('#report-title').textContent = src.title;
  $('#report-subtitle').textContent = src.kind === 'reference'
    ? 'A completed breast tumour versus normal methylation study.'
    : 'A responsive report generated from the selected pipeline run.';
  $('#report-meta').textContent = [src.subtitle, src.tier_label].filter(Boolean).join(' · ');
  $('#provenance-source').textContent = src.kind === 'reference' ? 'Breast published study' : 'Sample / uploaded analysis';
  $('#provenance-detail').textContent = src.subtitle || 'No additional source description was recorded.';
  const caveat = src.caveat || (src.kind === 'run'
    ? 'This report describes the selected run only. Test and simulated runs demonstrate the method and are not research findings.'
    : 'This bundled source is presented as the completed reference study.');
  $('#report-caveat').innerHTML = `<strong>Interpretation note</strong><p>${esc(caveat)}</p>`;
}

function drawCharts(d) {
  viz.renderDirection(panel('direction'), d.direction, $('#report-direction'), $('#report-direction-legend'));
  viz.renderValidation(panel('validation'), d.validation, $('#report-validation'), $('#report-validation-note'));
  viz.renderRoc(panel('roc'), d.roc, $('#report-roc'));
  viz.renderVolcano(panel('volcano'), d.volcano, $('#report-volcano'));
}

function render(d) {
  dashboard = d;
  renderHeader(d);
  viz.renderCards(panel('cards'), d.cards);
  viz.renderMovers(panel('movers'), d.movers);
  viz.renderTable(panel('table'), d.table, '');
  viz.renderTable(panel('panel'), d.panel, '');
  viz.renderEnrichment(panel('enrichment'), d.enrichment);
  viz.renderCohort(panel('cohort'), d.cohort);
  viz.renderDownloads(panel('downloads'), d.downloads);
  renderMethods(d);
  drawCharts(d);
  $('#report-main').setAttribute('aria-busy', 'false');
}

async function boot() {
  try {
    const response = await fetch(queryUrl());
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || response.statusText);
    if (data.schema !== 4) throw new Error(`Unsupported report schema ${data.schema}.`);
    render(data);
  } catch (error) {
    $('#report-main').innerHTML = `<div class="report-error"><strong>This report could not be prepared.</strong><p>${esc(error.message)}</p></div>`;
    $('#report-main').setAttribute('aria-busy', 'false');
  }
}

window.addEventListener('resize', () => { if (dashboard) drawCharts(dashboard); });
boot();


