/* The visualizations, as fixed functions.
 *
 * Every chart here is a pure function of one section of the dashboard
 * contract (server/dashboard/schema.py). It reads `section.state` first and
 * draws one of three things:
 *
 *   ok           the chart
 *   empty        the reason, as a sentence - the step ran, there was nothing
 *   unavailable  the reason, as a sentence - this source cannot produce it
 *
 * Nothing here knows or cares whether the numbers came from the published
 * study or from a file you dropped in this morning. That is the whole point:
 * upload new data and the same code draws it, the same way, or says plainly
 * why it cannot. A panel is never hidden - a panel that vanishes looks
 * exactly like a panel that is broken.
 *
 * Colour rule, unchanged from v3: the interface is greyscale; colour is only
 * used where it carries the finding. Red is methylation gained, blue is
 * methylation lost. Those two are the only hues on a chart, and the pair is
 * distinguishable under protanopia and deuteranopia (OKLab ΔE 26.1) - the
 * red/green pair v3 used measured 6.1 and was not.
 */

export const INK = '#15181f';
export const MUTED = '#5f6673';
export const GRID = '#e8eaee';
export const FAINT = '#d3d7de';

/* the only colours on a chart */
export const HYPER = '#c0392b';    // gained methylation
export const HYPO = '#2a78d6';     // lost methylation
export const NEUTRAL = '#8f94a0';  // no real change

const OK = 'ok';

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = n => (typeof n === 'number' ? n.toLocaleString() : n);

/* ------------------------------------------------------------------ state */

/* Every panel renders its own state. `host` is the panel element; the state
 * note replaces the chart body rather than hiding the panel around it. */
export function paintState(host, section) {
  const body = host.querySelector('[data-body]');
  const note = host.querySelector('[data-state]');
  if (!body || !note) return true;
  const ok = section && section.state === OK;
  body.hidden = !ok;
  note.hidden = ok;
  if (!ok) {
    const kind = section ? section.state : 'unavailable';
    note.className = 'pstate ' + kind;
    note.innerHTML = `<span class="pstate-tag">${
      kind === 'empty' ? 'Nothing to show' : 'Not available here'}</span>
      <span>${esc((section && section.reason) || 'No data.')}</span>`;
  }
  return ok;
}

/* A canvas sized for the display, or null when its tab is not on screen.
 * Redrawn when the tab is shown - never drawn at zero width. */
function ctx2(canvas, h) {
  if (!canvas) return null;
  const r = canvas.getBoundingClientRect();
  if (!r.width) return null;
  const d = window.devicePixelRatio || 1;
  canvas.width = r.width * d;
  canvas.height = h * d;
  const x = canvas.getContext('2d');
  x.setTransform(d, 0, 0, d, 0, 0);
  x.clearRect(0, 0, r.width, h);
  return { x, W: r.width, H: h };
}

const DIRECTION_LABEL = {
  silencing: 'switched off', activation: 'switched on', ambiguous: 'unclear',
};
const DIRECTION_COLOUR = {
  silencing: HYPER, activation: HYPO, ambiguous: NEUTRAL,
};

/* ------------------------------------------------------------------ cards */

export function renderCards(host, section) {
  if (!paintState(host, section)) return;
  host.querySelector('[data-body]').innerHTML = (section.items || []).map(c => `
    <div class="card ${c.tone ? 'tone-' + c.tone : ''}">
      <div class="cnum">${c.kind === 'auc' && typeof c.value === 'number'
    ? c.value.toFixed(3) : num(c.value)}</div>
      <div class="clbl">${esc(c.label)}</div>
      ${c.note ? `<div class="cnote">${esc(c.note)}</div>` : ''}
    </div>`).join('');
}

/* ----------------------------------------------------------------- movers */

export function renderMovers(host, section) {
  if (!paintState(host, section)) return;
  const rows = section.items || [];
  const max = Math.max(...rows.map(r => Math.abs(r.delta)), 0.0001);
  host.querySelector('[data-body]').innerHTML = rows.map(r => {
    const pct = Math.abs(r.delta) / max * 50;      // half-width each side of centre
    const up = r.delta > 0;
    // The group means only exist on sources that carry them. Absent is
    // absent - the tooltip says less rather than implying a number.
    const means = (r.tumor != null && r.normal != null)
      ? ` · tumour ${r.tumor.toFixed(2)} vs normal ${r.normal.toFixed(2)}` : '';
    return `<div class="mrow" title="${esc(r.probe)}${means}">
      <span class="mgene">${esc(r.gene)}</span>
      <span class="mtrack">
        <i class="mbar ${up ? 'up' : 'down'}"
           style="${up ? 'left:50%' : 'right:50%'};width:${pct}%"></i>
        <i class="mzero"></i>
      </span>
      <span class="mval ${up ? 'up' : 'down'}">${up ? '+' : ''}${r.delta.toFixed(2)}</span>
    </div>`;
  }).join('');
}

/* -------------------------------------------------------------- direction */

export function renderDirection(host, section, canvas, legend) {
  if (!paintState(host, section)) return;
  const entries = Object.entries(section.counts || {}).filter(([, v]) => v > 0);
  const d = ctx2(canvas, 230);
  legend.innerHTML = entries.map(([k, v]) => {
    const total = entries.reduce((a, b) => a + b[1], 0) || 1;
    return `<div class="dl"><i style="background:${DIRECTION_COLOUR[k] || NEUTRAL}"></i>
      <span><b>${num(v)}</b> ${esc(DIRECTION_LABEL[k] || k)}
        <small>${(v / total * 100).toFixed(0)}%</small></span></div>`;
  }).join('');
  if (!d || !entries.length) return;

  const { x, W, H } = d;
  const total = entries.reduce((a, b) => a + b[1], 0);
  const cx = Math.min(120, W / 3), cy = H / 2;
  const R = Math.min(88, H / 2 - 12), r0 = R * 0.58;
  let a0 = -Math.PI / 2;
  entries.forEach(([k, v]) => {
    const a1 = a0 + (v / total) * Math.PI * 2;
    x.beginPath();
    x.arc(cx, cy, R, a0, a1);
    x.arc(cx, cy, r0, a1, a0, true);
    x.closePath();
    x.fillStyle = DIRECTION_COLOUR[k] || NEUTRAL;
    x.fill();
    // A 2px surface gap between segments, so neighbouring slices read apart
    // without a border colour doing the work.
    x.strokeStyle = '#ffffff';
    x.lineWidth = 2;
    x.stroke();
    a0 = a1;
  });
  x.fillStyle = INK;
  x.font = 'bold 19px system-ui, -apple-system, "Segoe UI", sans-serif';
  x.textAlign = 'center';
  x.fillText(total >= 1000 ? (total / 1000).toFixed(0) + 'k' : String(total), cx, cy + 2);
  x.font = '11px system-ui, -apple-system, "Segoe UI", sans-serif';
  x.fillStyle = MUTED;
  x.fillText('sites', cx, cy + 17);
  x.textAlign = 'left';
}

/* ------------------------------------------------------------- validation */

export function renderValidation(host, section, canvas, note) {
  if (!paintState(host, section)) return;
  const model = section.model || {};
  const list = section.folds || [];
  note.textContent = model.roc_auc_mean != null
    ? `${String(model.model || '').replace(/_/g, ' ')} · ${model.cv_folds || '?'} rounds · ` +
      `average ${model.roc_auc_mean.toFixed(3)}` +
      `${model.roc_auc_std != null ? ' ± ' + model.roc_auc_std.toFixed(3) : ''}` +
      `${model.nested ? ' · nested cross-validation' : ''}`
    : '';

  const d = ctx2(canvas, 230);
  if (!d) return;
  const { x, W, H } = d, pad = 40;

  if (!list.length) {
    // No per-round scores recorded, but the average is real. Show the number
    // alone rather than an empty axis.
    x.fillStyle = INK;
    x.font = 'bold 44px system-ui, -apple-system, "Segoe UI", sans-serif';
    x.textAlign = 'center';
    x.fillText((model.roc_auc_mean || 0).toFixed(3), W / 2, H / 2);
    x.fillStyle = MUTED;
    x.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif';
    x.fillText('average score across ' + (model.cv_folds || '?') + ' rounds', W / 2, H / 2 + 22);
    x.textAlign = 'left';
    return;
  }

  const lo = Math.min(0.5, ...list) - 0.02, hi = 1.002;
  const py = v => H - pad - ((v - lo) / (hi - lo)) * (H - pad - 26);
  x.font = '10.5px system-ui, -apple-system, "Segoe UI", sans-serif';
  x.lineWidth = 1;
  [0.5, 0.75, 0.9, 1.0].filter(v => v >= lo).forEach(v => {
    const y = py(v);
    x.strokeStyle = GRID;
    x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 14, y); x.stroke();
    x.fillStyle = MUTED;
    x.fillText(v.toFixed(2), 8, y + 3);
  });
  const step = (W - pad - 24) / list.length;
  list.forEach((v, i) => {
    const X = pad + step * (i + 0.5), Y = py(v);
    x.strokeStyle = FAINT;
    x.beginPath(); x.moveTo(X, H - pad); x.lineTo(X, Y); x.stroke();
    // A cross-validation round encodes no direction, so it stays ink, not
    // one of the two data colours.
    x.fillStyle = INK;
    x.beginPath(); x.arc(X, Y, 5, 0, 6.284); x.fill();
    x.fillStyle = MUTED;
    x.textAlign = 'center';
    x.fillText('round ' + (i + 1), X, H - pad + 15);
    x.textAlign = 'left';
  });
  if (model.roc_auc_mean != null) {
    const y = py(model.roc_auc_mean);
    x.strokeStyle = MUTED;
    x.setLineDash([5, 4]);
    x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 14, y); x.stroke();
    x.setLineDash([]);
  }
}

/* -------------------------------------------------------------------- roc */

/* Computed by every run since v1 and never drawn until now. */
export function renderRoc(host, section, canvas) {
  if (!paintState(host, section)) return;
  const head = host.querySelector('.phead h3');
  const copy = host.querySelector('.phead p');
  if (head) head.textContent = section.heading || 'Where it trades off';
  if (copy) copy.textContent = section.description ||
    'Every threshold at once. Up is catching more of the tumours; right is calling more healthy samples tumours by mistake. The further the line bows into the top-left, the better the shortlist separates the groups.';
  const body = host.querySelector('[data-body]');
  const oldFigure = body && body.querySelector('.published-figure');
  const oldCaption = body && body.querySelector('.figure-caption');
  if (section.image_url) {
    if (canvas) canvas.hidden = true;
    const img = oldFigure || document.createElement('img');
    img.className = 'published-figure';
    img.src = section.image_url;
    img.alt = section.image_alt || 'Published BRCA validation figure';
    if (!oldFigure) body.prepend(img);
    if (section.caption) {
      const caption = oldCaption || document.createElement('p');
      caption.className = 'figure-caption';
      caption.textContent = section.caption;
      if (!oldCaption) body.append(caption);
    } else if (oldCaption) oldCaption.remove();
    return;
  }
  if (oldFigure) oldFigure.remove();
  if (oldCaption) oldCaption.remove();
  if (canvas) canvas.hidden = false;
  const d = ctx2(canvas, 300);
  if (!d) return;
  const { x, W, H } = d, pad = 46;
  const fpr = section.fpr || [], tpr = section.tpr || [];
  const px = t => pad + t * (W - pad - 22);
  const py = t => H - pad - t * (H - pad - 22);

  x.font = '10.5px system-ui, -apple-system, "Segoe UI", sans-serif';
  x.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const v = i / 4;
    x.strokeStyle = GRID;
    x.beginPath(); x.moveTo(pad, py(v)); x.lineTo(W - 22, py(v)); x.stroke();
    x.beginPath(); x.moveTo(px(v), 16); x.lineTo(px(v), H - pad); x.stroke();
    x.fillStyle = MUTED;
    x.fillText(v.toFixed(2), 10, py(v) + 3);
    x.fillText(v.toFixed(2), px(v) - 12, H - pad + 16);
  }
  // The coin-flip line: anything on it is no better than guessing.
  x.strokeStyle = FAINT;
  x.setLineDash([5, 4]);
  x.beginPath(); x.moveTo(px(0), py(0)); x.lineTo(px(1), py(1)); x.stroke();
  x.setLineDash([]);

  x.strokeStyle = INK;
  x.lineWidth = 2;
  x.lineJoin = 'round';
  x.beginPath();
  fpr.forEach((v, i) => (i ? x.lineTo(px(v), py(tpr[i])) : x.moveTo(px(v), py(tpr[i]))));
  x.stroke();

  x.fillStyle = MUTED;
  x.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif';
  x.fillText('false alarms', W / 2 - 34, H - 10);
  x.save();
  x.translate(14, H / 2 + 34);
  x.rotate(-Math.PI / 2);
  x.fillText('caught correctly', 0, 0);
  x.restore();
}

/* ---------------------------------------------------------------- volcano */

export function renderVolcano(host, section, canvas) {
  if (!paintState(host, section)) return;
  const body = host.querySelector('[data-body]');
  const chartbox = body && body.querySelector('.chartbox');
  const legend = chartbox && chartbox.querySelector('.legend');
  const oldFigure = chartbox && chartbox.querySelector('.published-figure');
  const oldCaption = body && body.querySelector('.figure-caption');
  if (section.image_url) {
    if (canvas) canvas.hidden = true;
    if (legend) legend.hidden = true;
    const img = oldFigure || document.createElement('img');
    img.className = 'published-figure';
    img.src = section.image_url;
    img.alt = section.image_alt || 'Published BRCA volcano plot';
    if (!oldFigure) chartbox.prepend(img);
    if (section.caption) {
      const caption = oldCaption || document.createElement('p');
      caption.className = 'figure-caption';
      caption.textContent = section.caption;
      if (!oldCaption) body.append(caption);
    } else if (oldCaption) oldCaption.remove();
    return;
  }
  if (oldFigure) oldFigure.remove();
  if (oldCaption) oldCaption.remove();
  if (canvas) canvas.hidden = false;
  if (legend) legend.hidden = false;
  const d = ctx2(canvas, 360);
  if (!d) return;
  const { x, W, H } = d, pad = 54;
  const vx = section.x || [], vy = section.y || [];
  const xm = Math.max(0.2, ...vx.map(Math.abs)) * 1.08;
  const ym = Math.max(2, ...vy) * 1.08;
  const px = t => pad + (t + xm) / (2 * xm) * (W - pad - 20);
  const py = t => H - pad - (t / ym) * (H - pad - 24);

  x.font = '11px system-ui, -apple-system, "Segoe UI", sans-serif';
  x.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const val = ym * i / 4, y = py(val);
    x.strokeStyle = GRID;
    x.beginPath(); x.moveTo(pad, y); x.lineTo(W - 20, y); x.stroke();
    x.fillStyle = MUTED;
    x.fillText(val.toFixed(0), 10, y + 3);
  }
  for (let i = -2; i <= 2; i++) {
    const val = xm * i / 2, X = px(val);
    x.strokeStyle = GRID;
    x.beginPath(); x.moveTo(X, 18); x.lineTo(X, H - pad); x.stroke();
    x.fillStyle = MUTED;
    x.fillText(val.toFixed(2), X - 13, H - pad + 17);
  }
  for (let i = 0; i < vx.length; i++) {
    const sig = vy[i] > 1.301 && Math.abs(vx[i]) >= 0.2;
    x.fillStyle = sig ? (vx[i] > 0 ? 'rgba(192,57,43,.62)' : 'rgba(42,120,214,.62)')
      : 'rgba(143,148,160,.26)';
    x.beginPath();
    x.arc(px(vx[i]), py(vy[i]), 2.4, 0, 6.284);
    x.fill();
  }
  x.fillStyle = MUTED;
  x.font = '12px system-ui, -apple-system, "Segoe UI", sans-serif';
  x.fillText('size of the difference', W / 2 - 62, H - 12);
  x.save();
  x.translate(16, H / 2 + 46);
  x.rotate(-Math.PI / 2);
  x.fillText('confidence', 0, 0);
  x.restore();
}

/* ----------------------------------------------------------------- cohort */

export function renderCohort(host, section) {
  if (!paintState(host, section)) return;
  const subs = section.subtypes || {};
  const total = Object.values(subs).reduce((a, b) => a + b, 0) || 1;
  const age = section.age || {};
  host.querySelector('[data-body]').innerHTML = Object.entries(subs)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `
      <div class="crow"><span class="ck">${esc(k)}</span>
        <span class="cbar"><i style="width:${(v / total * 100).toFixed(1)}%"></i></span>
        <span class="cv">${num(v)}</span></div>`).join('')
    + `<p class="sub" style="margin-top:10px">${num(section.tumor)} tumour ·
       ${num(section.normal)} normal tissue${
  age.tumor_median ? ` · median age ${age.tumor_median}` : ''}</p>`;
}

/* ------------------------------------------------------------- enrichment */

/* Also computed by every run since v1 and never drawn until now. */
export function renderEnrichment(host, section) {
  if (!paintState(host, section)) return;
  const rows = section.items || [];
  const key = r => r.term || r.pathway || r.name || r.description || '';
  const score = r => r.neg_log10_p != null ? r.neg_log10_p
    : (r.adjusted_p != null ? -Math.log10(Math.max(r.adjusted_p, 1e-300))
      : (r.p_value != null ? -Math.log10(Math.max(r.p_value, 1e-300)) : null));
  const max = Math.max(...rows.map(r => score(r) || 0), 0.0001);
  host.querySelector('[data-body]').innerHTML = rows.slice(0, 12).map(r => {
    const s = score(r);
    const n = r.n_genes != null ? r.n_genes : (r.overlap != null ? r.overlap : null);
    return `<div class="crow">
      <span class="ck" title="${esc(key(r))}">${esc(key(r))}</span>
      <span class="cbar"><i style="width:${s ? (s / max * 100).toFixed(1) : 0}%"></i></span>
      <span class="cv">${n != null ? num(n) + ' genes' : (s ? s.toFixed(1) : '')}</span>
    </div>`;
  }).join('') + (section.caption
    ? `<p class="figure-caption">${esc(section.caption)}</p>` : '');
}

/* ------------------------------------------------------------------ table */

const NICE_COLUMN = {
  probe_id: 'site', gene: 'gene', chrom: 'chromosome', delta_beta: 'difference',
  abs_delta_beta: 'size of difference', fdr: 'confidence (FDR)', direction: 'change',
  functional_region: 'where on the gene', predicted_expression_effect: 'likely effect',
  panel_rank: 'rank',
};

export function renderTable(host, section, filter) {
  if (!paintState(host, section)) return;
  let rows = section.rows || [];
  const needle = (filter || '').toLowerCase();
  if (needle) {
    rows = rows.filter(r => Object.values(r).some(v =>
      String(v).toLowerCase().includes(needle)));
  }
  const body = host.querySelector('[data-body]');
  if (!rows.length) {
    body.innerHTML = `<p class="sub pad">Nothing matches "${esc(filter)}".</p>`;
    return;
  }
  const cols = section.columns && section.columns.length
    ? section.columns : Object.keys(rows[0]);
  body.innerHTML = `<table><thead><tr>${
    cols.map(c => `<th>${esc(NICE_COLUMN[c] || c.replace(/_/g, ' '))}</th>`).join('')
  }</tr></thead><tbody>${
    rows.slice(0, 200).map(r => '<tr>' + cols.map(c => {
      const v = r[c];
      if (c === 'direction') {
        const up = String(v).startsWith('hyper');
        return `<td class="${up ? 'hyper' : 'hypo'}">${
          up ? 'gained' : 'lost'} methylation</td>`;
      }
      if (c === 'probe_id') return `<td><code>${esc(v)}</code></td>`;
      if (typeof v === 'number' && !Number.isInteger(v)) {
        return `<td class="numcell">${
          Math.abs(v) < 1e-3 && v !== 0 ? v.toExponential(1) : v.toFixed(3)}</td>`;
      }
      return `<td>${esc(v)}</td>`;
    }).join('') + '</tr>').join('')
  }</tbody></table>${
    rows.length > 200 ? `<p class="sub pad">Showing the first 200 of ${num(rows.length)}.</p>` : ''
  }`;
}

/* -------------------------------------------------------------- downloads */

const bytes = b => b == null ? '' : b < 1024 ? b + ' B'
  : b < 1048576 ? (b / 1024).toFixed(0) + ' KB' : (b / 1048576).toFixed(1) + ' MB';

export function renderDownloads(host, section) {
  if (!paintState(host, section)) return;
  host.querySelector('[data-body]').innerHTML = `<table><thead><tr>
      <th>File</th><th>Size</th><th>What it is</th><th></th></tr></thead><tbody>${
  (section.items || []).map(f => `<tr>
        <td><code>${esc(f.name)}</code></td>
        <td class="numcell">${bytes(f.size)}</td>
        <td>${esc(f.note)}</td>
        <td><a href="${esc(f.url)}">download</a></td></tr>`).join('')
}</tbody></table>`;
}
