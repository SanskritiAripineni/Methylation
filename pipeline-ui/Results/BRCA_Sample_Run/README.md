# BRCA sample-run results

This folder contains an easy-access copy of the complete output from run
`20260731-062458-full-8217f9`.

Important: this run used the bundled BRCA demonstration cohort. The per-sample
methylation values are simulated, so these files demonstrate the analysis
workflow and are not clinical or publishable breast-cancer findings.

## Start here

- `run_report.html` — complete one-page report with charts and explanations.
- `bundle.zip` — all original output files in one download.
- `candidate_biomarker_panel.tsv` — the 100-site candidate panel.
- `differential_methylation.tsv` — results for all tested CpG sites.
- `differential_with_mechanics.tsv` — effect-filtered sites with gene and
  silencing/activation interpretation.
- `classifier_summary.json` and `cv_folds.tsv` — internal cross-validation
  summary and fold-level scores.
- `enrichment_*.tsv` — pathway-enrichment tables.
- `qc_sample_missingness.tsv` — sample-level quality-control table.
- `results.json` — machine-readable report data.
- `run_record.json`, `run_manifest.json`, and `run_log.txt` — provenance,
  settings, file manifest, and execution log.

The original generated files remain unchanged in
`runs/20260731-062458-full-8217f9/`.
