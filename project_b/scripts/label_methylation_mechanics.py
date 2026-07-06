#!/usr/bin/env python3
"""Phase 1: label methylation mechanics from Phase 0 probe annotation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Union

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "brca_local_inputs.json"

ANNOTATION_COLUMNS = [
    "probe_id",
    "genes_all",
    "gene_nearest",
    "dist_to_tss",
    "functional_region",
    "is_promoter",
    "cgi_relation",
    "cgi_id",
]


def resolve_project_path(path: Union[str, Path]) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def load_output_dir(config_path: Path) -> Path:
    config = json.loads(config_path.read_text())
    return resolve_project_path(config.get("output_dir", "outputs/brca_methylation"))


def normalize_bool(value: object) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def label_effect(row: pd.Series) -> str:
    is_promoter = normalize_bool(row.get("is_promoter"))
    direction = str(row.get("direction", "")).strip().lower()
    if is_promoter and direction == "hypermethylated":
        return "silencing"
    if is_promoter and direction == "hypomethylated":
        return "activation"
    return "ambiguous"


def label_basis(row: pd.Series) -> str:
    if pd.isna(row.get("functional_region")):
        return "missing_phase0_annotation"
    is_promoter = normalize_bool(row.get("is_promoter"))
    direction = str(row.get("direction", "")).strip().lower()
    if is_promoter and direction == "hypermethylated":
        return "promoter_hypermethylation"
    if is_promoter and direction == "hypomethylated":
        return "promoter_hypomethylation"
    if direction not in {"hypermethylated", "hypomethylated"}:
        return "unknown_methylation_direction"
    return "non_promoter_or_intergenic"


def load_annotation(annotation_path: Path) -> pd.DataFrame:
    annotation = pd.read_csv(annotation_path, sep="\t", usecols=ANNOTATION_COLUMNS, low_memory=False)
    if annotation["probe_id"].duplicated().any():
        duplicates = annotation.loc[annotation["probe_id"].duplicated(), "probe_id"].head().tolist()
        raise ValueError(f"Phase 0 annotation has duplicate probe_id values, e.g. {duplicates}")
    return annotation


def annotate_table(input_path: Path, annotation: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    table = pd.read_csv(input_path, sep="\t", low_memory=False)
    if "probe_id" not in table.columns:
        raise ValueError(f"{input_path} has no probe_id column")
    if "direction" not in table.columns:
        raise ValueError(f"{input_path} has no direction column")

    merged = table.merge(annotation, on="probe_id", how="left", validate="many_to_one")
    merged["predicted_expression_effect"] = merged.apply(label_effect, axis=1)
    merged["mechanics_basis"] = merged.apply(label_basis, axis=1)
    merged.to_csv(output_path, sep="\t", index=False)
    return merged


def effect_counts(df: pd.DataFrame, significant_only: bool = False, top_n: int | None = None) -> dict[str, int]:
    subset = df
    if significant_only:
        subset = subset[pd.to_numeric(subset["fdr"], errors="coerce") < 0.05]
    if top_n is not None:
        subset = subset.head(top_n)
    counts = subset["predicted_expression_effect"].value_counts().to_dict()
    return {label: int(counts.get(label, 0)) for label in ["silencing", "activation", "ambiguous"]}


def write_mechanism_note(out_dir: Path, diff: pd.DataFrame, panel: pd.DataFrame, counts: dict) -> None:
    significant = diff[pd.to_numeric(diff["fdr"], errors="coerce") < 0.05]
    missing_sig = int(significant["functional_region"].isna().sum())
    missing_sig_ids = significant.loc[significant["functional_region"].isna(), "probe_id"].astype(str)
    control_missing = int(missing_sig_ids.str.startswith("ctl_").sum())

    lines = [
        "# Phase 1 - Methylation Mechanics",
        "",
        "This phase adds a conservative predicted expression-effect label using Phase 0 probe-region annotation. The rule is intentionally narrow:",
        "",
        "- promoter plus hypermethylated: `silencing`",
        "- promoter plus hypomethylated: `activation`",
        "- gene body, intergenic, distal, or unannotated probes: `ambiguous`",
        "",
        "Promoter status comes from Phase 0's `is_promoter` flag, which captures any transcript/gene TSS within the promoter window. The label is not inferred from the sparse original probeMap or from gene names.",
        "",
        "The biology caveat is central: promoter methylation can repress transcription by blocking or altering promoter-associated regulatory binding, but gene-body methylation often tracks active transcription and can have different or context-dependent effects. Therefore, this table does not assert silencing outside promoter/TSS context.",
        "",
        "These labels are hypotheses about likely expression direction, not measured RNA-expression effects.",
        "",
        "## Counts",
        "",
        "| set | silencing | activation | ambiguous |",
        "|---|---:|---:|---:|",
        (
            f"| full significant set (`fdr < 0.05`) | {counts['full_significant']['silencing']} | "
            f"{counts['full_significant']['activation']} | {counts['full_significant']['ambiguous']} |"
        ),
        (
            f"| full candidate panel (all rows) | {counts['candidate_panel_all']['silencing']} | "
            f"{counts['candidate_panel_all']['activation']} | {counts['candidate_panel_all']['ambiguous']} |"
        ),
        (
            f"| top-20 candidate panel | {counts['candidate_panel_top20']['silencing']} | "
            f"{counts['candidate_panel_top20']['activation']} | {counts['candidate_panel_top20']['ambiguous']} |"
        ),
        "",
        f"The full significant set has `{missing_sig}` rows without Phase 0 annotation; `{control_missing}` of them are `ctl_` control probes. They are labeled `ambiguous`, not assigned a biological region.",
    ]
    (out_dir / "methylation_mechanics.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    out_dir = load_output_dir(args.config)
    annotation_path = out_dir / "annotation" / "probe_annotation_enriched.tsv"
    diff_path = out_dir / "differential_methylation.tsv"
    panel_path = out_dir / "candidate_biomarker_panel.tsv"
    diff_out = out_dir / "differential_methylation_mechanics.tsv"
    panel_out = out_dir / "candidate_biomarker_panel_mechanics.tsv"

    annotation = load_annotation(annotation_path)
    diff = annotate_table(diff_path, annotation, diff_out)
    panel = annotate_table(panel_path, annotation, panel_out)

    counts = {
        "full_significant": effect_counts(diff, significant_only=True),
        "candidate_panel_all": effect_counts(panel),
        "candidate_panel_top20": effect_counts(panel, top_n=20),
    }
    (out_dir / "methylation_mechanics_counts.json").write_text(json.dumps(counts, indent=2) + "\n")
    write_mechanism_note(out_dir, diff, panel, counts)

    print(f"Wrote {diff_out}")
    print(f"Wrote {panel_out}")
    print(f"Wrote {out_dir / 'methylation_mechanics.md'}")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
