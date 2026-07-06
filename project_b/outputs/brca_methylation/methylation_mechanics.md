# Phase 1 - Methylation Mechanics

This phase adds a conservative predicted expression-effect label using Phase 0 probe-region annotation. The rule is intentionally narrow:

- promoter plus hypermethylated: `silencing`
- promoter plus hypomethylated: `activation`
- gene body, intergenic, distal, or unannotated probes: `ambiguous`

Promoter status comes from Phase 0's `is_promoter` flag, which captures any transcript/gene TSS within the promoter window. The label is not inferred from the sparse original probeMap or from gene names.

The biology caveat is central: promoter methylation can repress transcription by blocking or altering promoter-associated regulatory binding, but gene-body methylation often tracks active transcription and can have different or context-dependent effects. Therefore, this table does not assert silencing outside promoter/TSS context.

These labels are hypotheses about likely expression direction, not measured RNA-expression effects.

## Counts

| set | silencing | activation | ambiguous |
|---|---:|---:|---:|
| full significant set (`fdr < 0.05`) | 98839 | 60755 | 162229 |
| full candidate panel (all rows) | 55 | 1 | 44 |
| top-20 candidate panel | 14 | 0 | 6 |

The full significant set has `118` rows without Phase 0 annotation; `118` of them are `ctl_` control probes. They are labeled `ambiguous`, not assigned a biological region.
