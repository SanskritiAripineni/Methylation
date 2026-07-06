# ORA versus methylation-aware GSEA

Phase 3 ORA is kept as a baseline and compared with missMethyl probe-number-bias correction plus methylGSA/methylRRA rank-based GSEA. This file now includes both the original 14-set curated longevity collection and the supervisor antibody-array collection.

## Verdict

- Generic stem/pluripotency: partially survives, as before. `reactome_pluripotent_stem_cell_transcription` survives missMethyl; `kegg_pluripotency_stem_cell_signaling` and `go_positive_regulation_stem_cell_differentiation` survive only in undirected methylRRA.
- Generic AMPK: collapses after methylation-aware testing.
- Supervisor focus sets under missMethyl bias correction: all five collapse (`14. FGF Family; 09. IGF / Insulin Signaling; 16. Wnt Signaling; 13. TGF-beta Signaling; 15. ECM / Skin Aging`). None has missMethyl FDR < 0.05.
- Supervisor rank-based counterpoint: 14. FGF Family, 09. IGF / Insulin Signaling, 16. Wnt Signaling, 15. ECM / Skin Aging retain methylRRA support, so those remain rank-based methylation associations rather than bias-corrected over-representation hits.

These are methylation enrichment results only. They do not prove expression repression; promoter/body context must still be used before assigning a silencing or activation mechanism.

## Supervisor Arrays

The supervisor-array collection contains custom antibody/protein-array categories rather than canonical pathway definitions. Some groupings are biologically loose; for example, the telomere set includes ICAM1/2/3. Several sets are tiny and have little power, including `03. FOXO Pathway` (2 Entrez-mapped genes), `18. Circadian Clock` (2), `16. Hedgehog Signaling` (3), `10. GDF Aging Biomarkers` (3), and `11. NAD+ Metabolism` (4). Nulls for these tiny sets should not be overinterpreted.

### FGF / IGF / Wnt / TGF-beta / ECM Focus

| set | ORA p | ORA adj-p | missMethyl FDR | methylRRA hyper padj | methylRRA all padj | verdict |
|---|---:|---:|---:|---:|---:|---|
| 14. FGF Family | 5.959e-03 | 2.648e-02 | 4.992e-01 | 2.435e-01 | 1.046e-02 | collapses under missMethyl; retains methylRRA rank support |
| 09. IGF / Insulin Signaling | 4.045e-04 | 4.045e-03 | 2.770e-01 | 1.705e-01 | 2.803e-02 | collapses under missMethyl; retains methylRRA rank support |
| 16. Wnt Signaling | 1.160e-03 | 7.731e-03 | 4.203e-01 | 1.705e-01 | 1.046e-02 | collapses under missMethyl; retains methylRRA rank support |
| 13. TGF-beta Signaling | 2.523e-04 | 3.364e-03 | 4.031e-01 | 2.692e-01 | 7.013e-02 | collapses under methylation-aware testing |
| 15. ECM / Skin Aging | 1.193e-07 | 4.773e-06 | 2.075e-01 | 8.115e-05 | 9.256e-06 | collapses under missMethyl; retains methylRRA rank support |

Full supervisor-array comparison: `supervisor_arrays_gsea_vs_ora.tsv`. Combined comparison: `gsea_vs_ora.tsv`.

## Significant Supervisor Array Sets

- ORA hypermethylated: 09. IGF / Insulin Signaling, 13. TGF-beta Signaling, 14. EGF / EGFR Signaling, 14. FGF Family, 14. Neurotrophins, 14. PDGF Signaling, 15. ECM / Skin Aging, 16. Wnt Signaling, 18. Oncogenes / Tumor Suppressors
- ORA hypomethylated: 14. EGF / EGFR Signaling, 15. ECM / Skin Aging
- missMethyl hypermethylated: none
- missMethyl hypomethylated: none
- methylRRA all p-values: 02. Sirtuins, 09. IGF / Insulin Signaling, 13. BMP / GDF Signaling, 14. EGF / EGFR Signaling, 14. FGF Family, 15. ECM / Skin Aging, 16. Wnt Signaling
- methylRRA hyper-direction p-values: 15. ECM / Skin Aging
- methylRRA hypo-direction p-values: none

## Original 14-Set Longevity Collection

- ORA hypermethylated: go_positive_regulation_stem_cell_differentiation, kegg_ampk_signaling, kegg_pluripotency_stem_cell_signaling, reactome_pluripotent_stem_cell_transcription
- missMethyl hypermethylated: reactome_pluripotent_stem_cell_transcription
- methylRRA all p-values: go_positive_regulation_stem_cell_differentiation, kegg_pluripotency_stem_cell_signaling

### Original Collection Table

| term | direction | ORA adj-p | missMethyl FDR | methylRRA direction padj | methylRRA all padj | ORA sig | missMethyl sig | methylRRA all sig |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reactome_pluripotent_stem_cell_transcription | hypermethylated | 1.658e-06 | 1.186e-02 | 8.061e-02 | 1.824e-01 | True | True | False |
| go_positive_regulation_stem_cell_differentiation | hypermethylated | 1.687e-03 | 1.016e-01 | 8.061e-02 | 8.114e-03 | True | False | True |
| kegg_pluripotency_stem_cell_signaling | hypermethylated | 3.442e-07 | 1.016e-01 | 7.964e-02 | 4.451e-02 | True | False | True |
| kegg_ampk_signaling | hypermethylated | 1.136e-02 | 9.970e-01 | 2.517e-01 | 4.266e-01 | True | False | False |
| go_positive_regulation_stem_cell_differentiation | hypomethylated | 1.695e-01 | 9.960e-01 | 9.990e-01 | 8.114e-03 | False | False | True |
| kegg_pluripotency_stem_cell_signaling | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 4.451e-02 | False | False | True |
| reactome_pluripotent_stem_cell_transcription | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.824e-01 | False | False | False |
| kegg_ampk_signaling | hypomethylated | 1.289e-01 | 9.960e-01 | 9.990e-01 | 4.266e-01 | False | False | False |
| go_negative_regulation_stem_cell_differentiation | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 9.721e-01 | False | False | False |
| kegg_foxo_signaling | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | False | False | False |
| reactome_foxo_mediated_transcription | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | False | False | False |
| kegg_mtor_signaling | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | False | False | False |
| reactome_transcriptional_activation_mitochondrial_biogenesis | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | False | False | False |
| reactome_mtor_signaling | hypomethylated | 9.286e-01 | 9.960e-01 | 9.990e-01 | 1.000e+00 | False | False | False |

## Methods Caveat And References

HM450 gene-set enrichment is vulnerable to probe-number and probe-placement bias: genes represented by more CpGs are more likely to be called hit genes. The bias problem is described by Geeleher et al. 2013, Bioinformatics 29(15):1851. The missMethyl/gometh correction used here follows Phipson, Maksimovic & Oshlack 2016, Bioinformatics 32(2):286. The rank-based methylation GSEA cross-check follows the methylGSA framing from Maksimovic et al. 2021, Genome Biology 22:173.

Counterpoint: Polycomb/stem-cell target hypermethylation in cancer is real biology reported in the Ohm/Widschwendter 2007 literature, but in HM450 pathway analysis that signal is confounded with CpG-island/promoter probe-density bias. Treat surviving enrichments as hypotheses, not direct expression or causal-aging claims.
