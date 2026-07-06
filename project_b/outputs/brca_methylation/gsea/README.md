# Methylation-aware GSEA provenance

This directory replaces the Phase 3 pure-Python ORA interpretation layer with methylation-aware enrichment while leaving the Phase 3 ORA outputs untouched as the comparison baseline.

## Install

R 4.4.2 and Bioconductor 3.20 were used for this run. From the repository root:

```r
install.packages("BiocManager", repos = "https://cloud.r-project.org")
BiocManager::install(c(
  "missMethyl",
  "methylGSA",
  "IlluminaHumanMethylation450kanno.ilmn12.hg19",
  "IlluminaHumanMethylation450kmanifest",
  "org.Hs.eg.db",
  "reactome.db"
), ask = FALSE, update = FALSE)
install.packages("ggtangle", repos = "https://cloud.r-project.org")
```

If source builds fail for CRAN dependencies on macOS, rerun the same `BiocManager::install()` command with `type = "binary"` for CRAN dependencies, then rerun the Bioconductor install. This run required that for several CRAN dependencies before the 450K annotation packages were built from source.

## Run

```bash
LC_ALL=C Rscript project_b/scripts/run_methylation_gsea.R
```

The script discovers `project_b/brca_local_inputs.json`, reads `outputs/brca_methylation/differential_methylation.tsv`, `outputs/brca_methylation/differential_methylation_mechanics.tsv`, and the Phase 3 curated `pathway_enrichment_longevity/longevity_gene_sets.gmt`, then writes only to `outputs/brca_methylation/gsea/`.

## Methods

- Significant CpGs for missMethyl used the same Phase 3/ORA gate: FDR < 0.05 and |delta_beta| >= 0.2, split into hypermethylated and hypomethylated directions.
- The missMethyl universe (`all.cpg`) starts from every probe ID in `differential_methylation.tsv` and is restricted to CpGs present in the native Illumina 450K hg19 annotation because missMethyl models probe-number bias through that annotation.
- missMethyl `gometh()` was run for built-in GO and KEGG collections. `gsameth()` was run for custom Reactome and curated longevity collections, with custom sets represented as Entrez Gene IDs.
- methylGSA `methylRRA(method = "GSEA")` was run on per-CpG p-values for all valid tested CpGs. The `all` run is the strict threshold-free rank test; hyper/hypo companion runs keep the same CpG universe but set opposite-direction CpGs to p = 1 to provide direction-specific checks without a significance threshold.
- methylGSA retrieves built-in KEGG annotations through KEGG REST during the run. The curated longevity comparison remains pinned to the Phase 3 GMT on disk.
- missMethyl uses hg19 gene annotation for enrichment. This is acceptable here because the enrichment test is gene-membership based and does not alter the Phase 0/Phase 2 hg38 site maps or coordinate-level biological claims.
- Methylation enrichment does not imply expression repression except for promoter-context CpGs. Body/intergenic methylation remains mechanistically ambiguous.

## Probe accounting

- Raw tested probe IDs: 486427
- Native 450K-annotated CpGs used by missMethyl: 485512
- Probe IDs outside native 450K annotation/control/non-CpG IDs excluded from missMethyl universe: 915
- CpGs with finite p-values used by methylGSA: 420890
- Hypermethylated significant CpGs used by missMethyl: 16623
- Hypomethylated significant CpGs used by missMethyl: 14460

## Package versions

- R: 4.4.2
- missMethyl: 1.40.3
- methylGSA: 1.24.0
- IlluminaHumanMethylation450kanno.ilmn12.hg19: 0.6.1
- IlluminaHumanMethylation450kmanifest: 0.4.0
- org.Hs.eg.db: 3.20.0
- reactome.db: 1.89.0
