# Project B Implementation Plan: TCGA-BRCA Methylation

## First-pass scope

Build a clean, reproducible methylation pipeline for:

`Solid Tissue Normal` vs `Primary Tumor`

using TCGA BRCA HM450 beta values.

## Inputs

- HM450 beta value matrix
- TCGA clinical metadata
- HM450 probe annotation map
- optional BRCA subtype table

## First-pass outputs

- `cohort_manifest.tsv`
- `cohort_summary.json`
- `differential_methylation.tsv`
- `top_hypomethylated_markers.tsv`
- `top_hypermethylated_markers.tsv`
- `top_markers_abs_delta_beta.tsv`
- `volcano_top_markers.png`
- `pca_samples.png`

Subtype extension:

- `basal_vs_normal/`
- `luminal_a_vs_normal/`
- `her2_vs_normal/`

## Pipeline steps

1. Load the methylation matrix header and collect sample barcodes
2. Load clinical metadata and derive a clean tumor/normal label
3. Intersect samples across files and keep only `Primary Tumor` and
   `Solid Tissue Normal`
4. Stream through the beta matrix in chunks
5. For each CpG:
   - compute tumor mean beta
   - compute normal mean beta
   - compute `delta_beta`
   - run Welch's t-test
6. Apply Benjamini-Hochberg FDR correction
7. Join probe annotations
8. Export ranked biomarker tables
9. Generate quick-look PCA and volcano plots

## Subtype extension

If a subtype table is provided, the pipeline can also subset tumors by
subtype and compare one subtype against normal breast tissue.

## Notes

- This first version uses processed beta values, not raw IDATs
- It is intentionally scoped to a straightforward BRCA baseline
- Subtype modeling is the next layer after this baseline is stable
