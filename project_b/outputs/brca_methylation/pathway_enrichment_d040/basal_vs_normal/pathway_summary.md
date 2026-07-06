# Pathway Enrichment: basal_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and `abs_delta_beta >= 0.4`
- significant probes: `1016`
- hypermethylated significant probes: `753`
- hypomethylated significant probes: `263`
- significant genes, combined: `690`
- hypermethylated genes: `493`
- hypomethylated genes: `205`
- gene rows with mixed direction: `8`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 73 | 4.673e-26 | 5.360e-23 |
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 52 | 2.796e-22 | 1.604e-19 |
| GO_MF | combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 81 | 4.317e-22 | 4.951e-19 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 49 | 1.823e-21 | 5.570e-19 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 51 | 1.942e-21 | 5.570e-19 |
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 58 | 6.847e-20 | 3.927e-17 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 60 | 3.514e-19 | 8.060e-17 |
| GO_MF | hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 59 | 5.250e-19 | 1.004e-16 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 55 | 7.984e-18 | 3.052e-15 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 51 | 8.799e-17 | 2.239e-14 |
| GO_MF | combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 68 | 1.048e-16 | 2.239e-14 |
| GO_MF | combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 67 | 1.171e-16 | 2.239e-14 |

## Focused Cancer-Relevant Highlights

No FDR-significant focused-category terms were found by keyword highlighting.

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
