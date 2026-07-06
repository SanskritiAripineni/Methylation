#!/usr/bin/env python3
"""Backfill Phase 1 QC, heatmap, classifier, and close-out memo."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = PROJECT_ROOT / "data" / "raw" / "TCGA-BRCA.methylation450.tsv.gz"
ANNOTATION_PATH = PROJECT_ROOT / "data" / "raw" / "HM450.hg38.manifest.gencode.v36.probeMap"
OUT_DIR = PROJECT_ROOT / "outputs" / "brca_methylation" / "tumor_vs_normal"

MAX_SAMPLE_MISSINGNESS = 0.25
MAX_PROBE_MISSINGNESS = 0.10
DROP_SEX_CHROMOSOMES = True
HEATMAP_TOP_N = 50
CLASSIFIER_TOP_N = 25


def load_manifest() -> pd.DataFrame:
    manifest = pd.read_csv(OUT_DIR / "cohort_manifest.tsv", sep="\t", low_memory=False)
    return manifest


def load_probe_map() -> pd.DataFrame:
    probe_map = pd.read_csv(ANNOTATION_PATH, sep="\t", low_memory=False).rename(columns={"#id": "probe_id"})
    keep = [col for col in ["probe_id", "gene", "chrom", "chromStart", "chromEnd", "strand"] if col in probe_map.columns]
    probe_map = probe_map[keep].drop_duplicates(subset=["probe_id"])
    if DROP_SEX_CHROMOSOMES and "chrom" in probe_map.columns:
        probe_map = probe_map[~probe_map["chrom"].isin(["chrX", "chrY"])].copy()
    return probe_map


def compute_missingness(manifest: pd.DataFrame, probe_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    sample_columns = manifest["sample_barcode"].tolist()
    allowed_probe_ids = set(probe_map["probe_id"])
    sample_missing = pd.Series(0, index=sample_columns, dtype=np.int64)
    total_seen = 0
    duplicate_probe_rows = 0
    seen_probe_ids: set[str] = set()
    probe_missing_records: list[pd.DataFrame] = []

    for chunk in pd.read_csv(
        MATRIX_PATH,
        sep="\t",
        compression="gzip",
        usecols=["Composite Element REF", *sample_columns],
        chunksize=5000,
        low_memory=False,
    ):
        chunk = chunk.rename(columns={"Composite Element REF": "probe_id"})
        chunk = chunk[chunk["probe_id"].isin(allowed_probe_ids)].copy()
        if chunk.empty:
            continue
        probe_ids = chunk["probe_id"].astype(str)
        duplicate_probe_rows += int(probe_ids.duplicated().sum())
        duplicate_probe_rows += int(probe_ids.isin(seen_probe_ids).sum())
        seen_probe_ids.update(probe_ids.tolist())
        beta = chunk[sample_columns].apply(pd.to_numeric, errors="coerce")
        sample_missing += beta.isna().sum(axis=0)
        probe_missing_records.append(
            pd.DataFrame(
                {
                    "probe_id": chunk["probe_id"].values,
                    "probe_missing_fraction": beta.isna().mean(axis=1).to_numpy(dtype=float),
                }
            )
        )
        total_seen += len(chunk)

    probe_missing = pd.concat(probe_missing_records, ignore_index=True)
    probe_missing = probe_missing.groupby("probe_id", as_index=False)["probe_missing_fraction"].mean()
    probe_missing = probe_missing.merge(probe_map, on="probe_id", how="left")
    sample_missing_df = (
        (sample_missing / max(total_seen, 1))
        .rename_axis("sample_barcode")
        .reset_index(name="missing_fraction")
    )
    sample_missing_df["retained"] = sample_missing_df["missing_fraction"] <= MAX_SAMPLE_MISSINGNESS
    probe_missing["retained"] = probe_missing["probe_missing_fraction"] <= MAX_PROBE_MISSINGNESS

    qc = {
        "input_sample_count": int(len(sample_columns)),
        "filtered_sample_count": int(sample_missing_df["retained"].sum()),
        "input_probe_count_after_annotation_filter": int(total_seen),
        "filtered_probe_count": int(probe_missing["retained"].sum()),
        "sample_duplicates_in_header": int(pd.Index(sample_columns).duplicated().sum()),
        "duplicate_probe_rows_detected": int(duplicate_probe_rows),
        "max_sample_missingness_threshold": MAX_SAMPLE_MISSINGNESS,
        "max_probe_missingness_threshold": MAX_PROBE_MISSINGNESS,
        "drop_sex_chromosomes": DROP_SEX_CHROMOSOMES,
        "n_samples_removed_for_missingness": int((~sample_missing_df["retained"]).sum()),
        "n_probes_removed_for_missingness_or_filtering": int((~probe_missing["retained"]).sum()),
        "median_sample_missing_fraction": float(sample_missing_df["missing_fraction"].median()),
        "max_sample_missing_fraction": float(sample_missing_df["missing_fraction"].max()),
        "median_probe_missing_fraction": float(probe_missing["probe_missing_fraction"].median()),
        "n_tumor_after_filtering": int((manifest["sample_class"] == "tumor").sum()),
        "n_normal_after_filtering": int((manifest["sample_class"] == "normal").sum()),
    }
    return sample_missing_df, probe_missing, qc


def load_marker_matrix(manifest: pd.DataFrame, top_probes: list[str]) -> pd.DataFrame:
    sample_columns = manifest["sample_barcode"].tolist()
    chunks = []
    found = 0
    for chunk in pd.read_csv(
        MATRIX_PATH,
        sep="\t",
        compression="gzip",
        usecols=["Composite Element REF", *sample_columns],
        chunksize=5000,
        low_memory=False,
    ):
        chunk = chunk.rename(columns={"Composite Element REF": "probe_id"})
        selected = chunk[chunk["probe_id"].isin(top_probes)].copy()
        if not selected.empty:
            chunks.append(selected)
            found += len(selected)
        if found >= len(top_probes):
            break
    marker_df = pd.concat(chunks, ignore_index=True).drop_duplicates(subset=["probe_id"])
    marker_df = marker_df.set_index("probe_id").reindex(top_probes)
    return marker_df


def build_heatmap(manifest: pd.DataFrame, candidate_panel: pd.DataFrame) -> None:
    top_probes = candidate_panel["probe_id"].head(HEATMAP_TOP_N).tolist()
    marker_df = load_marker_matrix(manifest, top_probes)
    sample_columns = manifest["sample_barcode"].tolist()
    beta = marker_df[sample_columns].apply(pd.to_numeric, errors="coerce")
    beta = beta.T.fillna(beta.mean(axis=1)).T.fillna(beta.mean(axis=0)).fillna(0.0)
    ordered_manifest = manifest.sort_values(["sample_class", "sample_barcode"]).reset_index(drop=True)
    ordered_samples = ordered_manifest["sample_barcode"].tolist()
    matrix = beta[ordered_samples].to_numpy(dtype=float)
    row_means = matrix.mean(axis=1, keepdims=True)
    row_stds = matrix.std(axis=1, keepdims=True)
    row_stds[row_stds == 0] = 1.0
    z = (matrix - row_means) / row_stds

    cmap = LinearSegmentedColormap.from_list("methylation_heatmap", ["#2166ac", "#f7f7f7", "#b2182b"])
    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(z, aspect="auto", interpolation="nearest", cmap=cmap, vmin=-2.5, vmax=2.5)
    ax.set_xticks([])
    ax.set_yticks(range(len(top_probes)))
    labels = []
    for probe_id in top_probes:
        row = candidate_panel[candidate_panel["probe_id"] == probe_id]
        gene = row["gene"].iloc[0] if not row.empty and pd.notna(row["gene"].iloc[0]) and str(row["gene"].iloc[0]).strip() else probe_id
        labels.append(str(gene))
    ax.set_yticklabels(labels, fontsize=7)
    normal_count = int((ordered_manifest["sample_class"] == "normal").sum())
    ax.axvline(normal_count - 0.5, color="black", linewidth=1)
    ax.text(max(normal_count / 2, 1), -1.5, "normal", ha="center", va="bottom", fontsize=9)
    ax.text(normal_count + max((len(ordered_samples) - normal_count) / 2, 1), -1.5, "tumor", ha="center", va="bottom", fontsize=9)
    ax.set_title(f"Top {len(top_probes)} Candidate Markers")
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02, label="row z-score")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "heatmap_top_markers.png", dpi=200)
    plt.close()


def run_classifier(manifest: pd.DataFrame, candidate_panel: pd.DataFrame) -> None:
    top_probes = candidate_panel["probe_id"].head(CLASSIFIER_TOP_N).tolist()
    feature_df = load_marker_matrix(manifest, top_probes)
    sample_columns = manifest["sample_barcode"].tolist()
    X = feature_df[sample_columns].T.apply(pd.to_numeric, errors="coerce")
    X = X.fillna(X.mean(axis=0)).fillna(X.mean(axis=1), axis=0).fillna(0.0)
    y = (manifest.set_index("sample_barcode").loc[X.index, "sample_class"] == "tumor").astype(int).to_numpy()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    aucs = []
    for train_idx, test_idx in cv.split(X, y):
        clf = LogisticRegression(max_iter=2000, solver="liblinear")
        clf.fit(X.iloc[train_idx], y[train_idx])
        probs = clf.predict_proba(X.iloc[test_idx])[:, 1]
        aucs.append(roc_auc_score(y[test_idx], probs))
    summary = {
        "model": "logistic_regression",
        "n_features": int(len(top_probes)),
        "cv_folds": 5,
        "roc_auc_mean": float(np.mean(aucs)),
        "roc_auc_std": float(np.std(aucs)),
        "roc_auc_per_fold": [float(x) for x in aucs],
    }
    (OUT_DIR / "classifier_summary.json").write_text(json.dumps(summary, indent=2))


def write_validation_memo(qc: dict, classifier: dict) -> None:
    lines = [
        "# Phase 1 Close-Out",
        "",
        "Phase 1 is complete for the baseline `TCGA-BRCA tumor vs normal` methylation workflow.",
        "",
        "## Deliverables",
        "",
        "- ingestion and metadata harmonization",
        "- cohort manifest",
        "- QC summary and missingness tables",
        "- differential methylation table",
        "- ranked hyper/hypomethylated marker tables",
        "- candidate biomarker panel",
        "- PCA plot",
        "- volcano plot",
        "- heatmap of top candidate markers",
        "- simple classifier benchmark",
        "- short report summary",
        "",
        "## QC Snapshot",
        "",
        f"- retained samples: `{qc['filtered_sample_count']}`",
        f"- retained probes: `{qc['filtered_probe_count']}`",
        f"- sample duplicates in header: `{qc['sample_duplicates_in_header']}`",
        f"- duplicate probe rows detected: `{qc['duplicate_probe_rows_detected']}`",
        f"- sex chromosomes dropped: `{qc['drop_sex_chromosomes']}`",
        f"- median sample missingness: `{qc['median_sample_missing_fraction']:.4f}`",
        f"- median probe missingness: `{qc['median_probe_missing_fraction']:.4f}`",
        "",
        "## Classifier Snapshot",
        "",
        f"- model: `{classifier['model']}`",
        f"- features: `{classifier['n_features']}`",
        f"- 5-fold ROC AUC mean: `{classifier['roc_auc_mean']:.3f}`",
        f"- 5-fold ROC AUC std: `{classifier['roc_auc_std']:.3f}`",
        "",
        "## Next Phase",
        "",
        "Phase 2 should focus on subtype comparisons:",
        "",
        "1. `Basal/TNBC vs normal`",
        "2. `LumA vs normal`",
        "3. `TNBC vs non-TNBC`",
        "4. shared versus subtype-skewed CpG markers",
        "",
    ]
    (PROJECT_ROOT / "outputs" / "brca_methylation" / "project_b_validation_complete.md").write_text("\n".join(lines))


def main() -> None:
    manifest = load_manifest()
    probe_map = load_probe_map()
    candidate_panel = pd.read_csv(OUT_DIR / "candidate_biomarker_panel.tsv", sep="\t", low_memory=False)

    sample_missing, probe_missing, qc = compute_missingness(manifest, probe_map)
    sample_missing.to_csv(OUT_DIR / "sample_missingness.tsv", sep="\t", index=False)
    probe_missing.to_csv(OUT_DIR / "probe_missingness.tsv", sep="\t", index=False)
    (OUT_DIR / "qc_summary.json").write_text(json.dumps(qc, indent=2))
    qc_md = [
        "# QC Summary",
        "",
        f"- input samples: `{qc['input_sample_count']}`",
        f"- retained samples: `{qc['filtered_sample_count']}`",
        f"- retained probes: `{qc['filtered_probe_count']}`",
        f"- sample duplicates in header: `{qc['sample_duplicates_in_header']}`",
        f"- duplicate probe rows detected: `{qc['duplicate_probe_rows_detected']}`",
        f"- sex chromosomes dropped: `{qc['drop_sex_chromosomes']}`",
        f"- median sample missingness: `{qc['median_sample_missing_fraction']:.4f}`",
        f"- max sample missingness: `{qc['max_sample_missing_fraction']:.4f}`",
        f"- median probe missingness: `{qc['median_probe_missing_fraction']:.4f}`",
    ]
    (OUT_DIR / "qc_summary.md").write_text("\n".join(qc_md) + "\n")

    build_heatmap(manifest, candidate_panel)
    run_classifier(manifest, candidate_panel)
    classifier = json.loads((OUT_DIR / "classifier_summary.json").read_text())
    write_validation_memo(qc, classifier)


if __name__ == "__main__":
    main()
