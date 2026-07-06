# Basal Vs Non Basal Methylation Report

## Cohort

- `137` `Basal` samples
- `643` `non_basal` samples
- `383471` probes tested

## Summary

- `228583` probes with `FDR < 0.05`
- `16713` probes with `|delta_beta| >= 0.20`
- `16713` probes meeting both thresholds
- `3760` probes meeting `FDR < 0.05` and `|delta_beta| >= 0.30`

## Top Markers By Absolute Effect Size

| probe_id | gene | delta_beta | fdr | direction |
|---|---|---:|---:|---|
| `cg00428457` | `—` | 0.636 | 5.346e-65 | hypermethylated |
| `cg17154724` | `DNM3` | -0.595 | 7.219e-72 | hypomethylated |
| `cg27429080` | `DNM3` | -0.588 | 2.731e-65 | hypomethylated |
| `cg07205203` | `AC092164.1` | -0.586 | 2.400e-64 | hypomethylated |
| `cg23440816` | `CAPN2` | 0.585 | 3.120e-140 | hypermethylated |
| `cg03441279` | `BCL9` | 0.566 | 1.272e-160 | hypermethylated |
| `cg27500148` | `AC110749.1,RPL23` | -0.550 | 3.507e-51 | hypomethylated |
| `cg17219660` | `GPR37L1` | 0.547 | 6.417e-81 | hypermethylated |
| `cg13488570` | `SKI` | -0.547 | 3.616e-70 | hypomethylated |
| `cg19081101` | `CHI3L1` | -0.546 | 6.607e-56 | hypomethylated |

## Top Hypermethylated Markers

| probe_id | gene | delta_beta | fdr | direction |
|---|---|---:|---:|---|
| `cg00428457` | `—` | 0.636 | 5.346e-65 | hypermethylated |
| `cg23440816` | `CAPN2` | 0.585 | 3.120e-140 | hypermethylated |
| `cg03441279` | `BCL9` | 0.566 | 1.272e-160 | hypermethylated |
| `cg17219660` | `GPR37L1` | 0.547 | 6.417e-81 | hypermethylated |
| `cg08960448` | `AC020663.4,SEPTIN12;SMIM22` | 0.530 | 9.889e-72 | hypermethylated |
| `cg03228065` | `E4F1` | 0.529 | 3.093e-131 | hypermethylated |
| `cg05327192` | `KLHL35` | 0.518 | 7.415e-120 | hypermethylated |
| `cg23703633` | `ANK3` | 0.509 | 3.042e-98 | hypermethylated |
| `cg20776543` | `AC073957.3,GET4;SUN1` | 0.505 | 1.391e-95 | hypermethylated |
| `cg20035127` | `AC036214.4` | 0.501 | 2.974e-135 | hypermethylated |

## Top Hypomethylated Markers

| probe_id | gene | delta_beta | fdr | direction |
|---|---|---:|---:|---|
| `cg17154724` | `DNM3` | -0.595 | 7.219e-72 | hypomethylated |
| `cg27429080` | `DNM3` | -0.588 | 2.731e-65 | hypomethylated |
| `cg07205203` | `AC092164.1` | -0.586 | 2.400e-64 | hypomethylated |
| `cg27500148` | `AC110749.1,RPL23` | -0.550 | 3.507e-51 | hypomethylated |
| `cg13488570` | `SKI` | -0.547 | 3.616e-70 | hypomethylated |
| `cg19081101` | `CHI3L1` | -0.546 | 6.607e-56 | hypomethylated |
| `cg10883503` | `AC025171.1,AC025171.3` | -0.543 | 1.060e-76 | hypomethylated |
| `cg17627629` | `—` | -0.542 | 1.162e-102 | hypomethylated |
| `cg15732840` | `AC007098.1` | -0.541 | 1.586e-50 | hypomethylated |
| `cg10558233` | `PDP1` | -0.541 | 4.734e-68 | hypomethylated |

## Outputs

- `differential_methylation.tsv`
- `candidate_biomarker_panel.tsv`
- `qc_summary.json`
- `qc_summary.md`
- `sample_missingness.tsv`
- `probe_missingness.tsv`
- `top_markers_abs_delta_beta.tsv`
- `top_hypermethylated_markers.tsv`
- `top_hypomethylated_markers.tsv`
- `pca_samples.png`
- `heatmap_top_markers.png`
- `volcano_top_markers.png`
- `classifier_summary.json`
