"""The published study, loaded for display.

The studio opens on the completed BRCA analysis rather than on an empty
screen, so you can see what a finished result looks like before running
anything. Every number here is read from data/reference/ - the files the
published analysis actually wrote. Nothing is illustrative or made up.

This is clearly labelled as the published study in the UI. It is never
presented as the output of a run you just did.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from console_v2 import study

REF = study.ROOT / "data" / "reference"


def _json(name, default=None):
    path = REF / name
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _table(name, rows=None):
    path = REF / name
    if not path.is_file():
        return None
    frame = pd.read_csv(path, sep="\t")
    return frame.head(rows) if rows else frame


def _fmt(n):
    return int(n) if isinstance(n, (int, float)) and float(n).is_integer() else n


def payload():
    cohort = _json("cohort_summary.json", {}) or {}
    analysis = _json("analysis_summary.json", {}) or {}
    clf = _json("classifier_summary.json", {}) or {}
    mech = (_json("methylation_mechanics_counts.json", {}) or {}).get("full_significant", {})
    nested = _json("nested_validation_summary.json", {}) or {}

    markers = _table("top_markers_abs_delta_beta.tsv")
    panel = _table("candidate_biomarker_panel.tsv")

    cards = [
        {"label": "Samples in the study", "value": cohort.get("n_samples"),
         "note": "%s tumour · %s normal" % (cohort.get("n_tumor"), cohort.get("n_normal"))},
        {"label": "DNA sites tested", "value": analysis.get("n_probes_tested"),
         "note": "across the whole array"},
        {"label": "Sites that changed", "value": analysis.get("n_fdr_lt_0_05_and_abs_delta_ge_0_20"),
         "note": "confident and a difference of 0.20 or more", "tone": "red"},
        {"label": "Told the groups apart", "value": clf.get("roc_auc_mean"),
         "note": "%d-fold cross-validation" % (clf.get("cv_folds") or 5),
         "tone": "green", "kind": "auc"},
    ]

    # Top movers: one bar per gene, signed, biggest absolute change first.
    movers = []
    if markers is not None and "gene" in markers.columns:
        top = (markers.dropna(subset=["gene"])
               .sort_values("abs_delta_beta", ascending=False)
               .drop_duplicates(subset=["gene"])
               .head(16))
        movers = [{"gene": str(r.gene), "probe": str(r.probe_id),
                   "delta": round(float(r.delta_beta), 4),
                   "tumor": round(float(r.tumor_mean_beta), 4),
                   "normal": round(float(r.normal_mean_beta), 4),
                   "direction": str(r.direction)}
                  for r in top.itertuples()]

    table_rows, table_cols = [], []
    if markers is not None:
        cols = [c for c in ("probe_id", "gene", "chrom", "delta_beta", "fdr", "direction")
                if c in markers.columns]
        table_cols = cols
        table_rows = json.loads(markers.head(200)[cols].to_json(orient="records"))

    panel_rows, panel_cols = [], []
    if panel is not None:
        cols = [c for c in ("probe_id", "gene", "chrom", "delta_beta", "fdr", "direction")
                if c in panel.columns]
        panel_cols = cols
        panel_rows = json.loads(panel.head(100)[cols].to_json(orient="records"))

    folds = (nested.get("nested_internal_cv") or {}).get("roc_auc_per_fold") \
        or clf.get("roc_auc_per_fold") or []

    return {
        "is_reference": True,
        "title": "Breast tumour vs normal tissue — published study",
        "subtitle": "%s samples · %s DNA sites tested · TCGA-BRCA" % (
            f"{cohort.get('n_samples', 0):,}", f"{analysis.get('n_probes_tested', 0):,}"),
        "cards": cards,
        "cohort": {
            "subtypes": {k: v for k, v in (cohort.get("subtypes") or {}).items()
                         if k not in ("nan", "NA")},
            "tumor": cohort.get("n_tumor"), "normal": cohort.get("n_normal"),
            "age": cohort.get("ages", {}),
        },
        "direction": {
            "silencing": mech.get("silencing"), "activation": mech.get("activation"),
            "ambiguous": mech.get("ambiguous"),
        },
        "movers": movers,
        "folds": [round(float(f), 4) for f in folds],
        "model": {
            "model": clf.get("model"), "cv_folds": clf.get("cv_folds"),
            "roc_auc_mean": clf.get("roc_auc_mean"), "roc_auc_std": clf.get("roc_auc_std"),
            "nested": bool(nested.get("nested_internal_cv")),
        },
        "thresholds_used": {"fdr": 0.05, "delta_beta": 0.20},
        "table": {"rows": table_rows, "columns": table_cols},
        "panel": {"rows": panel_rows, "columns": panel_cols},
        "report_url": "/site/Results_Presentation.html",
        "report_alt": [
            {"label": "Single-page report", "url": "/site/Results_Presentation.html"},
            {"label": "Multi-page site", "url": "/site/website_v2/index.html"},
        ],
        "caveat": "This is the completed study this project published, shown so the screen is "
                  "not empty. It is not the output of a run you started here.",
    }


# ---------------------------------------------------------------------------
# The same dashboard shape, built from a run's own results.
# One renderer, two sources - so the layout cannot drift between them.
# ---------------------------------------------------------------------------

_CARD_ORDER = [
    ("Samples loaded", "Samples analysed", None, ""),
    ("Probes tested", "DNA sites tested", None, ""),
    ("Significant probes", "Sites that changed", "red", "confident and past the effect threshold"),
    ("ROC-AUC", "Told the groups apart", "green", "cross-validated"),
]


def from_run(res, snap=None):
    stats = {s["label"]: s["value"] for s in (res.get("stats") or [])}
    cards = []
    for key, label, tone, note in _CARD_ORDER:
        if key in stats:
            cards.append({"label": label, "value": stats[key], "tone": tone, "note": note,
                          "kind": "auc" if key == "ROC-AUC" else None})
    # Anything else the run reported, kept but not promoted.
    extra = [{"label": k, "value": v} for k, v in stats.items()
             if k not in {c[0] for c in _CARD_ORDER}]

    movers = []
    for row in (res.get("top_markers") or [])[:40]:
        gene = row.get("gene")
        if not gene or gene != gene:            # skip NaN
            continue
        if any(m["gene"] == gene for m in movers):
            continue
        movers.append({"gene": str(gene), "probe": str(row.get("probe_id", "")),
                       "delta": round(float(row.get("delta_beta") or 0), 4),
                       "direction": str(row.get("direction", ""))})
        if len(movers) >= 16:
            break

    model = res.get("model") or {}
    return {
        "is_reference": False,
        "title": (snap or {}).get("label") or "This run",
        "subtitle": "%s · %s" % ((snap or {}).get("tier_label", "run"),
                                 (res.get("data_provenance") or "")[:90]),
        "cards": cards,
        "extra_stats": extra,
        "cohort": {},
        "direction": res.get("mechanics_counts") or {},
        "movers": movers,
        "folds": model.get("roc_auc_per_fold") or [],
        "model": model,
        "volcano": res.get("volcano"),
        "roc": res.get("roc"),
        "enrichment": res.get("enrichment_top") or [],
        "enrichment_null": res.get("enrichment_null", False),
        "table": {"rows": res.get("top_markers") or [],
                  "columns": res.get("top_marker_columns") or []},
        "panel": {"rows": res.get("panel") or [],
                  "columns": res.get("panel_columns") or []},
        "caveat": "",
    }
