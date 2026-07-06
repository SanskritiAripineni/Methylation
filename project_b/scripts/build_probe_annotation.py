#!/usr/bin/env python3
"""Phase 0: build an enriched HM450 probe annotation with functional region + CpG-island context.

The Xena `HM450.hg38.manifest.gencode.v36.probeMap` used by the main pipeline carries only
`gene, chrom, chromStart, chromEnd, strand` -- it has no promoter/body region and no CpG-island
relation. Every downstream "hyper-methylation silences / hypo-methylation activates" claim needs
that context, because the silencing rule only holds in promoter/TSS regions (in gene bodies
hyper-methylation frequently tracks *higher* expression).

This script reads the coordinate-consistent Zhou-lab (sesame) hg38 manifest, which provides a
signed distance-to-TSS per transcript and a CpG-island position, and derives:

- `functional_region`  : TSS200 / TSS1500 / 5UTR_1stExon / gene_body / upstream_distal / intergenic
- `is_promoter`        : True if ANY transcript places the CpG in a promoter (TSS-1500 .. +500)
- `dist_to_tss`        : signed distance to the nearest TSS (negative = upstream, positive = downstream)
- `gene_nearest`       : gene of the nearest TSS
- `cgi_relation`       : Island / N_Shore / S_Shore / N_Shelf / S_Shelf / OpenSea

Sign convention (verified on cg13869341/WASH7P): negative distToTSS = upstream of the TSS
(promoter side), positive = downstream (gene-body side); strand is already accounted for in the
manifest's signed value.

Output: `<output_dir>/annotation/probe_annotation_enriched.tsv` plus a coverage summary
(`annotation_coverage.json` / `.md`) that reports how many significant probes received a region call.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"
DEFAULT_MANIFEST = "data/raw/HM450.hg38.manifest.gencode.v36.zhou.tsv.gz"

# Promoter window around the TSS, in bp. Negative = upstream. Covers TSS1500 + TSS200 and just
# into the 5'UTR/1st exon, matching the region where promoter hyper-methylation silences a gene.
PROMOTER_UPSTREAM = -1500
PROMOTER_DOWNSTREAM = 500


def resolve_project_path(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def load_output_dir(config_path: Path) -> Path:
    config = json.loads(config_path.read_text())
    return resolve_project_path(config.get("output_dir", "outputs/brca_methylation"))


def classify_region(dist_nearest) -> str:
    """Map the signed nearest-TSS distance to an Illumina-style functional region label."""
    if dist_nearest is None or pd.isna(dist_nearest):
        return "intergenic"
    d = int(dist_nearest)
    if -200 <= d <= 0:
        return "TSS200"
    if PROMOTER_UPSTREAM <= d < -200:
        return "TSS1500"
    if 0 < d <= PROMOTER_DOWNSTREAM:
        return "5UTR_1stExon"
    if d > PROMOTER_DOWNSTREAM:
        return "gene_body"
    # d < PROMOTER_UPSTREAM
    return "upstream_distal"


def parse_dist_list(raw: object) -> list[int]:
    """Parse a ';'-separated signed-int distToTSS list; drop NA / non-numeric entries."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)) or raw == "NA":
        return []
    out: list[int] = []
    for tok in str(raw).split(";"):
        tok = tok.strip()
        if tok == "" or tok == "NA":
            continue
        try:
            out.append(int(tok))
        except ValueError:
            continue
    return out


def annotate_probes(manifest: pd.DataFrame) -> pd.DataFrame:
    records = []
    for row in manifest.itertuples(index=False):
        dists = parse_dist_list(row.distToTSS)
        genes = [g.strip() for g in str(row.geneNames).split(";")] if pd.notna(row.geneNames) else []

        if dists:
            # nearest TSS = smallest absolute signed distance
            near_idx = min(range(len(dists)), key=lambda i: abs(dists[i]))
            dist_nearest = dists[near_idx]
            gene_nearest = genes[near_idx] if near_idx < len(genes) else ""
            is_promoter = any(PROMOTER_UPSTREAM <= d <= PROMOTER_DOWNSTREAM for d in dists)
        else:
            dist_nearest = None
            gene_nearest = ""
            is_promoter = False

        if not gene_nearest and pd.notna(row.genesUniq) and str(row.genesUniq) not in ("", "NA"):
            gene_nearest = str(row.genesUniq).split(";")[0].strip()

        cgi_relation = row.CGIposition
        if pd.isna(cgi_relation) or cgi_relation == "NA":
            cgi_relation = "OpenSea"

        records.append(
            {
                "probe_id": row.probeID,
                "chrom": row.CpG_chrm,
                "chromStart": row.CpG_beg,
                "chromEnd": row.CpG_end,
                "strand": row.probe_strand,
                "genes_all": "" if pd.isna(row.genesUniq) else row.genesUniq,
                "gene_nearest": gene_nearest,
                "dist_to_tss": dist_nearest,
                "functional_region": classify_region(dist_nearest),
                "is_promoter": is_promoter,
                "cgi_relation": cgi_relation,
                "cgi_id": "" if pd.isna(row.CGI) else row.CGI,
            }
        )
    return pd.DataFrame.from_records(records)


def write_coverage_report(
    annotation: pd.DataFrame,
    out_dir: Path,
    ann_dir: Path,
    fdr_threshold: float,
) -> dict:
    region_counts = annotation["functional_region"].value_counts().to_dict()
    cgi_counts = annotation["cgi_relation"].value_counts().to_dict()

    summary = {
        "manifest_probe_count": int(len(annotation)),
        "region_counts": {k: int(v) for k, v in region_counts.items()},
        "cgi_relation_counts": {k: int(v) for k, v in cgi_counts.items()},
        "promoter_probe_count": int(annotation["is_promoter"].sum()),
    }

    # Coverage against significant probes from the main differential analysis, if available.
    diff_path = out_dir / "differential_methylation.tsv"
    if diff_path.exists():
        diff = pd.read_csv(diff_path, sep="\t", usecols=["probe_id", "fdr"], low_memory=False)
        sig = diff[diff["fdr"] < fdr_threshold]
        ann_probes = set(annotation["probe_id"])
        region_ok = set(
            annotation.loc[annotation["functional_region"] != "intergenic", "probe_id"]
        )
        n_sig = int(len(sig))
        n_in_manifest = int(sig["probe_id"].isin(ann_probes).sum())
        n_region = int(sig["probe_id"].isin(region_ok).sum())
        summary["significant_probes"] = {
            "fdr_threshold": fdr_threshold,
            "n_significant": n_sig,
            "n_annotated_in_manifest": n_in_manifest,
            "n_with_region_call": n_region,
            "pct_with_region_call": round(100.0 * n_region / n_sig, 2) if n_sig else None,
        }

    (ann_dir / "annotation_coverage.json").write_text(json.dumps(summary, indent=2))

    lines = ["# Phase 0 — Enriched probe annotation coverage", ""]
    lines.append(f"- manifest probes annotated: `{summary['manifest_probe_count']}`")
    lines.append(f"- probes in a promoter (any isoform): `{summary['promoter_probe_count']}`")
    lines.append("")
    lines.append("## functional_region distribution")
    for region, count in sorted(region_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"- `{region}`: {count}")
    lines.append("")
    lines.append("## cgi_relation distribution")
    for rel, count in sorted(cgi_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"- `{rel}`: {count}")
    if "significant_probes" in summary:
        s = summary["significant_probes"]
        lines.append("")
        lines.append(f"## Significant-probe coverage (fdr < {s['fdr_threshold']})")
        lines.append(f"- significant probes: `{s['n_significant']}`")
        lines.append(f"- found in manifest: `{s['n_annotated_in_manifest']}`")
        lines.append(
            f"- with a functional-region call: `{s['n_with_region_call']}` "
            f"(`{s['pct_with_region_call']}%`)"
        )
    (ann_dir / "annotation_coverage.md").write_text("\n".join(lines) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help=f"Zhou-lab hg38 manifest tsv(.gz). Defaults to config 'probe_annotation_zhou' or {DEFAULT_MANIFEST}.",
    )
    parser.add_argument("--fdr-threshold", type=float, default=0.05)
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    manifest_path = resolve_project_path(
        args.manifest or config.get("probe_annotation_zhou", DEFAULT_MANIFEST)
    )
    if not manifest_path.exists():
        raise SystemExit(
            f"Zhou manifest not found at {manifest_path}. Download the coordinate-matched hg38 "
            "manifest (HM450.hg38.manifest.gencode.v36.tsv.gz) into data/raw/."
        )

    out_dir = load_output_dir(args.config)
    ann_dir = out_dir / "annotation"
    ann_dir.mkdir(parents=True, exist_ok=True)

    usecols = [
        "CpG_chrm", "CpG_beg", "CpG_end", "probe_strand", "probeID",
        "genesUniq", "geneNames", "distToTSS", "CGI", "CGIposition",
    ]
    manifest = pd.read_csv(manifest_path, sep="\t", usecols=usecols, low_memory=False)
    print(f"Loaded manifest: {len(manifest)} probes from {manifest_path}")

    annotation = annotate_probes(manifest)
    out_path = ann_dir / "probe_annotation_enriched.tsv"
    annotation.to_csv(out_path, sep="\t", index=False)
    print(f"Wrote {len(annotation)} annotated probes -> {out_path}")

    summary = write_coverage_report(annotation, out_dir, ann_dir, args.fdr_threshold)
    if "significant_probes" in summary:
        s = summary["significant_probes"]
        print(
            f"Significant-probe region coverage: {s['n_with_region_call']}/{s['n_significant']} "
            f"({s['pct_with_region_call']}%)"
        )


if __name__ == "__main__":
    main()
