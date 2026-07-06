# BRCA Methylation Project Progress

## Before Step 3b — Locked Prior Work And Baseline Context

Completed prior work is locked and will not be modified during Steps 3b-5.

- Paths and local data were made project-contained under `project_b/data/raw/`; the 2.8 GB methylation matrix is a symlink, and smaller metadata inputs are local copies.
- Validation leakage was audited in `outputs/brca_methylation/leakage_audit.md`.
- Original internal Phase 4 CV was `0.996392` mean ROC AUC, `0.003273` std.
- Corrected nested internal CV was `0.995997` mean ROC AUC, `0.003349` std, in `outputs/brca_methylation/phase4_validation_nested/nested_validation_summary.json`.
- Existing pathway baseline at `outputs/brca_methylation/pathway_enrichment/` used `fdr < 0.05` and `abs_delta_beta >= 0.20`.
- Baseline background was `382924` retained probes and `33010` unique genes from `retained == True` probes.
- Baseline tumor-vs-normal significant set: `31083` probes, `10956` genes; hyper genes `6435`, hypo genes `6284`.
- Baseline basal-vs-normal significant set: `22415` probes, `8661` genes; hyper genes `4216`, hypo genes `5412`.

Issues fixed before Step 3b: none.

## Before Step 4 — Step 3b Results

Step 3b completed.

Script changes:

- `project_b/scripts/run_pathway_enrichment.py` now supports `--top-n-probes`.
- `--top-n-probes`, when set, applies the `fdr < 0.05` gate first and then selects the top N probes by `abs_delta_beta`, instead of applying the flat `--min-abs-delta-beta` gate.
- `--output-name` was added so tuned runs write to separate `pathway_enrichment*` directories without overwriting the 0.20 baseline.
- Each run writes `threshold_summary.md` plus per-comparison `top15_terms_by_library.tsv`.

Required threshold runs:

- `pathway_enrichment_d030/`: tumor-vs-normal `3796` genes, basal-vs-normal `2623` genes. Tumor-vs-normal exceeded the target 500-3000 gene range.
- `pathway_enrichment_d040/`: tumor-vs-normal `721` genes, basal-vs-normal `690` genes. Both were in range, but top GO_BP/Reactome terms still leaned heavily toward generic transcriptional and neuronal categories.

Additional non-critical tuning runs:

- `pathway_enrichment_top1000/`: tumor-vs-normal `852` genes, basal-vs-normal `676` genes; Reactome coverage was sparse, with zero FDR-significant basal-vs-normal Reactome terms.
- `pathway_enrichment_top2000/`: tumor-vs-normal `1474` genes, basal-vs-normal `1187` genes; both were in range and retained more cancer-relevant KEGG/Reactome signal.

Canonical Step 4 input:

- Chosen run: `outputs/brca_methylation/pathway_enrichment_top2000/`.
- Rationale: It keeps both query gene sets in the target range and is sharper than the 0.20/0.30 runs while retaining interpretable, FDR-significant cancer-relevant rows such as `Transcriptional misregulation in cancer`, `MAPK signaling pathway`, `MicroRNAs in cancer`, `G1/S Transition Of Mitotic Cell Cycle`, and basal/tumor shared GPCR/signal-transduction terms.
- Background remained fixed at `382924` retained probes and `33010` unique genes from `retained == True` probes.

Issues fixed in Step 3b:

- Non-critical syntax issue in the new command-string construction was caught by `py_compile` and fixed before final Step 3b runs.
- Non-critical threshold specificity issue was handled by using the new top-N option; the required 0.30 and 0.40 outputs were preserved for comparison.

Gate decision:

- PASS. Proceeding to Step 4 with `pathway_enrichment_top2000/`.

## Before Step 5 — Step 4 Results

Step 4 completed.

Output:

- `outputs/brca_methylation/biological_interpretation.md`

Key table-backed interpretation points:

- Tumor-vs-normal hypermethylated genes are associated with transcriptional regulation, including `Regulation Of Transcription By RNA Polymerase II (GO:0006357)`, hypermethylated `adj_p = 3.535e-33`, and KEGG `Transcriptional misregulation in cancer`, hypermethylated `adj_p = 2.007e-03`.
- Tumor-vs-normal combined genes include a cell-cycle row, `G1/S Transition Of Mitotic Cell Cycle (GO:0000082)`, combined `adj_p = 4.763e-03`.
- Tumor-vs-normal hypomethylated genes include `MAPK signaling pathway`, hypomethylated `adj_p = 1.680e-03`, and `Tight junction`, hypomethylated `adj_p = 9.287e-03`.
- Basal-vs-normal hypermethylated genes include KEGG `Transcriptional misregulation in cancer`, hypermethylated `adj_p = 2.393e-02`.
- Basal-vs-normal has no FDR-significant hypomethylated-only GO, KEGG, or Reactome terms in the chosen run.
- Several 20-CpG panel genes overlap enriched terms, including `BCL9`, `CAPN2`, `ENPP2`, `RYR2`, `USP44`, and `ABCC9`; the interpretation file states that these overlaps do not imply driver status.

Issues fixed in Step 4:

- None.

Gate decision:

- PASS. Proceeding to Step 5.

## After Step 5 — Final Report Completion

Step 5 completed.

Output:

- `outputs/brca_methylation/FINAL_REPORT.md`

Final report contents:

- Title: "Cancer DNA Methylation Biomarker & Pathway Analysis"
- Includes all requested sections: overview, data, methods, differential methylation, 20-CpG panel, validation, pathway enrichment, biological interpretation, limitations, future directions, and reproducibility appendix.
- Uses the canonical Step 3b enrichment run: `outputs/brca_methylation/pathway_enrichment_top2000/`.
- States the required validation caveat: nested CV validates the methylation signal at approximately `0.9960` ROC AUC, while the exact 20-CpG panel is full-cohort-selected and mildly optimistic.
- States association-only and residual 450K probe-number-bias limitations.
- Future directions mention neoantigen integration and longevity only as future expansions, not completed analyses.

Final checks:

- `py_compile` passed for `project_b/scripts/run_pathway_enrichment.py`.
- Required files exist: `PROGRESS.md`, `biological_interpretation.md`, `FINAL_REPORT.md`, and tuned pathway summaries.
- Canonical pathway counts reconciled from disk: tumor-vs-normal `2000` probes and `1474` genes; basal-vs-normal `2000` probes and `1187` genes.

Issues fixed in Step 5:

- None.

Gate decision:

- PASS. Steps 3b, 4, and 5 are complete.
