# Biological Interpretation

Input enrichment run: `outputs/brca_methylation/pathway_enrichment_top2000/`.

This interpretation is association-only. It summarizes enriched gene-set patterns from methylation-associated genes and does not establish causality, clinical utility, or direct gene regulation.

## Canonical Enrichment Setting

The canonical query uses `fdr < 0.05`, then selects the top `2000` probes by `abs_delta_beta`.

- `tumor_vs_normal`: `1474` unique query genes; `1045` hypermethylated genes; `463` hypomethylated genes.
- `basal_vs_normal`: `1187` unique query genes; `762` hypermethylated genes; `441` hypomethylated genes.
- Background: `33010` unique genes from `382924` probes where `retained == True`.

## Tumor-Vs-Normal Interpretation

### Hypermethylated Gene Set

The tumor-vs-normal hypermethylated query is strongly associated with transcriptional regulatory biology, which is consistent with methylation changes intersecting regulatory genes rather than random genomic background. This is supported by `Regulation Of Transcription By RNA Polymerase II (GO:0006357)`, hypermethylated direction, `adj_p = 3.535e-33`, and `Regulation Of DNA-templated Transcription (GO:0006355)`, hypermethylated direction, `adj_p = 4.217e-27` in `tumor_vs_normal/enrichment_GO_BP.tsv`.

The hypermethylated set also intersects a cancer-annotated transcriptional program: `Transcriptional misregulation in cancer`, hypermethylated direction, `adj_p = 2.007e-03`, in `tumor_vs_normal/enrichment_KEGG.tsv`. This supports an association with cancer transcriptional regulation, not proof of silencing or driver status.

Cell-cycle control appears in the combined tumor-vs-normal query through `G1/S Transition Of Mitotic Cell Cycle (GO:0000082)`, combined direction, `adj_p = 4.763e-03`, in `tumor_vs_normal/enrichment_GO_BP.tsv`. Because the significant row is combined rather than hypermethylated-only, the result supports a methylation-associated cell-cycle signal but not a direction-specific silencing claim.

MicroRNA-related cancer annotation is present in the hypermethylated query: `MicroRNAs in cancer`, hypermethylated direction, `adj_p = 2.406e-02`, in `tumor_vs_normal/enrichment_KEGG.tsv`. This supports an association between hypermethylated CpG-linked genes and cancer microRNA pathway annotations.

### Hypomethylated Gene Set

The tumor-vs-normal hypomethylated query is associated with signaling terms. `MAPK signaling pathway`, hypomethylated direction, is significant with `adj_p = 1.680e-03` in `tumor_vs_normal/enrichment_KEGG.tsv`. Interpreted cautiously, this is compatible with a de-repression/activation-oriented methylation pattern in signaling genes, but methylation location is not promoter-resolved here.

The hypomethylated query also intersects `Tight junction`, hypomethylated direction, `adj_p = 9.287e-03`, in `tumor_vs_normal/enrichment_KEGG.tsv`. This supports an association with epithelial junction/cell-organization biology. It does not prove altered barrier function.

The hypomethylated-only rows are also enriched for neuronal/sensory annotations, including `Neuronal System R-HSA-112316`, hypomethylated direction, `adj_p = 7.352e-03`, in `tumor_vs_normal/enrichment_Reactome.tsv`, and olfactory/sensory terms in `tumor_vs_normal/enrichment_GO_BP.tsv` and `tumor_vs_normal/enrichment_Reactome.tsv`. These should be interpreted cautiously because neuronal/olfactory terms are a known residual 450K enrichment artifact even after gene-level collapse.

## Basal-Vs-Normal Interpretation

### Hypermethylated Gene Set

Basal-vs-normal hypermethylated genes again show strong transcriptional-regulatory enrichment. `Regulation Of Transcription By RNA Polymerase II (GO:0006357)`, hypermethylated direction, has `adj_p = 8.593e-18`, and `Regulation Of DNA-templated Transcription (GO:0006355)`, hypermethylated direction, has `adj_p = 1.425e-15` in `basal_vs_normal/enrichment_GO_BP.tsv`.

Basal-vs-normal also retains a cancer transcription annotation: `Transcriptional misregulation in cancer`, hypermethylated direction, `adj_p = 2.393e-02`, in `basal_vs_normal/enrichment_KEGG.tsv`. This supports a basal/TNBC-relevant association with cancer transcriptional programs.

The basal-vs-normal combined query contains `DNA-binding Transcription Repressor Activity, RNA Polymerase II-specific (GO:0001227)`, combined direction, `adj_p = 1.149e-03`, in `basal_vs_normal/enrichment_GO_MF.tsv`. Because the significant row is combined, this supports transcription-repressor involvement but does not assign that signal solely to hypermethylation or hypomethylation.

Basal-vs-normal shows cytoskeletal and adhesion-related biology in the combined query, including `Catenin Complex (GO:0016342)`, combined direction, `adj_p = 2.468e-02`, and `Actin Cytoskeleton (GO:0015629)`, combined direction, `adj_p = 2.468e-02`, in `basal_vs_normal/enrichment_GO_CC.tsv`.

### Hypomethylated Gene Set

No basal-vs-normal hypomethylated-only GO, KEGG, or Reactome terms reached `adj_p < 0.05` in the chosen `pathway_enrichment_top2000` run. Therefore, no basal-specific hypomethylated pathway interpretation is made.

## Tumor-Vs-Normal Compared With Basal-Vs-Normal

Shared biology is dominated by transcriptional regulation. Both comparisons have significant `Regulation Of Transcription By RNA Polymerase II (GO:0006357)` in GO BP: tumor-vs-normal hypermethylated `adj_p = 3.535e-33`; basal-vs-normal hypermethylated `adj_p = 8.593e-18`.

Both comparisons also share KEGG `Transcriptional misregulation in cancer`: tumor-vs-normal combined `adj_p = 3.261e-04`; basal-vs-normal combined `adj_p = 1.041e-02`.

Basal-vs-normal has additional combined terms not present as FDR-significant tumor-vs-normal rows in the same chosen run, including `DNA-binding Transcription Repressor Activity, RNA Polymerase II-specific (GO:0001227)`, `adj_p = 1.149e-03`, `Catenin Complex (GO:0016342)`, `adj_p = 2.468e-02`, and `Actin Cytoskeleton (GO:0015629)`, `adj_p = 2.468e-02`.

Reactome basal-vs-normal terms include `Protein-protein Interactions At Synapses R-HSA-6794362`, combined direction, `adj_p = 1.333e-03`, in `basal_vs_normal/enrichment_Reactome.tsv`. This is retained as a table-backed signal but interpreted cautiously because synaptic/neuronal categories may reflect residual probe/gene-set structure rather than breast-specific mechanism.

## 20-CpG Panel Cross-Reference

The exact 20-CpG panel was selected from full-cohort results and carries mild optimistic selection bias, even though the methylation signal was supported by nested CV. The cross-reference below asks only whether panel genes are present in enriched terms from the chosen run.

| panel gene | panel role | comparison | enriched term | direction | source table | adj_p |
|---|---|---|---|---|---|---:|
| `BCL9` | basal-skewed marker | tumor_vs_normal | `Regulation Of Transforming Growth Factor Beta Receptor Signaling Pathway (GO:0017015)` | combined | `enrichment_GO_BP.tsv` | 7.415e-03 |
| `BCL9` | basal-skewed marker | basal_vs_normal | `Regulation Of Transcription By RNA Polymerase II (GO:0006357)` | combined | `enrichment_GO_BP.tsv` | 6.477e-20 |
| `CAPN2` | basal-skewed marker | basal_vs_normal | `Actin Cytoskeleton (GO:0015629)` | combined | `enrichment_GO_CC.tsv` | 2.468e-02 |
| `ENPP2` | general tumor marker | tumor_vs_normal | `Regulation Of Cell Migration (GO:0030334)` | combined | `enrichment_GO_BP.tsv` | 3.111e-03 |
| `RYR2` | general tumor marker | tumor_vs_normal | `Calcium Channel Complex (GO:0034704)` | combined | `enrichment_GO_CC.tsv` | 9.762e-05 |
| `USP44` | general tumor marker | tumor_vs_normal | `Nucleus (GO:0005634)` | hypermethylated | `enrichment_GO_CC.tsv` | 1.080e-06 |
| `ABCC9` | general tumor marker | tumor_vs_normal | `Neuronal System R-HSA-112316` | combined | `enrichment_Reactome.tsv` | 1.147e-05 |

This cross-reference does not mean the panel genes drive the enriched pathways. It only shows that several panel genes fall inside enriched gene-set overlaps.

## Interpretation Caveats

- The chosen run does not produce an FDR-significant DNA-repair term. DNA repair should therefore be discussed as a future or negative/absent finding for this run, not as an observed enrichment.
- Direction is based on CpG methylation direction at mapped genes. The probe annotation does not distinguish promoter from gene-body methylation, so hypermethylated/silenced and hypomethylated/de-repressed language is interpretive and must remain cautious.
- Residual 450K probe-number bias is not fully corrected. Gene-level collapse and a retained-probe background reduce bias, but this is not equivalent to `missMethyl::gometh`.
