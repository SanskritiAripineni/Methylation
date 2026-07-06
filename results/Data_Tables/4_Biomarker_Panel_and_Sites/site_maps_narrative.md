# Phase 2 Site Maps: balanced

## Selection

- input: `differential_methylation_mechanics.tsv`
- initial gate: `fdr < 0.05` and `abs_delta_beta >= 0.2`
- gated probes: `31083` (`16623` hypermethylated, `14460` hypomethylated)
- promoter-gated probes for balanced selection: `13429` (`9358` hypermethylated, `4071` hypomethylated)
- selected panel probes: `20` (`10` hypermethylated, `10` hypomethylated)

No gene deduplication was applied. Promoter status comes from Phase 0 `is_promoter`.

## Multi-Site Genes

| gene | significant gated CpG sites |
|---|---:|
| MYT1L | 37 |
| LINC00461 | 30 |
| AC244517.11 | 26 |
| MEF2C-AS2 | 23 |
| AC244517.10 | 18 |
| KCNQ2 | 15 |
| USP44 | 9 |
| AL009179.2 | 9 |
| LINC00944 | 9 |
| LINC01138 | 8 |
| AC008875.3 | 7 |
| AC008875.2 | 7 |
| AC245100.1 | 7 |
| PCDHB18P | 6 |
| KLHDC8A | 5 |
| LINC02393 | 5 |
| AL021808.1 | 4 |
| HCK | 3 |
| SHCBP1L | 3 |
| AC091180.5 | 3 |
| CRYGD | 2 |
| MYT1L-AS1 | 2 |

## Lower-Confidence Selected CpGs

No selected CpGs were promoter-positive only through a secondary isoform while nearest-TSS `functional_region` was `gene_body`.

## Interpretation Guardrail

The `predicted_expression_effect` labels are hypotheses from methylation mechanics, not measured RNA expression. Non-promoter sites remain ambiguous by design.
