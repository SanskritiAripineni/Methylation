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
from pathlib import Path
from typing import List, Union

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"
HYPER_BETA = 0.70   # methylated / "crowded" promoter
HYPO_BETA = 0.30    # unmethylated / "clear" promoter


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

    # Differential table carries the HEALTHY baseline (normal_mean_beta) + mechanics/region columns
    d = pd.read_csv(out_dir / "differential_methylation_mechanics.tsv", sep="\t", low_memory=False)
    d["healthy_beta"] = pd.to_numeric(d["normal_mean_beta"], errors="coerce")

    # coordinates from Phase 0 annotation
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
                    "functional_region": getattr(row, "functional_region", None),
                    "is_promoter": getattr(row, "is_promoter", None),
                    "cgi_relation": getattr(row, "cgi_relation", None),
                    "healthy_beta": row.healthy_beta,
                    "healthy_state": classify_state(row.healthy_beta),
                    "tumor_direction": getattr(row, "direction", None),
                    "tumor_delta_beta": pd.to_numeric(getattr(row, "delta_beta", None), errors="coerce"),
                    "fdr": pd.to_numeric(getattr(row, "fdr", None), errors="coerce"),
                })
    atlas = pd.DataFrame.from_records(records).sort_values(
        ["category", "gene", "is_promoter", "chromStart"], ascending=[True, True, False, True]
    )
    atlas.to_csv(atlas_dir / "longevity_healthy_atlas_sites.tsv", sep="\t", index=False)

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
