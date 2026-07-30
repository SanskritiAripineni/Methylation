# Sample cohort - provenance

**The per-sample beta values in `sample_betas.tsv.gz` are simulated.** They are not
real patient measurements and must not be reported as results.

## Why
The published repository ships summary tables, not the raw 888 x 485,000 beta matrix
(that input is gitignored and lives outside the repo). A self-contained demo therefore
cannot use real per-sample values.

## Real, taken from the published outputs
- probe ids, gene symbols, chromosome and coordinates for the 500 reference probes
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
- the 2400 `sim*` background probes, which give the FDR step a realistic null
- sample identifiers (`SIM-T###`, `SIM-N###`) - no real TCGA barcode is reused
- missing values, including four low-quality samples and seventy low-quality probes
  planted so the QC filters visibly do something

## How to read a sample run
The *algorithms* are the real ones. The *numbers* are a faithful reconstruction at
n=130 rather than n=888, so effect sizes track the published values while
p-values are necessarily weaker. To get real results, switch the Load node to
`custom` and point it at the real TCGA matrix.

Seed: 20260729 (runs are reproducible)
