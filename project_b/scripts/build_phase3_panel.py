#!/usr/bin/env python3
"""Build a reduced Phase 3 biomarker panel from Phase 1 and Phase 2 outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "outputs" / "brca_methylation"
PHASE3 = OUT / "phase3_panel"
MATRIX = PROJECT_ROOT / "data" / "raw" / "TCGA-BRCA.methylation450.tsv.gz"


def gene_key(value: object, probe_id: str) -> str:
    if pd.isna(value) or not str(value).strip():
        return probe_id
    token = str(value).replace(";", ",").split(",")[0].strip()
    return token or probe_id


def dedupe_panel(df: pd.DataFrame, score_cols: list[str], n: int) -> pd.DataFrame:
    ranked = df.sort_values(score_cols, ascending=[False] * len(score_cols)).copy()
    ranked["gene_key"] = [gene_key(g, p) for g, p in zip(ranked["gene"], ranked["probe_id"])]
    ranked = ranked.drop_duplicates(subset=["gene_key"])
    return ranked.head(n).copy()


def load_candidates() -> tuple[pd.DataFrame, pd.DataFrame]:
    tumor = pd.read_csv(OUT / "tumor_vs_normal" / "candidate_biomarker_panel.tsv", sep="\t", low_memory=False)
    basal = pd.read_csv(OUT / "basal_vs_non_basal" / "candidate_biomarker_panel.tsv", sep="\t", low_memory=False)
    return tumor, basal


def build_panel() -> pd.DataFrame:
    tumor, basal = load_candidates()
    overlap = set(tumor["probe_id"]) & set(basal["probe_id"])

    tumor = tumor.copy()
    basal = basal.copy()
    tumor["gene_key"] = [gene_key(g, p) for g, p in zip(tumor["gene"], tumor["probe_id"])]
    basal["gene_key"] = [gene_key(g, p) for g, p in zip(basal["gene"], basal["probe_id"])]

    basal_gene_keys = set(basal["gene_key"])
    tumor_general = tumor[~tumor["probe_id"].isin(overlap)].copy()
    tumor_general = tumor_general[~tumor_general["gene_key"].isin(basal_gene_keys)].copy()
    tumor_general["priority_score"] = tumor_general["abs_delta_beta"] * (-np.log10(tumor_general["fdr"].clip(lower=1e-300)))
    basal_specific = basal[~basal["probe_id"].isin(overlap)].copy()
    basal_specific["priority_score"] = basal_specific["abs_delta_beta"] * (-np.log10(basal_specific["fdr"].clip(lower=1e-300)))

    general_panel = dedupe_panel(tumor_general, ["priority_score", "abs_delta_beta"], 12)
    basal_panel = dedupe_panel(basal_specific, ["priority_score", "abs_delta_beta"], 8)

    general_panel = general_panel.assign(
        panel_role="general_tumor_marker",
        source_run="tumor_vs_normal",
    )
    basal_panel = basal_panel.assign(
        panel_role="basal_skewed_marker",
        source_run="basal_vs_non_basal",
    )

    panel = pd.concat([general_panel, basal_panel], ignore_index=True)
    panel["panel_rank"] = np.arange(1, len(panel) + 1)
    cols = [
        "panel_rank",
        "panel_role",
        "source_run",
        "probe_id",
        "gene",
        "chrom",
        "delta_beta",
        "abs_delta_beta",
        "fdr",
        "direction",
        "tumor_n",
        "normal_n",
    ]
    return panel[cols].copy()


def load_feature_matrix(manifest_path: Path, probes: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    manifest = pd.read_csv(manifest_path, sep="\t", low_memory=False)
    sample_columns = manifest["sample_barcode"].tolist()
    chunks = []
    found = 0
    for chunk in pd.read_csv(
        MATRIX,
        sep="\t",
        compression="gzip",
        usecols=["Composite Element REF", *sample_columns],
        chunksize=5000,
        low_memory=False,
    ):
        chunk = chunk.rename(columns={"Composite Element REF": "probe_id"})
        selected = chunk[chunk["probe_id"].isin(probes)].copy()
        if not selected.empty:
            chunks.append(selected)
            found += len(selected)
        if found >= len(probes):
            break
    df = pd.concat(chunks, ignore_index=True).drop_duplicates(subset=["probe_id"]).set_index("probe_id").reindex(probes)
    X = df[sample_columns].T.apply(pd.to_numeric, errors="coerce")
    X = X.fillna(X.mean(axis=0)).fillna(X.mean(axis=1), axis=0).fillna(0.0)
    return manifest, X


def evaluate_classifier(manifest_path: Path, probes: list[str]) -> dict:
    manifest, X = load_feature_matrix(manifest_path, probes)
    group_col = "analysis_group" if "analysis_group" in manifest.columns else "sample_class"
    y = (manifest.set_index("sample_barcode").loc[X.index, group_col] == "tumor").astype(int).to_numpy()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    aucs = []
    for train_idx, test_idx in cv.split(X, y):
        clf = LogisticRegression(max_iter=2000, solver="liblinear")
        clf.fit(X.iloc[train_idx], y[train_idx])
        probs = clf.predict_proba(X.iloc[test_idx])[:, 1]
        aucs.append(roc_auc_score(y[test_idx], probs))
    return {
        "n_samples": int(len(X)),
        "n_features": int(len(probes)),
        "roc_auc_mean": float(np.mean(aucs)),
        "roc_auc_std": float(np.std(aucs)),
        "roc_auc_per_fold": [float(x) for x in aucs],
    }


def main() -> None:
    PHASE3.mkdir(parents=True, exist_ok=True)
    panel = build_panel()
    panel.to_csv(PHASE3 / "refined_biomarker_panel.tsv", sep="\t", index=False)

    probes = panel["probe_id"].tolist()
    tumor_eval = evaluate_classifier(OUT / "tumor_vs_normal" / "cohort_manifest.tsv", probes)
    basal_eval = evaluate_classifier(OUT / "basal_vs_non_basal" / "cohort_manifest.tsv", probes)
    summary = {
        "panel_size": int(len(panel)),
        "general_tumor_markers": int((panel["panel_role"] == "general_tumor_marker").sum()),
        "basal_skewed_markers": int((panel["panel_role"] == "basal_skewed_marker").sum()),
        "tumor_vs_normal_classifier": tumor_eval,
        "basal_vs_non_basal_classifier": basal_eval,
    }
    (PHASE3 / "panel_summary.json").write_text(json.dumps(summary, indent=2))

    lines = [
        "# Phase 3 Panel",
        "",
        "This panel reduces the earlier broad CpG hit lists into a smaller mixed panel with:",
        "",
        f"- `{summary['general_tumor_markers']}` general BRCA tumor markers",
        f"- `{summary['basal_skewed_markers']}` Basal-skewed markers",
        f"- `{summary['panel_size']}` total CpGs",
        "",
        "## Classifier Snapshot",
        "",
        f"- tumor vs normal ROC AUC mean: `{tumor_eval['roc_auc_mean']:.3f}`",
        f"- tumor vs normal ROC AUC std: `{tumor_eval['roc_auc_std']:.3f}`",
        f"- Basal vs non-Basal ROC AUC mean: `{basal_eval['roc_auc_mean']:.3f}`",
        f"- Basal vs non-Basal ROC AUC std: `{basal_eval['roc_auc_std']:.3f}`",
        "",
        "## Outputs",
        "",
        "- `refined_biomarker_panel.tsv`",
        "- `panel_summary.json`",
    ]
    (PHASE3 / "panel_summary.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
