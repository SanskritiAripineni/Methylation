# Cancer DNA Methylation Biomarker & Pathway Analysis

## 1. Overview & Objective

This project analyzes TCGA-BRCA Illumina HumanMethylation450 DNA methylation profiles to identify tumor-associated CpG methylation patterns, build a compact biomarker panel, validate the methylation signal, and interpret pathway-level biology from existing differential-methylation outputs.

All conclusions are association-based. They do not establish causality, clinical readiness, or treatment utility.

## 2. Data

The primary cohort contains `888` TCGA-BRCA samples: `791` primary tumor samples and `97` solid tissue normal samples. Inputs are HM450/450K methylation beta values, TCGA clinical/sample metadata, BRCA subtype annotations, and HM450 probe annotation.

Local raw inputs are configured in `project_b/brca_local_inputs.json` and stored under `project_b/data/raw/`. The large methylation matrix is symlinked to avoid duplicating the 2.8 GB file; smaller metadata and annotation files are local project copies.

Subtype counts in the tumor-vs-normal manifest include `421` LumA, `142` LumB, `137` Basal, `46` Her2, and additional NA/normal-labeled subtype rows.

## 3. Methods

Differential methylation was computed from existing project outputs by comparing beta values between analysis groups. The main tumor-vs-normal table contains `486427` tested CpGs. For pathway analysis, significant CpGs were selected with `fdr < 0.05`, followed by a tuned top-N effect-size gate.

The 20-CpG biomarker panel was built in Phase 3 from full-cohort candidate marker tables: `12` general tumor markers and `8` basal-skewed markers. This exact panel is full-cohort-selected, so panel-level performance should be interpreted with mild optimistic selection bias.

Validation includes the original Phase 4 5-fold TCGA CV, external GSE66695 scoring, and a corrected nested internal CV that reselects features inside each training fold. The nested CV validates a strong methylation signal, not an unbiased estimate of the exact full-cohort-selected panel.

Pathway enrichment used `outputs/brca_methylation/pathway_enrichment_top2000/` as the canonical tuned run. The query gate was `fdr < 0.05`, then top `2000` probes by `abs_delta_beta`. Probes were collapsed to unique genes, split by direction, and tested with pure-Python SciPy hypergeometric over-representation analysis against the analyzable background of `33010` unique genes from `382924` retained probes. Gene sets were cached from Enrichr GMT libraries: `GO_Biological_Process_2023`, `GO_Molecular_Function_2023`, `GO_Cellular_Component_2023`, `KEGG_2021_Human`, and `Reactome_2022`.

## 4. Differential Methylation Results

Tumor vs normal:

- Tested CpGs: `486427`
- `fdr < 0.05`: `321823`
- `fdr < 0.05` and `abs_delta_beta >= 0.20`: `31083`
- Hypermethylated at that gate: `16623`
- Hypomethylated at that gate: `14460`
- Tuned pathway query, top 2000 probes: `1474` unique genes

Basal vs normal:

- Tested CpGs: `486427`
- `fdr < 0.05`: `283471`
- `fdr < 0.05` and `abs_delta_beta >= 0.20`: `22415`
- Hypermethylated at that gate: `11015`
- Hypomethylated at that gate: `11400`
- Tuned pathway query, top 2000 probes: `1187` unique genes

Other subtype-oriented outputs already on disk include:

- Basal vs non-Basal: `383471` tested CpGs; `16713` CpGs pass `fdr < 0.05` and `abs_delta_beta >= 0.20`.
- LumA vs normal: the existing table contains `1000` rows; `57` CpGs pass `fdr < 0.05` and `abs_delta_beta >= 0.20`.

## 5. Biomarker Panel

The Phase 3 panel contains `20` CpGs:

- `12` general tumor markers
- `8` basal-skewed markers

The exact 20-CpG panel was selected from full-cohort differential results, so it carries mild optimistic selection bias. The stronger statement supported by the corrected evaluation is that the methylation signal is robust; the exact panel composition should be treated as an exploratory candidate panel.

## 6. Validation

Original Phase 4 internal TCGA 5-fold CV:

- ROC AUC mean: `0.996392`
- ROC AUC std: `0.003273`

Corrected nested internal CV:

- ROC AUC mean: `0.995997`
- ROC AUC std: `0.003349`

External GSE66695 validation:

- Samples: `120`
- Tumors: `80`
- Normals: `40`
- ROC AUC: `0.999688`

Stage-specific TCGA AUCs from the original Phase 4 score file were `0.997423` for Stage I, `0.997803` for Stage II, `0.994819` for Stage III, and `0.999063` for Stage IV.

Interpretation: the signal is validated by nested CV at approximately `0.9960` AUC, close to the original `0.9964`. The exact 20-CpG full-cohort-selected panel remains mildly optimistic.

## 7. Pathway Enrichment

The canonical pathway run is `pathway_enrichment_top2000`.

Tumor-vs-normal query:

- Significant probes selected: `2000`
- Hypermethylated probes: `1315`
- Hypomethylated probes: `685`
- Unique genes: `1474`
- Hypermethylated genes: `1045`
- Hypomethylated genes: `463`

Basal-vs-normal query:

- Significant probes selected: `2000`
- Hypermethylated probes: `1393`
- Hypomethylated probes: `607`
- Unique genes: `1187`
- Hypermethylated genes: `762`
- Hypomethylated genes: `441`

Cancer-relevant enriched terms include:

- Tumor-vs-normal KEGG `Transcriptional misregulation in cancer`, combined direction, `adj_p = 3.261e-04`; hypermethylated direction, `adj_p = 2.007e-03`.
- Tumor-vs-normal GO BP `G1/S Transition Of Mitotic Cell Cycle (GO:0000082)`, combined direction, `adj_p = 4.763e-03`.
- Tumor-vs-normal KEGG `MAPK signaling pathway`, hypomethylated direction, `adj_p = 1.680e-03`.
- Tumor-vs-normal KEGG `MicroRNAs in cancer`, hypermethylated direction, `adj_p = 2.406e-02`.
- Basal-vs-normal KEGG `Transcriptional misregulation in cancer`, combined direction, `adj_p = 1.041e-02`; hypermethylated direction, `adj_p = 2.393e-02`.
- Basal-vs-normal GO MF `DNA-binding Transcription Repressor Activity, RNA Polymerase II-specific (GO:0001227)`, combined direction, `adj_p = 1.149e-03`.
- Basal-vs-normal GO CC `Catenin Complex (GO:0016342)`, combined direction, `adj_p = 2.468e-02`.

The tuned run is more specific than the original 0.20 run, but residual neuronal/sensory terms remain, which is a known limitation of 450K methylation enrichment even with gene-level collapse and retained-probe background correction.

## 8. Biological Interpretation

The tumor-vs-normal hypermethylated gene set is associated with transcriptional regulatory programs and cancer transcription annotations, including GO BP `Regulation Of Transcription By RNA Polymerase II (GO:0006357)`, hypermethylated `adj_p = 3.535e-33`, and KEGG `Transcriptional misregulation in cancer`, hypermethylated `adj_p = 2.007e-03`.

The tumor-vs-normal combined query includes a cell-cycle signal through `G1/S Transition Of Mitotic Cell Cycle (GO:0000082)`, `adj_p = 4.763e-03`. This supports a methylation-associated cell-cycle pattern but does not prove functional cell-cycle deregulation.

The tumor-vs-normal hypomethylated query includes `MAPK signaling pathway`, `adj_p = 1.680e-03`, and `Tight junction`, `adj_p = 9.287e-03`, suggesting methylation-associated signaling and epithelial organization themes.

Basal-vs-normal shares transcriptional dysregulation with tumor-vs-normal but adds basal-associated combined terms such as `DNA-binding Transcription Repressor Activity, RNA Polymerase II-specific (GO:0001227)`, `Catenin Complex (GO:0016342)`, and `Actin Cytoskeleton (GO:0015629)`. No basal-vs-normal hypomethylated-only GO, KEGG, or Reactome terms reached `adj_p < 0.05` in the canonical run.

Panel cross-reference showed that several 20-CpG panel genes fall inside enriched term overlaps, including `BCL9`, `CAPN2`, `ENPP2`, `RYR2`, `USP44`, and `ABCC9`. These overlaps are descriptive and do not establish that the panel genes drive the enriched pathways.

## 9. Limitations

- This is association-only methylation and enrichment analysis, not causal biology or clinical validation.
- Effect-size gating and top-N tuning are necessary because large sample size makes many CpGs FDR-significant.
- Residual 450K probe-number bias is not fully corrected. Gene-level collapse and retained-probe background mitigate bias, but this is not equivalent to `missMethyl::gometh`; R/Bioconductor was intentionally avoided.
- Probe-gene mapping does not distinguish promoter from gene-body methylation, whose regulatory implications differ.
- Discovery is single-cohort TCGA-BRCA.
- The exact 20-CpG panel is full-cohort-selected and mildly optimistic, even though the nested CV supports the underlying signal.
- Some enriched neuronal/sensory categories persist and should be interpreted cautiously.

## 10. Future Directions

Future work could integrate neoantigen features with methylation-defined tumor biology. That analysis was not performed here.

Future work could also explore longevity-associated methylation questions as a separate, clearly labeled expansion. That analysis was not performed here.

Additional future work should include independent external cohorts, promoter-aware methylation interpretation, and an R/Bioconductor `gometh`-style sensitivity analysis if the project later allows that dependency.

## 11. Reproducibility Appendix

Path validation only, no full 2.8 GB pipeline rerun:

```bash
python3 project_b/scripts/run_brca_methylation_pipeline.py --config project_b/brca_local_inputs.json --validate-paths-only
```

Leakage-corrected nested validation:

```bash
python3 project_b/scripts/run_phase4_validation_nested.py
```

Pathway baseline run:

```bash
python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json
```

Required Step 3b threshold runs:

```bash
python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --min-abs-delta-beta 0.30 --output-name pathway_enrichment_d030
python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --min-abs-delta-beta 0.40 --output-name pathway_enrichment_d040
```

Additional Step 3b specificity-tuning runs:

```bash
python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --top-n-probes 1000 --output-name pathway_enrichment_top1000
python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --top-n-probes 2000 --output-name pathway_enrichment_top2000
```

Canonical enrichment command:

```bash
python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --top-n-probes 2000 --output-name pathway_enrichment_top2000
```

Syntax verification:

```bash
PYTHONPYCACHEPREFIX=/tmp/brca_pycache python3 -m py_compile project_b/scripts/run_pathway_enrichment.py
```
