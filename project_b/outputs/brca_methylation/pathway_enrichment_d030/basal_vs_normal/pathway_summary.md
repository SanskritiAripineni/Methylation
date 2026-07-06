# Pathway Enrichment: basal_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and `abs_delta_beta >= 0.3`
- significant probes: `5265`
- hypermethylated significant probes: `3232`
- hypomethylated significant probes: `2033`
- significant genes, combined: `2623`
- hypermethylated genes: `1467`
- hypomethylated genes: `1254`
- gene rows with mixed direction: `98`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 184 | 1.544e-54 | 1.771e-51 |
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 129 | 2.219e-46 | 1.272e-43 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 127 | 9.449e-45 | 3.613e-42 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 160 | 2.670e-44 | 7.655e-42 |
| GO_MF | hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 157 | 1.042e-43 | 2.389e-41 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 119 | 7.024e-43 | 1.343e-40 |
| GO_MF | combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 229 | 7.017e-41 | 8.048e-38 |
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 161 | 2.979e-38 | 1.709e-35 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 149 | 1.030e-35 | 3.937e-33 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 156 | 3.391e-35 | 9.661e-33 |
| GO_MF | combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 205 | 4.211e-35 | 9.661e-33 |
| GO_MF | combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 199 | 1.084e-33 | 2.072e-31 |

## Focused Cancer-Relevant Highlights

### Immune Regulation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| Reactome | hypomethylated | Immunoregulatory Interactions Between A Lymphoid And A non-Lymphoid Cell R-HSA-198933 | 15 | 1.708e-05 | 9.807e-03 |
| Reactome | hypomethylated | Adaptive Immune System R-HSA-1280218 | 48 | 4.570e-05 | 1.662e-02 |
| Reactome | hypomethylated | Immune System R-HSA-168256 | 99 | 1.467e-04 | 3.811e-02 |
| GO_BP | hypomethylated | Positive Regulation Of CD8-positive, Alpha-Beta T Cell Activation (GO:2001187) | 4 | 6.473e-05 | 3.889e-02 |

### Inflammation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | hypomethylated | Positive Regulation Of Cytokine Production (GO:0001819) | 31 | 5.089e-07 | 6.879e-04 |
| GO_BP | combined | Positive Regulation Of Cytokine Production (GO:0001819) | 43 | 1.164e-04 | 1.311e-02 |
| KEGG | combined | Inflammatory bowel disease | 12 | 2.270e-03 | 4.060e-02 |

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
