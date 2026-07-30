"""Standalone HTML report generator.

Styling deliberately mirrors the published Results_Presentation.html so a generated
run report sits next to the real site without looking foreign. The output is fully
self-contained: no external CSS, JS, fonts or images.
"""
from __future__ import annotations

import html
import json
import time

import pandas as pd

CSS = """
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#1a2733;line-height:1.6;margin:0;background:#eef1f5}
.wrap{max-width:1060px;margin:0 auto;padding:0 22px 70px}
header{background:linear-gradient(135deg,#173a5c,#2e75b6);color:#fff;padding:40px 22px 30px}
header h1{margin:0 0 6px;font-size:30px}.sub{opacity:.92;font-size:16px}.meta{opacity:.82;font-size:13px;margin-top:10px}
nav{background:#12314e;position:sticky;top:0;z-index:20;padding:9px 22px;overflow-x:auto;white-space:nowrap}
nav a{color:#cfe0f0;text-decoration:none;font-size:12.5px;margin-right:16px;font-weight:600}nav a:hover{color:#fff}
h2{color:#173a5c;border-bottom:3px solid #d3e0ee;padding-bottom:6px;margin-top:42px;font-size:22px}
h3{color:#2e5496;margin:20px 0 8px;font-size:16px}
.explain{background:#eaf4ff;border-left:5px solid #2e75b6;padding:12px 16px;border-radius:6px;margin:12px 0;font-size:14.5px}
.explain .tag{display:inline-block;background:#2e75b6;color:#fff;font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;margin-right:8px}
.cards{display:flex;flex-wrap:wrap;gap:13px;margin:16px 0}
.card{flex:1;min-width:150px;background:#fff;border-radius:10px;padding:15px;box-shadow:0 1px 4px rgba(0,0,0,.08);text-align:center}
.card .num{font-size:25px;font-weight:800;color:#173a5c}.card.red .num{color:#c0392b}.card.green .num{color:#1a7a3a}
.card .lbl{font-size:12px;color:#555;margin-top:4px}
table{border-collapse:collapse;width:100%;background:#fff;margin:12px 0;font-size:13px;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06)}
th{background:#173a5c;color:#fff;text-align:left;padding:8px 10px}
td{padding:7px 10px;border-top:1px solid #eef1f5;vertical-align:middle}tr:nth-child(even) td{background:#fafbfc}
td.hyper{color:#c0392b;font-weight:700}td.hypo{color:#1a7a3a;font-weight:700}
.tscroll{overflow-x:auto;margin:12px 0}.tscroll table{margin:0}
td code,code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;background:#eef1f5;padding:2px 6px;border-radius:3px;color:#1a2733}
.chartbox{background:#fff;border-radius:10px;padding:18px;margin:14px 0;box-shadow:0 1px 5px rgba(0,0,0,.09)}
.chartbox canvas{width:100%;display:block}
.legend{font-size:12.5px;color:#444;margin-top:8px}.legend .sw{display:inline-block;width:11px;height:11px;border-radius:50%;margin:0 4px 0 12px;vertical-align:middle}
.callout{padding:13px 17px;border-radius:6px;margin:14px 0}
.warn{background:#fff4e2;border-left:5px solid #e08a1e}.good{background:#eaf7ee;border-left:5px solid #1a7a3a}
.danger{background:#fdecea;border-left:5px solid #c0392b}
ul{margin:8px 0 8px 2px}li{margin:6px 0}
.small{font-size:12.5px;color:#666}
footer{margin-top:44px;padding-top:16px;border-top:1px solid #d7dde5;color:#888;font-size:12.5px}
.paramgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin:12px 0}
.paramcard{background:#fff;border-radius:8px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.paramcard h4{margin:0 0 6px;font-size:13.5px;color:#173a5c}
.paramcard dl{margin:0;font-size:12.5px}.paramcard dt{color:#666;float:left;clear:left;margin-right:6px}
.paramcard dd{margin:0 0 2px;color:#1a2733;font-weight:600}
"""


def esc(v):
    return html.escape(str(v))


def fmt(v, digits=3):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    if f != f:
        return "-"
    if f and (abs(f) < 1e-3 or abs(f) >= 1e5):
        return "%.2e" % f
    return ("%%.%df" % digits) % f


def table_html(frame, columns=None, limit=30):
    if frame is None or (hasattr(frame, "__len__") and len(frame) == 0):
        return "<p class='small'>No rows.</p>"
    if isinstance(frame, pd.DataFrame):
        cols = columns or list(frame.columns)
        rows = frame.head(limit)[cols].to_dict("records")
    else:
        rows = frame[:limit]
        cols = columns or (list(rows[0].keys()) if rows else [])
    head = "".join("<th>%s</th>" % esc(c.replace("_", " ")) for c in cols)
    body = []
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c)
            cls = ""
            if c == "direction":
                cls = " class='hyper'" if str(v).startswith("hyper") else " class='hypo'"
            if c == "probe_id":
                cells.append("<td><code>%s</code></td>" % esc(v))
            elif isinstance(v, float):
                cells.append("<td%s>%s</td>" % (cls, fmt(v)))
            else:
                cells.append("<td%s>%s</td>" % (cls, esc("" if v is None else v)))
        body.append("<tr>%s</tr>" % "".join(cells))
    return "<div class='tscroll'><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (
        head, "".join(body))


def build(run, p):
    ctx = run.ctx
    title = p.get("title") or "BRCA Methylation - Pipeline Run"
    stats = {s["label"]: s["value"] for s in run.stats}
    simulated = "simulated" in str(ctx.get("data_provenance", "")).lower()

    nav = ["<a href='#provenance'>Provenance</a>", "<a href='#headline'>Headline numbers</a>"]
    parts = []

    # -- provenance / caveats ------------------------------------------------
    parts.append("<h2 id='provenance'>Data provenance</h2>")
    if simulated:
        parts.append(
            "<div class='callout danger'><b>This run used the bundled sample cohort. "
            "Every per-sample beta value in it is simulated.</b> Probe identities, gene symbols, "
            "coordinates and the per-probe tumour/normal means for the reference probes come from "
            "the published TCGA-BRCA analysis; the individual sample values were drawn from a Beta "
            "distribution matched to those means and to the standard deviation implied by the "
            "published t-statistics. Treat every number below as a demonstration of the method, "
            "not as a scientific result. To produce real results, set the Load block to "
            "<code>custom</code> and point it at the real methylation matrix.</div>")
    else:
        parts.append("<div class='callout good'>Run executed against user-supplied input files: "
                     "<code>%s</code>.</div>" % esc(ctx.get("data_provenance", "")))

    if p.get("include_caveats"):
        nav.append("<a href='#caveats'>Caveats</a>")
        parts.append("<h2 id='caveats'>Caveats that travel with these numbers</h2>")
        parts.append(
            "<div class='callout warn'><ul>"
            "<li><b>&quot;Normal&quot; means tumour-adjacent tissue</b>, not healthy donors, so it "
            "can already carry mild early changes.</li>"
            "<li><b>HM450 is an array, not sequencing.</b> It reads a fixed ~485k CpG set that "
            "over-represents promoters of neuronal and developmental genes. That design bias is "
            "exactly why broad pathway claims do not hold up.</li>"
            "<li><b>Methylation predicts, it does not measure, gene activity.</b> Silencing and "
            "activation are predictions from promoter methylation, not expression measurements.</li>"
            "<li><b>Outside a promoter the consequence is not predictable</b> and is labelled "
            "ambiguous rather than guessed.</li>"
            "</ul></div>")
        if run.warnings:
            parts.append("<h3>Warnings raised by this run</h3><div class='callout warn'><ul>%s</ul></div>"
                         % "".join("<li>%s</li>" % esc(w) for w in run.warnings))

    # -- headline ------------------------------------------------------------
    parts.append("<h2 id='headline'>Headline numbers</h2>")
    cards = []
    for label in ("Probes loaded", "Probes after QC", "Probes tested", "Significant probes",
                  "Probes passing effect filter", "Panel size", "ROC-AUC"):
        if label in stats:
            v = stats[label]
            cls = " red" if label == "Significant probes" else (" green" if label == "ROC-AUC" else "")
            shown = "%s" % v if isinstance(v, float) else "{:,}".format(v) if isinstance(v, int) else esc(v)
            cards.append("<div class='card%s'><div class='num'>%s</div><div class='lbl'>%s</div></div>"
                         % (cls, shown, esc(label)))
    if cards:
        parts.append("<div class='cards'>%s</div>" % "".join(cards))

    qc = ctx.get("qc") or {}
    if qc:
        parts.append("<div class='explain'><span class='tag'>QC</span>"
                     "Dropped <b>%d</b> samples and <b>%d</b> probes on missingness, plus <b>%d</b> "
                     "sex-chromosome probes. These filters never look at the group labels, so they "
                     "cannot leak group information into the comparison.</div>"
                     % (qc.get("samples_dropped_missingness", 0),
                        qc.get("probes_dropped_missingness", 0),
                        qc.get("probes_dropped_sex_chromosome", 0)))

    # -- volcano -------------------------------------------------------------
    volcano = ctx.get("volcano")
    if p.get("include_volcano") and volcano and volcano.get("x"):
        nav.append("<a href='#volcano'>Volcano</a>")
        parts.append("<h2 id='volcano'>Volcano plot</h2>")
        parts.append(
            "<div class='explain'><span class='tag'>How to read it</span>Each dot is one CpG site. "
            "Left/right is the size and direction of the methylation change; up is statistical "
            "confidence. Points in the top corners are both large and confident.</div>")
        parts.append("<div class='chartbox'><canvas id='volc' height='420'></canvas>"
                     "<div class='legend'><span class='sw' style='background:#c0392b'></span>hyper"
                     "<span class='sw' style='background:#1a7a3a'></span>hypo"
                     "<span class='sw' style='background:#9aa5b1'></span>not significant</div></div>")

    # -- markers -------------------------------------------------------------
    st = ctx.get("stats")
    if p.get("include_tables") and isinstance(st, pd.DataFrame) and len(st):
        nav.append("<a href='#markers'>Top markers</a>")
        parts.append("<h2 id='markers'>Strongest markers</h2>")
        cols = [c for c in ["probe_id", "gene", "chrom", "delta_beta", "fdr", "direction",
                            "functional_region", "predicted_expression_effect"] if c in st.columns]
        parts.append(table_html(st.sort_values("abs_delta_beta", ascending=False), cols, 25))

    mech = ctx.get("mechanics_counts") or {}
    if mech:
        nav.append("<a href='#mechanics'>Direction of effect</a>")
        parts.append("<h2 id='mechanics'>Predicted direction of effect</h2>")
        parts.append("<div class='explain'><span class='tag'>The rule</span>Promoter + hyper = "
                     "predicted <b>silencing</b>. Promoter + hypo = predicted <b>activation</b>. "
                     "Anywhere else, the consequence is <b>ambiguous</b> and is not guessed.</div>")
        cls_map = {"silencing": " red", "activation": " green"}
        parts.append("<div class='cards'>%s</div>" % "".join(
            "<div class='card%s'><div class='num'>%s</div><div class='lbl'>%s</div></div>"
            % (cls_map.get(k, ""), "{:,}".format(v), esc(k)) for k, v in sorted(mech.items())))

    # -- panel + model -------------------------------------------------------
    panel = ctx.get("panel")
    if p.get("include_tables") and isinstance(panel, pd.DataFrame) and len(panel):
        nav.append("<a href='#panel'>Panel</a>")
        parts.append("<h2 id='panel'>Candidate biomarker panel</h2>")
        cols = [c for c in ["panel_rank", "probe_id", "gene", "chrom", "delta_beta", "fdr",
                            "direction", "predicted_expression_effect"] if c in panel.columns]
        parts.append(table_html(panel, cols, 30))

    model = ctx.get("model")
    if model:
        nav.append("<a href='#validation'>Validation</a>")
        parts.append("<h2 id='validation'>Classifier validation</h2>")
        parts.append(
            "<div class='cards'>"
            "<div class='card green'><div class='num'>%.4f</div><div class='lbl'>mean ROC-AUC</div></div>"
            "<div class='card'><div class='num'>%.4f</div><div class='lbl'>std across folds</div></div>"
            "<div class='card'><div class='num'>%d</div><div class='lbl'>features</div></div>"
            "<div class='card'><div class='num'>%d</div><div class='lbl'>CV folds</div></div></div>"
            % (model["roc_auc_mean"], model["roc_auc_std"], model["n_features"], model["cv_folds"]))
        parts.append("<div class='explain'><span class='tag'>Feature selection</span>%s</div>"
                     % esc(model["feature_selection"]))
        if ctx.get("roc"):
            parts.append("<div class='chartbox'><canvas id='roc' height='340'></canvas>"
                         "<div class='legend'>Pooled out-of-fold ROC curve. The diagonal is chance.</div></div>")

    # -- enrichment ----------------------------------------------------------
    top_terms = ctx.get("enrichment_top") or []
    if top_terms:
        nav.append("<a href='#pathways'>Pathways</a>")
        parts.append("<h2 id='pathways'>Pathway enrichment (exploratory)</h2>")
        parts.append("<div class='callout warn'><b>Read this first.</b> HM450 over-samples promoters "
                     "of neuronal and developmental genes. Enrichment on array-derived gene lists "
                     "inherits that bias, so these terms are exploratory and a negative result here "
                     "is a legitimate result.</div>")
        parts.append(table_html(
            [{"library": t["library"], "term": t["term"], "overlap": t["overlap"],
              "set_size": t["set_size"], "fdr": t["fdr"]} for t in top_terms],
            ["library", "term", "overlap", "set_size", "fdr"], 14))

    # -- methods -------------------------------------------------------------
    if p.get("include_methods"):
        nav.append("<a href='#methods'>Methods</a>")
        parts.append("<h2 id='methods'>Methods - exactly what this run did</h2>")
        blocks = []
        from . import catalog
        for node in run.graph.get("nodes", []):
            spec = catalog.NODES_BY_TYPE.get(node["type"])
            if not spec:
                continue
            params = catalog.merged_params(node["type"], node.get("params"))
            items = "".join("<dt>%s</dt><dd>%s</dd>" % (esc(k.replace("_", " ")), esc(v))
                            for k, v in params.items())
            blocks.append("<div class='paramcard'><h4>%s</h4><dl>%s</dl></div>"
                          % (esc(spec["name"]), items))
        parts.append("<div class='paramgrid'>%s</div>" % "".join(blocks))

    # -- files ---------------------------------------------------------------
    nav.append("<a href='#files'>Files</a>")
    parts.append("<h2 id='files'>Files produced by this run</h2>")
    files = run.files()
    parts.append(table_html([{"file": f["name"], "size_bytes": f["size"]} for f in files],
                            ["file", "size_bytes"], 100))

    chart_data = json.dumps({"volcano": volcano if p.get("include_volcano") else None,
                             "roc": ctx.get("roc")})

    doc = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>{css}</style></head><body>
<header><h1>{title}</h1>
<div class="sub">Generated by the pipeline builder - every number below was produced by the block graph shown in Methods.</div>
<div class="meta">Run {run_id} · {when} · {elapsed:.1f}s · comparison: {run_name}</div></header>
<nav>{nav}</nav>
<div class="wrap">
{body}
<footer>Generated {when} by the BRCA Methylation pipeline builder. Self-contained: this file needs no other file to display.</footer>
</div>
<script>
const DATA = {chart_data};
/* Returns null when the canvas has no layout yet - which is the case whenever this
   report is loaded inside a hidden iframe. The ResizeObserver below redraws once it
   gains a size, so the charts are never left blank. */
function hidpi(c,h){{const r=c.getBoundingClientRect(),d=window.devicePixelRatio||1;
if(!r.width) return null;
c.width=r.width*d;c.height=h*d;const x=c.getContext('2d');x.setTransform(d,0,0,d,0,0);return x;}}
function volcano(){{
 const c=document.getElementById('volc'); if(!c||!DATA.volcano) return;
 const H=420,pad=48,x=hidpi(c,H); if(!x) return;
 const W=c.getBoundingClientRect().width;
 const xs=DATA.volcano.x, ys=DATA.volcano.y;
 const xmax=Math.max(0.2,...xs.map(Math.abs))*1.08, ymax=Math.max(2,...ys)*1.08;
 const px=v=>pad+(v+xmax)/(2*xmax)*(W-pad-18), py=v=>H-pad-(v/ymax)*(H-pad-20);
 x.clearRect(0,0,W,H); x.strokeStyle='#e3e8ee'; x.fillStyle='#666'; x.font='11px sans-serif';
 for(let i=0;i<=4;i++){{const v=ymax*i/4,y=py(v);x.beginPath();x.moveTo(pad,y);x.lineTo(W-18,y);x.stroke();
  x.fillText(v.toFixed(0),6,y+3);}}
 for(let i=-2;i<=2;i++){{const v=xmax*i/2,X=px(v);x.beginPath();x.moveTo(X,20);x.lineTo(X,H-pad);x.stroke();
  x.fillText(v.toFixed(2),X-12,H-pad+16);}}
 for(let i=0;i<xs.length;i++){{
  const sig=ys[i]>1.301&&Math.abs(xs[i])>=0.2;
  x.fillStyle=sig?(xs[i]>0?'rgba(192,57,43,.55)':'rgba(26,122,58,.55)'):'rgba(154,165,177,.35)';
  x.beginPath();x.arc(px(xs[i]),py(ys[i]),2.1,0,6.284);x.fill();}}
 x.fillStyle='#333';x.font='12px sans-serif';
 x.fillText('delta-beta (tumour minus normal)',W/2-90,H-12);
 x.save();x.translate(14,H/2+70);x.rotate(-Math.PI/2);x.fillText('-log10(FDR)',0,0);x.restore();
}}
function roc(){{
 const c=document.getElementById('roc'); if(!c||!DATA.roc) return;
 const H=340,pad=44,x=hidpi(c,H); if(!x) return;
 const W=c.getBoundingClientRect().width;
 const px=v=>pad+v*(W-pad-18), py=v=>H-pad-v*(H-pad-20);
 x.clearRect(0,0,W,H);x.strokeStyle='#e3e8ee';
 for(let i=0;i<=5;i++){{const y=py(i/5);x.beginPath();x.moveTo(pad,y);x.lineTo(W-18,y);x.stroke();}}
 x.strokeStyle='#bbb';x.setLineDash([4,4]);x.beginPath();x.moveTo(px(0),py(0));x.lineTo(px(1),py(1));x.stroke();x.setLineDash([]);
 x.strokeStyle='#2e75b6';x.lineWidth=2.4;x.beginPath();
 DATA.roc.fpr.forEach((f,i)=>{{const X=px(f),Y=py(DATA.roc.tpr[i]);i?x.lineTo(X,Y):x.moveTo(X,Y);}});
 x.stroke();
 x.fillStyle='#333';x.font='12px sans-serif';x.fillText('false positive rate',W/2-52,H-12);
 x.save();x.translate(14,H/2+50);x.rotate(-Math.PI/2);x.fillText('true positive rate',0,0);x.restore();
}}
function drawAll(){{volcano();roc();}}
drawAll();
window.addEventListener('resize',drawAll);
/* When this report is loaded into a hidden tab or iframe its canvases have no width
   yet, so the first draw is a no-op. Rendering is suppressed there, which means
   requestAnimationFrame and ResizeObserver are unreliable - a timer is not. Poll until
   the canvas has a real width, draw once, then stop. */
(function(){{
  const probe=document.getElementById('volc')||document.getElementById('roc');
  if(!probe||probe.getBoundingClientRect().width>0) return;
  const iv=setInterval(function(){{
    if(probe.getBoundingClientRect().width>0){{clearInterval(iv);drawAll();}}
  }},250);
  setTimeout(function(){{clearInterval(iv);}},60000);
}})();
</script></body></html>""".format(
        title=esc(title), css=CSS, nav="".join(nav), body="\n".join(parts),
        run_id=esc(run.id), when=time.strftime("%Y-%m-%d %H:%M"),
        elapsed=(run.finished or time.time()) - run.started,
        run_name=esc(ctx.get("run_name", "-")), chart_data=chart_data)

    path = run.dir / "run_report.html"
    path.write_text(doc, encoding="utf-8")
    return path
