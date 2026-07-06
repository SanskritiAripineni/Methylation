#!/usr/bin/env python3
"""Phase 3: curated longevity gene-set ORA for BRCA methylation mechanics."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Set, Union

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_pathway_enrichment import (  # noqa: E402
    GENE_SET_LIBRARIES,
    download_gene_set_library,
    load_background_genes,
    load_output_dir,
    parse_gmt,
    run_ora,
    split_genes,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"
FDR_THRESHOLD = 0.05
MIN_ABS_DELTA_BETA = 0.20

CURATED_SET_SPECS = [
    {
        "set_name": "reactome_telomere_maintenance",
        "library_label": "Reactome",
        "library": "Reactome_2022",
        "term": "Telomere Maintenance R-HSA-157579",
        "source_db": "Reactome",
        "source_identifier": "R-HSA-157579",
        "source_url": "https://reactome.org/content/detail/R-HSA-157579",
    },
    {
        "set_name": "reactome_telomere_extension_by_telomerase",
        "library_label": "Reactome",
        "library": "Reactome_2022",
        "term": "Telomere Extension By Telomerase R-HSA-171319",
        "source_db": "Reactome",
        "source_identifier": "R-HSA-171319",
        "source_url": "https://reactome.org/content/detail/R-HSA-171319",
    },
    {
        "set_name": "reactome_mitochondrial_biogenesis",
        "library_label": "Reactome",
        "library": "Reactome_2022",
        "term": "Mitochondrial Biogenesis R-HSA-1592230",
        "source_db": "Reactome",
        "source_identifier": "R-HSA-1592230",
        "source_url": "https://reactome.org/content/detail/R-HSA-1592230",
    },
    {
        "set_name": "reactome_transcriptional_activation_mitochondrial_biogenesis",
        "library_label": "Reactome",
        "library": "Reactome_2022",
        "term": "Transcriptional Activation Of Mitochondrial Biogenesis R-HSA-2151201",
        "source_db": "Reactome",
        "source_identifier": "R-HSA-2151201",
        "source_url": "https://reactome.org/content/detail/R-HSA-2151201",
    },
    {
        "set_name": "kegg_pluripotency_stem_cell_signaling",
        "library_label": "KEGG",
        "library": "KEGG_2021_Human",
        "term": "Signaling pathways regulating pluripotency of stem cells",
        "source_db": "KEGG via Enrichr",
        "source_identifier": "KEGG_2021_Human:Signaling pathways regulating pluripotency of stem cells",
        "source_url": "https://maayanlab.cloud/Enrichr/#libraries/KEGG_2021_Human",
    },
    {
        "set_name": "reactome_pluripotent_stem_cell_transcription",
        "library_label": "Reactome",
        "library": "Reactome_2022",
        "term": "Transcriptional Regulation Of Pluripotent Stem Cells R-HSA-452723",
        "source_db": "Reactome",
        "source_identifier": "R-HSA-452723",
        "source_url": "https://reactome.org/content/detail/R-HSA-452723",
    },
    {
        "set_name": "go_positive_regulation_stem_cell_differentiation",
        "library_label": "GO_BP",
        "library": "GO_Biological_Process_2023",
        "term": "Positive Regulation Of Stem Cell Differentiation (GO:2000738)",
        "source_db": "Gene Ontology Biological Process via Enrichr",
        "source_identifier": "GO:2000738",
        "source_url": "https://amigo.geneontology.org/amigo/term/GO:2000738",
    },
    {
        "set_name": "go_negative_regulation_stem_cell_differentiation",
        "library_label": "GO_BP",
        "library": "GO_Biological_Process_2023",
        "term": "Negative Regulation Of Stem Cell Differentiation (GO:2000737)",
        "source_db": "Gene Ontology Biological Process via Enrichr",
        "source_identifier": "GO:2000737",
        "source_url": "https://amigo.geneontology.org/amigo/term/GO:2000737",
    },
    {
        "set_name": "kegg_ampk_signaling",
        "library_label": "KEGG",
        "library": "KEGG_2021_Human",
        "term": "AMPK signaling pathway",
        "source_db": "KEGG via Enrichr",
        "source_identifier": "KEGG_2021_Human:AMPK signaling pathway",
        "source_url": "https://maayanlab.cloud/Enrichr/#libraries/KEGG_2021_Human",
    },
    {
        "set_name": "kegg_foxo_signaling",
        "library_label": "KEGG",
        "library": "KEGG_2021_Human",
        "term": "FoxO signaling pathway",
        "source_db": "KEGG via Enrichr",
        "source_identifier": "KEGG_2021_Human:FoxO signaling pathway",
        "source_url": "https://maayanlab.cloud/Enrichr/#libraries/KEGG_2021_Human",
    },
    {
        "set_name": "kegg_mtor_signaling",
        "library_label": "KEGG",
        "library": "KEGG_2021_Human",
        "term": "mTOR signaling pathway",
        "source_db": "KEGG via Enrichr",
        "source_identifier": "KEGG_2021_Human:mTOR signaling pathway",
        "source_url": "https://maayanlab.cloud/Enrichr/#libraries/KEGG_2021_Human",
    },
    {
        "set_name": "reactome_mtor_signaling",
        "library_label": "Reactome",
        "library": "Reactome_2022",
        "term": "MTOR Signaling R-HSA-165159",
        "source_db": "Reactome",
        "source_identifier": "R-HSA-165159",
        "source_url": "https://reactome.org/content/detail/R-HSA-165159",
    },
    {
        "set_name": "reactome_lkb1_ampk_mtor_energy_regulation",
        "library_label": "Reactome",
        "library": "Reactome_2022",
        "term": "Energy Dependent Regulation Of mTOR By LKB1-AMPK R-HSA-380972",
        "source_db": "Reactome",
        "source_identifier": "R-HSA-380972",
        "source_url": "https://reactome.org/content/detail/R-HSA-380972",
    },
    {
        "set_name": "reactome_foxo_mediated_transcription",
        "library_label": "Reactome",
        "library": "Reactome_2022",
        "term": "FOXO-mediated Transcription R-HSA-9614085",
        "source_db": "Reactome",
        "source_identifier": "R-HSA-9614085",
        "source_url": "https://reactome.org/content/detail/R-HSA-9614085",
    },
]


def resolve_project_path(path_value: Union[str, Path]) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_libraries(cache_dir: Path) -> Dict[str, Dict[str, Set[str]]]:
    libraries = {}
    needed = sorted(set(spec["library"] for spec in CURATED_SET_SPECS))
    for library in needed:
        path = download_gene_set_library(cache_dir, library)
        libraries[library] = parse_gmt(path)
    return libraries


def curate_gene_sets(cache_dir: Path, output_dir: Path) -> Dict[str, Set[str]]:
    libraries = load_libraries(cache_dir)
    curated = {}
    provenance_rows = []
    retrieval_date = date.today().isoformat()
    for spec in CURATED_SET_SPECS:
        library_sets = libraries[spec["library"]]
        if spec["term"] not in library_sets:
            raise ValueError(f"Missing expected term {spec['term']} in {spec['library']}")
        genes = sorted(library_sets[spec["term"]])
        curated[spec["set_name"]] = set(genes)
        provenance_rows.append(
            {
                "set_name": spec["set_name"],
                "term": spec["term"],
                "source_db": spec["source_db"],
                "source_identifier": spec["source_identifier"],
                "source_url": spec["source_url"],
                "enrichr_library": spec["library"],
                "retrieval_date": retrieval_date,
                "n_genes": len(genes),
                "curation_mode": "public_gene_set_from_enrichr_gmt",
            }
        )

    gmt_lines = []
    for row in provenance_rows:
        genes = sorted(curated[row["set_name"]])
        gmt_lines.append("\t".join([row["set_name"], row["source_url"], *genes]))
    (output_dir / "longevity_gene_sets.gmt").write_text("\n".join(gmt_lines) + "\n")
    pd.DataFrame(provenance_rows).to_csv(output_dir / "longevity_gene_set_provenance.tsv", sep="\t", index=False)
    (output_dir / "longevity_gene_set_provenance.json").write_text(json.dumps(provenance_rows, indent=2) + "\n")
    return curated


def load_query_gene_sets(out_dir: Path) -> tuple[pd.DataFrame, Dict[str, Set[str]]]:
    path = out_dir / "differential_methylation_mechanics.tsv"
    df = pd.read_csv(path, sep="\t", low_memory=False)
    df["fdr"] = pd.to_numeric(df["fdr"], errors="coerce")
    df["abs_delta_beta"] = pd.to_numeric(df["abs_delta_beta"], errors="coerce")
    sig = df[(df["fdr"] < FDR_THRESHOLD) & (df["abs_delta_beta"] >= MIN_ABS_DELTA_BETA)].copy()

    gene_sets = {"hypermethylated": set(), "hypomethylated": set()}
    records = []
    for _, row in sig.iterrows():
        genes = split_genes(row.get("genes_all"))
        if not genes:
            genes = split_genes(row.get("gene"))
        nearest = row.get("gene_nearest")
        if pd.notna(nearest) and str(nearest).strip() and str(nearest).strip() not in genes:
            genes.append(str(nearest).strip())
        for gene in genes:
            direction = row["direction"]
            if direction in gene_sets:
                gene_sets[direction].add(gene)
                records.append(
                    {
                        "gene": gene,
                        "direction": direction,
                        "probe_id": row["probe_id"],
                        "abs_delta_beta": row["abs_delta_beta"],
                        "fdr": row["fdr"],
                    }
                )
    gene_rows = pd.DataFrame(records)
    if not gene_rows.empty:
        summary = (
            gene_rows.groupby(["gene", "direction"], as_index=False)
            .agg(n_probes=("probe_id", "nunique"), max_abs_delta_beta=("abs_delta_beta", "max"), min_fdr=("fdr", "min"))
            .sort_values(["direction", "gene"])
        )
    else:
        summary = pd.DataFrame(columns=["gene", "direction", "n_probes", "max_abs_delta_beta", "min_fdr"])
    return sig, {"hypermethylated": gene_sets["hypermethylated"], "hypomethylated": gene_sets["hypomethylated"]}, summary


def write_markdown_table(df: pd.DataFrame, columns: List[str]) -> List[str]:
    if df.empty:
        return ["No rows."]
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for _, row in df.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                value = f"{value:.3e}"
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_summary(
    out_path: Path,
    sig: pd.DataFrame,
    query_gene_sets: Dict[str, Set[str]],
    background_genes: Set[str],
    retained_probe_count: int,
    enrichment: pd.DataFrame,
    curated_sets: Dict[str, Set[str]],
) -> None:
    direction_counts = sig["direction"].value_counts().to_dict()
    sig_terms = enrichment[enrichment["adj_p"] < 0.05].copy()
    top = enrichment.sort_values(["adj_p", "p", "overlap_n"], ascending=[True, True, False]).head(20)

    null_sets = []
    for set_name in curated_sets:
        sub = enrichment[enrichment["term"] == set_name]
        if sub.empty or not (sub["adj_p"] < 0.05).any():
            null_sets.append(set_name)

    lines = [
        "# Phase 3 - Longevity Gene-Set ORA",
        "",
        "## Method",
        "",
        "Gene sets were selected from public Enrichr GMT libraries, cached locally, and tested with the same pure-Python one-sided hypergeometric ORA helper used by `run_pathway_enrichment.py`.",
        f"The query gate was `fdr < {FDR_THRESHOLD}` and `abs_delta_beta >= {MIN_ABS_DELTA_BETA}` on the full `differential_methylation_mechanics.tsv` table.",
        "Query genes were taken from Phase 0/1 gene annotation (`genes_all`, falling back to `gene`, with `gene_nearest` added when distinct).",
        f"Background universe: unique genes from `tumor_vs_normal/probe_missingness.tsv` rows where `retained == True`, matching the existing pathway pipeline. This gives `{len(background_genes)}` background genes from `{retained_probe_count}` retained probes.",
        "",
        "## Counts",
        "",
        f"- gated CpGs: `{len(sig)}`",
        f"- hypermethylated gated CpGs: `{int(direction_counts.get('hypermethylated', 0))}`",
        f"- hypomethylated gated CpGs: `{int(direction_counts.get('hypomethylated', 0))}`",
        f"- hypermethylated query genes before background intersection: `{len(query_gene_sets['hypermethylated'])}`",
        f"- hypomethylated query genes before background intersection: `{len(query_gene_sets['hypomethylated'])}`",
        f"- curated longevity sets: `{len(curated_sets)}`",
        "",
        "## Top ORA Results",
        "",
        *write_markdown_table(top, ["direction", "term", "n_genes", "query_size", "overlap_n", "overlap_genes", "p", "adj_p"]),
        "",
        "## Significant Results",
        "",
    ]
    if sig_terms.empty:
        lines.append("No curated longevity gene set reached `adj_p < 0.05` in either direction.")
    else:
        lines += write_markdown_table(
            sig_terms.sort_values(["direction", "adj_p", "p"]),
            ["direction", "term", "overlap_n", "overlap_genes", "p", "adj_p"],
        )
    lines += [
        "",
        "## Null Or Non-Significant Sets",
        "",
        ", ".join(null_sets) if null_sets else "Every curated set was significant in at least one direction.",
        "",
        "## Artifact And Interpretation Caveat",
        "",
        "The HM450 array is enriched for CpG-island/promoter probes and has a known neuronal/developmental probe-composition artifact that can inflate developmental and neural terms. This analysis partially controls for array composition by testing against the retained HM450 analyzable gene background rather than the whole genome, but it is not a full probe-number-bias correction such as missMethyl/gometh. Treat these enrichments as hypothesis-generating methylation associations, not causal longevity mechanisms or measured RNA-expression effects.",
    ]
    out_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    out_dir = load_output_dir(args.config)
    phase_dir = out_dir / "pathway_enrichment_longevity"
    cache_dir = phase_dir / "gene_sets"
    phase_dir.mkdir(parents=True, exist_ok=True)

    curated_sets = curate_gene_sets(cache_dir, phase_dir)
    background_genes, retained_probe_count = load_background_genes(out_dir)
    sig, query_gene_sets, query_gene_summary = load_query_gene_sets(out_dir)
    sig.to_csv(phase_dir / "significant_cpgs.tsv", sep="\t", index=False)
    query_gene_summary.to_csv(phase_dir / "significant_genes_by_direction.tsv", sep="\t", index=False)

    frames = []
    for direction in ["hypermethylated", "hypomethylated"]:
        result = run_ora(query_gene_sets[direction], background_genes, curated_sets, direction, "Longevity")
        result.to_csv(phase_dir / f"longevity_ora_{direction}.tsv", sep="\t", index=False)
        frames.append(result)
    enrichment = pd.concat(frames, ignore_index=True)
    enrichment = enrichment.sort_values(["direction", "adj_p", "p", "overlap_n"], ascending=[True, True, True, False])
    enrichment.to_csv(phase_dir / "longevity_ora_all.tsv", sep="\t", index=False)

    write_summary(
        phase_dir / "longevity_enrichment.md",
        sig,
        query_gene_sets,
        background_genes,
        retained_probe_count,
        enrichment,
        curated_sets,
    )
    summary = {
        "gated_cpgs": int(len(sig)),
        "hypermethylated_gated_cpgs": int((sig["direction"] == "hypermethylated").sum()),
        "hypomethylated_gated_cpgs": int((sig["direction"] == "hypomethylated").sum()),
        "background_genes": int(len(background_genes)),
        "retained_background_probes": int(retained_probe_count),
        "curated_gene_sets": int(len(curated_sets)),
        "significant_results_adj_p_lt_0_05": int((enrichment["adj_p"] < 0.05).sum()),
    }
    (phase_dir / "longevity_enrichment_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
