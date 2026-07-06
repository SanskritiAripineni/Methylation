#!/usr/bin/env python3
"""Run pure-Python pathway enrichment from existing BRCA methylation outputs."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import date
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
import scipy
from scipy.stats import hypergeom


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"
COMPARISONS = ("tumor_vs_normal", "basal_vs_normal")
GENE_SET_LIBRARIES = {
    "GO_BP": "GO_Biological_Process_2023",
    "GO_MF": "GO_Molecular_Function_2023",
    "GO_CC": "GO_Cellular_Component_2023",
    "KEGG": "KEGG_2021_Human",
    "Reactome": "Reactome_2022",
}
ENRICHR_GMT_URL = "https://maayanlab.cloud/Enrichr/geneSetLibrary?mode=text&libraryName={library}"
FOCUSED_CATEGORIES = {
    "immune regulation": (r"\bimmune\b", r"\bimmun\w*", r"\bt cell\b", r"\bb cell\b", r"\blymphocyte\b", r"\bleukocyte\b"),
    "antigen presentation": (r"\bantigen\b", r"\bmhc\b", r"\bhla\b", r"\bpresentation\b"),
    "inflammation": (r"\binflamm\w*", r"\bcytokine\b", r"\binterferon\b", r"\bchemokine\b", r"\bnf-kappa\b", r"\bnfkb\b"),
    "DNA repair": (
        r"\bdna repair\b",
        r"\brepair\b",
        r"\bmismatch repair\b",
        r"\bhomologous recombination\b",
        r"\bnucleotide excision\b",
        r"\bbase excision\b",
        r"\bdouble-strand break repair\b",
    ),
    "cell cycle": (r"\bcell cycle\b", r"\bmitotic\b", r"\bcheckpoint\b", r"\bcyclin\b", r"\be2f\b"),
    "hormone/estrogen signaling": (r"\bestrogen\b", r"\bhormone\b", r"\bsteroid\b", r"\bprogesterone\b", r"\bandrogen\b"),
    "tumor-suppressor pathways": (r"\bp53\b", r"\btp53\b", r"\brb\b", r"\bretinoblastoma\b", r"\bapoptosis\b", r"\bsenescence\b"),
    "epigenetic/chromatin silencing": (r"\bchromatin\b", r"\bhistone\b", r"\bmethylation\b", r"\bepigen\w*", r"\bpolycomb\b", r"\bsilencing\b"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--min-abs-delta-beta", type=float, default=0.20)
    parser.add_argument(
        "--top-n-probes",
        type=int,
        default=None,
        help="After the FDR gate, select the top N probes by abs_delta_beta instead of using --min-abs-delta-beta.",
    )
    parser.add_argument("--fdr-threshold", type=float, default=0.05)
    parser.add_argument("--comparisons", nargs="+", default=list(COMPARISONS), choices=COMPARISONS)
    parser.add_argument("--output-name", default="pathway_enrichment", help="Subdirectory under output_dir for results.")
    return parser.parse_args()


def resolve_project_path(path_value: Union[str, Path]) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_output_dir(config_path: Path) -> Path:
    config = json.loads(config_path.read_text())
    return resolve_project_path(config.get("output_dir", "outputs/brca_methylation"))


def split_genes(value: object) -> list[str]:
    if pd.isna(value):
        return []
    genes = []
    for gene in re.split(r"[;,]", str(value)):
        gene = gene.strip()
        if gene:
            genes.append(gene)
    return genes


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    n = len(ranked)
    q = ranked * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    out = np.empty_like(q)
    out[order] = q
    return [float(x) for x in out]


def load_background_genes(out_dir: Path) -> tuple[set[str], int]:
    background = pd.read_csv(out_dir / "tumor_vs_normal" / "probe_missingness.tsv", sep="\t", low_memory=False)
    retained = background["retained"].astype(str).str.lower().isin({"true", "1", "yes"})
    retained_df = background[retained].copy()
    genes = {
        gene
        for value in retained_df["gene"]
        for gene in split_genes(value)
    }
    return genes, int(len(retained_df))


def load_significant_inputs(
    out_dir: Path,
    comparison: str,
    fdr_threshold: float,
    min_abs_delta_beta: float,
    top_n_probes: Optional[int],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, set[str]]]:
    diff = pd.read_csv(out_dir / comparison / "differential_methylation.tsv", sep="\t", low_memory=False)
    diff["fdr"] = pd.to_numeric(diff["fdr"], errors="coerce")
    diff["abs_delta_beta"] = pd.to_numeric(diff["abs_delta_beta"], errors="coerce")
    fdr_pass = diff[pd.to_numeric(diff["fdr"], errors="coerce") < fdr_threshold].copy()
    if top_n_probes is not None:
        sig = fdr_pass.sort_values(["abs_delta_beta", "fdr"], ascending=[False, True]).head(top_n_probes).copy()
    else:
        sig = fdr_pass[fdr_pass["abs_delta_beta"] >= min_abs_delta_beta].copy()

    exploded_rows = []
    for _, row in sig.iterrows():
        for gene in split_genes(row.get("gene")):
            exploded_rows.append(
                {
                    "gene": gene,
                    "direction": row["direction"],
                    "probe_id": row["probe_id"],
                    "abs_delta_beta": row["abs_delta_beta"],
                    "fdr": row["fdr"],
                }
            )
    exploded = pd.DataFrame(exploded_rows)
    if exploded.empty:
        gene_summary = pd.DataFrame(
            columns=["gene", "direction", "n_significant_probes", "n_hyper_probes", "n_hypo_probes", "probe_ids"]
        )
        gene_sets = {"combined": set(), "hypermethylated": set(), "hypomethylated": set()}
        return sig, gene_summary, gene_sets

    grouped = []
    for gene, group in exploded.groupby("gene", sort=True):
        directions = set(group["direction"])
        grouped.append(
            {
                "gene": gene,
                "direction": next(iter(directions)) if len(directions) == 1 else "mixed",
                "n_significant_probes": int(group["probe_id"].nunique()),
                "n_hyper_probes": int(group.loc[group["direction"] == "hypermethylated", "probe_id"].nunique()),
                "n_hypo_probes": int(group.loc[group["direction"] == "hypomethylated", "probe_id"].nunique()),
                "probe_ids": ",".join(sorted(group["probe_id"].astype(str).unique())),
            }
        )
    gene_summary = pd.DataFrame(grouped).sort_values(["direction", "gene"])
    gene_sets = {
        "combined": set(exploded["gene"]),
        "hypermethylated": set(exploded.loc[exploded["direction"] == "hypermethylated", "gene"]),
        "hypomethylated": set(exploded.loc[exploded["direction"] == "hypomethylated", "gene"]),
    }
    return sig, gene_summary, gene_sets


def download_gene_set_library(cache_dir: Path, library: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{library}.gmt"
    meta = cache_dir / f"{library}.metadata.json"
    if target.exists() and target.stat().st_size > 0:
        return target
    url = ENRICHR_GMT_URL.format(library=library)
    with urllib.request.urlopen(url, timeout=120) as response:
        text = response.read().decode("utf-8", errors="replace")
    target.write_text(text)
    meta.write_text(
        json.dumps(
            {
                "source": "Enrichr geneSetLibrary GMT endpoint",
                "library": library,
                "url": url,
                "download_date": date.today().isoformat(),
            },
            indent=2,
        )
    )
    return target


def parse_gmt(path: Path) -> dict[str, set[str]]:
    gene_sets = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        term = parts[0]
        genes = {gene.strip() for gene in parts[2:] if gene.strip()}
        if genes:
            gene_sets[term] = genes
    return gene_sets


def run_ora(
    query_genes: set[str],
    background_genes: set[str],
    gene_sets: dict[str, set[str]],
    direction: str,
    library_label: str,
) -> pd.DataFrame:
    query = query_genes & background_genes
    universe_size = len(background_genes)
    query_size = len(query)
    records = []
    if query_size == 0:
        return pd.DataFrame(
            columns=[
                "library",
                "direction",
                "term",
                "n_genes",
                "query_size",
                "background_size",
                "overlap_n",
                "overlap_genes",
                "p",
                "adj_p",
            ]
        )

    for term, term_genes in gene_sets.items():
        term_background = term_genes & background_genes
        if not term_background:
            continue
        overlap = sorted(query & term_background)
        overlap_n = len(overlap)
        p_value = hypergeom.sf(overlap_n - 1, universe_size, len(term_background), query_size) if overlap_n else 1.0
        records.append(
            {
                "library": library_label,
                "direction": direction,
                "term": term,
                "n_genes": int(len(term_background)),
                "query_size": int(query_size),
                "background_size": int(universe_size),
                "overlap_n": int(overlap_n),
                "overlap_genes": ",".join(overlap),
                "p": float(p_value),
            }
        )
    result = pd.DataFrame(records)
    result["adj_p"] = benjamini_hochberg(result["p"].tolist())
    return result.sort_values(["adj_p", "p", "overlap_n"], ascending=[True, True, False])


def top_terms(enrichment_tables: dict[str, pd.DataFrame], max_rows: int = 12) -> pd.DataFrame:
    frames = [df for df in enrichment_tables.values() if not df.empty]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    return combined.sort_values(["adj_p", "p", "overlap_n"], ascending=[True, True, False]).head(max_rows)


def focused_terms(enrichment_tables: dict[str, pd.DataFrame], max_rows_per_category: int = 8) -> dict[str, pd.DataFrame]:
    frames = [df for df in enrichment_tables.values() if not df.empty]
    if not frames:
        return {}
    combined = pd.concat(frames, ignore_index=True)
    combined_sig = combined[combined["adj_p"] < 0.05].copy()
    out = {}
    for category, keywords in FOCUSED_CATEGORIES.items():
        pattern = "|".join(keywords)
        matches = combined_sig[combined_sig["term"].str.lower().str.contains(pattern, regex=True, na=False)]
        if not matches.empty:
            out[category] = matches.sort_values(["adj_p", "p"]).head(max_rows_per_category)
    return out


def write_markdown_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    if df.empty:
        return ["No terms found."]
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
    comparison_dir: Path,
    comparison: str,
    sig_cpgs: pd.DataFrame,
    sig_genes: pd.DataFrame,
    gene_sets: dict[str, set[str]],
    background_genes: set[str],
    retained_probe_count: int,
    enrichment_tables: dict[str, pd.DataFrame],
    fdr_threshold: float,
    min_abs_delta_beta: float,
    top_n_probes: Optional[int],
    output_name: str,
    command: str,
) -> None:
    direction_counts = sig_cpgs["direction"].value_counts().to_dict()
    gene_direction_counts = sig_genes["direction"].value_counts().to_dict() if not sig_genes.empty else {}
    top = top_terms(enrichment_tables)
    focused = focused_terms(enrichment_tables)
    gate_text = (
        f"`fdr < {fdr_threshold}` and top `{top_n_probes}` probes by `abs_delta_beta`"
        if top_n_probes is not None
        else f"`fdr < {fdr_threshold}` and `abs_delta_beta >= {min_abs_delta_beta}`"
    )
    lines = [
        f"# Pathway Enrichment: {comparison}",
        "",
        "## Method",
        "",
        "Pure-Python over-representation analysis using one-sided hypergeometric tests.",
        "Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.",
        "P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.",
        "",
        "## Thresholds And Counts",
        "",
        f"- CpG gate: {gate_text}",
        f"- significant probes: `{len(sig_cpgs)}`",
        f"- hypermethylated significant probes: `{direction_counts.get('hypermethylated', 0)}`",
        f"- hypomethylated significant probes: `{direction_counts.get('hypomethylated', 0)}`",
        f"- significant genes, combined: `{len(gene_sets['combined'])}`",
        f"- hypermethylated genes: `{len(gene_sets['hypermethylated'])}`",
        f"- hypomethylated genes: `{len(gene_sets['hypomethylated'])}`",
        f"- gene rows with mixed direction: `{gene_direction_counts.get('mixed', 0)}`",
        f"- retained background probes: `{retained_probe_count}`",
        f"- background genes from `retained == True` probes: `{len(background_genes)}`",
        "",
        "## Top Enriched Terms Overall",
        "",
        *write_markdown_table(top, ["library", "direction", "term", "overlap_n", "p", "adj_p"]),
        "",
        "## Focused Cancer-Relevant Highlights",
        "",
    ]
    if focused:
        for category, df in focused.items():
            lines += [
                f"### {category.title()}",
                "",
                *write_markdown_table(df, ["library", "direction", "term", "overlap_n", "p", "adj_p"]),
                "",
            ]
    else:
        lines += ["No FDR-significant focused-category terms were found by keyword highlighting.", ""]
    lines += [
        "## Limitations",
        "",
        "- This is association/enrichment, not causal or clinical evidence.",
        "- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.",
        "- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.",
        "- Discovery is single-cohort TCGA-BRCA.",
    ]
    (comparison_dir / "pathway_summary.md").write_text("\n".join(lines) + "\n")

    method_lines = [
        f"# Methods: {comparison}",
        "",
        f"- command: `{command}`",
        f"- CpG threshold: {gate_text}",
        "- significant probe-to-gene mapping: split `gene` on `;` and `,`, drop empty genes, deduplicate at gene level",
        "- background definition: unique genes mapped from `tumor_vs_normal/probe_missingness.tsv` rows where `retained == True`",
        f"- retained background probes: `{retained_probe_count}`",
        f"- background genes: `{len(background_genes)}`",
        "- enrichment method: one-sided hypergeometric over-representation analysis using SciPy",
        f"- SciPy version: `{scipy.__version__}`",
        "- multiple-testing correction: Benjamini-Hochberg FDR, per library and per direction",
        "- gene-level query sets: combined, hypermethylated only, and hypomethylated only",
        f"- gene-set source: Enrichr GMT endpoint cached to `{output_name}/gene_sets/`",
        f"- gene-set libraries: `{', '.join(GENE_SET_LIBRARIES.values())}`",
        f"- gene-set library labels/version years are encoded in the Enrichr library names; cache download date is `{date.today().isoformat()}` when first retrieved",
    ]
    (comparison_dir / "methods.md").write_text("\n".join(method_lines) + "\n")


def run_comparison(
    out_dir: Path,
    pathway_dir: Path,
    comparison: str,
    background_genes: set[str],
    retained_probe_count: int,
    library_gene_sets: dict[str, dict[str, set[str]]],
    fdr_threshold: float,
    min_abs_delta_beta: float,
    top_n_probes: Optional[int],
    output_name: str,
    command: str,
) -> dict:
    comparison_dir = pathway_dir / comparison
    comparison_dir.mkdir(parents=True, exist_ok=True)
    sig_cpgs, sig_genes, query_gene_sets = load_significant_inputs(
        out_dir, comparison, fdr_threshold, min_abs_delta_beta, top_n_probes
    )
    sig_cpgs.to_csv(comparison_dir / "significant_cpgs.tsv", sep="\t", index=False)
    sig_genes.to_csv(comparison_dir / "significant_genes.tsv", sep="\t", index=False)

    enrichment_tables = {}
    for label, gene_sets in library_gene_sets.items():
        direction_frames = []
        for direction, query_genes in query_gene_sets.items():
            direction_frames.append(run_ora(query_genes, background_genes, gene_sets, direction, label))
        table = pd.concat(direction_frames, ignore_index=True) if direction_frames else pd.DataFrame()
        table = table.sort_values(["direction", "adj_p", "p", "overlap_n"], ascending=[True, True, True, False])
        table.to_csv(comparison_dir / f"enrichment_{label}.tsv", sep="\t", index=False)
        enrichment_tables[label] = table

    write_summary(
        comparison_dir,
        comparison,
        sig_cpgs,
        sig_genes,
        query_gene_sets,
        background_genes,
        retained_probe_count,
        enrichment_tables,
        fdr_threshold,
        min_abs_delta_beta,
        top_n_probes,
        output_name,
        command,
    )
    return {
        "comparison": comparison,
        "significant_probes": int(len(sig_cpgs)),
        "hypermethylated_probes": int((sig_cpgs["direction"] == "hypermethylated").sum()),
        "hypomethylated_probes": int((sig_cpgs["direction"] == "hypomethylated").sum()),
        "significant_genes": int(len(query_gene_sets["combined"])),
        "hypermethylated_genes": int(len(query_gene_sets["hypermethylated"])),
        "hypomethylated_genes": int(len(query_gene_sets["hypomethylated"])),
    }


def write_threshold_summary(pathway_dir: Path, summaries: list[dict], command: str) -> None:
    lines = [
        f"# Threshold Summary: {pathway_dir.name}",
        "",
        f"- command: `{command}`",
        "",
        "| comparison | significant probes | hyper probes | hypo probes | significant genes | hyper genes | hypo genes |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        lines.append(
            "| {comparison} | {significant_probes} | {hypermethylated_probes} | {hypomethylated_probes} | "
            "{significant_genes} | {hypermethylated_genes} | {hypomethylated_genes} |".format(**summary)
        )
    lines += ["", "## Top 15 Terms Per Library", ""]
    for summary in summaries:
        comparison = summary["comparison"]
        lines += [f"### {comparison}", ""]
        comparison_dir = pathway_dir / comparison
        top_rows = []
        for label in GENE_SET_LIBRARIES:
            table = pd.read_csv(comparison_dir / f"enrichment_{label}.tsv", sep="\t", low_memory=False)
            top = table.sort_values(["adj_p", "p", "overlap_n"], ascending=[True, True, False]).head(15).copy()
            top_rows.append(top)
            lines += [f"#### {label}", ""]
            lines += write_markdown_table(top, ["direction", "term", "overlap_n", "p", "adj_p"])
            lines.append("")
        pd.concat(top_rows, ignore_index=True).to_csv(
            comparison_dir / "top15_terms_by_library.tsv",
            sep="\t",
            index=False,
        )
    (pathway_dir / "threshold_summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    out_dir = load_output_dir(args.config)
    pathway_dir = out_dir / args.output_name
    cache_dir = pathway_dir / "gene_sets"
    pathway_dir.mkdir(parents=True, exist_ok=True)

    background_genes, retained_probe_count = load_background_genes(out_dir)
    library_gene_sets = {
        label: parse_gmt(download_gene_set_library(cache_dir, library))
        for label, library in GENE_SET_LIBRARIES.items()
    }
    command_parts = [
        "python3",
        "project_b/scripts/run_pathway_enrichment.py",
        "--config",
        str(args.config),
        "--min-abs-delta-beta",
        str(args.min_abs_delta_beta),
    ]
    if args.top_n_probes is not None:
        command_parts.extend(["--top-n-probes", str(args.top_n_probes)])
    command_parts.extend(
        [
            "--fdr-threshold",
            str(args.fdr_threshold),
            "--comparisons",
            *args.comparisons,
            "--output-name",
            args.output_name,
        ]
    )
    command = " ".join(command_parts)
    summaries = []
    for comparison in args.comparisons:
        summaries.append(
            run_comparison(
                out_dir,
                pathway_dir,
                comparison,
                background_genes,
                retained_probe_count,
                library_gene_sets,
                args.fdr_threshold,
                args.min_abs_delta_beta,
                args.top_n_probes,
                args.output_name,
                command,
            )
        )
    write_threshold_summary(pathway_dir, summaries, command)

    print(f"Background genes from retained==True probes: {len(background_genes)}")
    print(f"Retained background probes: {retained_probe_count}")
    for summary in summaries:
        print(
            "{comparison}: significant probes={significant_probes} "
            "(hyper={hypermethylated_probes}, hypo={hypomethylated_probes}); "
            "significant genes={significant_genes} "
            "(hyper={hypermethylated_genes}, hypo={hypomethylated_genes})".format(**summary)
        )


if __name__ == "__main__":
    main()
