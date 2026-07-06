# Phase 1 Close-Out

Phase 1 is complete for the baseline `TCGA-BRCA tumor vs normal` methylation workflow.

## Deliverables

- ingestion and metadata harmonization
- cohort manifest
- QC summary and missingness tables
- differential methylation table
- ranked hyper/hypomethylated marker tables
- candidate biomarker panel
- PCA plot
- volcano plot
- heatmap of top candidate markers
- simple classifier benchmark
- short report summary

## QC Snapshot

- retained samples: `888`
- retained probes: `382924`
- sample duplicates in header: `0`
- duplicate probe rows detected: `0`
- sex chromosomes dropped: `True`
- median sample missingness: `0.1481`
- median probe missingness: `0.0000`

## Classifier Snapshot

- model: `logistic_regression`
- features: `25`
- 5-fold ROC AUC mean: `0.996`
- 5-fold ROC AUC std: `0.004`

## Next Phase

Phase 2 should focus on subtype comparisons:

1. `Basal/TNBC vs normal`
2. `LumA vs normal`
3. `TNBC vs non-TNBC`
4. shared versus subtype-skewed CpG markers
