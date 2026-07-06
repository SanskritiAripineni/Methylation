#!/usr/bin/env python3
"""Phase 2: select a biomarker panel and build site-level gene maps."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, List, Set, Union

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"

FDR_THRESHOLD = 0.05
MIN_ABS_DELTA_BETA = 0.20
PANEL_SIZE_PER_DIRECTION = 10
RAW_PANEL_SIZE = 20

ANNOTATION_MECHANICS_COLUMNS = [
    "genes_all",
    "gene_nearest",
    "dist_to_tss",
    "functional_region",
    "is_promoter",
    "cgi_relation",
    "cgi_id",
    "predicted_expression_effect",
    "mechanics_basis",
]

SITE_MAP_COLUMNS = [
    "mapped_gene",
    "selected_probe_for_gene",
    "selected_probe_id",
    "probe_id",
    "chrom",
    "chromStart",
    "chromEnd",
    "strand",
    "functional_region",
    "is_promoter",
    "promoter_via_secondary_isoform_only",
    "cgi_relation",
    "dist_to_tss",
    "direction",
    "delta_beta",
    "abs_delta_beta",
    "fdr",
    "predicted_expression_effect",
    "gene",
    "gene_nearest",
    "genes_all",
]


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
    genes = []
    for gene in re.split(r"[;,]", str(value)):
        gene = gene.strip()
        if gene and gene not in genes:
            genes.append(gene)
    return genes


def row_genes(row: pd.Series) -> List[str]:
    genes = split_genes(row.get("genes_all"))
    nearest = row.get("gene_nearest")
    if pd.notna(nearest) and str(nearest).strip() and str(nearest).strip() not in genes:
        genes.append(str(nearest).strip())
    legacy = split_genes(row.get("gene"))
    for gene in legacy:
        if gene not in genes:
            genes.append(gene)
    return genes


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def load_mechanics_table(out_dir: Path) -> pd.DataFrame:
    path = out_dir / "differential_methylation_mechanics.tsv"
    df = pd.read_csv(path, sep="\t", low_memory=False)
    required = {
        "probe_id",
        "fdr",
        "abs_delta_beta",
        "direction",
        "delta_beta",
        "functional_region",
        "is_promoter",
        "predicted_expression_effect",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    df["fdr"] = pd.to_numeric(df["fdr"], errors="coerce")
    df["abs_delta_beta"] = pd.to_numeric(df["abs_delta_beta"], errors="coerce")
    df["delta_beta"] = pd.to_numeric(df["delta_beta"], errors="coerce")
    df["is_promoter"] = bool_series(df["is_promoter"])
    return df


def gated_sites(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["fdr"] < FDR_THRESHOLD) & (df["abs_delta_beta"] >= MIN_ABS_DELTA_BETA)].copy()


def select_balanced(gated: pd.DataFrame) -> pd.DataFrame:
    promoter = gated[gated["is_promoter"]].copy()
    pieces = []
    for direction in ["hypermethylated", "hypomethylated"]:
        sub = promoter[promoter["direction"] == direction].copy()
        sub = sub.sort_values(["abs_delta_beta", "fdr", "probe_id"], ascending=[False, True, True])
        pieces.append(sub.head(PANEL_SIZE_PER_DIRECTION))
    return pd.concat(pieces, ignore_index=True)


def select_raw(gated: pd.DataFrame) -> pd.DataFrame:
    return gated.sort_values(["abs_delta_beta", "fdr", "probe_id"], ascending=[False, True, True]).head(RAW_PANEL_SIZE).copy()


def selected_gene_set(panel: pd.DataFrame) -> Set[str]:
    genes: Set[str] = set()
    for _, row in panel.iterrows():
        genes.update(row_genes(row))
    return genes


def explode_site_map_rows(gated: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    selected_genes = selected_gene_set(panel)
    selected_by_gene = {}
    for _, row in panel.iterrows():
        for gene in row_genes(row):
            selected_by_gene.setdefault(gene, []).append(row["probe_id"])

    records = []
    for _, row in gated.iterrows():
        genes = [gene for gene in row_genes(row) if gene in selected_genes]
        for gene in genes:
            record = row.to_dict()
            record["mapped_gene"] = gene
            selected_probe_ids = sorted(set(str(x) for x in selected_by_gene.get(gene, [])))
            record["selected_probe_for_gene"] = row["probe_id"] in selected_probe_ids
            record["selected_probe_id"] = ",".join(selected_probe_ids)
            record["promoter_via_secondary_isoform_only"] = bool(
                row["is_promoter"] and row.get("functional_region") == "gene_body"
            )
            records.append(record)
    if not records:
        return pd.DataFrame(columns=SITE_MAP_COLUMNS)
    site_map = pd.DataFrame(records)
    sort_cols = ["mapped_gene", "selected_probe_for_gene", "abs_delta_beta", "fdr", "probe_id"]
    site_map = site_map.sort_values(sort_cols, ascending=[True, False, False, True, True])
    return site_map[[col for col in SITE_MAP_COLUMNS if col in site_map.columns]]


def write_narrative(
    out_dir: Path,
    panel_name: str,
    panel: pd.DataFrame,
    gated: pd.DataFrame,
    site_map: pd.DataFrame,
) -> None:
    hyper_all = int((gated["direction"] == "hypermethylated").sum())
    hypo_all = int((gated["direction"] == "hypomethylated").sum())
    promoter = gated[gated["is_promoter"]]
    hyper_promoter = int((promoter["direction"] == "hypermethylated").sum())
    hypo_promoter = int((promoter["direction"] == "hypomethylated").sum())
    selected_counts = panel["direction"].value_counts().to_dict()

    selected_site_counts = (
        site_map.groupby("mapped_gene")["probe_id"].nunique().sort_values(ascending=False)
        if not site_map.empty
        else pd.Series(dtype=int)
    )
    multi_site = selected_site_counts[selected_site_counts > 1]
    lower_conf = panel[(panel["is_promoter"]) & (panel["functional_region"] == "gene_body")]

    lines = [
        f"# Phase 2 Site Maps: {panel_name}",
        "",
        "## Selection",
        "",
        f"- input: `differential_methylation_mechanics.tsv`",
        f"- initial gate: `fdr < {FDR_THRESHOLD}` and `abs_delta_beta >= {MIN_ABS_DELTA_BETA}`",
        f"- gated probes: `{len(gated)}` (`{hyper_all}` hypermethylated, `{hypo_all}` hypomethylated)",
        f"- promoter-gated probes for balanced selection: `{len(promoter)}` (`{hyper_promoter}` hypermethylated, `{hypo_promoter}` hypomethylated)",
        f"- selected panel probes: `{len(panel)}` (`{int(selected_counts.get('hypermethylated', 0))}` hypermethylated, `{int(selected_counts.get('hypomethylated', 0))}` hypomethylated)",
        "",
        "No gene deduplication was applied. Promoter status comes from Phase 0 `is_promoter`.",
        "",
        "## Multi-Site Genes",
        "",
    ]
    if multi_site.empty:
        lines.append("No selected genes had more than one gated significant CpG site.")
    else:
        lines += ["| gene | significant gated CpG sites |", "|---|---:|"]
        for gene, count in multi_site.items():
            lines.append(f"| {gene} | {int(count)} |")
    lines += ["", "## Lower-Confidence Selected CpGs", ""]
    if lower_conf.empty:
        lines.append("No selected CpGs were promoter-positive only through a secondary isoform while nearest-TSS `functional_region` was `gene_body`.")
    else:
        lines += ["| probe_id | gene_nearest | functional_region | dist_to_tss | direction | delta_beta |", "|---|---|---|---:|---|---:|"]
        for _, row in lower_conf.iterrows():
            lines.append(
                f"| {row['probe_id']} | {row.get('gene_nearest', '')} | {row.get('functional_region', '')} | "
                f"{row.get('dist_to_tss', '')} | {row.get('direction', '')} | {float(row.get('delta_beta', 0)):.3f} |"
            )
    lines += [
        "",
        "## Interpretation Guardrail",
        "",
        "The `predicted_expression_effect` labels are hypotheses from methylation mechanics, not measured RNA expression. Non-promoter sites remain ambiguous by design.",
    ]
    (out_dir / "site_maps_narrative.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--panel", choices=["balanced", "raw"], required=True)
    args = parser.parse_args()

    out_dir = load_output_dir(args.config)
    site_dir = out_dir / "site_maps"
    site_dir.mkdir(parents=True, exist_ok=True)

    df = load_mechanics_table(out_dir)
    gated = gated_sites(df)
    panel = select_balanced(gated) if args.panel == "balanced" else select_raw(gated)
    panel = panel.copy()
    panel["panel_rank"] = range(1, len(panel) + 1)
    panel["promoter_via_secondary_isoform_only"] = (
        panel["is_promoter"] & (panel["functional_region"] == "gene_body")
    )

    panel_cols = ["panel_rank"] + [col for col in panel.columns if col != "panel_rank"]
    panel.to_csv(site_dir / f"panel_{args.panel}.tsv", sep="\t", index=False, columns=panel_cols)

    site_map = explode_site_map_rows(gated, panel)
    site_map.to_csv(site_dir / f"{args.panel}_site_maps.tsv", sep="\t", index=False)
    write_narrative(site_dir, args.panel, panel, gated, site_map)

    promoter = gated[gated["is_promoter"]]
    print(f"Gated probes: {len(gated)}")
    print(f"Gated hyper/hypo: {gated['direction'].value_counts().to_dict()}")
    print(f"Promoter-gated hyper/hypo: {promoter['direction'].value_counts().to_dict()}")
    print(f"Selected {args.panel} panel: {panel['direction'].value_counts().to_dict()}")
    print(f"Selected genes: {len(selected_gene_set(panel))}")
    print(f"Site map rows: {len(site_map)}")


if __name__ == "__main__":
    main()
