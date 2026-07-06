# Leakage Audit

## Verdict

LEAKAGE for the original internal TCGA validation.

The 20-CpG panel is selected from full-cohort candidate outputs before cross-validation, and the CV loops refit only the classifier while reusing those pre-selected CpGs. GSE66695 scoring does not refit on GSE66695; the classifier is fit on TCGA and then applied to GSE66695.

## Evidence

### Are the panel CpGs selected on the full cohort before cross-validation?

Yes.

- `project_b/scripts/run_brca_methylation_pipeline.py:449-545` computes differential methylation using the manifest passed into the run, with tumor and normal columns taken from that full run manifest.
- `project_b/scripts/run_brca_methylation_pipeline.py:619-640` writes `candidate_biomarker_panel.tsv` by filtering and sorting the full-run differential methylation results.
- `project_b/scripts/build_phase3_panel.py:39-42` loads the already-written `tumor_vs_normal` and `basal_vs_non_basal` candidate panels.
- `project_b/scripts/build_phase3_panel.py:45-89` constructs the 20-CpG refined panel from those candidate files, using full-cohort `abs_delta_beta` and `fdr`-derived priority scores at lines 57-62.
- `project_b/scripts/build_phase3_panel.py:139-145` writes the refined panel and then evaluates it.

### Inside each CV fold, is feature selection re-done on the training split only?

No.

- `project_b/scripts/build_phase3_panel.py:143-145` passes the completed panel probe list into `evaluate_classifier`.
- `project_b/scripts/build_phase3_panel.py:118-128` performs 5-fold CV on the fixed `probes`; there is no fold-local CpG re-selection.
- `project_b/scripts/run_phase4_validation.py:177-188` loads the refined panel, loads those fixed probes from TCGA, fits a TCGA classifier, and computes internal CV using the same fixed feature matrix.
- `project_b/scripts/run_phase4_validation.py:127-139` refits only logistic regression within each fold; feature selection is not repeated inside the fold.

### Is GSE66695 external scoring fit only on TCGA, or is anything refit on GSE66695?

No GSE66695 refit was found.

- `project_b/scripts/run_phase4_validation.py:120-124` fits the logistic regression classifier on TCGA.
- `project_b/scripts/run_phase4_validation.py:180-183` loads TCGA panel features and fits the classifier before external scoring.
- `project_b/scripts/run_phase4_validation.py:189-202` parses GSE66695, applies `clf.predict_proba(external_X)`, and computes external ROC AUC from those scores. There is no `fit` call on `external_X`.

## Corrected Internal Evaluation

A new script, `project_b/scripts/run_phase4_validation_nested.py`, leaves the original validation intact and writes separate outputs under `project_b/outputs/brca_methylation/phase4_validation_nested/`.

The corrected run re-ranks retained QC-passing probes inside each training fold by absolute delta-beta using training samples only, selects 20 CpGs per fold, fits logistic regression on the training fold, and scores the held-out fold.

| evaluation | ROC AUC mean | ROC AUC std |
|---|---:|---:|
| original Phase 4 internal CV | 0.996392 | 0.003273 |
| nested train-only feature selection CV | 0.995997 | 0.003349 |

This correction addresses the internal feature-selection leakage. The high AUC remains an association/classification result within available methylation datasets; it does not establish clinical utility.
