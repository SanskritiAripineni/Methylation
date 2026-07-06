# Pathway Enrichment: tumor_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and `abs_delta_beta >= 0.3`
- significant probes: `6717`
- hypermethylated significant probes: `3899`
- hypomethylated significant probes: `2818`
- significant genes, combined: `3796`
- hypermethylated genes: `2370`
- hypomethylated genes: `1656`
- gene rows with mixed direction: `230`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 180 | 1.973e-56 | 2.263e-53 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 173 | 2.250e-51 | 1.290e-48 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 164 | 9.779e-51 | 3.739e-48 |
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 230 | 1.336e-48 | 3.831e-46 |
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 215 | 1.782e-47 | 2.044e-44 |
| GO_BP | hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 312 | 9.068e-48 | 4.903e-44 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 209 | 1.511e-43 | 3.467e-41 |
| GO_BP | hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 291 | 5.354e-42 | 1.448e-38 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 193 | 6.922e-41 | 3.970e-38 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 203 | 1.832e-40 | 7.004e-38 |
| GO_BP | combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 407 | 4.282e-41 | 2.315e-37 |
| GO_MF | hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 197 | 1.026e-38 | 1.962e-36 |

## Focused Cancer-Relevant Highlights

### Immune Regulation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | combined | Regulation Of Immune Effector Process (GO:0002697) | 6 | 1.818e-03 | 3.131e-02 |

### Inflammation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| KEGG | hypomethylated | Inflammatory mediator regulation of TRP channels | 12 | 2.875e-03 | 4.380e-02 |

### Cell Cycle

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | combined | G1/S Transition Of Mitotic Cell Cycle (GO:0000082) | 16 | 5.615e-04 | 1.349e-02 |
| GO_BP | hypermethylated | Regulation Of Transcription Involved In G1/S Transition Of Mitotic Cell Cycle (GO:0000083) | 6 | 1.165e-03 | 2.442e-02 |
| GO_BP | hypermethylated | G1/S Transition Of Mitotic Cell Cycle (GO:0000082) | 11 | 2.435e-03 | 4.317e-02 |

### Hormone/Estrogen Signaling

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | hypermethylated | Cellular Response To Hormone Stimulus (GO:0032870) | 18 | 6.875e-05 | 2.785e-03 |
| KEGG | hypermethylated | Parathyroid hormone synthesis, secretion and action | 19 | 1.528e-04 | 2.927e-03 |
| KEGG | combined | Parathyroid hormone synthesis, secretion and action | 24 | 6.135e-04 | 7.031e-03 |
| GO_BP | combined | Cellular Response To Peptide Hormone Stimulus (GO:0071375) | 20 | 1.560e-03 | 2.858e-02 |
| GO_MF | hypermethylated | Hormone Activity (GO:0005179) | 13 | 9.467e-04 | 4.065e-02 |
| GO_BP | combined | Cellular Response To Hormone Stimulus (GO:0032870) | 20 | 2.752e-03 | 4.264e-02 |

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
