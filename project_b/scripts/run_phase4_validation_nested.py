#!/usr/bin/env python3
"""Leakage-aware Phase 4 internal validation for TCGA-BRCA methylation."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "outputs" / "brca_methylation"
PHASE3 = OUT / "phase3_panel"
PHASE4 = OUT / "phase4_validation"
NESTED_OUT = OUT / "phase4_validation_nested"
TCGA_MATRIX = PROJECT_ROOT / "data" / "raw" / "TCGA-BRCA.methylation450.tsv.gz"


def load_original_summary() -> dict:
    return json.loads((PHASE4 / "validation_summary.json").read_text())


def load_probe_table() -> pd.DataFrame:
    probes = pd.read_csv(OUT / "tumor_vs_normal" / "probe_missingness.tsv", sep="\t", low_memory=False)
    probes = probes[probes["retained"].astype(bool)].copy()
    probes["probe_id"] = probes["probe_id"].astype(str)
    probes["gene"] = probes["gene"].fillna("").astype(str)
    return probes[["probe_id", "gene"]].drop_duplicates(subset=["probe_id"])


def load_tcga_matrix(manifest_path: Path, probes: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = pd.read_csv(manifest_path, sep="\t", low_memory=False)
    sample_columns = manifest["sample_barcode"].tolist()
    chunks = []
    found = 0
    for chunk in pd.read_csv(
        TCGA_MATRIX,
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
    matrix = pd.concat(chunks, ignore_index=True).drop_duplicates(subset=["probe_id"]).set_index("probe_id").reindex(probes)
    X = matrix[sample_columns].T.apply(pd.to_numeric, errors="coerce")
    X = X.fillna(X.mean(axis=0)).fillna(X.mean(axis=1), axis=0).fillna(0.0)
    return manifest, X


def select_train_only_features_for_all_folds(
    manifest: pd.DataFrame,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    probe_table: pd.DataFrame,
    n_features: int,
) -> dict[int, list[str]]:
    sample_columns = manifest["sample_barcode"].tolist()
    probe_ids = set(probe_table["probe_id"])
    gene_map = probe_table.set_index("probe_id")["gene"].to_dict()
    fold_candidates: dict[int, list[pd.DataFrame]] = {fold: [] for fold in range(1, len(folds) + 1)}

    chunk_count = 0
    for chunk in pd.read_csv(
        TCGA_MATRIX,
        sep="\t",
        compression="gzip",
        usecols=["Composite Element REF", *sample_columns],
        chunksize=5000,
        low_memory=False,
    ):
        chunk = chunk.rename(columns={"Composite Element REF": "probe_id"})
        chunk = chunk[chunk["probe_id"].astype(str).isin(probe_ids)].copy()
        if chunk.empty:
            continue
        chunk_count += 1
        if chunk_count % 10 == 0:
            print(f"processed {chunk_count} matrix chunks", flush=True)
        beta = chunk[sample_columns].apply(pd.to_numeric, errors="coerce")
        for fold, (train_idx, _) in enumerate(folds, start=1):
            tumor_cols = [sample_columns[i] for i in train_idx if y[i] == 1]
            normal_cols = [sample_columns[i] for i in train_idx if y[i] == 0]
            tumor_values = beta[tumor_cols].to_numpy(dtype=float)
            normal_values = beta[normal_cols].to_numpy(dtype=float)
            delta = np.nanmean(tumor_values, axis=1) - np.nanmean(normal_values, axis=1)
            scores = pd.DataFrame(
                {
                    "probe_id": chunk["probe_id"].astype(str).to_numpy(),
                    "abs_delta_beta": np.abs(delta),
                }
            )
            fold_candidates[fold].append(
                scores.nlargest(n_features * 20, "abs_delta_beta")
            )

    selected_by_fold = {}
    for fold, frames in fold_candidates.items():
        ranked = pd.concat(frames, ignore_index=True)
        ranked["gene"] = ranked["probe_id"].map(gene_map).fillna("")
        gene_token = ranked["gene"].str.replace(";", ",", regex=False).str.split(",").str[0].str.strip()
        ranked["gene_key"] = np.where(gene_token == "", ranked["probe_id"], gene_token)
        ranked = ranked.sort_values("abs_delta_beta", ascending=False)
        ranked = ranked.drop_duplicates(subset=["gene_key"])
        selected_by_fold[fold] = ranked["probe_id"].head(n_features).tolist()
    return selected_by_fold


def nested_crossval_scores(
    manifest: pd.DataFrame,
    y: np.ndarray,
    probe_table: pd.DataFrame,
    n_features: int,
) -> tuple[dict, pd.DataFrame]:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    folds = list(cv.split(np.zeros(len(y)), y))
    selected_by_fold = select_train_only_features_for_all_folds(manifest, y, folds, probe_table, n_features)
    selected_union = sorted({probe for probes in selected_by_fold.values() for probe in probes})
    _, X = load_tcga_matrix(OUT / "tumor_vs_normal" / "cohort_manifest.tsv", selected_union)
    aucs = []
    fold_rows = []
    for fold, (train_idx, test_idx) in enumerate(folds, start=1):
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_train = y[train_idx]
        y_test = y[test_idx]
        selected = selected_by_fold[fold]
        clf = LogisticRegression(max_iter=2000, solver="liblinear")
        clf.fit(X_train[selected], y_train)
        probs = clf.predict_proba(X_test[selected])[:, 1]
        auc = float(roc_auc_score(y_test, probs))
        aucs.append(auc)
        fold_rows.append(
            {
                "fold": fold,
                "n_train": int(len(train_idx)),
                "n_test": int(len(test_idx)),
                "roc_auc": auc,
                "selected_probes": ",".join(selected),
            }
        )
    summary = {
        "model": "logistic_regression",
        "cv_folds": 5,
        "feature_selection": "Within each fold, retained probes are re-ranked by absolute delta-beta using training samples only.",
        "candidate_feature_space": "Retained tumor_vs_normal probe universe from unsupervised QC; full-cohort differential rankings are not reused.",
        "n_features_per_fold": int(n_features),
        "roc_auc_mean": float(np.mean(aucs)),
        "roc_auc_std": float(np.std(aucs)),
        "roc_auc_per_fold": [float(x) for x in aucs],
    }
    return summary, pd.DataFrame(fold_rows)


def main() -> None:
    NESTED_OUT.mkdir(parents=True, exist_ok=True)
    probe_table = load_probe_table()
    manifest = pd.read_csv(OUT / "tumor_vs_normal" / "cohort_manifest.tsv", sep="\t", low_memory=False)
    y = (manifest["sample_class"] == "tumor").astype(int).to_numpy()
    original_panel = pd.read_csv(PHASE3 / "refined_biomarker_panel.tsv", sep="\t", low_memory=False)
    nested, folds = nested_crossval_scores(manifest, y, probe_table, n_features=len(original_panel))
    original = load_original_summary()["internal_tcga_cross_validation"]
    comparison = {
        "original_phase4_internal_cv": original,
        "nested_internal_cv": nested,
    }
    (NESTED_OUT / "nested_validation_summary.json").write_text(json.dumps(comparison, indent=2))
    folds.to_csv(NESTED_OUT / "nested_cv_folds.tsv", sep="\t", index=False)
    lines = [
        "# Phase 4 Nested Validation",
        "",
        "| evaluation | ROC AUC mean | ROC AUC std |",
        "|---|---:|---:|",
        f"| original Phase 4 internal CV | {original['roc_auc_mean']:.3f} | {original['roc_auc_std']:.3f} |",
        f"| nested train-only feature selection CV | {nested['roc_auc_mean']:.3f} | {nested['roc_auc_std']:.3f} |",
        "",
        "The nested run re-ranks probes inside each training fold before fitting the fold model.",
        "It uses retained QC-passing probes as the candidate feature space and does not overwrite the original Phase 4 outputs.",
    ]
    (NESTED_OUT / "nested_validation_summary.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
