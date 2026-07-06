#!/usr/bin/env python3
"""Phase 4: healthy-control methylation baseline for longevity gene sets."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple, Union

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_pathway_enrichment import load_output_dir, parse_gmt, split_genes  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"
DEFAULT_GSE = PROJECT_ROOT / "data" / "external" / "GSE66695_series_matrix.txt.gz"
DEFAULT_TCGA_MATRIX = PROJECT_ROOT / "data" / "raw" / "TCGA-BRCA.methylation450.tsv.gz"


def resolve_project_path(path_value: Union[str, Path]) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def parse_gse_metadata(series_matrix_path: Path) -> pd.DataFrame:
    meta: Dict[str, List[List[str]]] = {}
    with gzip.open(series_matrix_path, "rt", errors="replace") as handle:
        for line in handle:
            if line.startswith("!series_matrix_table_begin"):
                break
            if line.startswith(("!Sample_title", "!Sample_geo_accession", "!Sample_source_name_ch1", "!Sample_characteristics_ch1")):
                row = next(csv.reader([line], delimiter="\t"))
                meta.setdefault(row[0], []).append(row[1:])

    titles = meta["!Sample_title"][0]
    accessions = meta["!Sample_geo_accession"][0]
    source = meta["!Sample_source_name_ch1"][0]
    sample_type = [""] * len(accessions)
    disease_state = [""] * len(accessions)
    for values in meta.get("!Sample_characteristics_ch1", []):
        label = values[0].split(":", 1)[0].strip().lower() if values else ""
        if label == "sample type":
            sample_type = [v.split(":", 1)[1].strip() if ":" in v else v.strip() for v in values]
        if label == "disease state":
            disease_state = [v.split(":", 1)[1].strip() if ":" in v else v.strip() for v in values]

    records = []
    for title, gsm, src, stype, disease in zip(titles, accessions, source, sample_type, disease_state):
        source_class = src.strip().lower()
        disease_class = disease.strip().lower()
        title_class = "normal" if title.endswith("-N") else "tumor" if re.search(r"-T($|-)", title) else "unknown"
        sample_type_class = "normal" if stype.strip().lower() == "normal" else "tumor" if stype.strip() else "unknown"
        signals = [source_class, disease_class, title_class, sample_type_class]
        non_unknown = [x for x in signals if x in {"normal", "tumor"}]
        sample_class = non_unknown[0] if non_unknown else "unknown"
        label_agreement = all(x == sample_class for x in non_unknown)
        records.append(
            {
                "sample_geo_accession": gsm,
                "sample_title": title,
                "sample_source_name_ch1": src,
                "sample_type_characteristic": stype,
                "disease_state_characteristic": disease,
                "title_suffix_class": title_class,
                "sample_class": sample_class,
                "label_agreement": label_agreement,
            }
        )
    labels = pd.DataFrame(records)
    if not labels["label_agreement"].all():
        bad = labels[~labels["label_agreement"]].head().to_dict(orient="records")
        raise ValueError(f"GSE66695 sample label disagreement detected: {bad}")
    if labels["sample_class"].value_counts().to_dict() != {"tumor": 80, "normal": 40}:
        raise ValueError(f"Unexpected GSE66695 label counts: {labels['sample_class'].value_counts().to_dict()}")
    return labels


def find_gse_table_start(series_matrix_path: Path) -> int:
    with gzip.open(series_matrix_path, "rt", errors="replace") as handle:
        for i, line in enumerate(handle):
            if line.startswith("!series_matrix_table_begin"):
                return i
    raise ValueError("Could not find !series_matrix_table_begin in GSE series matrix")


def annotation_genes(row: pd.Series) -> List[str]:
    genes = split_genes(row.get("genes_all"))
    nearest = row.get("gene_nearest")
    if pd.notna(nearest) and str(nearest).strip() and str(nearest).strip() not in genes:
        genes.append(str(nearest).strip())
    return genes


def map_gene_sets_to_cpgs(out_dir: Path) -> Tuple[pd.DataFrame, Dict[str, Set[str]]]:
    gene_sets = parse_gmt(out_dir / "pathway_enrichment_longevity" / "longevity_gene_sets.gmt")
    gene_to_sets: Dict[str, Set[str]] = {}
    for set_name, genes in gene_sets.items():
        for gene in genes:
            gene_to_sets.setdefault(gene, set()).add(set_name)

    ann = pd.read_csv(
        out_dir / "annotation" / "probe_annotation_enriched.tsv",
        sep="\t",
        usecols=[
            "probe_id",
            "chrom",
            "chromStart",
            "chromEnd",
            "strand",
            "genes_all",
            "gene_nearest",
            "dist_to_tss",
            "functional_region",
            "is_promoter",
            "cgi_relation",
        ],
        low_memory=False,
    )
    records = []
    for _, row in ann.iterrows():
        genes = annotation_genes(row)
        sets_for_probe = sorted({set_name for gene in genes for set_name in gene_to_sets.get(gene, set())})
        for set_name in sets_for_probe:
            mapped_genes = sorted([gene for gene in genes if set_name in gene_to_sets.get(gene, set())])
            record = row.to_dict()
            record["set_name"] = set_name
            record["mapped_genes_in_set"] = ",".join(mapped_genes)
            records.append(record)
    mapped = pd.DataFrame(records)
    if mapped.empty:
        raise ValueError("No CpGs mapped to the Phase 3 longevity gene sets")
    return mapped, gene_sets


def stream_matrix_group_means(
    path: Path,
    id_col: str,
    target_probes: Set[str],
    normal_cols: List[str],
    tumor_cols: List[str],
    compression: str,
    skiprows: int = 0,
    comment: str = None,
    chunksize: int = 5000,
) -> pd.DataFrame:
    records = []
    usecols = [id_col] + normal_cols + tumor_cols
    reader = pd.read_csv(
        path,
        sep="\t",
        compression=compression,
        skiprows=skiprows,
        comment=comment,
        usecols=usecols,
        chunksize=chunksize,
        low_memory=False,
    )
    found: Set[str] = set()
    for chunk in reader:
        sub = chunk[chunk[id_col].astype(str).isin(target_probes)].copy()
        if sub.empty:
            continue
        found.update(sub[id_col].astype(str).tolist())
        normal_beta = sub[normal_cols].apply(pd.to_numeric, errors="coerce")
        tumor_beta = sub[tumor_cols].apply(pd.to_numeric, errors="coerce")
        rec = pd.DataFrame(
            {
                "probe_id": sub[id_col].astype(str).values,
                "normal_mean_beta": normal_beta.mean(axis=1).values,
                "normal_n": normal_beta.notna().sum(axis=1).astype(int).values,
                "tumor_mean_beta": tumor_beta.mean(axis=1).values,
                "tumor_n": tumor_beta.notna().sum(axis=1).astype(int).values,
            }
        )
        records.append(rec)
        if len(found) >= len(target_probes):
            break
    if not records:
        return pd.DataFrame(columns=["probe_id", "normal_mean_beta", "normal_n", "tumor_mean_beta", "tumor_n"])
    return pd.concat(records, ignore_index=True).drop_duplicates(subset=["probe_id"])


def load_tcga_manifest(out_dir: Path) -> pd.DataFrame:
    manifest = pd.read_csv(out_dir / "tumor_vs_normal" / "cohort_manifest.tsv", sep="\t", low_memory=False)
    if manifest["sample_class"].value_counts().to_dict() != {"tumor": 791, "normal": 97}:
        raise ValueError(f"Unexpected TCGA cohort counts: {manifest['sample_class'].value_counts().to_dict()}")
    return manifest


def count_gse_probe_overlap(series_matrix_path: Path, project_probe_ids: Set[str], target_probes: Set[str]) -> Dict[str, int]:
    begin = find_gse_table_start(series_matrix_path)
    total = 0
    project_overlap = 0
    target_overlap = 0
    for chunk in pd.read_csv(
        series_matrix_path,
        sep="\t",
        compression="gzip",
        skiprows=begin + 1,
        comment="!",
        usecols=["ID_REF"],
        chunksize=50000,
        low_memory=False,
    ):
        ids = set(chunk["ID_REF"].astype(str))
        total += len(ids)
        project_overlap += len(ids & project_probe_ids)
        target_overlap += len(ids & target_probes)
    return {
        "gse_probe_count": int(total),
        "project_hm450_probe_count": int(len(project_probe_ids)),
        "gse_project_probe_overlap": int(project_overlap),
        "longevity_target_probe_count": int(len(target_probes)),
        "gse_longevity_target_overlap": int(target_overlap),
    }


def build_cpg_baseline_table(
    mapped_cpgs: pd.DataFrame,
    gse_means: pd.DataFrame,
    tcga_means: pd.DataFrame,
    significant_cpgs: Set[str],
) -> pd.DataFrame:
    gse = gse_means.rename(
        columns={
            "normal_mean_beta": "gse_normal_mean_beta",
            "normal_n": "gse_normal_n",
            "tumor_mean_beta": "gse_tumor_mean_beta",
            "tumor_n": "gse_tumor_n",
        }
    )
    tcga = tcga_means.rename(
        columns={
            "normal_mean_beta": "tcga_normal_mean_beta",
            "normal_n": "tcga_normal_n",
            "tumor_mean_beta": "tcga_tumor_mean_beta",
            "tumor_n": "tcga_tumor_n",
        }
    )
    table = mapped_cpgs.merge(gse, on="probe_id", how="left").merge(tcga, on="probe_id", how="left")
    numerator = (
        table["gse_normal_mean_beta"].fillna(0) * table["gse_normal_n"].fillna(0)
        + table["tcga_normal_mean_beta"].fillna(0) * table["tcga_normal_n"].fillna(0)
    )
    denominator = table["gse_normal_n"].fillna(0) + table["tcga_normal_n"].fillna(0)
    table["combined_healthy_mean_beta"] = numerator / denominator.replace(0, np.nan)
    table["tcga_tumor_vs_combined_healthy_delta"] = table["tcga_tumor_mean_beta"] - table["combined_healthy_mean_beta"]
    table["gse_tumor_vs_combined_healthy_delta"] = table["gse_tumor_mean_beta"] - table["combined_healthy_mean_beta"]
    table["tcga_tumor_vs_tcga_normal_delta"] = table["tcga_tumor_mean_beta"] - table["tcga_normal_mean_beta"]
    table["gse_tumor_vs_gse_normal_delta"] = table["gse_tumor_mean_beta"] - table["gse_normal_mean_beta"]
    table["phase3_significant_cpg"] = table["probe_id"].isin(significant_cpgs)
    return table


def summarize_sets(cpg_table: pd.DataFrame, gene_sets: Dict[str, Set[str]]) -> pd.DataFrame:
    rows = []
    mean_cols = [
        "combined_healthy_mean_beta",
        "tcga_normal_mean_beta",
        "gse_normal_mean_beta",
        "tcga_tumor_mean_beta",
        "gse_tumor_mean_beta",
        "tcga_tumor_vs_combined_healthy_delta",
        "gse_tumor_vs_combined_healthy_delta",
        "tcga_tumor_vs_tcga_normal_delta",
        "gse_tumor_vs_gse_normal_delta",
    ]
    for set_name, group in cpg_table.groupby("set_name", sort=True):
        row = {
            "set_name": set_name,
            "n_genes_in_set": len(gene_sets[set_name]),
            "n_mapped_cpgs": int(group["probe_id"].nunique()),
            "n_phase3_significant_cpgs": int(group.loc[group["phase3_significant_cpg"], "probe_id"].nunique()),
            "n_cpgs_with_gse": int(group.loc[group["gse_normal_n"].fillna(0) > 0, "probe_id"].nunique()),
            "n_cpgs_with_tcga": int(group.loc[group["tcga_normal_n"].fillna(0) > 0, "probe_id"].nunique()),
        }
        for col in mean_cols:
            row[col] = float(group.drop_duplicates("probe_id")[col].mean())
        rows.append(row)
    return pd.DataFrame(rows).sort_values("set_name")


def sanity_check_labels(out_dir: Path, gse_means: pd.DataFrame) -> pd.DataFrame:
    panel_path = out_dir / "site_maps" / "panel_balanced.tsv"
    panel = pd.read_csv(panel_path, sep="\t", low_memory=False)
    sanity = panel[["probe_id", "direction", "delta_beta", "gene_nearest", "functional_region"]].merge(
        gse_means, on="probe_id", how="left"
    )
    sanity["gse_tumor_vs_normal_delta"] = sanity["tumor_mean_beta"] - sanity["normal_mean_beta"]
    hyper_median = sanity.loc[sanity["direction"] == "hypermethylated", "gse_tumor_vs_normal_delta"].median()
    hypo_median = sanity.loc[sanity["direction"] == "hypomethylated", "gse_tumor_vs_normal_delta"].median()
    sanity["label_sanity_pass"] = (hyper_median > 0) and (hypo_median < 0)
    if not bool(sanity["label_sanity_pass"].iloc[0]):
        raise ValueError(
            f"GSE label sanity check failed: median hyper delta={hyper_median}, median hypo delta={hypo_median}"
        )
    return sanity


def write_methods(
    out_path: Path,
    labels: pd.DataFrame,
    overlap: Dict[str, int],
    set_summary: pd.DataFrame,
    sanity: pd.DataFrame,
    dropped: Dict[str, List[str]],
) -> None:
    label_counts = labels["sample_class"].value_counts().to_dict()
    hyper_median = sanity.loc[sanity["direction"] == "hypermethylated", "gse_tumor_vs_normal_delta"].median()
    hypo_median = sanity.loc[sanity["direction"] == "hypomethylated", "gse_tumor_vs_normal_delta"].median()
    top_delta = set_summary.sort_values("tcga_tumor_vs_combined_healthy_delta", ascending=False).head(8)
    bottom_delta = set_summary.sort_values("tcga_tumor_vs_combined_healthy_delta", ascending=True).head(8)

    def table_lines(df: pd.DataFrame, cols: List[str]) -> List[str]:
        lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
        for _, row in df.iterrows():
            vals = []
            for col in cols:
                val = row[col]
                if isinstance(val, float):
                    val = f"{val:.4f}"
                vals.append(str(val))
            lines.append("| " + " | ".join(vals) + " |")
        return lines

    lines = [
        "# Phase 4 - Longevity Healthy-Control Baseline",
        "",
        "## Label Verification",
        "",
        f"GSE66695 labels were parsed from `Sample_source_name_ch1`, `sample type`, `disease state`, and sample-title suffixes. All parsed label signals agreed for all `{len(labels)}` samples.",
        f"Verified counts: `{label_counts.get('normal', 0)}` normal and `{label_counts.get('tumor', 0)}` tumor.",
        f"Known-marker sanity check using the Phase 2 balanced panel passed: median GSE tumor-normal delta was `{hyper_median:.4f}` for TCGA-hypermethylated panel probes and `{hypo_median:.4f}` for TCGA-hypomethylated panel probes.",
        "",
        "## Probe Overlap",
        "",
        f"- GSE66695 matrix probes: `{overlap['gse_probe_count']}`",
        f"- Phase 0 project HM450 probes: `{overlap['project_hm450_probe_count']}`",
        f"- GSE/project overlap: `{overlap['gse_project_probe_overlap']}`",
        f"- longevity target CpGs mapped from Phase 3 gene sets: `{overlap['longevity_target_probe_count']}`",
        f"- longevity target CpGs present in GSE66695: `{overlap['gse_longevity_target_overlap']}`",
        f"- longevity target CpGs present in local TCGA matrix: `{overlap['tcga_longevity_target_overlap']}`",
        f"- longevity target CpGs with non-missing TCGA normal beta values: `{overlap['tcga_longevity_target_with_normal_beta']}`",
        f"- longevity target CpGs with non-missing TCGA tumor beta values: `{overlap['tcga_longevity_target_with_tumor_beta']}`",
        "",
        "## Dropped Samples",
        "",
        f"- GSE samples dropped for unknown or conflicting labels: `{len(dropped['gse'])}`",
        f"- TCGA manifest samples absent from the methylation matrix: `{len(dropped['tcga'])}`",
        "",
        "## Baseline Definition",
        "",
        "For each longevity-set CpG, healthy baseline beta is the non-missing sample-count-weighted mean of GSE66695 normal samples and TCGA Solid Tissue Normal samples. Tumor deltas are reported both against this combined healthy baseline and within each cohort.",
        "",
        "## Largest TCGA Tumor vs Combined-Healthy Set Deltas",
        "",
        *table_lines(top_delta, ["set_name", "n_mapped_cpgs", "combined_healthy_mean_beta", "tcga_tumor_mean_beta", "tcga_tumor_vs_combined_healthy_delta"]),
        "",
        "## Smallest TCGA Tumor vs Combined-Healthy Set Deltas",
        "",
        *table_lines(bottom_delta, ["set_name", "n_mapped_cpgs", "combined_healthy_mean_beta", "tcga_tumor_mean_beta", "tcga_tumor_vs_combined_healthy_delta"]),
        "",
        "## Batch And Interpretation Caveat",
        "",
        "GSE66695 and TCGA are both HM450 beta-value datasets, but they were generated by different studies and preprocessing pipelines. Combined healthy baselines are useful descriptive benchmarks, not batch-corrected estimates. Within-cohort deltas are included so cross-study shifts are not overinterpreted.",
    ]
    out_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--gse-series-matrix", type=Path, default=DEFAULT_GSE)
    parser.add_argument("--tcga-matrix", type=Path, default=DEFAULT_TCGA_MATRIX)
    args = parser.parse_args()

    out_dir = load_output_dir(args.config)
    phase_dir = out_dir / "longevity_baseline"
    phase_dir.mkdir(parents=True, exist_ok=True)

    labels = parse_gse_metadata(resolve_project_path(args.gse_series_matrix))
    labels.to_csv(phase_dir / "gse66695_sample_labels.tsv", sep="\t", index=False)
    gse_normals = labels.loc[labels["sample_class"] == "normal", "sample_geo_accession"].tolist()
    gse_tumors = labels.loc[labels["sample_class"] == "tumor", "sample_geo_accession"].tolist()

    mapped_cpgs, gene_sets = map_gene_sets_to_cpgs(out_dir)
    mapped_cpgs.to_csv(phase_dir / "longevity_cpg_gene_set_map.tsv", sep="\t", index=False)
    target_probes = set(mapped_cpgs["probe_id"].astype(str))
    significant = pd.read_csv(out_dir / "pathway_enrichment_longevity" / "significant_cpgs.tsv", sep="\t", usecols=["probe_id"])
    significant_cpgs = set(significant["probe_id"].astype(str))

    project_probe_ids = set(
        pd.read_csv(out_dir / "annotation" / "probe_annotation_enriched.tsv", sep="\t", usecols=["probe_id"])["probe_id"].astype(str)
    )
    overlap = count_gse_probe_overlap(resolve_project_path(args.gse_series_matrix), project_probe_ids, target_probes)

    gse_begin = find_gse_table_start(resolve_project_path(args.gse_series_matrix))
    gse_means = stream_matrix_group_means(
        resolve_project_path(args.gse_series_matrix),
        "ID_REF",
        target_probes | set(pd.read_csv(out_dir / "site_maps" / "panel_balanced.tsv", sep="\t", usecols=["probe_id"])["probe_id"].astype(str)),
        gse_normals,
        gse_tumors,
        compression="gzip",
        skiprows=gse_begin + 1,
        comment="!",
    )
    gse_means.to_csv(phase_dir / "gse66695_longevity_probe_means.tsv", sep="\t", index=False)

    manifest = load_tcga_manifest(out_dir)
    tcga_normals = manifest.loc[manifest["sample_class"] == "normal", "sample_barcode"].tolist()
    tcga_tumors = manifest.loc[manifest["sample_class"] == "tumor", "sample_barcode"].tolist()
    matrix_header = pd.read_csv(resolve_project_path(args.tcga_matrix), sep="\t", compression="gzip", nrows=0).columns.tolist()
    matrix_cols = set(matrix_header)
    dropped_tcga = sorted([sample for sample in tcga_normals + tcga_tumors if sample not in matrix_cols])
    tcga_normals = [sample for sample in tcga_normals if sample in matrix_cols]
    tcga_tumors = [sample for sample in tcga_tumors if sample in matrix_cols]
    tcga_means = stream_matrix_group_means(
        resolve_project_path(args.tcga_matrix),
        "Composite Element REF",
        target_probes,
        tcga_normals,
        tcga_tumors,
        compression="gzip",
    )
    tcga_means.to_csv(phase_dir / "tcga_longevity_probe_means.tsv", sep="\t", index=False)
    overlap["tcga_longevity_target_overlap"] = int(tcga_means["probe_id"].nunique())
    overlap["tcga_longevity_target_with_normal_beta"] = int((tcga_means["normal_n"] > 0).sum())
    overlap["tcga_longevity_target_with_tumor_beta"] = int((tcga_means["tumor_n"] > 0).sum())

    cpg_table = build_cpg_baseline_table(mapped_cpgs, gse_means, tcga_means, significant_cpgs)
    cpg_table.to_csv(phase_dir / "longevity_baseline_cpgs.tsv", sep="\t", index=False)
    set_summary = summarize_sets(cpg_table, gene_sets)
    set_summary.to_csv(phase_dir / "longevity_baseline_set_summary.tsv", sep="\t", index=False)

    sanity = sanity_check_labels(out_dir, gse_means)
    sanity.to_csv(phase_dir / "label_sanity_check.tsv", sep="\t", index=False)

    dropped = {"gse": [], "tcga": dropped_tcga}
    write_methods(phase_dir / "baseline_methods.md", labels, overlap, set_summary, sanity, dropped)
    summary = {
        "gse_label_counts": {k: int(v) for k, v in labels["sample_class"].value_counts().to_dict().items()},
        "tcga_label_counts": {"normal": int(len(tcga_normals)), "tumor": int(len(tcga_tumors))},
        "dropped_samples": {"gse": 0, "tcga": len(dropped_tcga)},
        **overlap,
        "longevity_cpg_set_rows": int(len(cpg_table)),
        "longevity_sets": int(len(gene_sets)),
        "label_sanity_median_gse_delta_hyper": float(
            sanity.loc[sanity["direction"] == "hypermethylated", "gse_tumor_vs_normal_delta"].median()
        ),
        "label_sanity_median_gse_delta_hypo": float(
            sanity.loc[sanity["direction"] == "hypomethylated", "gse_tumor_vs_normal_delta"].median()
        ),
    }
    (phase_dir / "baseline_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
