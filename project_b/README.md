# Project B: BRCA Methylation Pipeline

This folder holds the first-pass breast cancer methylation workflow for
`TCGA-BRCA` using:

- HM450 beta values
- TCGA clinical/sample metadata
- HM450 probe annotation

Current starter goal:

`Solid Tissue Normal` vs `Primary Tumor`

The first pipeline version is designed to be lightweight and reproducible:

1. Harmonize TCGA sample IDs across the methylation matrix and clinical table
2. Build a clean cohort manifest
3. Run probe-level differential methylation
4. Annotate significant CpGs with genes and genomic positions
5. Export ranked marker tables and simple QC summaries

Optional next layer:

- merge a BRCA subtype table
- run `Basal/TNBC vs normal` or `Luminal vs normal` comparisons

## Data

Raw local inputs live in `data/raw/`:

- `TCGA-BRCA.methylation450.tsv.gz` — TCGA-BRCA HM450 beta-value matrix, 2.8 GB; stored here as a symlink to the previously downloaded file to avoid duplicating the large matrix.
- `TCGA-BRCA.clinical.tsv.gz` — TCGA clinical/sample metadata, 274 KB.
- `HM450.hg38.manifest.gencode.v36.probeMap` — HM450 hg38/Gencode v36 probe annotation, 21 MB.
- `TCGA-BRCA.subtypes.tsv` — TCGA-BRCA subtype metadata, 109 KB.

The TCGA methylation, clinical, and subtype files can be obtained from the
UCSC Xena TCGA-BRCA data hubs. The HM450 probe annotation can be obtained from
the UCSC Xena probeMap resources. Keep the same filenames under `data/raw/` so
`brca_local_inputs.json` resolves them correctly.

Suggested local output paths:

- `outputs/brca_methylation/`
- `data/`

The main entrypoint is:

`scripts/run_brca_methylation_pipeline.py`
