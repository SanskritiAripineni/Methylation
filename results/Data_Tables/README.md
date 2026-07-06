# Data Tables — index

The numbers behind the reports, organized by analysis. Small/medium result tables are copied
here directly; very large raw matrices stay in `project_b/outputs/` and are named as pointers in
each folder's README (with their path and size).

| Folder | What's inside |
|---|---|
| `1_Differential_Methylation/` | Tumor-vs-normal (and subtype) differential methylation: ranked markers and the candidate panel. |
| `2_Validation/` | The two validation checks: external panel replication (GSE66695) and leakage-audited nested cross-validation. |
| `3_Site_Annotation/` | Per-CpG genomic context: functional region, promoter flag, CpG-island relation, hg38 coordinate. |
| `4_Biomarker_Panel_and_Sites/` | The 20-CpG balanced panel, per-gene site maps, and the silencing/activation direction labels. |
| `5_Pathway_and_GSEA/` | Pathway enrichment (exploratory ORA) and the bias-corrected methylation-aware GSEA + verdicts. |
| `6_Healthy_Baseline_Atlas/` | Healthy-tissue methylation state of longevity genes: full site atlas + per-category summaries. |

Interactive Excel dashboard: `../Dashboard/Longevity_Methylation_Atlas.xlsx`.
Written reports: `../Reports/`.  Figures: `../Figures/`.
