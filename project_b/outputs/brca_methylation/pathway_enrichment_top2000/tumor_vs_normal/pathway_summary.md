# Pathway Enrichment: tumor_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and top `2000` probes by `abs_delta_beta`
- significant probes: `2000`
- hypermethylated significant probes: `1315`
- hypomethylated significant probes: `685`
- significant genes, combined: `1474`
- hypermethylated genes: `1045`
- hypomethylated genes: `463`
- gene rows with mixed direction: `34`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 103 | 3.898e-41 | 4.471e-38 |
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 118 | 2.324e-38 | 2.665e-35 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 94 | 3.082e-37 | 1.375e-34 |
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 129 | 3.596e-37 | 1.375e-34 |
| GO_BP | hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 170 | 6.537e-37 | 3.535e-33 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 95 | 6.472e-35 | 1.856e-32 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 104 | 3.413e-32 | 1.957e-29 |
| GO_MF | combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 147 | 5.617e-32 | 2.148e-29 |
| GO_BP | combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 200 | 3.169e-32 | 1.713e-28 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 107 | 6.684e-31 | 1.917e-28 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 113 | 8.633e-31 | 1.980e-28 |
| GO_BP | hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 154 | 1.560e-30 | 4.217e-27 |

## Focused Cancer-Relevant Highlights

### Cell Cycle

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | combined | G1/S Transition Of Mitotic Cell Cycle (GO:0000082) | 11 | 4.140e-05 | 4.763e-03 |

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
