"""The two builders. One shape, one set of algorithms, two sources.

`from_reference()` reads the published study out of data/reference/.
`from_run()` reads whatever a run you started wrote to results.json.

Where the two used to each do their own thing - picking top movers, choosing
table columns, counting direction - there is now one function that both call.
That is the point: the same code has to run over your uploaded data as runs
over the example cohort, or the two screens are not comparable and the
numbers on them cannot be trusted against each other.

Where a source genuinely cannot produce a panel, it says so in a sentence
the reader can act on. It does not hide the panel.
"""
from __future__ import annotations

import math

from . import schema
from .schema import ok, empty, unavailable

MOVER_LIMIT = 16
TABLE_LIMIT = 250

# Preferred column order for the marker/panel tables. Anything a source has
# that is not listed keeps its own order after these, so a new engine column
# shows up instead of being silently dropped.
_COLUMN_ORDER = ("probe_id", "gene", "chrom", "delta_beta", "abs_delta_beta",
                 "fdr", "direction", "functional_region",
                 "predicted_expression_effect", "panel_rank")


def _finite(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _clean_gene(v):
    """A gene name, or None. Guards NaN, the string 'nan', and blanks."""
    if v is None or (isinstance(v, float) and v != v):
        return None
    s = str(v).strip()
    return None if s.lower() in ("", "nan", "na", "none") else s


# ---------------------------------------------------------------------------
# the shared algorithms - identical for every source, by construction
# ---------------------------------------------------------------------------

def top_movers(rows, limit=MOVER_LIMIT):
    """Biggest signed change per gene, largest absolute first, one row a gene.

    `rows` are dicts with at least gene / probe_id / delta_beta. tumor_mean_beta
    and normal_mean_beta come through when the source has them and stay None
    when it does not - declared rather than omitted, so the renderer can show
    the group means where they exist without guessing.
    """
    best = {}
    for row in rows or []:
        gene = _clean_gene(row.get("gene"))
        delta = _finite(row.get("delta_beta"))
        if gene is None or delta is None:
            continue
        first = gene.split(",")[0].strip() or gene
        prev = best.get(first)
        if prev is not None and abs(prev["delta"]) >= abs(delta):
            continue
        best[first] = {
            "gene": first,
            "probe": str(row.get("probe_id") or ""),
            "delta": round(delta, 4),
            "tumor": _round(row.get("tumor_mean_beta")),
            "normal": _round(row.get("normal_mean_beta")),
            "direction": str(row.get("direction") or ""),
        }
    out = sorted(best.values(), key=lambda r: abs(r["delta"]), reverse=True)
    return out[:limit]


def _round(v, places=4):
    f = _finite(v)
    return None if f is None else round(f, places)


def direction_counts(raw):
    """The three slices, always all three. Absent means none, not unmeasured."""
    counts = {}
    for slice_ in schema.DIRECTION_SLICES:
        v = (raw or {}).get(slice_)
        counts[slice_] = int(v) if isinstance(v, (int, float)) and v == v else 0
    return counts


def order_columns(columns):
    """One column order for every source, so the tables line up side by side."""
    cols = [c for c in columns or []]
    known = [c for c in _COLUMN_ORDER if c in cols]
    rest = [c for c in cols if c not in _COLUMN_ORDER]
    return known + rest


def table_section(name, rows, columns, empty_reason):
    rows = list(rows or [])
    if not rows:
        return empty(name, empty_reason)
    cols = order_columns(columns or list(rows[0].keys()))
    return ok(name, rows=rows[:TABLE_LIMIT], columns=cols)


def validation_section(folds, model):
    """Cross-validation scores. An average with no per-round list is still a
    result - the renderer shows the number alone rather than an empty chart."""
    model = dict(model or {})
    folds = [f for f in (_round(f, 4) for f in (folds or [])) if f is not None]
    if not folds and model.get("roc_auc_mean") is None:
        return unavailable("validation",
                           "This run did not include the prediction test, so there is "
                           "no score to show.")
    return ok("validation", folds=folds, model=model)


# ---------------------------------------------------------------------------
# source 1 - the published study
# ---------------------------------------------------------------------------

def from_reference(files):
    """Build the dashboard for the published BRCA study.

    `files` is a small reader object (see console_v4.sources) so this module
    stays free of paths and pandas: .json(name) and .table(name) are all it
    needs, and the test can hand it fixtures.
    """
    cohort = files.json("cohort_summary.json") or {}
    analysis = files.json("analysis_summary.json") or {}
    clf = files.json("classifier_summary.json") or {}
    mech = (files.json("methylation_mechanics_counts.json") or {}).get("full_significant", {})
    nested = files.json("nested_validation_summary.json") or {}

    markers = files.table("top_markers_abs_delta_beta.tsv") or []
    panel_rows = files.table("candidate_biomarker_panel.tsv") or []

    src = schema.source(
        kind="reference",
        id="published-study",
        title="Breast tumour vs normal tissue - published study",
        subtitle="%s samples · %s DNA sites tested · TCGA-BRCA" % (
            "{:,}".format(cohort.get("n_samples") or 0),
            "{:,}".format(analysis.get("n_probes_tested") or 0)),
        tier_label="Published study",
        caveat="This is the completed study this project published, shown so the "
               "screen is not empty. It is not the output of a run you started here.",
    )
    model = schema.blank(src)

    model["cards"] = ok("cards", items=[
        {"label": "Samples in the study", "value": cohort.get("n_samples"),
         "note": "%s tumour · %s normal" % (cohort.get("n_tumor"), cohort.get("n_normal"))},
        {"label": "DNA sites tested", "value": analysis.get("n_probes_tested"),
         "note": "across the whole array"},
        {"label": "Sites that changed",
         "value": analysis.get("n_fdr_lt_0_05_and_abs_delta_ge_0_20"),
         "note": "confident and a difference of 0.20 or more", "tone": "hyper"},
        {"label": "Told the groups apart", "value": clf.get("roc_auc_mean"),
         "note": "%d-fold cross-validation" % (clf.get("cv_folds") or 5),
         "tone": "hypo", "kind": "auc"},
    ])

    movers = top_movers(markers)
    model["movers"] = ok("movers", items=movers) if movers else empty(
        "movers", "No marker in the published bundle carries a gene name.")

    counts = direction_counts(mech)
    model["direction"] = ok("direction", counts=counts) if sum(counts.values()) else empty(
        "direction", "The published bundle records no predicted effect for these sites.")

    folds = (nested.get("nested_internal_cv") or {}).get("roc_auc_per_fold") \
        or clf.get("roc_auc_per_fold") or []
    model["validation"] = validation_section(folds, {
        "model": clf.get("model"), "cv_folds": clf.get("cv_folds"),
        "roc_auc_mean": clf.get("roc_auc_mean"), "roc_auc_std": clf.get("roc_auc_std"),
        "nested": bool(nested.get("nested_internal_cv")),
    })

    # The published bundle stores per-fold scores, not the curve itself.
    model["roc"] = unavailable(
        "roc", "The published bundle stores the cross-validation scores but not the "
               "false-positive/true-positive curve behind them, so this cannot be "
               "drawn from it. A run you start here does record the curve.")

    # 250 top markers is not every probe, and a volcano of a pre-filtered
    # shortlist would be a misleading picture rather than a partial one.
    model["volcano"] = unavailable(
        "volcano", "This needs every DNA site tested. The published bundle keeps only "
                   "the %d strongest, so plotting it here would show a shortlist and "
                   "call it the whole array. A run you start here plots all of them."
                   % len(markers))

    subtypes = {k: v for k, v in (cohort.get("subtypes") or {}).items()
                if str(k).lower() not in ("nan", "na", "none")}
    model["cohort"] = ok("cohort", subtypes=subtypes, tumor=cohort.get("n_tumor"),
                         normal=cohort.get("n_normal"), age=cohort.get("ages") or {}) \
        if subtypes else empty("cohort", "No subtype breakdown in the published bundle.")

    model["enrichment"] = unavailable(
        "enrichment", "Pathway enrichment was not part of the published bundle. A run "
                      "you start here computes it.")

    model["table"] = table_section(
        "table", markers, markers[0].keys() if markers else [],
        "The published bundle contains no marker table.")
    model["panel"] = table_section(
        "panel", panel_rows, panel_rows[0].keys() if panel_rows else [],
        "The published bundle contains no shortlist.")

    model["thresholds"] = ok("thresholds", used={"fdr": 0.05, "delta_beta": 0.20})

    model["report"] = ok("report", url="/site/Results_Presentation.html", variants=[
        {"label": "Single-page report", "url": "/site/Results_Presentation.html"},
        {"label": "Multi-page site", "url": "/site/website_v2/index.html"},
    ])

    model["downloads"] = unavailable(
        "downloads", "The published study is read-only. Downloads come from runs you "
                     "start here.")
    return model


# ---------------------------------------------------------------------------
# source 2 - a run you started, over the example cohort or your own files
# ---------------------------------------------------------------------------

_CARD_ORDER = [
    ("Samples loaded", "Samples analysed", None, ""),
    ("Probes tested", "DNA sites tested", None, ""),
    ("Significant probes", "Sites that changed", "hyper",
     "confident and past the effect threshold"),
    ("ROC-AUC", "Told the groups apart", "hypo", "cross-validated"),
]


_FILE_NOTES = {
    "differential_methylation.tsv": "Every site tested, with its difference and p-value.",
    "differential_with_mechanics.tsv": "The same, plus gene context and likely effect.",
    "candidate_biomarker_panel.tsv": "The shortlist of top sites.",
    "classifier_summary.json": "How well the shortlist told the groups apart.",
    "cv_folds.tsv": "Score from each cross-validation round.",
    "qc_sample_missingness.tsv": "How much data was missing per sample.",
    "run_manifest.json": "Exactly which settings this run used.",
    "run_record.json": "The full record, including the checks and the verdict.",
    "run_log.txt": "The complete log.",
    "run_report.html": "The report.",
    "commands.txt": "What a real run would do, resolved but not executed.",
    "bundle.zip": "Everything above, in one archive.",
}


def describe_file(name):
    """What a downloaded file is, in one line. Server-side so the Downloads
    tab and the report describe the same file the same way."""
    if name.startswith("enrichment_"):
        return "Pathways the hit genes fall into."
    if name.startswith("demo_sample_"):
        return "The subset this test run used."
    return _FILE_NOTES.get(name, "")


def from_run(res, snap=None, report_url=None, files=None, bundle_url=None):
    """Build the dashboard for one run, from its own results.json.

    `report_url` is passed in rather than guessed: a run that never reached
    the report step has none, and showing an older run's report in its place
    would describe the wrong analysis. `files` and `bundle_url` come from the
    same call, so the Downloads tab cannot end up describing a different run
    than the charts above it.
    """
    res = res or {}
    snap = snap or {}
    stats = {s["label"]: s["value"] for s in (res.get("stats") or [])}

    src = schema.source(
        kind="run",
        id=str(snap.get("id") or snap.get("run_id") or ""),
        title=snap.get("label") or "This run",
        subtitle=" · ".join(p for p in (snap.get("tier_label") or snap.get("mode") or "",
                                        (res.get("data_provenance") or "")[:90]) if p),
        tier_label=snap.get("tier_label") or snap.get("mode") or "",
        caveat="",
    )
    model = schema.blank(src)

    cards = [{"label": label, "value": stats[key], "tone": tone, "note": note,
              "kind": "auc" if key == "ROC-AUC" else None}
             for key, label, tone, note in _CARD_ORDER if key in stats]
    model["cards"] = ok("cards", items=cards) if cards else empty(
        "cards", "This run recorded no headline numbers.")

    # Anything else the run reported, kept but not promoted to a card.
    model["extra_stats"] = [{"label": k, "value": v} for k, v in stats.items()
                            if k not in {c[0] for c in _CARD_ORDER}]

    movers = top_movers(res.get("top_markers"))
    model["movers"] = ok("movers", items=movers) if movers else empty(
        "movers", "No site that passed the filters could be matched to a gene.")

    counts = direction_counts(res.get("mechanics_counts"))
    model["direction"] = ok("direction", counts=counts) if sum(counts.values()) else empty(
        "direction", "No site passed the filters, so there was nothing to classify as "
                     "switching a gene off or on.")

    mdl = dict(res.get("model") or {})
    model["validation"] = validation_section(mdl.get("roc_auc_per_fold"), mdl)

    roc = res.get("roc") or {}
    fpr, tpr = list(roc.get("fpr") or []), list(roc.get("tpr") or [])
    model["roc"] = ok("roc", fpr=fpr, tpr=tpr) if len(fpr) == len(tpr) and fpr else \
        unavailable("roc", "This run did not include the prediction test, so there is "
                           "no curve to draw.")

    v = res.get("volcano") or {}
    vx, vy = list(v.get("x") or []), list(v.get("y") or [])
    model["volcano"] = ok("volcano", x=vx, y=vy, probe=list(v.get("probe") or [])) \
        if vx and len(vx) == len(vy) else \
        unavailable("volcano", "This run stopped before the per-site table was written, "
                               "so there is nothing to plot.")

    # A run's results carry no clinical annotation - it is in the sample sheet
    # the run was pointed at, not in what the engine writes out.
    model["cohort"] = unavailable(
        "cohort", "A run records the groups it compared, not the clinical subtypes "
                  "behind them. The published study shows those because they were "
                  "curated with it.")

    enrich = res.get("enrichment_top") or []
    if enrich:
        model["enrichment"] = ok("enrichment", items=enrich)
    elif res.get("enrichment_null"):
        model["enrichment"] = empty(
            "enrichment", "Enrichment ran and no pathway came out ahead of chance. "
                          "That is an answer: the changed genes are spread across "
                          "pathways rather than concentrated in one.")
    else:
        model["enrichment"] = unavailable(
            "enrichment", "This run did not reach the enrichment step.")

    model["table"] = table_section(
        "table", res.get("top_markers"), res.get("top_marker_columns"),
        "No site passed both the confidence and the effect-size filter.")
    model["panel"] = table_section(
        "panel", res.get("panel"), res.get("panel_columns"),
        "There was no shortlist to build - nothing cleared the filters.")

    used = snap.get("thresholds") or {}
    model["thresholds"] = ok("thresholds", used=used) if used else unavailable(
        "thresholds", "This run did not record the thresholds it used.")

    model["report"] = ok("report", url=report_url, variants=[]) if report_url else \
        unavailable("report", "The report step did not finish for this run. An older "
                              "report is not shown in its place - it would not "
                              "describe this run.")

    items = [{"name": f.get("name"), "size": f.get("size"),
              "note": describe_file(f.get("name") or ""), "url": f.get("url")}
             for f in (files or []) if f.get("name")]
    model["downloads"] = ok("downloads", items=items, bundle_url=bundle_url) if items else \
        empty("downloads", "No step in this run produced a file.")
    return model
