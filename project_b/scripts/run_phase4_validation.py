#!/usr/bin/env python3
"""Phase 4 validation for the refined BRCA methylation panel."""

from __future__ import annotations

import gzip
import json
import os
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "outputs" / "brca_methylation"
PHASE3 = OUT / "phase3_panel"
PHASE4 = OUT / "phase4_validation"
TCGA_MATRIX = PROJECT_ROOT / "data" / "raw" / "TCGA-BRCA.methylation450.tsv.gz"
EXTERNAL_DIR = PROJECT_ROOT / "data" / "external"
EXTERNAL_PATH = EXTERNAL_DIR / "GSE66695_series_matrix.txt.gz"
EXTERNAL_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE66nnn/GSE66695/matrix/GSE66695_series_matrix.txt.gz"


def load_panel() -> pd.DataFrame:
    return pd.read_csv(PHASE3 / "refined_biomarker_panel.tsv", sep="\t", low_memory=False)


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


def ensure_external_download() -> None:
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    if EXTERNAL_PATH.exists():
        return
    with urllib.request.urlopen(EXTERNAL_URL) as resp, open(EXTERNAL_PATH, "wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def parse_gse66695(probes: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_external_download()
    wanted = set(probes)
    sample_ids = []
    sample_titles = []
    sample_sources = []
    table_sample_ids = []
    rows = {}
    in_table = False
    with gzip.open(EXTERNAL_PATH, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("!Sample_geo_accession"):
                sample_ids = line.split("\t")[1:]
            elif line.startswith("!Sample_title"):
                sample_titles = line.split("\t")[1:]
            elif line.startswith("!Sample_source_name_ch1"):
                sample_sources = line.split("\t")[1:]
            elif line == "!series_matrix_table_begin":
                in_table = True
                continue
            elif line == "!series_matrix_table_end":
                break
            elif in_table and not table_sample_ids:
                table_sample_ids = [x.strip('"') for x in line.split("\t")[1:]]
            elif in_table and line.startswith('"cg'):
                parts = line.split("\t")
                probe_id = parts[0].strip('"')
                if probe_id in wanted:
                    rows[probe_id] = parts[1:]
    meta = pd.DataFrame(
        {
            "geo_accession": sample_ids,
            "sample_title": sample_titles,
            "sample_source": sample_sources,
        }
    )
    for col in ["geo_accession", "sample_title", "sample_source"]:
        meta[col] = meta[col].astype(str).str.strip().str.strip('"')
    meta["sample_class"] = meta["sample_source"].str.lower().map({"tumor": "tumor", "normal": "normal"})
    matrix = pd.DataFrame(rows).T.reindex(probes)
    matrix.columns = table_sample_ids
    X = matrix.T.apply(pd.to_numeric, errors="coerce")
    X = X.fillna(X.mean(axis=0)).fillna(X.mean(axis=1), axis=0).fillna(0.0)
    X = X.loc[meta["geo_accession"]]
    return meta, X


def fit_tcga_classifier(X: pd.DataFrame, manifest: pd.DataFrame) -> tuple[LogisticRegression, np.ndarray]:
    y = (manifest.set_index("sample_barcode").loc[X.index, "sample_class"] == "tumor").astype(int).to_numpy()
    clf = LogisticRegression(max_iter=2000, solver="liblinear")
    clf.fit(X, y)
    return clf, y


def crossval_scores(X: pd.DataFrame, y: np.ndarray) -> dict:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    aucs = []
    for train_idx, test_idx in cv.split(X, y):
        clf = LogisticRegression(max_iter=2000, solver="liblinear")
        clf.fit(X.iloc[train_idx], y[train_idx])
        probs = clf.predict_proba(X.iloc[test_idx])[:, 1]
        aucs.append(roc_auc_score(y[test_idx], probs))
    return {
        "roc_auc_mean": float(np.mean(aucs)),
        "roc_auc_std": float(np.std(aucs)),
        "roc_auc_per_fold": [float(x) for x in aucs],
    }


def stage_bucket(value: object) -> str:
    text = str(value).upper()
    if "IV" in text:
        return "Stage IV"
    if "III" in text:
        return "Stage III"
    if "II" in text:
        return "Stage II"
    if "I" in text:
        return "Stage I"
    return "Unknown"


def evaluate_stage_specific(scores_df: pd.DataFrame) -> dict:
    normals = scores_df[scores_df["sample_class"] == "normal"].copy()
    tumors = scores_df[scores_df["sample_class"] == "tumor"].copy()
    tumors["stage_bucket"] = tumors["ajcc_pathologic_stage.diagnoses"].apply(stage_bucket)
    out = {}
    for stage, group in tumors.groupby("stage_bucket"):
        if stage == "Unknown" or len(group) < 10:
            continue
        subset = pd.concat([group, normals], ignore_index=True)
        y = (subset["sample_class"] == "tumor").astype(int).to_numpy()
        if len(np.unique(y)) < 2:
            continue
        out[stage] = {
            "n_tumor": int(len(group)),
            "n_normal": int(len(normals)),
            "roc_auc": float(roc_auc_score(y, subset["panel_score"])),
        }
    return out


def main() -> None:
    PHASE4.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    probes = panel["probe_id"].tolist()

    tcga_manifest, tcga_X = load_tcga_matrix(OUT / "tumor_vs_normal" / "cohort_manifest.tsv", probes)
    clf, tcga_y = fit_tcga_classifier(tcga_X, tcga_manifest)
    tcga_probs = clf.predict_proba(tcga_X)[:, 1]
    tcga_scores = tcga_manifest.set_index("sample_barcode").loc[tcga_X.index].reset_index()
    tcga_scores["panel_score"] = tcga_probs
    tcga_scores.to_csv(PHASE4 / "tcga_panel_scores.tsv", sep="\t", index=False)

    internal_cv = crossval_scores(tcga_X, tcga_y)

    external_meta, external_X = parse_gse66695(probes)
    external_meta = external_meta[external_meta["sample_class"].isin(["tumor", "normal"])].copy()
    external_X = external_X.loc[external_meta["geo_accession"]]
    external_probs = clf.predict_proba(external_X)[:, 1]
    external_y = (external_meta["sample_class"] == "tumor").astype(int).to_numpy()
    external_meta["panel_score"] = external_probs
    external_meta.to_csv(PHASE4 / "gse66695_panel_scores.tsv", sep="\t", index=False)
    external_validation = {
        "dataset": "GSE66695",
        "n_samples": int(len(external_meta)),
        "n_tumor": int((external_meta["sample_class"] == "tumor").sum()),
        "n_normal": int((external_meta["sample_class"] == "normal").sum()),
        "roc_auc": float(roc_auc_score(external_y, external_probs)),
    }

    age_assoc = {}
    for group in ["tumor", "normal"]:
        subset = tcga_scores[tcga_scores["sample_class"] == group].copy()
        subset = subset[np.isfinite(subset["age_years"])]
        if len(subset) >= 10:
            rho, p = spearmanr(subset["age_years"], subset["panel_score"])
            age_assoc[group] = {"n": int(len(subset)), "spearman_rho": float(rho), "p_value": float(p)}

    stage_auc = evaluate_stage_specific(tcga_scores)

    summary = {
        "panel_size": int(len(panel)),
        "internal_tcga_cross_validation": internal_cv,
        "external_validation": external_validation,
        "age_association": age_assoc,
        "stage_specific_auc": stage_auc,
    }
    (PHASE4 / "validation_summary.json").write_text(json.dumps(summary, indent=2))

    lines = [
        "# Phase 4 Validation",
        "",
        f"- panel size: `{len(panel)}` CpGs",
        "",
        "## Internal TCGA Validation",
        "",
        f"- 5-fold ROC AUC mean: `{internal_cv['roc_auc_mean']:.3f}`",
        f"- 5-fold ROC AUC std: `{internal_cv['roc_auc_std']:.3f}`",
        "",
        "## External Validation",
        "",
        f"- dataset: `{external_validation['dataset']}`",
        f"- samples: `{external_validation['n_samples']}`",
        f"- tumors: `{external_validation['n_tumor']}`",
        f"- normals: `{external_validation['n_normal']}`",
        f"- external ROC AUC: `{external_validation['roc_auc']:.3f}`",
        "",
        "## Age Association",
        "",
    ]
    for group, vals in age_assoc.items():
        lines.append(f"- {group}: rho=`{vals['spearman_rho']:.3f}`, p=`{vals['p_value']:.3e}`, n=`{vals['n']}`")
    lines += ["", "## Stage-Specific TCGA AUC", ""]
    for stage, vals in stage_auc.items():
        lines.append(f"- {stage}: ROC AUC=`{vals['roc_auc']:.3f}` with `{vals['n_tumor']}` tumors and `{vals['n_normal']}` normals")
    (PHASE4 / "validation_summary.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
