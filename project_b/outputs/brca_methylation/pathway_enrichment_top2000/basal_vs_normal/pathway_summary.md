# Pathway Enrichment: basal_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and top `2000` probes by `abs_delta_beta`
- significant probes: `2000`
- hypermethylated significant probes: `1393`
- hypomethylated significant probes: `607`
- significant genes, combined: `1187`
- hypermethylated genes: `762`
- hypomethylated genes: `441`
- gene rows with mixed direction: `16`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 104 | 7.172e-34 | 8.227e-31 |
| GO_MF | combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 129 | 1.404e-31 | 1.611e-28 |
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 75 | 5.532e-30 | 3.173e-27 |
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 93 | 2.541e-29 | 1.457e-26 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 72 | 1.268e-27 | 3.750e-25 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 69 | 1.308e-27 | 3.750e-25 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 88 | 3.359e-26 | 7.706e-24 |
| GO_MF | combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 112 | 1.772e-25 | 5.787e-23 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 87 | 2.520e-25 | 5.787e-23 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 83 | 2.522e-25 | 5.787e-23 |
| GO_MF | hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 85 | 5.475e-25 | 1.047e-22 |
| GO_MF | combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 109 | 1.120e-24 | 2.140e-22 |

## Focused Cancer-Relevant Highlights

No FDR-significant focused-category terms were found by keyword highlighting.

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
