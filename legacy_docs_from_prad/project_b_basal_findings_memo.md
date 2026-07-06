# Basal vs Normal BRCA Methylation: First-Pass Findings

## Status

This memo summarizes the current `Basal vs normal` subtype comparison from the
Project B BRCA methylation pipeline.

Important scope note:

- this memo is based on the `1,000-probe smoke test`, not the full HM450 probe set
- the full `Basal vs normal` run is in progress separately

Current analysis cohort:

- `137` Basal tumors
- `97` solid tissue normal samples

## Early signal

Within the first 1,000 HM450 probes:

- `580` probes reached `FDR < 0.05`
- `43` probes showed both `FDR < 0.05` and `|delta_beta| >= 0.20`

This is a strong early indication that the subtype comparison is working and
that Basal tumors carry a clear methylation signal relative to normal breast
tissue.

## Top markers by absolute effect size

Top early CpGs include:

| probe_id | gene | delta_beta | direction | fdr |
|---|---|---:|---|---:|
| `cg00000165` | — | 0.434 | hypermethylated | 1.13e-48 |
| `cg00028935` | `ZIC1,ZIC4` | 0.429 | hypermethylated | 1.67e-66 |
| `cg00007326` | `CACNA1A` | -0.390 | hypomethylated | 1.92e-40 |
| `cg00002719` | `CCDC181` | 0.352 | hypermethylated | 3.33e-27 |
| `cg00025647` | `AC092957.1` | 0.344 | hypermethylated | 5.90e-34 |
| `cg00001583` | `NR5A2` | 0.338 | hypermethylated | 2.27e-32 |
| `cg00009292` | — | 0.327 | hypermethylated | 3.01e-28 |
| `cg00008629` | `PTBP3` | -0.323 | hypomethylated | 2.00e-38 |
| `cg00036011` | `H2BC10,H3C8` | 0.319 | hypermethylated | 6.44e-22 |
| `cg00017489` | `DPP6` | 0.314 | hypermethylated | 5.66e-29 |

## Most hypermethylated early hits

The strongest early hypermethylated markers include:

- `ZIC1/ZIC4`
- `CCDC181`
- `NR5A2`
- `DPP6`
- `PANTR1`

These are useful candidates for follow-up because they combine large effect
sizes with very small adjusted p-values in the subset run.

## Most hypomethylated early hits

The strongest early hypomethylated markers include:

- `CACNA1A`
- `PTBP3`
- `DEPDC7`
- `CDH8`
- `PTPRN2`
- `GALNT9`
- `DLGAP2`
- `ETV6`

This gives us a balanced early panel rather than only one-direction changes.

## Practical interpretation

The first-pass Basal comparison already suggests:

1. Basal tumors separate from normal tissue at the methylation level
2. the pipeline is detecting both hypermethylated and hypomethylated CpGs
3. we should wait for the full HM450 run before deciding which markers deserve
   to become the first formal candidate panel

## Next actions

1. Finish the full `Basal vs normal` HM450 run
2. Re-rank markers across the complete probe set
3. Run `LumA vs normal` as the next subtype baseline
4. Compare whether early Basal hits remain Basal-specific or also appear in
   LumA
