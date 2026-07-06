# BRCA Tumor vs Normal Methylation Report

## Scope

This report summarizes the first full `TCGA-BRCA` methylation comparison:

- `791` primary tumor samples
- `97` solid tissue normal samples
- `486,427` HM450 probes tested

Input data:

- `TCGA-BRCA.methylation450.tsv.gz`
- `TCGA-BRCA.clinical.tsv.gz`
- `HM450.hg38.manifest.gencode.v36.probeMap`

## Summary

Across the full probe set:

- `321,823` probes reached `FDR < 0.05`
- `31,128` probes showed `|delta_beta| >= 0.20`
- `31,083` probes met both `FDR < 0.05` and `|delta_beta| >= 0.20`
- `6,717` probes met `FDR < 0.05` and `|delta_beta| >= 0.30`

This indicates a very strong tumor-versus-normal methylation signal in the BRCA
cohort.

## Top Markers By Absolute Effect Size

| probe_id | gene | delta_beta | fdr | direction |
|---|---|---:|---:|---|
| `cg08104202` | `CCDC181` | 0.458 | 9.093e-263 | hypermethylated |
| `cg15584221` | `HHAT` | -0.386 | 1.443e-255 | hypomethylated |
| `cg26765743` | `MIR646HG` | -0.432 | 3.836e-252 | hypomethylated |
| `cg11785980` | `RIMBP2` | -0.430 | 6.373e-251 | hypomethylated |
| `cg00002719` | `CCDC181` | 0.486 | 5.673e-249 | hypermethylated |
| `cg07936456` | `RBFOX1` | -0.399 | 2.451e-244 | hypomethylated |
| `cg27527345` | `OR10J5` | -0.383 | 5.633e-243 | hypomethylated |
| `cg08180884` | `ZNF536` | -0.378 | 8.559e-243 | hypomethylated |
| `cg02051545` | `—` | -0.386 | 4.965e-238 | hypomethylated |
| `cg08160063` | `RBFOX1` | -0.406 | 3.570e-236 | hypomethylated |

## Early Interpretation

The strongest global BRCA tumor-versus-normal signal includes both
hypermethylated and hypomethylated CpGs, which is what we want to see in a
useful biomarker search. This does not yet prove subtype specificity or
clinical utility, but it does show that the baseline methylation pipeline is
working on the full cohort and producing a large pool of candidate markers.

## Outputs

Current main outputs:

- [cohort_manifest.tsv](../project_b/outputs/brca_methylation/cohort_manifest.tsv)
- [cohort_summary.json](../project_b/outputs/brca_methylation/cohort_summary.json)
- [differential_methylation.tsv](../project_b/outputs/brca_methylation/differential_methylation.tsv)
- [top_markers_abs_delta_beta.tsv](../project_b/outputs/brca_methylation/top_markers_abs_delta_beta.tsv)
- [top_hypermethylated_markers.tsv](../project_b/outputs/brca_methylation/top_hypermethylated_markers.tsv)
- [top_hypomethylated_markers.tsv](../project_b/outputs/brca_methylation/top_hypomethylated_markers.tsv)
- [pca_samples.png](../project_b/outputs/brca_methylation/pca_samples.png)
- [volcano_top_markers.png](../project_b/outputs/brca_methylation/volcano_top_markers.png)

The cleaned rerun is writing into:

- [tumor_vs_normal](../project_b/outputs/brca_methylation/tumor_vs_normal)

That rerun will add:

- a dedicated `tumor_vs_normal` result folder
- cleaner finite-FDR marker ranking
- `candidate_biomarker_panel.tsv`
- `analysis_summary.json`
- `report_summary.md`

## Next Step

After the cleaned tumor-vs-normal rerun finishes, the next high-value step is
to compare:

1. `Basal/TNBC vs normal`
2. `LumA vs normal`
3. shared markers versus subtype-skewed markers
