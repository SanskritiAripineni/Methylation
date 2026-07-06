# Clinician-Facing Research Summary

## Intended Use

This package is a research-use methylation screening summary for breast tumor-associated signal. It is not a validated diagnostic medical device and should not be used as a standalone basis for patient care decisions.

## Panel Composition

- `20` total CpGs
- `12` general tumor-associated markers
- `8` Basal-skewed markers

## Validation Snapshot

- Internal TCGA ROC AUC mean: `0.996`
- External GEO GSE66695 ROC AUC: `1.000`
- Tumor age association rho: `0.175`

## Interpretation Bands

- Low: `score <= 0.447`
- Indeterminate: `0.447 < score < 0.835`
- High: `score >= 0.835`

## Caveats

- performance is derived from retrospective public cohorts
- tumor purity and cohort composition may affect score distributions
- age remains a modest confounder in tumor samples
- subtype inference is currently stronger for Basal-skewed biology than for full clinical receptor-status definitions

## Recommended Clinical Framing

- describe this as a research methylation signal score
- report confidence cautiously and avoid diagnostic wording
- pair the score with histopathology, imaging, and standard clinical biomarkers
