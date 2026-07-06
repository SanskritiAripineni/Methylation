# Pathway Enrichment: tumor_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and `abs_delta_beta >= 0.4`
- significant probes: `823`
- hypermethylated significant probes: `612`
- hypomethylated significant probes: `211`
- significant genes, combined: `721`
- hypermethylated genes: `561`
- hypomethylated genes: `169`
- gene rows with mixed direction: `9`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 68 | 4.306e-26 | 4.939e-23 |
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 59 | 4.056e-25 | 4.652e-22 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 56 | 1.610e-24 | 9.231e-22 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 57 | 1.734e-23 | 6.631e-21 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 64 | 4.180e-23 | 2.397e-20 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 60 | 3.579e-22 | 1.119e-19 |
| GO_MF | combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 83 | 3.902e-22 | 1.119e-19 |
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 72 | 5.269e-22 | 1.511e-19 |
| GO_BP | hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 92 | 1.423e-20 | 7.692e-17 |
| GO_BP | combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 107 | 2.182e-20 | 1.180e-16 |
| GO_MF | combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 73 | 1.460e-18 | 3.349e-16 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 62 | 1.004e-17 | 2.304e-15 |

## Focused Cancer-Relevant Highlights

No FDR-significant focused-category terms were found by keyword highlighting.

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
