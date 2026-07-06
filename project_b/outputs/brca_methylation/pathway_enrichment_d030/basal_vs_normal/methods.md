# Methods: basal_vs_normal

- command: `python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --min-abs-delta-beta 0.3 --fdr-threshold 0.05 --comparisons tumor_vs_normal basal_vs_normal --output-name pathway_enrichment_d030`
- CpG threshold: `fdr < 0.05` and `abs_delta_beta >= 0.3`
- significant probe-to-gene mapping: split `gene` on `;` and `,`, drop empty genes, deduplicate at gene level
- background definition: unique genes mapped from `tumor_vs_normal/probe_missingness.tsv` rows where `retained == True`
- retained background probes: `382924`
- background genes: `33010`
- enrichment method: one-sided hypergeometric over-representation analysis using SciPy
- SciPy version: `1.13.1`
- multiple-testing correction: Benjamini-Hochberg FDR, per library and per direction
- gene-level query sets: combined, hypermethylated only, and hypomethylated only
- gene-set source: Enrichr GMT endpoint cached to `pathway_enrichment_d030/gene_sets/`
- gene-set libraries: `GO_Biological_Process_2023, GO_Molecular_Function_2023, GO_Cellular_Component_2023, KEGG_2021_Human, Reactome_2022`
- gene-set library labels/version years are encoded in the Enrichr library names; cache download date is `2026-06-29` when first retrieved
