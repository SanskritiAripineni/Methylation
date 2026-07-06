# Pathway Enrichment: tumor_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and top `1000` probes by `abs_delta_beta`
- significant probes: `1000`
- hypermethylated significant probes: `718`
- hypomethylated significant probes: `282`
- significant genes, combined: `852`
- hypermethylated genes: `648`
- hypomethylated genes: `215`
- gene rows with mixed direction: `11`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 81 | 3.325e-31 | 3.814e-28 |
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 70 | 2.263e-30 | 2.483e-27 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 67 | 4.330e-30 | 2.483e-27 |
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 89 | 3.986e-29 | 1.524e-26 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 68 | 1.095e-28 | 3.140e-26 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 77 | 3.763e-28 | 2.158e-25 |
| GO_MF | combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 101 | 9.708e-28 | 3.712e-25 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 73 | 1.353e-27 | 3.880e-25 |
| GO_BP | hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 109 | 4.590e-25 | 2.482e-21 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 77 | 1.118e-23 | 2.565e-21 |
| GO_MF | combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 89 | 2.547e-23 | 5.842e-21 |
| GO_BP | combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 127 | 3.798e-24 | 2.054e-20 |

## Focused Cancer-Relevant Highlights

No FDR-significant focused-category terms were found by keyword highlighting.

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
