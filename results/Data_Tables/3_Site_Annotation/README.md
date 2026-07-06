# Enriched probe annotation (Phase 0)

Built by `scripts/build_probe_annotation.py` from the Zhou-lab (sesame) hg38 manifest
`data/raw/HM450.hg38.manifest.gencode.v36.zhou.tsv.gz`. Coordinate-consistent with the
project's existing hg38 probeMap. Regenerate with:

```
python3 scripts/build_probe_annotation.py
```

## `probe_annotation_enriched.tsv` schema (key = `probe_id`)

| column | meaning |
|---|---|
| `probe_id` | HM450 CpG id (join key) |
| `chrom`, `chromStart`, `chromEnd`, `strand` | CpG genomic coordinates (hg38) |
| `genes_all` | all unique genes overlapping/near the probe (`;`-separated) |
| `gene_nearest` | gene of the nearest TSS |
| `dist_to_tss` | signed distance to nearest TSS. **negative = upstream (promoter side), positive = downstream (gene body)** |
| `functional_region` | `TSS200` (−200..0) · `TSS1500` (−1500..−200) · `5UTR_1stExon` (0..+500) · `gene_body` (>+500) · `upstream_distal` (<−1500) · `intergenic` (no TSS) |
| `is_promoter` | True if **any** isoform TSS falls in −1500..+500 of the CpG |
| `cgi_relation` | `Island` · `N_Shore` · `S_Shore` · `N_Shelf` · `S_Shelf` · `OpenSea` |
| `cgi_id` | CpG-island id (blank if OpenSea) |

## Promoter rule for downstream mechanics (Phase 1)

`is_promoter == True` → hyper-methylation = **silencing**, hypo = **activation**.
Otherwise (`gene_body`, `intergenic`) → **ambiguous** (in gene bodies hyper-methylation
often tracks *higher* expression, so do not assert silencing there).

## Coverage

485,577 probes annotated. 99.96% of FDR<0.05 significant probes are covered (118 absent
from the sesame manifest). ~13% of significant probes are genuinely `intergenic` — a real
Illumina 450K category, treat as `ambiguous`. See `annotation_coverage.{json,md}`.
