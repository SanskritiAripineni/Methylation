# ORA versus methylation-aware GSEA

Phase 3 ORA is kept as the baseline. The new columns compare that thresholded gene-list hypergeometric result with missMethyl probe-number-bias correction and methylGSA/methylRRA rank-based GSEA.

## Verdict

- Stem-cell/pluripotency: At least one ORA stem/pluripotency term remained significant after methylation-aware testing: kegg_pluripotency_stem_cell_signaling, reactome_pluripotent_stem_cell_transcription, go_positive_regulation_stem_cell_differentiation.
- Longevity families: Some longevity-family verdicts changed after bias-aware/rank testing: kegg_ampk_signaling.
- TERC/rank-based check: TERC did not surface as a leading-edge/core-enrichment gene in the curated longevity methylRRA results.

These are methylation enrichment results only. They do not prove expression repression, and promoter/body context must still be used before assigning a silencing or activation mechanism.

## Significant curated longevity sets

- ORA hypermethylated: go_positive_regulation_stem_cell_differentiation, kegg_ampk_signaling, kegg_pluripotency_stem_cell_signaling, reactome_pluripotent_stem_cell_transcription
- ORA hypomethylated: none
- missMethyl hypermethylated: reactome_pluripotent_stem_cell_transcription
- missMethyl hypomethylated: none
- methylRRA all p-values: go_positive_regulation_stem_cell_differentiation, kegg_pluripotency_stem_cell_signaling
- methylRRA hyper-direction p-values: none
- methylRRA hypo-direction p-values: none

`methylRRA all p-values` is the undirected threshold-free rank test and is repeated on both direction rows in `gsea_vs_ora.tsv`; use the hyper/hypo methylRRA columns for direction-specific rank checks.

## Comparison Table

| term | direction | ORA adj-p | missMethyl FDR | methylRRA direction padj | methylRRA all padj | ORA sig | missMethyl sig | methylRRA all sig |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reactome_pluripotent_stem_cell_transcription | hypermethylated | 1.658e-06 | 1.186e-02 | 8.061e-02 | 1.824e-01 | TRUE | TRUE | FALSE |
| go_positive_regulation_stem_cell_differentiation | hypermethylated | 1.687e-03 | 1.016e-01 | 8.061e-02 | 8.114e-03 | TRUE | FALSE | TRUE |
| kegg_pluripotency_stem_cell_signaling | hypermethylated | 3.442e-07 | 1.016e-01 | 7.964e-02 | 4.451e-02 | TRUE | FALSE | TRUE |
| kegg_ampk_signaling | hypermethylated | 1.136e-02 | 9.970e-01 | 2.517e-01 | 4.266e-01 | TRUE | FALSE | FALSE |
| go_positive_regulation_stem_cell_differentiation | hypomethylated | 1.695e-01 | 9.960e-01 | 9.990e-01 | 8.114e-03 | FALSE | FALSE | TRUE |
| kegg_pluripotency_stem_cell_signaling | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 4.451e-02 | FALSE | FALSE | TRUE |
| reactome_pluripotent_stem_cell_transcription | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.824e-01 | FALSE | FALSE | FALSE |
| kegg_ampk_signaling | hypomethylated | 1.289e-01 | 9.960e-01 | 9.990e-01 | 4.266e-01 | FALSE | FALSE | FALSE |
| go_negative_regulation_stem_cell_differentiation | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 9.721e-01 | FALSE | FALSE | FALSE |
| kegg_foxo_signaling | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | FALSE | FALSE | FALSE |
| kegg_mtor_signaling | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | FALSE | FALSE | FALSE |
| reactome_foxo_mediated_transcription | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | FALSE | FALSE | FALSE |
| reactome_lkb1_ampk_mtor_energy_regulation | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | FALSE | FALSE | FALSE |
| reactome_mitochondrial_biogenesis | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | FALSE | FALSE | FALSE |

Full per-set comparison: `gsea_vs_ora.tsv`.
