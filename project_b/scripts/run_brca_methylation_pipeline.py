#!/usr/bin/env python3
"""Run a first-pass TCGA-BRCA methylation analysis."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


VALID_SAMPLE_TYPES = {"Primary Tumor", "Solid Tissue Normal"}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="JSON config file")
    parser.add_argument("--methylation-matrix", type=Path, default=None)
    parser.add_argument("--clinical-metadata", type=Path, default=None)
    parser.add_argument("--probe-annotation", type=Path, default=None)
    parser.add_argument("--subtype-metadata", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--max-sample-missingness", type=float, default=0.05)
    parser.add_argument("--max-probe-missingness", type=float, default=0.10)
    parser.add_argument("--drop-sex-chromosomes", action="store_true", default=True)
    parser.add_argument("--keep-sex-chromosomes", action="store_true")
    parser.add_argument("--heatmap-top-n", type=int, default=50)
    parser.add_argument("--classifier-top-n", type=int, default=25)
    parser.add_argument(
        "--comparison",
        choices=["tumor_vs_normal", "subtype_vs_normal", "subtype_vs_subtype"],
        default="tumor_vs_normal",
    )
    parser.add_argument(
        "--subtype-label",
        default=None,
        help="Subtype label to compare against normal when comparison=subtype_vs_normal",
    )
    parser.add_argument(
        "--reference-subtype",
        default=None,
        help="Reference subtype label or 'non_<subtype>' for subtype_vs_subtype",
    )
    parser.add_argument(
        "--max-probes",
        type=int,
        default=None,
        help="Optional limit for smoke tests",
    )
    parser.add_argument(
        "--validate-paths-only",
        action="store_true",
        help="Resolve configured paths and check input readability/output writability without loading data.",
    )
    return parser.parse_args()


def load_config(args: argparse.Namespace) -> dict:
    config = {}
    if args.config:
        config = json.loads(args.config.read_text())
    return {
        "methylation_matrix": str(args.methylation_matrix or config.get("methylation_matrix", "")),
        "clinical_metadata": str(args.clinical_metadata or config.get("clinical_metadata", "")),
        "probe_annotation": str(args.probe_annotation or config.get("probe_annotation", "")),
        "subtype_metadata": str(args.subtype_metadata or config.get("subtype_metadata", "")),
        "output_dir": str(args.output_dir or config.get("output_dir", "")),
        "chunk_size": args.chunk_size,
        "max_sample_missingness": float(config.get("max_sample_missingness", args.max_sample_missingness)),
        "max_probe_missingness": float(config.get("max_probe_missingness", args.max_probe_missingness)),
        "drop_sex_chromosomes": False if args.keep_sex_chromosomes else bool(
            config.get("drop_sex_chromosomes", args.drop_sex_chromosomes)
        ),
        "heatmap_top_n": int(config.get("heatmap_top_n", args.heatmap_top_n)),
        "classifier_top_n": int(config.get("classifier_top_n", args.classifier_top_n)),
        "max_probes": args.max_probes,
        "comparison": args.comparison,
        "subtype_label": args.subtype_label,
        "reference_subtype": args.reference_subtype,
        "validate_paths_only": args.validate_paths_only,
    }


def resolve_project_path(path_value: str | Path, *, must_exist: bool = False) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve(strict=must_exist)
    return path


def ensure_paths(cfg: dict) -> dict:
    required = ["methylation_matrix", "clinical_metadata", "probe_annotation", "output_dir"]
    missing = [key for key in required if not cfg.get(key)]
    if missing:
        raise SystemExit(f"Missing required paths: {', '.join(missing)}")
    cfg["methylation_matrix"] = resolve_project_path(cfg["methylation_matrix"])
    cfg["clinical_metadata"] = resolve_project_path(cfg["clinical_metadata"])
    cfg["probe_annotation"] = resolve_project_path(cfg["probe_annotation"])
    if cfg.get("subtype_metadata"):
        cfg["subtype_metadata"] = resolve_project_path(cfg["subtype_metadata"])
    else:
        cfg["subtype_metadata"] = None
    cfg["output_dir"] = resolve_project_path(cfg["output_dir"])
    cfg["output_dir"].mkdir(parents=True, exist_ok=True)
    return cfg


def validate_configured_paths(cfg: dict) -> None:
    input_keys = ["methylation_matrix", "clinical_metadata", "probe_annotation"]
    if cfg["subtype_metadata"] is not None:
        input_keys.append("subtype_metadata")
    for key in input_keys:
        path = cfg[key]
        if not path.is_file():
            raise SystemExit(f"{key} is not a readable file: {path}")
        with path.open("rb"):
            pass
        print(f"OK input {key}: {path}")
    test_path = cfg["output_dir"] / ".path_validation_write_test"
    try:
        test_path.write_text("ok\n")
    finally:
        test_path.unlink(missing_ok=True)
    print(f"OK output output_dir: {cfg['output_dir']}")


def read_matrix_header(matrix_path: Path) -> list[str]:
    with gzip.open(matrix_path, "rt", encoding="utf-8", errors="ignore") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
    return header


def barcode_sample_type(sample_barcode: str) -> str:
    if len(sample_barcode) >= 15:
        code = sample_barcode[13:15]
        if code == "01":
            return "Primary Tumor"
        if code == "11":
            return "Solid Tissue Normal"
    return "Other"


def load_clinical_metadata(path: Path) -> pd.DataFrame:
    clinical = pd.read_csv(path, sep="\t", compression="gzip", low_memory=False)
    clinical = clinical.rename(columns={"sample": "sample_barcode"})
    keep = [
        "sample_barcode",
        "case_id",
        "submitter_id",
        "sample_type.samples",
        "tissue_type.samples",
        "gender.demographic",
        "age_at_index.demographic",
        "ajcc_pathologic_stage.diagnoses",
        "primary_diagnosis.diagnoses",
        "tumor_descriptor.samples",
    ]
    missing = [col for col in keep if col not in clinical.columns]
    if missing:
        raise SystemExit(f"Clinical metadata missing columns: {missing}")
    clinical = clinical[keep].copy()
    clinical["sample_type"] = clinical["sample_type.samples"].fillna("")
    clinical.loc[clinical["sample_type"] == "", "sample_type"] = clinical["sample_barcode"].map(
        barcode_sample_type
    )
    clinical = clinical[clinical["sample_type"].isin(VALID_SAMPLE_TYPES)].copy()
    clinical = clinical.drop_duplicates(subset=["sample_barcode"])
    clinical["sample_class"] = clinical["sample_type"].map(
        {"Primary Tumor": "tumor", "Solid Tissue Normal": "normal"}
    )
    clinical["patient_barcode"] = clinical["submitter_id"].astype(str).str.slice(0, 12)
    clinical["age_years"] = pd.to_numeric(
        clinical["age_at_index.demographic"], errors="coerce"
    )
    return clinical


def load_subtype_metadata(path: Path) -> pd.DataFrame:
    subtype = pd.read_csv(path, sep=None, engine="python")
    patient_col = None
    subtype_col = None
    for col in subtype.columns:
        lc = col.lower()
        if patient_col is None and lc in {
            "patient",
            "patient_id",
            "patient_barcode",
            "submitter_id",
            "case_submitter_id",
        }:
            patient_col = col
        if lc == "brca_subtype_pam50":
            subtype_col = col
        elif subtype_col is None and ("subtype" in lc or "pam50" in lc):
            subtype_col = col

    rename_map = {}
    if patient_col is not None:
        rename_map[patient_col] = "patient_barcode"
    for col in subtype.columns:
        lc = col.lower()
        if lc in {"sample", "sample_id", "sample_barcode", "barcode"}:
            rename_map[col] = "sample_barcode"
    if subtype_col is not None:
        rename_map[subtype_col] = "subtype"

    subtype = subtype.rename(columns=rename_map)
    if "subtype" not in subtype.columns:
        raise SystemExit("Subtype metadata must include a subtype/PAM50 column.")
    if "patient_barcode" not in subtype.columns and "sample_barcode" not in subtype.columns:
        raise SystemExit("Subtype metadata must include sample_barcode or patient_barcode.")
    if "patient_barcode" not in subtype.columns and "sample_barcode" in subtype.columns:
        subtype["patient_barcode"] = subtype["sample_barcode"].astype(str).str.slice(0, 12)
    subtype["patient_barcode"] = subtype["patient_barcode"].astype(str).str.slice(0, 12)
    subtype["subtype"] = subtype["subtype"].astype(str).str.strip()
    subtype = subtype[subtype["subtype"] != ""].copy()
    subtype = subtype[["patient_barcode", "subtype"]].drop_duplicates()
    return subtype


def build_cohort_manifest(matrix_header: list[str], clinical: pd.DataFrame) -> pd.DataFrame:
    matrix_samples = pd.DataFrame({"sample_barcode": matrix_header[1:]})
    manifest = matrix_samples.merge(clinical, on="sample_barcode", how="inner")
    manifest = manifest[manifest["sample_type"].isin(VALID_SAMPLE_TYPES)].copy()
    manifest = manifest.sort_values(["sample_class", "sample_barcode"]).reset_index(drop=True)
    return manifest


def attach_subtypes(manifest: pd.DataFrame, subtype_df: pd.DataFrame | None) -> pd.DataFrame:
    if subtype_df is None:
        manifest["subtype"] = pd.NA
        return manifest
    merged = manifest.merge(subtype_df, on="patient_barcode", how="left")
    merged.loc[merged["sample_class"] == "normal", "subtype"] = pd.NA
    return merged


def select_analysis_manifest(
    manifest: pd.DataFrame,
    comparison: str,
    subtype_label: str | None,
    reference_subtype: str | None,
) -> tuple[pd.DataFrame, str]:
    if comparison == "tumor_vs_normal":
        selected = manifest[manifest["sample_type"].isin(VALID_SAMPLE_TYPES)].copy()
        selected["analysis_group"] = selected["sample_class"]
        selected["analysis_group_label"] = selected["sample_class"]
        return selected, "tumor_vs_normal"

    if comparison == "subtype_vs_normal":
        if not subtype_label:
            raise SystemExit("--subtype-label is required for subtype_vs_normal")

        normals = manifest[manifest["sample_class"] == "normal"].copy()
        tumors = manifest[
            (manifest["sample_class"] == "tumor")
            & (manifest["subtype"].fillna("").str.lower() == subtype_label.lower())
        ].copy()
        selected = pd.concat([tumors, normals], ignore_index=True)
        if selected.empty or tumors.empty or normals.empty:
            raise SystemExit(f"No samples found for subtype comparison: {subtype_label}")
        selected.loc[selected["sample_class"] == "tumor", "analysis_group"] = "tumor"
        selected.loc[selected["sample_class"] == "normal", "analysis_group"] = "normal"
        selected.loc[selected["sample_class"] == "tumor", "analysis_group_label"] = subtype_label
        selected.loc[selected["sample_class"] == "normal", "analysis_group_label"] = "normal"
        slug = (
            subtype_label.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_")
        )
        return selected, f"{slug}_vs_normal"

    if comparison == "subtype_vs_subtype":
        if not subtype_label or not reference_subtype:
            raise SystemExit("--subtype-label and --reference-subtype are required for subtype_vs_subtype")
        tumors = manifest[manifest["sample_class"] == "tumor"].copy()
        known_tumors = tumors[~tumors["subtype"].fillna("").str.lower().isin(["", "na", "nan"])].copy()
        case = known_tumors[known_tumors["subtype"].fillna("").str.lower() == subtype_label.lower()].copy()
        ref_label_lower = reference_subtype.lower()
        if ref_label_lower.startswith("non_"):
            exclude = ref_label_lower.replace("non_", "", 1)
            reference = known_tumors[known_tumors["subtype"].fillna("").str.lower() != exclude].copy()
        else:
            reference = known_tumors[known_tumors["subtype"].fillna("").str.lower() == ref_label_lower].copy()
        reference = reference[~reference["sample_barcode"].isin(case["sample_barcode"])].copy()
        if case.empty or reference.empty:
            raise SystemExit(f"No samples found for subtype-vs-subtype comparison: {subtype_label} vs {reference_subtype}")
        case = case.copy()
        reference = reference.copy()
        case["analysis_group"] = "tumor"
        reference["analysis_group"] = "normal"
        case["analysis_group_label"] = subtype_label
        reference["analysis_group_label"] = reference_subtype
        selected = pd.concat([case, reference], ignore_index=True)
        case_slug = subtype_label.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
        ref_slug = reference_subtype.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
        return selected, f"{case_slug}_vs_{ref_slug}"

    raise SystemExit(f"Unsupported comparison: {comparison}")


def save_cohort_outputs(manifest: pd.DataFrame, out_dir: Path) -> None:
    group_col = "analysis_group" if "analysis_group" in manifest.columns else "sample_class"
    manifest.to_csv(out_dir / "cohort_manifest.tsv", sep="\t", index=False)
    summary = {
        "n_samples": int(len(manifest)),
        "n_case": int((manifest[group_col] == "tumor").sum()),
        "n_reference": int((manifest[group_col] == "normal").sum()),
        "sample_types": manifest["sample_type"].value_counts().to_dict(),
        "subtypes": manifest["subtype"].fillna("NA").value_counts().to_dict()
        if "subtype" in manifest.columns
        else {},
        "analysis_groups": manifest.get("analysis_group_label", manifest[group_col]).fillna("NA").value_counts().to_dict(),
        "ages": {
            "tumor_median": float(
                manifest.loc[manifest[group_col] == "tumor", "age_years"].median()
            ),
            "normal_median": float(
                manifest.loc[manifest[group_col] == "normal", "age_years"].median()
            ),
        },
    }
    (out_dir / "cohort_summary.json").write_text(json.dumps(summary, indent=2))


def compute_missingness_and_filtering(
    matrix_path: Path,
    manifest: pd.DataFrame,
    probe_map: pd.DataFrame,
    chunk_size: int,
    max_sample_missingness: float,
    max_probe_missingness: float,
    drop_sex_chromosomes: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    sample_columns = manifest["sample_barcode"].tolist()
    probe_meta = probe_map.copy()
    if drop_sex_chromosomes and "chrom" in probe_meta.columns:
        probe_meta = probe_meta[~probe_meta["chrom"].isin(["chrX", "chrY"])].copy()
    allowed_probe_ids = set(probe_meta["probe_id"])

    sample_missing = pd.Series(0, index=sample_columns, dtype=np.int64)
    total_seen = 0
    duplicate_probe_rows = 0
    seen_probe_ids: set[str] = set()
    probe_missing_records: list[pd.DataFrame] = []
    usecols = ["Composite Element REF", *sample_columns]

    for chunk in pd.read_csv(
        matrix_path,
        sep="\t",
        compression="gzip",
        usecols=usecols,
        chunksize=chunk_size,
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

    probe_missing_df = pd.concat(probe_missing_records, ignore_index=True)
    probe_missing_df = probe_missing_df.groupby("probe_id", as_index=False)["probe_missing_fraction"].mean()
    kept_probe_df = probe_missing_df[probe_missing_df["probe_missing_fraction"] <= max_probe_missingness].copy()
    filtered_probe_map = probe_meta.merge(kept_probe_df, on="probe_id", how="inner")

    sample_missing_fraction = (sample_missing / max(total_seen, 1)).sort_index()
    kept_samples = sample_missing_fraction[sample_missing_fraction <= max_sample_missingness].index.tolist()
    filtered_manifest = manifest[manifest["sample_barcode"].isin(kept_samples)].copy()

    qc = {
        "input_sample_count": int(len(sample_columns)),
        "filtered_sample_count": int(len(filtered_manifest)),
        "input_probe_count_after_annotation_filter": int(total_seen),
        "filtered_probe_count": int(len(filtered_probe_map)),
        "sample_duplicates_in_header": int(pd.Index(sample_columns).duplicated().sum()),
        "duplicate_probe_rows_detected": int(duplicate_probe_rows),
        "max_sample_missingness_threshold": float(max_sample_missingness),
        "max_probe_missingness_threshold": float(max_probe_missingness),
        "drop_sex_chromosomes": bool(drop_sex_chromosomes),
        "n_samples_removed_for_missingness": int(len(sample_columns) - len(filtered_manifest)),
        "n_probes_removed_for_missingness_or_filtering": int(total_seen - len(filtered_probe_map)),
    }
    details = {
        "sample_missing_fraction": sample_missing_fraction.to_dict(),
        "probe_missing_df": kept_probe_df,
        "qc": qc,
    }
    return filtered_manifest, filtered_probe_map, details


def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    out = np.full_like(p, np.nan)
    valid = np.isfinite(p)
    if valid.sum() == 0:
        return out
    pv = p[valid]
    order = np.argsort(pv)
    ranked = pv[order]
    n = len(ranked)
    q = ranked * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    restored = np.empty_like(q)
    restored[order] = q
    out[valid] = restored
    return out


def stream_differential_methylation(
    matrix_path: Path,
    manifest: pd.DataFrame,
    probe_map: pd.DataFrame,
    chunk_size: int,
    max_probes: int | None = None,
) -> pd.DataFrame:
    sample_columns = manifest["sample_barcode"].tolist()
    group_col = "analysis_group" if "analysis_group" in manifest.columns else "sample_class"
    tumor_columns = manifest.loc[manifest[group_col] == "tumor", "sample_barcode"].tolist()
    normal_columns = manifest.loc[manifest[group_col] == "normal", "sample_barcode"].tolist()
    usecols = ["Composite Element REF", *sample_columns]
    allowed_probe_ids = set(probe_map["probe_id"])
    tumor_idx = [sample_columns.index(col) for col in tumor_columns]
    normal_idx = [sample_columns.index(col) for col in normal_columns]
    results: list[pd.DataFrame] = []
    processed = 0
    for chunk in pd.read_csv(
        matrix_path,
        sep="\t",
        compression="gzip",
        usecols=usecols,
        chunksize=chunk_size,
        low_memory=False,
    ):
        chunk = chunk.rename(columns={"Composite Element REF": "probe_id"})
        chunk = chunk[chunk["probe_id"].isin(allowed_probe_ids)].copy()
        if chunk.empty:
            continue
        if max_probes is not None:
            remaining = max_probes - processed
            if remaining <= 0:
                break
            chunk = chunk.iloc[:remaining].copy()
        processed += len(chunk)

        beta = chunk[sample_columns].apply(pd.to_numeric, errors="coerce").astype(np.float32)
        tumor_vals = beta[tumor_columns].to_numpy(dtype=np.float32)
        normal_vals = beta[normal_columns].to_numpy(dtype=np.float32)
        eps = np.float32(1e-6)
        beta_matrix = beta.to_numpy(dtype=np.float32)
        beta_clipped = np.clip(beta_matrix, eps, 1 - eps)
        m_values = np.log2(beta_clipped / (1 - beta_clipped))
        tumor_m = m_values[:, tumor_idx]
        normal_m = m_values[:, normal_idx]

        tumor_n = np.sum(np.isfinite(tumor_vals), axis=1)
        normal_n = np.sum(np.isfinite(normal_vals), axis=1)
        tumor_sum = np.nansum(tumor_vals, axis=1)
        normal_sum = np.nansum(normal_vals, axis=1)
        tumor_mean = np.divide(
            tumor_sum,
            tumor_n,
            out=np.full(len(chunk), np.nan, dtype=float),
            where=tumor_n > 0,
        )
        normal_mean = np.divide(
            normal_sum,
            normal_n,
            out=np.full(len(chunk), np.nan, dtype=float),
            where=normal_n > 0,
        )
        delta_beta = tumor_mean - normal_mean

        valid_for_test = (tumor_n >= 2) & (normal_n >= 2)
        p_value = np.full(len(chunk), np.nan, dtype=float)
        test_statistic = np.full(len(chunk), np.nan, dtype=float)
        if np.any(valid_for_test):
            test = stats.ttest_ind(
                tumor_m[valid_for_test],
                normal_m[valid_for_test],
                axis=1,
                equal_var=False,
                nan_policy="omit",
            )
            p_value[valid_for_test] = test.pvalue
            test_statistic[valid_for_test] = test.statistic

        tumor_mean_m = np.nanmean(tumor_m, axis=1)
        normal_mean_m = np.nanmean(normal_m, axis=1)

        summary = pd.DataFrame(
            {
                "probe_id": chunk["probe_id"].values,
                "tumor_mean_beta": tumor_mean,
                "normal_mean_beta": normal_mean,
                "tumor_mean_m": tumor_mean_m,
                "normal_mean_m": normal_mean_m,
                "delta_beta": delta_beta,
                "delta_m": tumor_mean_m - normal_mean_m,
                "tumor_n": tumor_n,
                "normal_n": normal_n,
                "test_statistic": test_statistic,
                "p_value": p_value,
            }
        )
        results.append(summary)
        if max_probes is not None and processed >= max_probes:
            break

    result = pd.concat(results, ignore_index=True)
    result["fdr"] = benjamini_hochberg(result["p_value"].to_numpy())
    result["abs_delta_beta"] = result["delta_beta"].abs()
    result["direction"] = np.where(result["delta_beta"] >= 0, "hypermethylated", "hypomethylated")
    result = result.merge(probe_map, on="probe_id", how="left")
    result = result.sort_values(["fdr", "abs_delta_beta"], ascending=[True, False]).reset_index(drop=True)
    return result


def load_probe_annotation(path: Path) -> pd.DataFrame:
    probe_map = pd.read_csv(path, sep="\t", low_memory=False)
    probe_map = probe_map.rename(columns={"#id": "probe_id"})
    keep = [col for col in ["probe_id", "gene", "chrom", "chromStart", "chromEnd", "strand"] if col in probe_map.columns]
    return probe_map[keep].drop_duplicates(subset=["probe_id"])


def write_qc_outputs(
    manifest: pd.DataFrame,
    filtered_manifest: pd.DataFrame,
    qc_details: dict,
    probe_map: pd.DataFrame,
    out_dir: Path,
) -> None:
    group_col = "analysis_group" if "analysis_group" in filtered_manifest.columns else "sample_class"
    sample_missing = (
        pd.Series(qc_details["sample_missing_fraction"])
        .rename_axis("sample_barcode")
        .reset_index(name="missing_fraction")
    )
    sample_missing["retained"] = sample_missing["sample_barcode"].isin(filtered_manifest["sample_barcode"])
    sample_missing.to_csv(out_dir / "sample_missingness.tsv", sep="\t", index=False)

    probe_missing = qc_details["probe_missing_df"].merge(
        probe_map[["probe_id", "chrom", "gene"]].drop_duplicates(subset=["probe_id"]),
        on="probe_id",
        how="left",
    )
    probe_missing.to_csv(out_dir / "probe_missingness.tsv", sep="\t", index=False)

    qc_summary = qc_details["qc"].copy()
    qc_summary.update(
        {
            "n_case_after_filtering": int((filtered_manifest[group_col] == "tumor").sum()),
            "n_reference_after_filtering": int((filtered_manifest[group_col] == "normal").sum()),
            "median_sample_missing_fraction": float(sample_missing["missing_fraction"].median()),
            "max_sample_missing_fraction": float(sample_missing["missing_fraction"].max()),
            "median_probe_missing_fraction": float(probe_missing["probe_missing_fraction"].median()),
        }
    )
    (out_dir / "qc_summary.json").write_text(json.dumps(qc_summary, indent=2))
    lines = [
        "# QC Summary",
        "",
        f"- input samples: `{qc_summary['input_sample_count']}`",
        f"- retained samples: `{qc_summary['filtered_sample_count']}`",
        f"- case samples after filtering: `{qc_summary['n_case_after_filtering']}`",
        f"- reference samples after filtering: `{qc_summary['n_reference_after_filtering']}`",
        f"- retained probes: `{qc_summary['filtered_probe_count']}`",
        f"- sample duplicates in matrix header: `{qc_summary['sample_duplicates_in_header']}`",
        f"- duplicate probe rows detected: `{qc_summary['duplicate_probe_rows_detected']}`",
        f"- sex chromosomes dropped: `{qc_summary['drop_sex_chromosomes']}`",
        f"- max sample missingness threshold: `{qc_summary['max_sample_missingness_threshold']}`",
        f"- max probe missingness threshold: `{qc_summary['max_probe_missingness_threshold']}`",
        f"- median sample missingness: `{qc_summary['median_sample_missing_fraction']:.4f}`",
        f"- max sample missingness: `{qc_summary['max_sample_missing_fraction']:.4f}`",
        f"- median retained-probe missingness: `{qc_summary['median_probe_missing_fraction']:.4f}`",
    ]
    (out_dir / "qc_summary.md").write_text("\n".join(lines) + "\n")


def save_ranked_outputs(results: pd.DataFrame, out_dir: Path) -> None:
    results.to_csv(out_dir / "differential_methylation.tsv", sep="\t", index=False)

    ranked = results[np.isfinite(results["fdr"])].copy()
    top_abs = ranked.sort_values(["abs_delta_beta", "fdr"], ascending=[False, True]).head(250)
    top_hyper = ranked[ranked["delta_beta"] > 0].sort_values(
        ["delta_beta", "fdr"], ascending=[False, True]
    ).head(250)
    top_hypo = ranked[ranked["delta_beta"] < 0].sort_values(
        ["delta_beta", "fdr"], ascending=[True, True]
    ).head(250)
    candidate_panel = ranked[
        (ranked["fdr"] < 0.05)
        & (ranked["abs_delta_beta"] >= 0.20)
        & (ranked["tumor_n"] >= 20)
        & (ranked["normal_n"] >= 20)
    ].sort_values(["abs_delta_beta", "fdr"], ascending=[False, True]).head(100)

    top_abs.to_csv(out_dir / "top_markers_abs_delta_beta.tsv", sep="\t", index=False)
    top_hyper.to_csv(out_dir / "top_hypermethylated_markers.tsv", sep="\t", index=False)
    top_hypo.to_csv(out_dir / "top_hypomethylated_markers.tsv", sep="\t", index=False)
    candidate_panel.to_csv(out_dir / "candidate_biomarker_panel.tsv", sep="\t", index=False)


def write_summary_report(results: pd.DataFrame, manifest: pd.DataFrame, out_dir: Path, run_name: str) -> None:
    group_col = "analysis_group" if "analysis_group" in manifest.columns else "sample_class"
    label_col = "analysis_group_label" if "analysis_group_label" in manifest.columns else group_col
    ranked = results[np.isfinite(results["fdr"])].copy()
    stringent = ranked[
        (ranked["fdr"] < 0.05)
        & (ranked["abs_delta_beta"] >= 0.20)
        & (ranked["tumor_n"] >= 20)
        & (ranked["normal_n"] >= 20)
    ].copy()
    top_abs = ranked.sort_values(["abs_delta_beta", "fdr"], ascending=[False, True]).head(10)
    top_hyper = ranked[ranked["delta_beta"] > 0].sort_values(["delta_beta", "fdr"], ascending=[False, True]).head(10)
    top_hypo = ranked[ranked["delta_beta"] < 0].sort_values(["delta_beta", "fdr"], ascending=[True, True]).head(10)

    summary = {
        "run_name": run_name,
        "n_samples": int(len(manifest)),
        "n_case": int((manifest[group_col] == "tumor").sum()),
        "n_reference": int((manifest[group_col] == "normal").sum()),
        "n_probes_tested": int(len(results)),
        "n_probes_with_finite_fdr": int(len(ranked)),
        "n_fdr_lt_0_05": int((ranked["fdr"] < 0.05).sum()),
        "n_abs_delta_ge_0_20": int((ranked["abs_delta_beta"] >= 0.20).sum()),
        "n_fdr_lt_0_05_and_abs_delta_ge_0_20": int(len(stringent)),
        "n_fdr_lt_0_05_and_abs_delta_ge_0_30": int(
            ((ranked["fdr"] < 0.05) & (ranked["abs_delta_beta"] >= 0.30)).sum()
        ),
    }
    (out_dir / "analysis_summary.json").write_text(json.dumps(summary, indent=2))

    def format_table(df: pd.DataFrame) -> list[str]:
        lines = ["| probe_id | gene | delta_beta | fdr | direction |", "|---|---|---:|---:|---|"]
        for _, row in df.iterrows():
            gene = row["gene"] if pd.notna(row["gene"]) and str(row["gene"]).strip() else "—"
            lines.append(
                f"| `{row['probe_id']}` | `{gene}` | {row['delta_beta']:.3f} | {row['fdr']:.3e} | {row['direction']} |"
            )
        return lines

    title = run_name.replace("_", " ").title()
    case_label = manifest.loc[manifest[group_col] == "tumor", label_col].dropna().astype(str).mode()
    ref_label = manifest.loc[manifest[group_col] == "normal", label_col].dropna().astype(str).mode()
    case_label = case_label.iloc[0] if not case_label.empty else "case"
    ref_label = ref_label.iloc[0] if not ref_label.empty else "reference"
    memo_lines = [
        f"# {title} Methylation Report",
        "",
        "## Cohort",
        "",
        f"- `{summary['n_case']}` `{case_label}` samples",
        f"- `{summary['n_reference']}` `{ref_label}` samples",
        f"- `{summary['n_probes_tested']}` probes tested",
        "",
        "## Summary",
        "",
        f"- `{summary['n_fdr_lt_0_05']}` probes with `FDR < 0.05`",
        f"- `{summary['n_abs_delta_ge_0_20']}` probes with `|delta_beta| >= 0.20`",
        f"- `{summary['n_fdr_lt_0_05_and_abs_delta_ge_0_20']}` probes meeting both thresholds",
        f"- `{summary['n_fdr_lt_0_05_and_abs_delta_ge_0_30']}` probes meeting `FDR < 0.05` and `|delta_beta| >= 0.30`",
        "",
        "## Top Markers By Absolute Effect Size",
        "",
        *format_table(top_abs),
        "",
        "## Top Hypermethylated Markers",
        "",
        *format_table(top_hyper),
        "",
        "## Top Hypomethylated Markers",
        "",
        *format_table(top_hypo),
        "",
        "## Outputs",
        "",
        "- `differential_methylation.tsv`",
        "- `candidate_biomarker_panel.tsv`",
        "- `qc_summary.json`",
        "- `qc_summary.md`",
        "- `sample_missingness.tsv`",
        "- `probe_missingness.tsv`",
        "- `top_markers_abs_delta_beta.tsv`",
        "- `top_hypermethylated_markers.tsv`",
        "- `top_hypomethylated_markers.tsv`",
        "- `pca_samples.png`",
        "- `heatmap_top_markers.png`",
        "- `volcano_top_markers.png`",
        "- `classifier_summary.json`",
    ]
    (out_dir / "report_summary.md").write_text("\n".join(memo_lines) + "\n")


def build_pca_plot(matrix_path: Path, manifest: pd.DataFrame, out_dir: Path, n_probe_sample: int = 5000) -> None:
    group_col = "analysis_group" if "analysis_group" in manifest.columns else "sample_class"
    label_col = "analysis_group_label" if "analysis_group_label" in manifest.columns else group_col
    sample_columns = manifest["sample_barcode"].tolist()
    usecols = ["Composite Element REF", *sample_columns]
    frames = []
    seen = 0
    for chunk in pd.read_csv(
        matrix_path,
        sep="\t",
        compression="gzip",
        usecols=usecols,
        chunksize=2000,
        low_memory=False,
    ):
        chunk = chunk.rename(columns={"Composite Element REF": "probe_id"})
        frames.append(chunk)
        seen += len(chunk)
        if seen >= n_probe_sample:
            break
    pca_df = pd.concat(frames, ignore_index=True).iloc[:n_probe_sample]
    beta = pca_df[sample_columns].apply(pd.to_numeric, errors="coerce")
    row_means = beta.mean(axis=1)
    beta = beta.T.fillna(row_means).T
    beta = beta.fillna(beta.mean(axis=0))
    beta = beta.fillna(beta.mean(axis=1), axis=0)
    beta = beta.fillna(0.0)
    matrix = beta.T.to_numpy(dtype=float)
    coords = PCA(n_components=2, random_state=0).fit_transform(matrix)
    pca_out = manifest[["sample_barcode", group_col, label_col, "sample_type"]].copy()
    pca_out = pca_out.rename(columns={group_col: "sample_class", label_col: "sample_group_label"})
    pca_out["PC1"] = coords[:, 0]
    pca_out["PC2"] = coords[:, 1]
    pca_out.to_csv(out_dir / "pca_samples.tsv", sep="\t", index=False)

    plt.figure(figsize=(8, 6))
    colors = {"tumor": "#b2182b", "normal": "#2166ac"}
    for label, group in pca_out.groupby("sample_group_label"):
        group_class = group["sample_class"].iloc[0]
        plt.scatter(group["PC1"], group["PC2"], s=24, alpha=0.75, label=label, c=colors.get(group_class, "#444444"))
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.title("TCGA-BRCA HM450 Sample PCA")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(out_dir / "pca_samples.png", dpi=200)
    plt.close()


def build_volcano_plot(results: pd.DataFrame, out_dir: Path) -> None:
    plot_df = results.copy()
    plot_df["neg_log10_fdr"] = -np.log10(plot_df["fdr"].clip(lower=1e-300))
    plt.figure(figsize=(8, 6))
    plt.scatter(plot_df["delta_beta"], plot_df["neg_log10_fdr"], s=4, alpha=0.3, c="#666666")
    highlight = plot_df.nsmallest(15, "fdr")
    plt.scatter(highlight["delta_beta"], highlight["neg_log10_fdr"], s=18, c="#b2182b")
    for _, row in highlight.iterrows():
        label = row["gene"] if pd.notna(row.get("gene")) and row["gene"] else row["probe_id"]
        plt.text(row["delta_beta"], row["neg_log10_fdr"], str(label), fontsize=7)
    plt.xlabel("Delta beta (tumor - normal)")
    plt.ylabel("-log10(FDR)")
    plt.title("BRCA Differential Methylation")
    plt.tight_layout()
    plt.savefig(out_dir / "volcano_top_markers.png", dpi=200)
    plt.close()


def build_heatmap_plot(
    matrix_path: Path,
    manifest: pd.DataFrame,
    candidate_panel: pd.DataFrame,
    out_dir: Path,
    top_n: int,
) -> None:
    group_col = "analysis_group" if "analysis_group" in manifest.columns else "sample_class"
    label_col = "analysis_group_label" if "analysis_group_label" in manifest.columns else group_col
    top_probes = candidate_panel["probe_id"].head(top_n).tolist()
    if not top_probes:
        return
    sample_columns = manifest["sample_barcode"].tolist()
    usecols = ["Composite Element REF", *sample_columns]
    chunks = []
    found = 0
    for chunk in pd.read_csv(
        matrix_path,
        sep="\t",
        compression="gzip",
        usecols=usecols,
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
    if not chunks:
        return
    heatmap_df = pd.concat(chunks, ignore_index=True).drop_duplicates(subset=["probe_id"])
    heatmap_df = heatmap_df.set_index("probe_id").reindex(top_probes)
    beta = heatmap_df[sample_columns].apply(pd.to_numeric, errors="coerce")
    beta = beta.T.fillna(beta.mean(axis=1)).T
    beta = beta.fillna(beta.mean(axis=0))
    beta = beta.fillna(0.0)

    ordered_manifest = manifest.sort_values([group_col, "sample_barcode"]).reset_index(drop=True)
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
        match = candidate_panel.loc[candidate_panel["probe_id"] == probe_id, "gene"]
        gene = match.iloc[0] if not match.empty and pd.notna(match.iloc[0]) and str(match.iloc[0]).strip() else probe_id
        labels.append(str(gene))
    ax.set_yticklabels(labels, fontsize=7)
    normal_count = int((ordered_manifest[group_col] == "normal").sum())
    ref_label = ordered_manifest.loc[ordered_manifest[group_col] == "normal", label_col].dropna().astype(str).mode()
    case_label = ordered_manifest.loc[ordered_manifest[group_col] == "tumor", label_col].dropna().astype(str).mode()
    ref_label = ref_label.iloc[0] if not ref_label.empty else "reference"
    case_label = case_label.iloc[0] if not case_label.empty else "case"
    ax.axvline(normal_count - 0.5, color="black", linewidth=1)
    ax.text(max(normal_count / 2, 1), -1.5, ref_label, ha="center", va="bottom", fontsize=9)
    ax.text(normal_count + max((len(ordered_samples) - normal_count) / 2, 1), -1.5, case_label, ha="center", va="bottom", fontsize=9)
    ax.set_title(f"Top {len(top_probes)} Candidate Markers")
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02, label="row z-score")
    plt.tight_layout()
    plt.savefig(out_dir / "heatmap_top_markers.png", dpi=200)
    plt.close()


def run_classifier(
    matrix_path: Path,
    manifest: pd.DataFrame,
    candidate_panel: pd.DataFrame,
    out_dir: Path,
    top_n: int,
) -> None:
    group_col = "analysis_group" if "analysis_group" in manifest.columns else "sample_class"
    top_probes = candidate_panel["probe_id"].head(top_n).tolist()
    if len(top_probes) < 2:
        return
    sample_columns = manifest["sample_barcode"].tolist()
    usecols = ["Composite Element REF", *sample_columns]
    chunks = []
    found = 0
    for chunk in pd.read_csv(
        matrix_path,
        sep="\t",
        compression="gzip",
        usecols=usecols,
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
    if not chunks:
        return
    feature_df = pd.concat(chunks, ignore_index=True).drop_duplicates(subset=["probe_id"])
    feature_df = feature_df.set_index("probe_id").reindex(top_probes)
    X = feature_df[sample_columns].T.apply(pd.to_numeric, errors="coerce")
    X = X.fillna(X.mean(axis=0))
    X = X.fillna(X.mean(axis=1), axis=0)
    X = X.fillna(0.0)
    y = (manifest.set_index("sample_barcode").loc[X.index, group_col] == "tumor").astype(int).to_numpy()
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
    (out_dir / "classifier_summary.json").write_text(json.dumps(summary, indent=2))


def main() -> None:
    args = parse_args()
    cfg = ensure_paths(load_config(args))
    if cfg["validate_paths_only"]:
        validate_configured_paths(cfg)
        return

    matrix_header = read_matrix_header(cfg["methylation_matrix"])
    clinical = load_clinical_metadata(cfg["clinical_metadata"])
    manifest = build_cohort_manifest(matrix_header, clinical)
    subtype_df = load_subtype_metadata(cfg["subtype_metadata"]) if cfg["subtype_metadata"] else None
    manifest = attach_subtypes(manifest, subtype_df)
    manifest, run_name = select_analysis_manifest(
        manifest,
        comparison=cfg["comparison"],
        subtype_label=cfg["subtype_label"],
        reference_subtype=cfg["reference_subtype"],
    )
    run_output_dir = cfg["output_dir"] / run_name
    run_output_dir.mkdir(parents=True, exist_ok=True)
    if manifest.empty:
        raise SystemExit("No overlapping BRCA samples found between matrix and clinical metadata.")
    group_col = "analysis_group" if "analysis_group" in manifest.columns else "sample_class"
    if (manifest[group_col] == "normal").sum() == 0 or (manifest[group_col] == "tumor").sum() == 0:
        raise SystemExit("Need both tumor and normal samples for the first-pass comparison.")

    save_cohort_outputs(manifest, run_output_dir)
    probe_map = load_probe_annotation(cfg["probe_annotation"])
    filtered_manifest, filtered_probe_map, qc_details = compute_missingness_and_filtering(
        cfg["methylation_matrix"],
        manifest,
        probe_map,
        chunk_size=cfg["chunk_size"],
        max_sample_missingness=cfg["max_sample_missingness"],
        max_probe_missingness=cfg["max_probe_missingness"],
        drop_sex_chromosomes=cfg["drop_sex_chromosomes"],
    )
    if (filtered_manifest[group_col] == "normal").sum() == 0 or (filtered_manifest[group_col] == "tumor").sum() == 0:
        raise SystemExit("Filtering removed one of the classes; relax the missingness thresholds.")
    write_qc_outputs(manifest, filtered_manifest, qc_details, filtered_probe_map, run_output_dir)
    results = stream_differential_methylation(
        cfg["methylation_matrix"],
        filtered_manifest,
        filtered_probe_map,
        chunk_size=cfg["chunk_size"],
        max_probes=cfg["max_probes"],
    )
    save_ranked_outputs(results, run_output_dir)
    candidate_panel = pd.read_csv(run_output_dir / "candidate_biomarker_panel.tsv", sep="\t")
    build_pca_plot(cfg["methylation_matrix"], filtered_manifest, run_output_dir)
    build_volcano_plot(results, run_output_dir)
    build_heatmap_plot(
        cfg["methylation_matrix"],
        filtered_manifest,
        candidate_panel,
        run_output_dir,
        top_n=cfg["heatmap_top_n"],
    )
    run_classifier(
        cfg["methylation_matrix"],
        filtered_manifest,
        candidate_panel,
        run_output_dir,
        top_n=cfg["classifier_top_n"],
    )
    write_summary_report(results, filtered_manifest, run_output_dir, run_name)


if __name__ == "__main__":
    main()
