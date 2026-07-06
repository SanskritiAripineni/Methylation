# Tumor Vs Normal Methylation Report

## Cohort

- `791` tumor samples
- `97` normal samples
- `486427` probes tested

## Summary

- `321823` probes with `FDR < 0.05`
- `31094` probes with `|delta_beta| >= 0.20`
- `30827` probes meeting both thresholds
- `6717` probes meeting `FDR < 0.05` and `|delta_beta| >= 0.30`

## Top Markers By Absolute Effect Size

| probe_id | gene | delta_beta | fdr | direction |
|---|---|---:|---:|---|
| `cg17326769` | `HCK` | 0.660 | 1.838e-09 | hypermethylated |
| `cg03161803` | `AL009179.2` | 0.633 | 4.055e-196 | hypermethylated |
| `cg07077665` | `—` | 0.613 | 4.893e-07 | hypermethylated |
| `cg17534034` | `ZFPM2,ZFPM2-AS1` | -0.612 | 1.942e-17 | hypomethylated |
| `cg08860070` | `—` | 0.593 | 3.721e-52 | hypermethylated |
| `cg22740796` | `—` | -0.592 | 4.727e-121 | hypomethylated |
| `cg06958563` | `LINC00461,MEF2C-AS2` | 0.582 | 2.379e-38 | hypermethylated |
| `cg13294849` | `SOX2-OT` | 0.580 | 1.708e-124 | hypermethylated |
| `cg08159989` | `KLHDC8A` | 0.564 | 2.519e-08 | hypermethylated |
| `cg14088921` | `MATN2` | 0.563 | 6.045e-35 | hypermethylated |

## Top Hypermethylated Markers

| probe_id | gene | delta_beta | fdr | direction |
|---|---|---:|---:|---|
| `cg17326769` | `HCK` | 0.660 | 1.838e-09 | hypermethylated |
| `cg03161803` | `AL009179.2` | 0.633 | 4.055e-196 | hypermethylated |
| `cg07077665` | `—` | 0.613 | 4.893e-07 | hypermethylated |
| `cg08860070` | `—` | 0.593 | 3.721e-52 | hypermethylated |
| `cg06958563` | `LINC00461,MEF2C-AS2` | 0.582 | 2.379e-38 | hypermethylated |
| `cg13294849` | `SOX2-OT` | 0.580 | 1.708e-124 | hypermethylated |
| `cg08159989` | `KLHDC8A` | 0.564 | 2.519e-08 | hypermethylated |
| `cg14088921` | `MATN2` | 0.563 | 6.045e-35 | hypermethylated |
| `cg01518607` | `AL021808.1` | 0.556 | 1.134e-99 | hypermethylated |
| `cg22399133` | `CRYGD` | 0.556 | 6.167e-48 | hypermethylated |

## Top Hypomethylated Markers

| probe_id | gene | delta_beta | fdr | direction |
|---|---|---:|---:|---|
| `cg17534034` | `ZFPM2,ZFPM2-AS1` | -0.612 | 1.942e-17 | hypomethylated |
| `cg22740796` | `—` | -0.592 | 4.727e-121 | hypomethylated |
| `cg20197130` | `LINC00944` | -0.551 | 4.669e-39 | hypomethylated |
| `cg13894852` | `AC091180.5,EIF4EP2` | -0.550 | 1.460e-07 | hypomethylated |
| `cg05280527` | `NRXN3` | -0.543 | 4.357e-14 | hypomethylated |
| `cg08387538` | `DLGAP2,DLGAP2-AS1` | -0.540 | 1.187e-164 | hypomethylated |
| `cg25708982` | `—` | -0.528 | 4.081e-63 | hypomethylated |
| `cg06841499` | `—` | -0.520 | 7.697e-16 | hypomethylated |
| `cg10168086` | `—` | -0.507 | 3.769e-84 | hypomethylated |
| `cg01952226` | `GRHL2` | -0.506 | 5.098e-21 | hypomethylated |

## Outputs

- `differential_methylation.tsv`
- `candidate_biomarker_panel.tsv`
- `top_markers_abs_delta_beta.tsv`
- `top_hypermethylated_markers.tsv`
- `top_hypomethylated_markers.tsv`
- `pca_samples.png`
- `volcano_top_markers.png`
