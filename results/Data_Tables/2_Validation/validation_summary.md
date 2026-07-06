# Phase 4 Validation

- panel size: `20` CpGs

## Internal TCGA Validation

- 5-fold ROC AUC mean: `0.996`
- 5-fold ROC AUC std: `0.003`

## External Validation

- dataset: `GSE66695`
- samples: `120`
- tumors: `80`
- normals: `40`
- external ROC AUC: `1.000`

## Age Association

- tumor: rho=`0.175`, p=`7.584e-07`, n=`790`
- normal: rho=`0.061`, p=`5.532e-01`, n=`97`

## Stage-Specific TCGA AUC

- Stage I: ROC AUC=`0.997` with `128` tumors and `97` normals
- Stage II: ROC AUC=`0.998` with `441` tumors and `97` normals
- Stage III: ROC AUC=`0.995` with `199` tumors and `97` normals
- Stage IV: ROC AUC=`0.999` with `11` tumors and `97` normals
