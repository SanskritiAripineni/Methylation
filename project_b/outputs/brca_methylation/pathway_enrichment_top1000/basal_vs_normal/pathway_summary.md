# Pathway Enrichment: basal_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and top `1000` probes by `abs_delta_beta`
- significant probes: `1000`
- hypermethylated significant probes: `744`
- hypomethylated significant probes: `256`
- significant genes, combined: `676`
- hypermethylated genes: `484`
- hypomethylated genes: `200`
- gene rows with mixed direction: `8`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 72 | 7.697e-26 | 8.828e-23 |
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 51 | 7.473e-22 | 4.286e-19 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 50 | 5.164e-21 | 1.494e-18 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 48 | 5.209e-21 | 1.494e-18 |
| GO_MF | combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 79 | 1.884e-21 | 2.161e-18 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 59 | 6.463e-19 | 1.483e-16 |
| GO_MF | hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 58 | 9.851e-19 | 1.883e-16 |
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 56 | 5.981e-19 | 3.430e-16 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 53 | 6.548e-17 | 2.504e-14 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 50 | 1.734e-16 | 4.973e-14 |
| GO_MF | combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 66 | 4.745e-16 | 1.044e-13 |
| GO_MF | combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 65 | 5.459e-16 | 1.044e-13 |

## Focused Cancer-Relevant Highlights

No FDR-significant focused-category terms were found by keyword highlighting.

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
