#!/usr/bin/env python3
"""GSEA branch: parse the supervisor's longevity/anti-aging antibody-array catalog into gene sets.

Source: Longevity_AntiAging_AllBLG1-16.xlsx (1,964 protein targets across 16 SA4 antibody arrays
BLG-1..BLG-16, grouped into 40 aging/longevity biological categories). Each entry has a HGNC gene
symbol, UniProt id, and Entrez Gene ID. We use the authoritative `Full List` sheet.

These are the SUPERVISOR'S curated categories, not standard KEGG/Reactome/GO pathways, and the
source is a protein antibody-array panel. Treat the sets as custom, supervisor-defined collections
when interpreting enrichment. Entrez IDs are emitted so the methylation-aware GSEA (missMethyl
gsameth / methylGSA) can consume them directly.

Outputs (under <output_dir>/gsea/longevity_arrays/):
  - longevity_arrays_gene_sets.gmt        (category -> gene symbols)
  - longevity_arrays_entrez.tsv           (set_name, entrez ids, for R/Bioconductor collections)
  - longevity_arrays_long.tsv             (tidy: category, gene, entrez, uniprot)
  - longevity_arrays_summary.tsv          (per-category gene counts)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Union

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"
DEFAULT_XLSX = PROJECT_ROOT / "data" / "external" / "Longevity_AntiAging_AllBLG1-16.xlsx"
NON_GENE_TOKENS = {"", "-", "nan", "none"}


def resolve_project_path(path_value: Union[str, Path]) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_output_dir(config_path: Path) -> Path:
    config = json.loads(config_path.read_text())
    return resolve_project_path(config.get("output_dir", "outputs/brca_methylation"))


def parse_full_list(xlsx_path: Path) -> pd.DataFrame:
    # The real header sits on the second row (row 0 is a merged title banner).
    df = pd.read_excel(xlsx_path, sheet_name="Full List", header=1)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(
        columns={
            "Gene Symbol": "gene",
            "Gene ID": "entrez",
            "Category": "category",
            "UniProt ID": "uniprot",
            "Protein / Target Name": "target_name",
        }
    )
    df = df[["gene", "entrez", "uniprot", "category", "target_name"]].copy()
    df["gene"] = df["gene"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df = df[~df["gene"].str.lower().isin(NON_GENE_TOKENS)]
    df = df[~df["category"].str.lower().isin(NON_GENE_TOKENS)]
    # normalise entrez to a clean integer-like string where present
    def clean_entrez(v):
        s = str(v).strip()
        if s.lower() in NON_GENE_TOKENS:
            return ""
        try:
            return str(int(float(s)))
        except ValueError:
            return ""
    df["entrez"] = df["entrez"].map(clean_entrez)
    df = df.drop_duplicates(subset=["category", "gene"]).reset_index(drop=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    args = parser.parse_args()

    xlsx_path = resolve_project_path(args.xlsx)
    if not xlsx_path.exists():
        raise SystemExit(f"Longevity array catalog not found at {xlsx_path}")

    out_dir = load_output_dir(args.config) / "gsea" / "longevity_arrays"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = parse_full_list(xlsx_path)
    df.to_csv(out_dir / "longevity_arrays_long.tsv", sep="\t", index=False)

    # GMT: set_name <tab> source_tag <tab> gene1 <tab> gene2 ...
    gmt_lines, entrez_rows, summary_rows = [], [], []
    for category, grp in df.groupby("category", sort=True):
        genes = sorted(set(grp["gene"]))
        entrez = sorted({e for e in grp["entrez"] if e})
        gmt_lines.append("\t".join([category, "supervisor_curated_antibody_array_BLG1-16", *genes]))
        entrez_rows.append({"set_name": category, "n_genes": len(genes), "n_entrez": len(entrez),
                            "entrez_ids": ",".join(entrez)})
        summary_rows.append({"category": category, "n_genes": len(genes), "n_with_entrez": len(entrez)})

    (out_dir / "longevity_arrays_gene_sets.gmt").write_text("\n".join(gmt_lines) + "\n")
    pd.DataFrame(entrez_rows).to_csv(out_dir / "longevity_arrays_entrez.tsv", sep="\t", index=False)
    summary = pd.DataFrame(summary_rows).sort_values("n_genes", ascending=False)
    summary.to_csv(out_dir / "longevity_arrays_summary.tsv", sep="\t", index=False)

    print(f"source: {xlsx_path.name}")
    print(f"entries: {len(df)} | unique genes: {df['gene'].nunique()} | categories: {df['category'].nunique()}")
    print(f"wrote gene sets -> {out_dir}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
