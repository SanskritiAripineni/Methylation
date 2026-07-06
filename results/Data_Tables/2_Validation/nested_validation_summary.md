# Phase 4 Nested Validation

| evaluation | ROC AUC mean | ROC AUC std |
|---|---:|---:|
| original Phase 4 internal CV | 0.996 | 0.003 |
| nested train-only feature selection CV | 0.996 | 0.003 |

The nested run re-ranks probes inside each training fold before fitting the fold model.
It uses retained QC-passing probes as the candidate feature space and does not overwrite the original Phase 4 outputs.
