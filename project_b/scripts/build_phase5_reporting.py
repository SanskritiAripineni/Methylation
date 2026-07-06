#!/usr/bin/env python3
"""Build the Phase 5 clinician-style reporting package."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "outputs" / "brca_methylation"
PHASE3 = OUT / "phase3_panel"
PHASE4 = OUT / "phase4_validation"
PHASE5 = OUT / "phase5_reporting"


def load_inputs():
    panel = pd.read_csv(PHASE3 / "refined_biomarker_panel.tsv", sep="\t", low_memory=False)
    validation = json.loads((PHASE4 / "validation_summary.json").read_text())
    tcga = pd.read_csv(PHASE4 / "tcga_panel_scores.tsv", sep="\t", low_memory=False)
    external = pd.read_csv(PHASE4 / "gse66695_panel_scores.tsv", sep="\t", low_memory=False)
    return panel, validation, tcga, external


def compute_thresholds(tcga: pd.DataFrame, external: pd.DataFrame) -> dict:
    tcga_norm = tcga.loc[tcga["sample_class"] == "normal", "panel_score"]
    tcga_tumor = tcga.loc[tcga["sample_class"] == "tumor", "panel_score"]
    ext_norm = external.loc[external["sample_class"] == "normal", "panel_score"]
    ext_tumor = external.loc[external["sample_class"] == "tumor", "panel_score"]

    normal_p95 = float(np.quantile(tcga_norm, 0.95))
    tumor_p05 = float(np.quantile(tcga_tumor, 0.05))
    conservative_negative = float(np.quantile(pd.concat([tcga_norm, ext_norm]), 0.95))
    conservative_positive = float(np.quantile(pd.concat([tcga_tumor, ext_tumor]), 0.05))

    thresholds = {
        "tcga_normal_p95": normal_p95,
        "tcga_tumor_p05": tumor_p05,
        "conservative_negative_upper": conservative_negative,
        "conservative_positive_lower": conservative_positive,
        "interpretation_rules": {
            "low": f"score <= {conservative_negative:.3f}",
            "indeterminate": f"{conservative_negative:.3f} < score < {conservative_positive:.3f}",
            "high": f"score >= {conservative_positive:.3f}",
        },
    }
    return thresholds


def classify_score(score: float, thresholds: dict) -> tuple[str, str]:
    low_cut = thresholds["conservative_negative_upper"]
    high_cut = thresholds["conservative_positive_lower"]
    if score <= low_cut:
        return "Low", "Score is within the range mostly observed in normal/reference samples."
    if score >= high_cut:
        return "High", "Score is within the range mostly observed in tumor-associated samples."
    return "Indeterminate", "Score lies between the normal-associated and tumor-associated reference bands."


def choose_examples(tcga: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    normal = tcga[tcga["sample_class"] == "normal"].copy()
    tumor = tcga[tcga["sample_class"] == "tumor"].copy()
    normal = normal.iloc[(normal["panel_score"] - normal["panel_score"].median()).abs().argsort()].iloc[0]
    tumor = tumor.iloc[(tumor["panel_score"] - tumor["panel_score"].median()).abs().argsort()].iloc[0]
    return normal, tumor


def write_example_report(row: pd.Series, thresholds: dict, validation: dict, target: Path) -> None:
    score = float(row["panel_score"])
    band, interp = classify_score(score, thresholds)
    sample_id = row.get("index", row.get("geo_accession", "sample"))
    subtype = row.get("subtype", "NA")
    stage = row.get("ajcc_pathologic_stage.diagnoses", "NA")
    lines = [
        "# Research Methylation Report",
        "",
        "## Summary",
        "",
        f"- Sample ID: `{sample_id}`",
        f"- Panel score: `{score:.3f}`",
        f"- Interpretation band: `{band}`",
        f"- Interpretation note: {interp}",
        "",
        "## Context",
        "",
        f"- Sample class in reference dataset: `{row['sample_class']}`",
        f"- Subtype label if available: `{subtype}`",
        f"- Stage if available: `{stage}`",
        "",
        "## Validation Anchor",
        "",
        f"- Internal TCGA ROC AUC mean: `{validation['internal_tcga_cross_validation']['roc_auc_mean']:.3f}`",
        f"- External GEO ROC AUC: `{validation['external_validation']['roc_auc']:.3f}`",
        "",
        "## Important Limitation",
        "",
        "This is a research-use-only interpretation layer and is not a diagnostic clinical assay.",
    ]
    target.write_text("\n".join(lines) + "\n")


def main() -> None:
    PHASE5.mkdir(parents=True, exist_ok=True)
    panel, validation, tcga, external = load_inputs()
    thresholds = compute_thresholds(tcga, external)
    (PHASE5 / "reporting_thresholds.json").write_text(json.dumps(thresholds, indent=2))

    general = panel[panel["panel_role"] == "general_tumor_marker"].copy()
    basal = panel[panel["panel_role"] == "basal_skewed_marker"].copy()

    clinician_lines = [
        "# Clinician-Facing Research Summary",
        "",
        "## Intended Use",
        "",
        "This package is a research-use methylation screening summary for breast tumor-associated signal. It is not a validated diagnostic medical device and should not be used as a standalone basis for patient care decisions.",
        "",
        "## Panel Composition",
        "",
        f"- `{len(panel)}` total CpGs",
        f"- `{len(general)}` general tumor-associated markers",
        f"- `{len(basal)}` Basal-skewed markers",
        "",
        "## Validation Snapshot",
        "",
        f"- Internal TCGA ROC AUC mean: `{validation['internal_tcga_cross_validation']['roc_auc_mean']:.3f}`",
        f"- External GEO GSE66695 ROC AUC: `{validation['external_validation']['roc_auc']:.3f}`",
        f"- Tumor age association rho: `{validation['age_association']['tumor']['spearman_rho']:.3f}`",
        "",
        "## Interpretation Bands",
        "",
        f"- Low: `{thresholds['interpretation_rules']['low']}`",
        f"- Indeterminate: `{thresholds['interpretation_rules']['indeterminate']}`",
        f"- High: `{thresholds['interpretation_rules']['high']}`",
        "",
        "## Caveats",
        "",
        "- performance is derived from retrospective public cohorts",
        "- tumor purity and cohort composition may affect score distributions",
        "- age remains a modest confounder in tumor samples",
        "- subtype inference is currently stronger for Basal-skewed biology than for full clinical receptor-status definitions",
        "",
        "## Recommended Clinical Framing",
        "",
        "- describe this as a research methylation signal score",
        "- report confidence cautiously and avoid diagnostic wording",
        "- pair the score with histopathology, imaging, and standard clinical biomarkers",
    ]
    (PHASE5 / "clinician_summary.md").write_text("\n".join(clinician_lines) + "\n")

    schema = {
        "report_name": "research_methylation_signal_report",
        "fields": [
            "sample_id",
            "report_version",
            "panel_score",
            "interpretation_band",
            "interpretation_note",
            "comparison_context",
            "subtype_context_if_available",
            "validation_anchor",
            "limitations",
            "recommended_clinical_use_statement",
        ],
    }
    (PHASE5 / "report_schema.json").write_text(json.dumps(schema, indent=2))

    template_lines = [
        "# Research Methylation Signal Report",
        "",
        "## Sample",
        "",
        "- Sample ID: `<sample_id>`",
        "- Report version: `v1`",
        "",
        "## Result",
        "",
        "- Panel score: `<panel_score>`",
        "- Interpretation band: `<Low | Indeterminate | High>`",
        "- Interpretation note: `<brief note>`",
        "",
        "## Comparison Context",
        "",
        "- Primary validated comparison: `normal breast tissue vs BRCA tumor`",
        "- Subtype context if applicable: `<Basal-skewed / not available>`",
        "",
        "## Validation Anchor",
        "",
        f"- Internal TCGA ROC AUC mean: `{validation['internal_tcga_cross_validation']['roc_auc_mean']:.3f}`",
        f"- External GEO ROC AUC: `{validation['external_validation']['roc_auc']:.3f}`",
        "",
        "## Limitations",
        "",
        "- research-use only",
        "- not a standalone diagnostic assay",
        "- age and cohort composition can influence score distributions",
        "",
        "## Recommended Clinical Use Statement",
        "",
        "Use only as a research adjunct to pathology and standard clinical assessment.",
    ]
    (PHASE5 / "report_template.md").write_text("\n".join(template_lines) + "\n")

    normal_ex, tumor_ex = choose_examples(tcga)
    write_example_report(normal_ex, thresholds, validation, PHASE5 / "example_report_normal.md")
    write_example_report(tumor_ex, thresholds, validation, PHASE5 / "example_report_tumor.md")


if __name__ == "__main__":
    main()
