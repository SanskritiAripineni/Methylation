"""Build the bundled sample cohort used by the 'Run sample' button.

Honesty note, repeated in data/sample/PROVENANCE.md and in every generated report:
the per-sample beta values here are SIMULATED. The published project ships summary
tables, not the raw 888-sample x 485k beta matrix, so a self-contained demo cannot
use real per-sample values.

What is real:
  * probe ids, gene symbols, chromosome + coordinates for the ~600 reference probes
    (taken from the published top-marker and candidate-panel tables),
  * their measured tumour and normal mean beta values,
  * their within-group standard deviation, back-solved from the published t-test
    p-value, delta-beta and per-group n,
  * the region / CpG-island annotation for the 100 candidate-panel probes,
  * the cohort's subtype proportions,
  * the gene-set libraries used downstream.

What is simulated:
  * every individual sample's beta value (drawn from a Beta distribution matched to
    the real per-probe group mean and standard deviation),
  * the background probes (`sim*` ids) that pad the matrix out so the multiple-testing
    correction has a realistic null to work against,
  * sample identifiers (deliberately anonymous - no real TCGA barcodes are reused).

Re-generate with:  python server/engine/make_sample_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "data" / "reference"
OUT = ROOT / "data" / "sample"

SEED = 20260729
N_TUMOR = 90
# 40 normals so the published ">=30 samples per group" marker filter still has room
# to work after QC drops the deliberately low-quality samples.
N_NORMAL = 40
N_BACKGROUND = 2400

SUBTYPE_MIX = [("LumA", 0.47), ("LumB", 0.16), ("Basal", 0.15), ("NA", 0.12),
               ("Her2", 0.05), ("Normal", 0.05)]

REGION_MIX = [("gene_body", 124800), ("5UTR_1stExon", 54500), ("TSS1500", 52400),
              ("TSS200", 47800), ("intergenic", 42300)]

CGI_MIX = [("OpenSea", 0.36), ("Island", 0.31), ("N_Shore", 0.12),
           ("S_Shore", 0.11), ("N_Shelf", 0.05), ("S_Shelf", 0.05)]

AUTOSOMES = ["chr%d" % i for i in range(1, 23)]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def back_solve_sd(delta, p_value, n_a, n_b):
    """Recover the pooled within-group SD implied by a published t-test result."""
    p = np.clip(np.asarray(p_value, dtype=float), 1e-300, 1.0)
    delta = np.abs(np.asarray(delta, dtype=float))
    n_a = np.asarray(n_a, dtype=float)
    n_b = np.asarray(n_b, dtype=float)
    df = np.maximum(n_a + n_b - 2.0, 1.0)
    t_abs = np.abs(stats.t.isf(p / 2.0, df))
    t_abs = np.where(t_abs < 1e-6, 1e-6, t_abs)
    se = delta / t_abs
    sd = se / np.sqrt(1.0 / n_a + 1.0 / n_b)
    return np.clip(sd, 0.02, 0.28)


def beta_draw(rng, means, sd):
    """Draw one beta value per requested mean, all sharing a within-group SD."""
    means = np.clip(np.atleast_1d(np.asarray(means, dtype=float)), 0.002, 0.998)
    var_cap = 0.9 * means * (1.0 - means)
    var = np.clip(sd * sd, 1e-6, var_cap)
    k = np.maximum(means * (1.0 - means) / var - 1.0, 0.05)
    a = np.maximum(means * k, 1e-3)
    b = np.maximum((1.0 - means) * k, 1e-3)
    return np.clip(rng.beta(a, b), 0.0, 1.0)


def weighted_choice(rng, pairs, size):
    labels = [p[0] for p in pairs]
    weights = np.array([float(p[1]) for p in pairs])
    weights = weights / weights.sum()
    return rng.choice(labels, size=size, p=weights)


def gene_universe():
    """Gene symbols present in the bundled GMT libraries."""
    genes = set()
    for gmt in sorted((OUT / "gene_sets").glob("*.gmt")):
        for line in gmt.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.rstrip("\n").split("\t")
            for g in parts[2:]:
                g = g.split(",")[0].strip()
                if g:
                    genes.add(g)
    return sorted(genes)


# ---------------------------------------------------------------------------
# reference probes (real statistics)
# ---------------------------------------------------------------------------

def load_reference_probes():
    frames = []
    for name in ("top_markers_abs_delta_beta.tsv", "top_hypermethylated_markers.tsv",
                 "top_hypomethylated_markers.tsv", "candidate_biomarker_panel.tsv"):
        path = REF / name
        if path.exists():
            frames.append(pd.read_csv(path, sep="\t"))
    ref = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["probe_id"])

    mech_path = REF / "candidate_biomarker_panel_mechanics.tsv"
    if mech_path.exists():
        mech = pd.read_csv(mech_path, sep="\t")
        keep = ["probe_id", "gene_nearest", "dist_to_tss", "functional_region",
                "is_promoter", "cgi_relation", "cgi_id"]
        mech = mech[[c for c in keep if c in mech.columns]]
        ref = ref.merge(mech, on="probe_id", how="left")

    ref = ref[np.isfinite(ref["delta_beta"]) & np.isfinite(ref["p_value"])].copy()
    ref["sd_within"] = back_solve_sd(ref["delta_beta"], ref["p_value"],
                                     ref["tumor_n"], ref["normal_n"])
    ref["probe_class"] = "reference_real_stats"
    return ref.reset_index(drop=True)


def build_background(rng, n, genes, taken_positions):
    """Null / weak-signal probes so FDR has a realistic null distribution."""
    probe_ids = ["sim%07d" % i for i in range(1, n + 1)]

    # 450K beta values are strongly bimodal (unmethylated or fully methylated).
    high = rng.random(n) < 0.42
    means = np.where(high, rng.beta(8.0, 1.4, size=n), rng.beta(1.4, 8.0, size=n))
    sds = np.clip(rng.lognormal(np.log(0.055), 0.55, size=n), 0.02, 0.28)

    # Real tissue comparisons contain many small true shifts, not a pure null.
    has_shift = rng.random(n) < 0.28
    shift = rng.normal(0.0, 0.055, size=n) * has_shift
    tumor_mean = np.clip(means + shift, 0.002, 0.998)
    normal_mean = means

    chrom = rng.choice(AUTOSOMES, size=n)
    sex = rng.random(n) < 0.04
    chrom = np.where(sex, rng.choice(["chrX", "chrY"], size=n), chrom)

    start = rng.integers(1_000_000, 240_000_000, size=n)
    gene = rng.choice(genes, size=n) if genes else np.array([""] * n)
    # A slice of probes is intergenic and has no gene, as on the real array.
    region = weighted_choice(rng, REGION_MIX, n)
    gene = np.where(region == "intergenic", "", gene)

    df = pd.DataFrame({
        "probe_id": probe_ids,
        "tumor_mean_beta": tumor_mean,
        "normal_mean_beta": normal_mean,
        "delta_beta": tumor_mean - normal_mean,
        "sd_within": sds,
        "gene": gene,
        "chrom": chrom,
        "chromStart": start,
        "chromEnd": start + 2,
        "strand": rng.choice(["+", "-"], size=n),
        "functional_region": region,
        "cgi_relation": weighted_choice(rng, CGI_MIX, n),
        "probe_class": "simulated_background",
    })
    df["is_promoter"] = df["functional_region"].isin(["TSS200", "TSS1500"])
    df["dist_to_tss"] = np.where(
        df["functional_region"] == "TSS200", rng.integers(-200, 1, size=n),
        np.where(df["functional_region"] == "TSS1500", rng.integers(-1500, -200, size=n),
                 np.where(df["functional_region"] == "gene_body", rng.integers(500, 40000, size=n),
                          rng.integers(-200000, 200000, size=n))))
    df["cgi_id"] = np.where(df["cgi_relation"] == "OpenSea", "",
                            ["CGI:%s:%d-%d" % (c, s - 400, s + 400)
                             for c, s in zip(df["chrom"], df["chromStart"])])
    return df


# ---------------------------------------------------------------------------
# main build
# ---------------------------------------------------------------------------

def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    ref = load_reference_probes()
    genes = gene_universe()
    bg = build_background(rng, N_BACKGROUND, genes, None)

    # --- probe table -------------------------------------------------------
    ref_slim = pd.DataFrame({
        "probe_id": ref["probe_id"],
        "tumor_mean_beta": ref["tumor_mean_beta"],
        "normal_mean_beta": ref["normal_mean_beta"],
        "delta_beta": ref["delta_beta"],
        "sd_within": ref["sd_within"],
        "gene": ref["gene"].fillna(""),
        "chrom": ref["chrom"].fillna("chr1"),
        "chromStart": ref["chromStart"].fillna(0).astype("int64"),
        "chromEnd": ref["chromEnd"].fillna(2).astype("int64"),
        "strand": ref["strand"].fillna("+"),
        "probe_class": ref["probe_class"],
    })

    n_ref = len(ref_slim)
    have_region = ref["functional_region"].notna() if "functional_region" in ref else pd.Series([False] * n_ref)
    imputed_region = weighted_choice(rng, REGION_MIX, n_ref)
    imputed_cgi = weighted_choice(rng, CGI_MIX, n_ref)

    ref_slim["functional_region"] = np.where(
        have_region, ref.get("functional_region", pd.Series([None] * n_ref)), imputed_region)
    ref_slim["cgi_relation"] = np.where(
        have_region, ref.get("cgi_relation", pd.Series([None] * n_ref)), imputed_cgi)
    ref_slim["annotation_source"] = np.where(have_region, "published_manifest", "imputed_from_region_mix")
    ref_slim["is_promoter"] = ref_slim["functional_region"].isin(["TSS200", "TSS1500"])
    ref_slim["dist_to_tss"] = np.where(
        have_region, ref.get("dist_to_tss", pd.Series([np.nan] * n_ref)).fillna(0),
        np.where(ref_slim["is_promoter"], rng.integers(-1500, 1, size=n_ref),
                 rng.integers(500, 40000, size=n_ref)))
    ref_slim["cgi_id"] = ""

    bg["annotation_source"] = "simulated"
    probes = pd.concat([ref_slim, bg], ignore_index=True)
    probes = probes.drop_duplicates(subset=["probe_id"]).reset_index(drop=True)

    # --- sample manifest ---------------------------------------------------
    tumor_ids = ["SIM-T%03d" % (i + 1) for i in range(N_TUMOR)]
    normal_ids = ["SIM-N%03d" % (i + 1) for i in range(N_NORMAL)]
    samples = tumor_ids + normal_ids
    subtypes = list(weighted_choice(rng, SUBTYPE_MIX, N_TUMOR)) + [""] * N_NORMAL
    manifest = pd.DataFrame({
        "sample_barcode": samples,
        "sample_class": ["tumor"] * N_TUMOR + ["normal"] * N_NORMAL,
        "sample_type": ["Primary Tumor"] * N_TUMOR + ["Solid Tissue Normal"] * N_NORMAL,
        "subtype": subtypes,
        "age_years": np.round(rng.normal(58.0, 12.0, size=len(samples))).clip(26, 90).astype(int),
        "gender": ["female"] * len(samples),
    })
    manifest["simulated"] = True

    # --- beta matrix -------------------------------------------------------
    # Three sample-level effects keep the cohort from separating unrealistically
    # cleanly - each one models a limitation the published caveats call out:
    #   purity     - how much of a tumour sample is actually tumour. Low-purity
    #                samples carry only part of the shift and genuinely overlap normals.
    #   field      - TCGA "normal" is tumour-adjacent tissue, so some normals already
    #                carry a fraction of the tumour signal.
    #   tech       - per-sample offset standing in for batch / array-position effects.
    # Both distributions are mixtures, because real cohorts contain a minority of
    # genuinely hard samples: low-purity tumours, and adjacent normals carrying a
    # strong field effect. Those are what stop the classifier scoring a flat 1.000.
    purity = np.clip(rng.beta(6.0, 2.0, size=N_TUMOR) * 0.55 + 0.45, 0.45, 1.0)
    low_purity = rng.random(N_TUMOR) < 0.12
    purity = np.where(low_purity, rng.uniform(0.15, 0.45, size=N_TUMOR), purity)

    field = np.clip(rng.beta(1.3, 10.0, size=N_NORMAL), 0.0, 0.35)
    heavy_field = rng.random(N_NORMAL) < 0.10
    field = np.where(heavy_field, rng.uniform(0.20, 0.45, size=N_NORMAL), field)
    tech = rng.normal(0.0, 0.018, size=len(samples))
    manifest["tumor_purity"] = np.round(np.concatenate([purity, np.full(N_NORMAL, np.nan)]), 3)
    manifest["adjacent_field_effect"] = np.round(
        np.concatenate([np.full(N_TUMOR, np.nan), field]), 3)

    n_probes = len(probes)
    mat = np.empty((n_probes, len(samples)), dtype=np.float32)
    t_mean = probes["tumor_mean_beta"].to_numpy(dtype=float)
    n_mean = probes["normal_mean_beta"].to_numpy(dtype=float)
    sd = probes["sd_within"].to_numpy(dtype=float)

    # Purity and field effect both shrink the observed gap, so the latent "pure tissue"
    # means are widened by exactly the amount they will shrink. That keeps the observed
    # group means equal to the published ones while still giving individual samples
    # realistic heterogeneity.
    #   E[tumour] = base + mean(purity)*span_pure = published tumour mean
    #   E[normal] = base + mean(field) *span_pure = published normal mean
    span_pure = (t_mean - n_mean) / (purity.mean() - field.mean())
    base = n_mean - field.mean() * span_pure

    for i in range(n_probes):
        tumour_means = base[i] + purity * span_pure[i] + tech[:N_TUMOR]
        normal_means = base[i] + field * span_pure[i] + tech[N_TUMOR:]
        mat[i, :N_TUMOR] = beta_draw(rng, tumour_means, sd[i])
        mat[i, N_TUMOR:] = beta_draw(rng, normal_means, sd[i])

    # --- realistic missingness so the QC node has real work to do ----------
    miss = rng.random(mat.shape) < 0.005                      # baseline dropout
    bad_samples = rng.choice(len(samples), size=4, replace=False)
    for s in bad_samples:                                      # samples QC should drop
        miss[:, s] |= rng.random(n_probes) < 0.38
    bad_probes = rng.choice(n_probes, size=70, replace=False)
    for p in bad_probes:                                       # probes QC should drop
        miss[p, :] |= rng.random(len(samples)) < 0.30
    mat[miss] = np.nan

    betas = pd.DataFrame(np.round(mat, 4), index=probes["probe_id"], columns=samples)
    betas.index.name = "probe_id"
    betas.to_csv(OUT / "sample_betas.tsv.gz", sep="\t", compression="gzip")
    manifest.to_csv(OUT / "sample_manifest.tsv", sep="\t", index=False)

    ann_cols = ["probe_id", "gene", "chrom", "chromStart", "chromEnd", "strand",
                "functional_region", "is_promoter", "dist_to_tss", "cgi_relation",
                "cgi_id", "probe_class", "annotation_source"]
    probes[ann_cols].to_csv(OUT / "probe_annotation.tsv", sep="\t", index=False)

    summary = {
        "seed": SEED,
        "n_probes": int(n_probes),
        "n_reference_probes_real_stats": int((probes["probe_class"] == "reference_real_stats").sum()),
        "n_simulated_background_probes": int((probes["probe_class"] == "simulated_background").sum()),
        "n_samples": len(samples),
        "n_tumor": N_TUMOR,
        "n_normal": N_NORMAL,
        "n_sex_chromosome_probes": int(probes["chrom"].isin(["chrX", "chrY"]).sum()),
        "deliberately_low_quality_samples": int(len(bad_samples)),
        "deliberately_low_quality_probes": int(len(bad_probes)),
        "per_sample_values": "SIMULATED",
        "per_probe_group_means": "REAL for reference probes, simulated for background",
    }
    (OUT / "sample_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    provenance = """# Sample cohort - provenance

**The per-sample beta values in `sample_betas.tsv.gz` are simulated.** They are not
real patient measurements and must not be reported as results.

## Why
The published repository ships summary tables, not the raw 888 x 485,000 beta matrix
(that input is gitignored and lives outside the repo). A self-contained demo therefore
cannot use real per-sample values.

## Real, taken from the published outputs
- probe ids, gene symbols, chromosome and coordinates for the {n_ref} reference probes
- their measured tumour and normal mean beta values
- their within-group SD, back-solved from the published p-value, delta-beta and group n
- region / CpG-island annotation for the 100 candidate-panel probes
- cohort subtype proportions
- the KEGG / Reactome / GO / longevity GMT libraries

## Simulated
- every individual sample value (Beta distribution matched to the real per-probe mean and SD)
- three sample-level effects that stop the cohort separating unrealistically cleanly,
  each modelling a limitation the published caveats call out:
  * **tumour purity** - a per-tumour scalar that scales the whole tumour-vs-normal
    shift, so low-purity samples genuinely overlap the normals
  * **adjacent-normal field effect** - TCGA "normal" is tumour-adjacent tissue, so a
    few normals already carry part of the tumour signal
  * **technical offset** - a small per-sample shift standing in for batch and
    array-position effects
- the {n_bg} `sim*` background probes, which give the FDR step a realistic null
- sample identifiers (`SIM-T###`, `SIM-N###`) - no real TCGA barcode is reused
- missing values, including four low-quality samples and seventy low-quality probes
  planted so the QC filters visibly do something

## How to read a sample run
The *algorithms* are the real ones. The *numbers* are a faithful reconstruction at
n={n_samples} rather than n=888, so effect sizes track the published values while
p-values are necessarily weaker. To get real results, switch the Load node to
`custom` and point it at the real TCGA matrix.

Seed: {seed} (runs are reproducible)
""".format(n_ref=summary["n_reference_probes_real_stats"],
           n_bg=summary["n_simulated_background_probes"],
           n_samples=summary["n_samples"], seed=SEED)
    (OUT / "PROVENANCE.md").write_text(provenance, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
