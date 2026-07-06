# BRCA Methylation — Supervisor Expansion Plan

Execution plan for the items from the supervisor meeting. Designed so **Codex runs one
phase at a time** and **Claude code-reviews each phase against disk before the next
starts**. Phases are ordered by dependency, not by supervisor talking order.

## Ground truth this plan is built on
- Existing pipeline is solid: differential methylation (tumor/normal + subtypes),
  candidate panel with `direction/gene/coords`, nested-CV validation (~0.996, confirmed
  real), and pure-Python ORA via Enrichr (GO/KEGG/Reactome).
- `candidate_biomarker_panel.tsv` already carries `direction` (hyper/hypo), `gene`,
  `chrom/chromStart/chromEnd`, `delta_beta`, `fdr`.
- **Annotation gap (blocker):** current probeMap has gene + coordinate only. No
  region (promoter/TSS/body/UTR), no CpG-island context. Needed for any "silencing vs
  activation" claim.
- Datasets: TCGA-BRCA HM450 (~864 samples = the "888 array"); `GSE66695` (120 samples,
  40 normal + 80 tumor) = external / healthy-baseline set. **No single-cell data on disk.**

## Scientific-integrity guardrails (apply to every phase)
Per the project's standing stance (validation is strong; the pathway/longevity layer is
the WEAKEST and is dominated by the known 450K neuronal/developmental artifact):
1. **hyper ≠ always silencing.** Only assert silencing/activation with region context
   (promoter/TSS). Body/intergenic sites get an explicit "ambiguous" label.
2. **Disclose the artifact.** Any longevity/GSEA result must be reported alongside the
   background-artifact caveat and be ready to report *negative* results.
3. Some supervisor framings are biologically loose (e.g. "homo/hetero methylation",
   "citrulline enzymes for telomere", methylation directly *setting* telomere length).
   Model them as hypotheses to test, not facts to confirm. Do not fabricate a mechanism
   the data doesn't support.
4. No new leakage: keep any modeling fold-local; baselines use held-out/independent data.

---

## Phase 0 — Enriched probe annotation  ✅ DONE (Claude, 2026-07-06)
**Why:** every downstream biological claim needs region + island context.
**Built:** `scripts/build_probe_annotation.py` derives region + island context from the
coordinate-consistent Zhou-lab (sesame) hg38 manifest
(`data/raw/HM450.hg38.manifest.gencode.v36.zhou.tsv.gz`, added to `brca_local_inputs.json`
as `probe_annotation_zhou`). Sign convention verified (negative distToTSS = upstream/promoter).
**Deliverable (on disk):** `outputs/brca_methylation/annotation/probe_annotation_enriched.tsv`
+ `annotation_coverage.{json,md}` + `README.md` (schema).
**Output contract — columns Phase 1+ join on (key = `probe_id`):**
`probe_id, chrom, chromStart, chromEnd, strand, genes_all, gene_nearest, dist_to_tss (signed,
neg=upstream), functional_region (TSS200 | TSS1500 | 5UTR_1stExon | gene_body | upstream_distal |
intergenic), is_promoter (bool, any-isoform TSS in −1500..+500), cgi_relation (Island | N_Shore |
S_Shore | N_Shelf | S_Shelf | OpenSea), cgi_id`.
**Result:** 485,577 probes annotated; **99.96% of significant probes covered** (only 118
missing from the sesame manifest). Region mix of sig probes: gene_body 124.8k, 5UTR_1stExon
54.5k, TSS1500 52.4k, TSS200 47.8k, intergenic 42.3k. Validated against BRCA1 / GSTP1 / MLH1
promoter loci (all land in TSS200/TSS1500 islands/shores) and plus-strand sign check (100%).
**Note for Phase 1:** the ~13% "intergenic" is a genuine 450K category, not a gap — treat as
`ambiguous` for silencing calls. The **promoter rule** to use: `is_promoter==True` → hyper =
silencing, hypo = activation; otherwise (gene_body / intergenic) → `ambiguous`.

## Phase 1 — Methylation-mechanics direction labeling
**Depends on:** Phase 0.
**Do:** add `predicted_expression_effect` to differential outputs — promoter+hyper →
silencing(down), promoter+hypo → activation(up), body → ambiguous/flagged. Encode the
hyper/hypo → TF-binding mechanic explicitly in a short methods note.
**Deliverable:** augmented `differential_methylation.tsv` + `candidate_biomarker_panel.tsv`
with the new column; `methylation_mechanics.md` (one-page mechanism writeup).
**Accept:** every significant probe has an effect label; counts of silencing vs
activation vs ambiguous reported.
**Review focus:** the promoter rule is applied from Phase-0 regions, not re-guessed.

## Phase 2 — Top-20 CpG site-level gene mapping
**Depends on:** Phase 0.
**Do:** for the top-20 prioritized biomarkers (and the full significant set), emit
per-gene site maps: every altered CpG in a gene, its coordinate, region, direction,
delta-beta — surfacing genes with multiple distinct altered sites.
**Deliverable:** `outputs/brca_methylation/site_maps/top20_site_maps.tsv` +
`site_maps_narrative.md` (per-gene: which sites moved, promoter vs body, likely
functional consequence).
**Accept:** all 20 map to ≥1 annotated site; multi-site genes explicitly listed.
**Review focus:** coordinates match manifest; no gene/coordinate mismatches.

## Phase 3 — Longevity gene-set curation + GSEA layer
**Depends on:** Phase 1 (needs direction) + existing ORA infra.
**Do:** curate custom GMT gene sets for telomere maintenance (TERT, TERC, shelterin…),
mitochondrial biogenesis (PPARGC1A/TFAM…), stem-cell differentiation, and AMPK/FoxO/mTOR;
include named targets (FGF2, telomerase). Add as libraries alongside KEGG/Reactome; run
enrichment on hyper/hypo gene lists.
**Deliverable:** `pathway_enrichment_longevity/` with per-set ORA tables +
`longevity_enrichment.md`. Cache the curated GMTs with provenance.
**Accept:** results reproduce on re-run; each curated set documents its source.
**Review focus:** background gene universe is correct; **artifact caveat present**;
no cherry-picking of terms.

## Phase 4 — Healthy-control baseline (GEO)
**Depends on:** Phase 3 gene sets.
**Do:** wire `GSE66695` normals + TCGA normals into a baseline: methylation profile of
the longevity gene sets in healthy tissue, as the benchmark tumor shifts are measured
against. Confirm GSE66695 is actually parsed/aligned to HM450 probes.
**Deliverable:** `outputs/brca_methylation/longevity_baseline/` (baseline betas per set,
tumor-vs-baseline deltas) + `baseline_methods.md`.
**Accept:** GSE66695 sample labels match series matrix (40N/80T); probe overlap reported.
**Review focus:** normal/tumor labels not swapped; batch/platform differences disclosed.

## Phase 5 — Longevity landscape synthesis
**Depends on:** 2, 3, 4.
**Do:** integrate site maps + direction + GSEA + baseline into the "longevity landscape"
narrative (telomere length, FGF2, mito biogenesis, stem-cell differentiation) — how
shifts at specific sites plausibly toggle TF binding. Integrity-forward: lead with what's
supported, label the speculative.
**Deliverable:** `LONGEVITY_LANDSCAPE.md` + refreshed figures.
**Accept:** every claim traces to a table/coordinate; speculation clearly marked.

## Phase 6 — Single-cell methylation extension (feasibility spike, no runnable data yet)
**Depends on:** nothing; standalone/last.
**Do:** scope only — identify a candidate public scWGBS / snmC-seq BRCA dataset, define
what pseudobulk/deconvolution vs the 450K bulk signal would add, list data + compute
requirements. **No pipeline build until a dataset is chosen with the supervisor.**
**Deliverable:** `single_cell_extension_scoping.md`.

---

## Suggested execution order for Codex
`Phase 0 → 1 → 2` (annotation + mechanics + site maps: high-confidence, mostly mechanical)
then `3 → 4 → 5` (longevity layer: scientifically riskier, review harder), and `6` any
time as a doc-only spike. Claude reviews each phase against disk before the next begins.
