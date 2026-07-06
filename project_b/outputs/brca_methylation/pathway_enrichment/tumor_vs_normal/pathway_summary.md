# Pathway Enrichment: tumor_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and `abs_delta_beta >= 0.2`
- significant probes: `31083`
- hypermethylated significant probes: `16623`
- hypomethylated significant probes: `14460`
- significant genes, combined: `10956`
- hypermethylated genes: `6435`
- hypomethylated genes: `6284`
- gene rows with mixed direction: `1763`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 331 | 4.162e-70 | 4.774e-67 |
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 329 | 1.886e-68 | 1.081e-65 |
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 454 | 1.112e-60 | 4.252e-58 |
| GO_BP | hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 651 | 2.562e-61 | 1.385e-57 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 296 | 3.787e-59 | 1.086e-56 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 414 | 1.221e-54 | 2.800e-52 |
| GO_BP | hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 610 | 2.744e-53 | 7.419e-50 |
| GO_MF | hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 396 | 1.520e-49 | 2.907e-47 |
| Reactome | combined | Signal Transduction R-HSA-162582 | 1079 | 3.210e-47 | 5.835e-44 |
| Reactome | hypomethylated | Olfactory Signaling Pathway R-HSA-381753 | 161 | 1.015e-46 | 1.845e-43 |
| Reactome | hypomethylated | Expression And Translocation Of Olfactory Receptors R-HSA-9752946 | 158 | 2.533e-46 | 2.302e-43 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 395 | 8.812e-46 | 5.658e-43 |

## Focused Cancer-Relevant Highlights

### Immune Regulation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| Reactome | combined | Immune System R-HSA-168256 | 708 | 2.105e-10 | 1.664e-08 |
| Reactome | hypomethylated | Immune System R-HSA-168256 | 432 | 8.072e-10 | 1.467e-07 |
| Reactome | combined | Cytokine Signaling In Immune System R-HSA-1280215 | 263 | 9.408e-06 | 3.001e-04 |
| Reactome | hypomethylated | Immunoregulatory Interactions Between A Lymphoid And A non-Lymphoid Cell R-HSA-198933 | 40 | 5.902e-06 | 3.904e-04 |
| KEGG | combined | Leukocyte transendothelial migration | 54 | 7.317e-05 | 5.203e-04 |
| KEGG | hypermethylated | Leukocyte transendothelial migration | 37 | 1.399e-04 | 7.587e-04 |
| GO_BP | combined | Regulation Of T Cell Activation (GO:0050863) | 34 | 5.379e-05 | 1.021e-03 |
| Reactome | hypomethylated | Adaptive Immune System R-HSA-1280218 | 170 | 2.194e-05 | 1.023e-03 |

### Antigen Presentation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypomethylated | Inhibitory MHC Class I Receptor Activity (GO:0032396) | 7 | 4.664e-05 | 2.548e-03 |
| GO_CC | combined | MHC Class II Protein Complex (GO:0042613) | 10 | 4.083e-04 | 3.337e-03 |
| GO_MF | combined | MHC Class II Receptor Activity (GO:0032395) | 7 | 3.675e-04 | 6.291e-03 |
| Reactome | hypermethylated | Assembly And Cell Surface Presentation Of NMDA Receptors R-HSA-9609736 | 12 | 6.933e-04 | 1.042e-02 |
| GO_BP | combined | MHC Class II Protein Complex Assembly (GO:0002399) | 9 | 1.063e-03 | 1.168e-02 |
| GO_BP | combined | Peptide Antigen Assembly With MHC Class II Protein Complex (GO:0002503) | 9 | 1.063e-03 | 1.168e-02 |
| GO_BP | combined | Antigen Receptor-Mediated Signaling Pathway (GO:0050851) | 52 | 1.258e-03 | 1.296e-02 |
| GO_CC | hypomethylated | MHC Class II Protein Complex (GO:0042613) | 7 | 2.310e-03 | 2.234e-02 |

### Inflammation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| Reactome | combined | Anti-inflammatory Response Favoring Leishmania Infection R-HSA-9662851 | 86 | 3.325e-09 | 2.084e-07 |
| Reactome | combined | ADORA2B Mediated Anti-Inflammatory Cytokine Production R-HSA-9660821 | 73 | 4.464e-09 | 2.705e-07 |
| GO_BP | combined | Regulation Of Inflammatory Response (GO:0050727) | 113 | 3.333e-08 | 1.750e-06 |
| Reactome | hypermethylated | Anti-inflammatory Response Favoring Leishmania Infection R-HSA-9662851 | 57 | 3.453e-07 | 1.962e-05 |
| KEGG | hypermethylated | Inflammatory mediator regulation of TRP channels | 38 | 4.453e-06 | 3.562e-05 |
| KEGG | combined | Inflammatory mediator regulation of TRP channels | 52 | 1.162e-05 | 9.662e-05 |
| Reactome | hypermethylated | ADORA2B Mediated Anti-Inflammatory Cytokine Production R-HSA-9660821 | 47 | 2.348e-06 | 1.017e-04 |
| GO_BP | combined | Regulation Of Cytokine Production (GO:0001817) | 77 | 7.070e-06 | 1.829e-04 |

### Cell Cycle

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | hypermethylated | Regulation Of Mitotic Nuclear Division (GO:0007088) | 20 | 2.915e-03 | 2.297e-02 |
| GO_BP | combined | Negative Regulation Of Cell Cycle G2/M Phase Transition (GO:1902750) | 5 | 3.521e-03 | 2.759e-02 |
| GO_BP | hypermethylated | Negative Regulation Of Cell Cycle (GO:0045786) | 26 | 4.191e-03 | 3.019e-02 |
| GO_BP | combined | Regulation Of Mitotic Nuclear Division (GO:0007088) | 28 | 4.454e-03 | 3.359e-02 |

### Hormone/Estrogen Signaling

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | hypermethylated | Cellular Response To Hormone Stimulus (GO:0032870) | 39 | 2.201e-07 | 7.880e-06 |
| KEGG | hypermethylated | Parathyroid hormone synthesis, secretion and action | 41 | 2.101e-06 | 1.921e-05 |
| GO_BP | combined | Cellular Response To Hormone Stimulus (GO:0032870) | 48 | 4.317e-05 | 8.487e-04 |
| KEGG | combined | Parathyroid hormone synthesis, secretion and action | 52 | 1.827e-04 | 1.063e-03 |
| KEGG | hypermethylated | Growth hormone synthesis, secretion and action | 36 | 9.960e-04 | 3.984e-03 |
| KEGG | hypermethylated | Thyroid hormone signaling pathway | 36 | 1.977e-03 | 6.878e-03 |
| GO_BP | hypermethylated | Peptide Hormone Secretion (GO:0030072) | 12 | 6.933e-04 | 7.351e-03 |
| KEGG | combined | Growth hormone synthesis, secretion and action | 51 | 2.939e-03 | 1.033e-02 |

### Tumor-Suppressor Pathways

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| Reactome | hypermethylated | Regulation Of TP53 Activity Thru Association With Co-factors R-HSA-6804759 | 8 | 1.874e-03 | 2.213e-02 |
| KEGG | hypermethylated | Cellular senescence | 41 | 1.295e-02 | 3.396e-02 |
| GO_BP | hypermethylated | Regulation Of Cellular Senescence (GO:2000772) | 13 | 7.971e-03 | 4.887e-02 |

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
