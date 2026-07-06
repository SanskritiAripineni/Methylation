# Pathway Enrichment: basal_vs_normal

## Method

Pure-Python over-representation analysis using one-sided hypergeometric tests.
Gene sets were cached from Enrichr GMT libraries, then tested locally against the retained-probe analyzable gene background.
P-values were adjusted with Benjamini-Hochberg FDR correction separately for each library and direction.

## Thresholds And Counts

- CpG gate: `fdr < 0.05` and `abs_delta_beta >= 0.2`
- significant probes: `22415`
- hypermethylated significant probes: `11015`
- hypomethylated significant probes: `11400`
- significant genes, combined: `8661`
- hypermethylated genes: `4216`
- hypomethylated genes: `5412`
- gene rows with mixed direction: `967`
- retained background probes: `382924`
- background genes from `retained == True` probes: `33010`

## Top Enriched Terms Overall

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 249 | 1.313e-59 | 1.506e-56 |
| GO_MF | hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 345 | 4.461e-58 | 1.960e-55 |
| GO_MF | hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 246 | 5.125e-58 | 1.960e-55 |
| GO_BP | hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 483 | 2.180e-58 | 1.179e-54 |
| GO_MF | hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 231 | 3.025e-56 | 8.675e-54 |
| GO_MF | hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 308 | 3.764e-49 | 8.633e-47 |
| GO_MF | hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 302 | 1.486e-48 | 2.841e-46 |
| GO_BP | hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 447 | 2.967e-49 | 8.022e-46 |
| GO_BP | combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 731 | 2.731e-40 | 1.477e-36 |
| GO_MF | combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 330 | 1.810e-39 | 2.076e-36 |
| GO_MF | combined | Double-Stranded DNA Binding (GO:0003690) | 304 | 1.845e-36 | 7.238e-34 |
| GO_MF | combined | Sequence-Specific DNA Binding (GO:0043565) | 324 | 1.893e-36 | 7.238e-34 |

## Focused Cancer-Relevant Highlights

### Immune Regulation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| Reactome | hypomethylated | Immune System R-HSA-168256 | 401 | 1.474e-12 | 5.359e-10 |
| Reactome | combined | Immune System R-HSA-168256 | 579 | 6.199e-10 | 1.024e-07 |
| Reactome | hypomethylated | Immunoregulatory Interactions Between A Lymphoid And A non-Lymphoid Cell R-HSA-198933 | 43 | 5.019e-09 | 1.014e-06 |
| Reactome | combined | Immunoregulatory Interactions Between A Lymphoid And A non-Lymphoid Cell R-HSA-198933 | 54 | 1.243e-07 | 9.823e-06 |
| GO_BP | combined | Positive Regulation Of Leukocyte Cell-Cell Adhesion (GO:1903039) | 26 | 2.064e-07 | 1.717e-05 |
| GO_BP | combined | T Cell Activation (GO:0042110) | 44 | 9.291e-07 | 6.441e-05 |
| GO_BP | combined | Positive Regulation Of Lymphocyte Activation (GO:0051251) | 26 | 1.608e-06 | 9.768e-05 |
| KEGG | combined | Leukocyte transendothelial migration | 48 | 1.440e-05 | 1.002e-04 |

### Antigen Presentation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_MF | hypomethylated | Inhibitory MHC Class I Receptor Activity (GO:0032396) | 8 | 4.337e-07 | 1.658e-04 |
| GO_MF | combined | MHC Class II Protein Complex Binding (GO:0023026) | 16 | 5.286e-06 | 2.298e-04 |
| GO_BP | combined | MHC Class II Protein Complex Assembly (GO:0002399) | 10 | 1.079e-05 | 4.524e-04 |
| GO_BP | combined | Peptide Antigen Assembly With MHC Class II Protein Complex (GO:0002503) | 10 | 1.079e-05 | 4.524e-04 |
| GO_CC | combined | MHC Class II Protein Complex (GO:0042613) | 10 | 4.965e-05 | 6.724e-04 |
| GO_MF | combined | Inhibitory MHC Class I Receptor Activity (GO:0032396) | 8 | 1.934e-05 | 6.930e-04 |
| GO_MF | combined | MHC Class II Receptor Activity (GO:0032395) | 7 | 7.511e-05 | 1.958e-03 |
| GO_CC | combined | MHC Protein Complex (GO:0042611) | 12 | 3.123e-04 | 3.021e-03 |

### Inflammation

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | hypomethylated | Positive Regulation Of Cytokine Production (GO:0001819) | 97 | 2.272e-12 | 6.142e-09 |
| GO_BP | combined | Positive Regulation Of Cytokine Production (GO:0001819) | 127 | 3.506e-10 | 7.583e-08 |
| Reactome | combined | Anti-inflammatory Response Favoring Leishmania Infection R-HSA-9662851 | 75 | 1.631e-09 | 2.118e-07 |
| Reactome | combined | ADORA2B Mediated Anti-Inflammatory Cytokine Production R-HSA-9660821 | 63 | 6.887e-09 | 7.825e-07 |
| KEGG | hypomethylated | Inflammatory bowel disease | 29 | 5.304e-09 | 8.486e-07 |
| KEGG | combined | Inflammatory bowel disease | 33 | 1.375e-06 | 1.630e-05 |
| KEGG | combined | Inflammatory mediator regulation of TRP channels | 46 | 3.481e-06 | 3.276e-05 |
| Reactome | hypermethylated | Anti-inflammatory Response Favoring Leishmania Infection R-HSA-9662851 | 43 | 4.629e-07 | 4.429e-05 |

### Cell Cycle

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| GO_BP | combined | Positive Regulation Of Cell Cycle (GO:0045787) | 27 | 9.626e-04 | 1.479e-02 |
| KEGG | combined | PD-L1 expression and PD-1 checkpoint pathway in cancer | 32 | 1.796e-02 | 3.806e-02 |
| GO_BP | combined | Positive Regulation Of Cyclin-Dependent Protein Kinase Activity (GO:1904031) | 10 | 3.924e-03 | 3.864e-02 |
| GO_BP | hypermethylated | Positive Regulation Of Cyclin-Dependent Protein Kinase Activity (GO:1904031) | 7 | 3.153e-03 | 3.965e-02 |
| GO_BP | combined | Negative Regulation Of Mitotic Nuclear Division (GO:0045839) | 6 | 4.969e-03 | 4.554e-02 |

### Hormone/Estrogen Signaling

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| KEGG | combined | Thyroid hormone signaling pathway | 53 | 3.719e-06 | 3.400e-05 |
| KEGG | combined | Growth hormone synthesis, secretion and action | 51 | 6.395e-06 | 4.991e-05 |
| KEGG | combined | Parathyroid hormone synthesis, secretion and action | 47 | 1.887e-05 | 1.258e-04 |
| KEGG | hypermethylated | Thyroid hormone signaling pathway | 32 | 1.533e-05 | 1.582e-04 |
| KEGG | combined | Estrogen signaling pathway | 57 | 2.883e-05 | 1.774e-04 |
| KEGG | hypermethylated | Parathyroid hormone synthesis, secretion and action | 29 | 3.085e-05 | 2.742e-04 |
| KEGG | combined | Progesterone-mediated oocyte maturation | 39 | 6.577e-05 | 3.395e-04 |
| KEGG | combined | Thyroid hormone synthesis | 34 | 9.854e-05 | 4.707e-04 |

### Tumor-Suppressor Pathways

| library | direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|---|
| Reactome | combined | Regulation Of TP53 Activity Thru Association With Co-factors R-HSA-6804759 | 11 | 5.365e-05 | 1.682e-03 |
| KEGG | combined | Cellular senescence | 57 | 9.256e-04 | 2.904e-03 |
| GO_BP | combined | Regulation Of Cellular Senescence (GO:2000772) | 17 | 2.068e-03 | 2.484e-02 |
| KEGG | hypermethylated | Cellular senescence | 30 | 8.597e-03 | 2.738e-02 |
| Reactome | combined | Regulation Of TP53 Expression And Degradation R-HSA-6806003 | 18 | 2.284e-03 | 3.145e-02 |
| Reactome | combined | TP53 Regulates Transcription Of Additional Cell Death Genes With Uncertain Roles In P53-Dependent Apoptosis R-HSA-6803205 | 9 | 2.694e-03 | 3.498e-02 |
| GO_BP | combined | Negative Regulation Of Cellular Senescence (GO:2000773) | 10 | 3.924e-03 | 3.864e-02 |
| KEGG | hypomethylated | Cellular senescence | 35 | 1.527e-02 | 4.699e-02 |

## Limitations

- This is association/enrichment, not causal or clinical evidence.
- 450K probe-number bias: gene-level collapse plus an analyzable retained-probe background mitigates most of it, but residual bias is not fully corrected. A full probe-number-bias correction such as `missMethyl::gometh` would require R/Bioconductor, which is intentionally avoided here.
- Probe gene mapping does not distinguish promoter from gene-body methylation; direction should be interpreted cautiously.
- Discovery is single-cohort TCGA-BRCA.
