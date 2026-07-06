#!/usr/bin/env python3
"""GSEA branch: healthy-baseline methylation atlas for the supervisor's longevity gene catalog.

For every CpG site in every gene of the longevity/anti-aging antibody-array categories, report the
ABSOLUTE methylation level in healthy tissue (TCGA Solid Tissue Normal, n=97) and classify the site
as hyper-methylated (methylated, beta>=0.70), hypo-methylated (unmethylated, beta<=0.30), or
intermediate. This is the baseline "on/off" epigenetic state of the longevity pathways in normal
tissue, with exact coordinates and promoter/body context. The tumor delta is carried alongside for
reference but the classification here is the HEALTHY state, not the tumor-vs-normal direction.

Note: TCGA "Solid Tissue Normal" is tumor-ADJACENT normal breast tissue (not disease-free donor
tissue), so treat "healthy" accordingly. Beta thresholds 0.30/0.70 are standard conventions.

Outputs (under <output_dir>/gsea/longevity_healthy_atlas/):
  - longevity_healthy_atlas_sites.tsv     (one row per gene-CpG with healthy beta + state)
  - longevity_healthy_atlas_category_summary.tsv  (per category: promoter-site state counts)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Union

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"
DEFAULT_GSE = PROJECT_ROOT / "data" / "external" / "GSE66695_series_matrix.txt.gz"
HYPER_BETA = 0.70   # methylated / "crowded" promoter
HYPO_BETA = 0.30    # unmethylated / "clear" promoter

# Focused per-category tables to break out for the supervisor's named interests.
FOCUS_CATEGORIES = [
    "01. Telomere Maintenance",
    "12. Stem Cell Regulation",
    "08. Mitochondrial Function",
    "14. FGF Family",
    "10. FGF21-FGF23-Klotho Axis",
]

# Reuse the reviewed Phase 4 GSE parsing / streaming helpers.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from build_longevity_baseline import (  # noqa: E402
    parse_gse_metadata,
    find_gse_table_start,
    stream_matrix_group_means,
)


def resolve_project_path(path_value: Union[str, Path]) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_output_dir(config_path: Path) -> Path:
    config = json.loads(config_path.read_text())
    return resolve_project_path(config.get("output_dir", "outputs/brca_methylation"))


def split_genes(value: object) -> List[str]:
    if pd.isna(value):
        return []
    out = []
    for g in re.split(r"[;,]", str(value)):
        g = g.strip()
        if g and g not in out:
            out.append(g)
    return out


def classify_state(beta: float) -> str:
    if pd.isna(beta):
        return "NA"
    if beta >= HYPER_BETA:
        return "HYPER_methylated"
    if beta <= HYPO_BETA:
        return "HYPO_unmethylated"
    return "intermediate"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--gse-series-matrix", type=Path, default=DEFAULT_GSE)
    parser.add_argument("--no-gse", action="store_true", help="Skip GSE66695; use TCGA normal only.")
    args = parser.parse_args()

    out_dir = load_output_dir(args.config)
    atlas_dir = out_dir / "gsea" / "longevity_healthy_atlas"
    atlas_dir.mkdir(parents=True, exist_ok=True)

    # Supervisor longevity catalog: gene -> categories (a gene may appear in several categories)
    cat = pd.read_csv(out_dir / "gsea" / "longevity_arrays" / "longevity_arrays_long.tsv", sep="\t")
    gene_to_cats: dict[str, set] = {}
    for _, r in cat.iterrows():
        gene_to_cats.setdefault(str(r["gene"]).strip(), set()).add(str(r["category"]).strip())
    catalog_genes = set(gene_to_cats)

    # Differential table carries the TCGA healthy baseline (normal_mean_beta) + mechanics/region cols
    d = pd.read_csv(out_dir / "differential_methylation_mechanics.tsv", sep="\t", low_memory=False)
    d["tcga_normal_beta"] = pd.to_numeric(d["normal_mean_beta"], errors="coerce")
    d["tcga_normal_n"] = pd.to_numeric(d["normal_n"], errors="coerce")

    # coordinates from Phase 0 annotation (drop any pre-existing coord cols to avoid _x/_y collision)
    d = d.drop(columns=[c for c in ["chrom", "chromStart", "chromEnd", "strand"] if c in d.columns])
    ann = pd.read_csv(
        out_dir / "annotation" / "probe_annotation_enriched.tsv",
        sep="\t", usecols=["probe_id", "chrom", "chromStart", "chromEnd", "strand"], low_memory=False,
    )
    d = d.merge(ann, on="probe_id", how="left")

    records = []
    for row in d.itertuples(index=False):
        genes = split_genes(getattr(row, "genes_all", None))
        nearest = getattr(row, "gene_nearest", None)
        if pd.notna(nearest) and str(nearest).strip() and str(nearest).strip() not in genes:
            genes.append(str(nearest).strip())
        hit = [g for g in genes if g in catalog_genes]
        if not hit:
            continue
        for gene in hit:
            for category in sorted(gene_to_cats[gene]):
                records.append({
                    "category": category,
                    "gene": gene,
                    "probe_id": row.probe_id,
                    "chrom": getattr(row, "chrom", None),
                    "chromStart": getattr(row, "chromStart", None),
                    "chromEnd": getattr(row, "chromEnd", None),
                    "strand": getattr(row, "strand", None),
                    "functional_region": getattr(row, "functional_region", None),
                    "is_promoter": getattr(row, "is_promoter", None),
                    "cgi_relation": getattr(row, "cgi_relation", None),
                    "tcga_normal_beta": row.tcga_normal_beta,
                    "tcga_normal_n": row.tcga_normal_n,
                    "tumor_direction": getattr(row, "direction", None),
                    "tumor_delta_beta": pd.to_numeric(getattr(row, "delta_beta", None), errors="coerce"),
                    "fdr": pd.to_numeric(getattr(row, "fdr", None), errors="coerce"),
                })
    atlas = pd.DataFrame.from_records(records)

    # --- Add GSE66695 healthy (normal) samples and a combined healthy baseline ---
    if not args.no_gse and resolve_project_path(args.gse_series_matrix).exists():
        gse_path = resolve_project_path(args.gse_series_matrix)
        labels = parse_gse_metadata(gse_path)
        gse_normals = labels.loc[labels["sample_class"] == "normal", "sample_geo_accession"].tolist()
        target = set(atlas["probe_id"].astype(str))
        begin = find_gse_table_start(gse_path)
        gse = stream_matrix_group_means(
            gse_path, "ID_REF", target, gse_normals, [], compression="gzip",
            skiprows=begin + 1, comment="!",
        )[["probe_id", "normal_mean_beta", "normal_n"]].rename(
            columns={"normal_mean_beta": "gse_normal_beta", "normal_n": "gse_normal_n"}
        )
        atlas = atlas.merge(gse, on="probe_id", how="left")
        print(f"GSE66695 healthy normals: {len(gse_normals)}; probes matched: {gse['probe_id'].nunique()}")
    else:
        atlas["gse_normal_beta"] = pd.NA
        atlas["gse_normal_n"] = 0

    # Combined healthy baseline = sample-count-weighted mean of TCGA-normal + GSE-normal
    tn = atlas["tcga_normal_beta"].fillna(0) * atlas["tcga_normal_n"].fillna(0)
    gn = atlas["gse_normal_beta"].fillna(0) * atlas["gse_normal_n"].fillna(0)
    denom = atlas["tcga_normal_n"].fillna(0) + atlas["gse_normal_n"].fillna(0)
    atlas["healthy_beta"] = (tn + gn) / denom.replace(0, pd.NA)
    atlas["healthy_state"] = atlas["healthy_beta"].map(classify_state)
    atlas["locus"] = (
        atlas["chrom"].astype(str) + ":"
        + atlas["chromStart"].astype("Int64").astype(str) + "-"
        + atlas["chromEnd"].astype("Int64").astype(str)
    )

    col_order = [
        "category", "gene", "probe_id", "locus", "chrom", "chromStart", "chromEnd", "strand",
        "functional_region", "is_promoter", "cgi_relation",
        "healthy_beta", "healthy_state", "tcga_normal_beta", "tcga_normal_n",
        "gse_normal_beta", "gse_normal_n",
        "tumor_direction", "tumor_delta_beta", "fdr",
    ]
    atlas = atlas[[c for c in col_order if c in atlas.columns]].sort_values(
        ["category", "gene", "is_promoter", "chromStart"], ascending=[True, True, False, True]
    )
    atlas.to_csv(atlas_dir / "longevity_healthy_atlas_sites.tsv", sep="\t", index=False)

    # --- Focused per-category tables for the supervisor's named interests ---
    focus_dir = atlas_dir / "focus_categories"
    focus_dir.mkdir(exist_ok=True)
    for category in FOCUS_CATEGORIES:
        sub = atlas[atlas["category"] == category]
        if sub.empty:
            continue
        slug = re.sub(r"[^a-z0-9]+", "_", category.lower()).strip("_")
        sub.to_csv(focus_dir / f"{slug}.tsv", sep="\t", index=False)

    # Per-category summary of PROMOTER-site healthy states (the interpretable "on/off" signal)
    prom = atlas[atlas["is_promoter"] == True]
    summ = (
        prom.groupby("category")
        .agg(
            genes=("gene", "nunique"),
            promoter_cpgs=("probe_id", "nunique"),
            hypo_unmethylated=("healthy_state", lambda s: int((s == "HYPO_unmethylated").sum())),
            intermediate=("healthy_state", lambda s: int((s == "intermediate").sum())),
            hyper_methylated=("healthy_state", lambda s: int((s == "HYPER_methylated").sum())),
        )
        .reset_index()
        .sort_values("promoter_cpgs", ascending=False)
    )
    summ.to_csv(atlas_dir / "longevity_healthy_atlas_category_summary.tsv", sep="\t", index=False)

    print(f"atlas sites: {len(atlas)} | genes covered: {atlas['gene'].nunique()}/{len(catalog_genes)} | categories: {atlas['category'].nunique()}")
    print(f"wrote -> {atlas_dir}")
    print("\nPromoter-site healthy state by category (unmethylated = 'clear/active' at baseline):")
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
