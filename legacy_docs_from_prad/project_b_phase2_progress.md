# Phase 2 Progress

Phase 2 extends the baseline BRCA methylation workflow into subtype-aware
comparisons.

## Implemented comparison modes

- `subtype_vs_normal`
- `subtype_vs_subtype`

The current practical mapping is:

- `Basal` as the TNBC proxy
- `non_basal` as the non-TNBC proxy

## Active and available comparisons

1. `Basal vs normal`
2. `LumA vs normal`
3. `Basal vs non_basal`

## Current status

- pipeline support for Phase 2 comparisons is implemented in
  `studies/brca/project_b/scripts/run_brca_methylation_pipeline.py`
- existing smoke-test outputs are available for `Basal vs normal` and
  `LumA vs normal`
- the full `Basal vs non_basal` run is in progress

## Notes

- `TNBC vs non-TNBC` is currently implemented as a PAM50-based proxy analysis
  because the available subtype table provides `Basal`, `LumA`, `LumB`, and
  `Her2` labels rather than explicit ER/PR/HER2 receptor status
- if a receptor-status table is added later, we can refine this into a stricter
  clinical TNBC definition
