# Phase 0 Verification

Verdict: PASS.

I independently checked `project_b/scripts/build_probe_annotation.py`, the enriched annotation outputs, the raw Zhou/sesame HM450 hg38 manifest, the original Xena probeMap, the downstream differential methylation table, and `project_b/brca_local_inputs.json`.

What I verified:

- Source appropriateness: Phase 0 uses `data/raw/HM450.hg38.manifest.gencode.v36.zhou.tsv.gz`, which supplies hg38 coordinates, GENCODE v36 transcript relationships, signed `distToTSS`, and CpG-island context. This is the right source to enrich the sparse Xena probeMap for promoter/body/island interpretation.
- Coordinate consistency: all 485,547 probes shared by the original `HM450.hg38.manifest.gencode.v36.probeMap` and the Zhou manifest have identical chromosome, start, end, and strand values. There are no duplicate probe IDs in the raw manifest, original probeMap, or enriched annotation.
- Signed-distance convention: using raw `CpG_beg`, `distToTSS`, and transcript IDs, plus-strand examples such as `GSTP1` and `ESR1` give a constant transcript TSS from `CpG_beg - distToTSS`, while minus-strand examples such as `BRCA1`, `RASSF1`, and `WASH7P` give a constant transcript TSS from `CpG_beg + distToTSS`. This supports the script's interpretation that negative `distToTSS` is upstream/promoter side and positive is downstream/gene-body side after strand is accounted for by the manifest.
- Multi-value handling: every row with `distToTSS` has aligned `geneNames` and distance lists; I found no nonnumeric distance tokens and no distance/gene-list length mismatches. The script's nearest-TSS selection and any-isoform promoter flag are therefore computationally well-defined for this manifest.
- Missing/edge cases: rows without TSS information are labeled `intergenic`, and missing `CGIposition` is labeled `OpenSea`. The 30 manifest-only probes with missing coordinates are not significant downstream and are labeled intergenic/OpenSea rather than assigned fabricated coordinates.
- Downstream coverage: the downstream `differential_methylation.tsv` has 321,823 rows with `fdr < 0.05`; the 118 significant rows absent from Phase 0 are all `ctl_...` control probes with no genomic coordinate or gene. All significant non-control HM450 probe rows are present in the enriched annotation.
- Biological spot checks: known breast-cancer methylation genes including `GSTP1`, `RASSF1`, `SOX17`, `WIF1`, `APC`, `TWIST1`, and `ESR1` have significant probes annotated in promoter/TSS windows and CpG islands or shores where expected. `BRCA1` illustrates an important multi-gene/neighboring-TSS case: some probes are nearest to `NBR2` but still promoter-positive by the any-isoform flag.
- Reproducibility: re-running the script's annotation logic from the raw manifest reproduces the current enriched table, apart from read/write representation of blank fields as empty strings versus pandas NA.

Caveats for downstream use:

- `annotation_coverage.md` reports "with a functional-region call" as non-intergenic only. That wording understates coverage because `intergenic` is a valid Phase 0 label for downstream ambiguity, not a join failure.
- 7,313 probes have `functional_region == gene_body` while `is_promoter == True`, because the nearest TSS is just outside the +500 bp promoter window but another transcript/gene TSS places the probe inside the promoter window. Phase 1 should therefore use `is_promoter` from Phase 0, not infer promoter status from `functional_region` alone.

Overall, Phase 0 is scientifically and computationally sound for Phase 1 mechanics labeling, as long as non-promoter and unannotated control probes are labeled conservatively as ambiguous.
