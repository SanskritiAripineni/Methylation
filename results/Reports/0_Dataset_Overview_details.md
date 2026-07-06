# Datasets & Data Provenance — BRCA Methylation Project

A complete, bioinformatician-facing description of every dataset used: what it is, where it
came from (lab / company / consortium), how it was generated, its file format, its fields, and
its credibility. Accessions and access terms are listed so any result can be traced to source.

---

## Abstract

This project characterizes DNA-methylation differences between breast tumor and normal tissue and
maps them onto longevity/anti-aging genes. **All methylation data are Illumina Infinium
HumanMethylation450 (HM450) BeadChip *array* data — not sequencing.** The primary cohort is
**TCGA-BRCA** (888 samples) accessed via **UCSC Xena**; an independent **GEO** cohort
(**GSE66695**, 120 samples) provides external validation and a healthy baseline. Probe-to-genome
annotation uses the **UCSC Xena probeMap** and the **Zhou-lab (sesame) hg38 manifest**. Pathway
gene sets come from **KEGG / Reactome / GO** (via Enrichr), and the longevity gene catalog is a
supervisor-supplied **antibody-array** target list. No ArrayExpress, SRA, or dbGaP-controlled data
were used; all inputs are open-access processed data.

---

## Assay primer — how HM450 methylation is measured (important: it is an array, not sequencing)

The Illumina Infinium HumanMethylation450 BeadChip interrogates **~485,512 CpG sites** genome-wide.
Workflow: genomic DNA → **sodium bisulfite conversion** (unmethylated C → U/T; methylated C stays C)
→ whole-genome amplification → hybridization to bead-bound probes → single-base extension with
labeled nucleotides → two-color (Cy3/Cy5) scan. Two probe chemistries (Infinium Type I and Type II)
are combined.

- **Measurement unit:** *beta value* β = M / (M + U + 100), where M = methylated and U =
  unmethylated intensity. β ∈ [0, 1]: 0 = fully unmethylated, 1 = fully methylated.
- **What "sequenced" means here:** there are **no reads or coverage** — the platform is
  hybridization-based, so every sample has the *same fixed ~485k probe set*. A CpG not on the chip
  simply does not exist in the data. (This fixed, CpG-island-biased probe design is the origin of
  the enrichment "probe-number artifact" discussed in the analysis reports.)

---

## Dataset 1 — TCGA-BRCA HM450 methylation matrix  *(primary discovery data)*

| Field | Value |
|---|---|
| **What** | Genome-wide CpG methylation β-values for TCGA breast-cancer cohort |
| **Producer / provenance** | **The Cancer Genome Atlas (TCGA)** — a joint **NCI + NHGRI (US NIH)** program; harmonized by the **Genomic Data Commons (GDC)** |
| **Accessed via** | **UCSC Xena** GDC hub (Goldman et al. 2020, *Nat Biotechnol*) — `TCGA-BRCA.methylation450.tsv.gz` |
| **Platform** | Illumina Infinium HumanMethylation450 BeadChip (GPL13534) |
| **Processing level** | GDC Level-3 processed β-values (background-corrected, normalized) |
| **File format** | Gzip-compressed TSV; matrix = **probes (rows) × samples (columns)** |
| **Row key** | `Composite Element REF` = Illumina probe ID (e.g. `cg00000029`) |
| **Values** | β ∈ [0,1]; missing = `NA` |
| **Dimensions** | ~485k probes × ~888 BRCA samples (columns = TCGA barcodes, e.g. `TCGA-XX-XXXX-01A`) |
| **Cohort used** | **791 Primary Tumor + 97 Solid Tissue Normal = 888** |
| **Genome build** | Coordinates supplied by the probeMap (hg38 / GENCODE v36); the matrix itself is probe-indexed |
| **Credibility** | ★★★★★ Gold standard — the most widely used, peer-reviewed cancer-genomics resource; tens of thousands of citations |
| **License / access** | Open-access tier (processed β-values are non-controlled; no dbGaP needed) |
| **Known limitations** | "Solid Tissue Normal" is **tumor-adjacent** normal, not disease-free donor tissue (possible field effects); batch effects across TCGA plates |

## Dataset 2 — TCGA-BRCA clinical / phenotype

| Field | Value |
|---|---|
| **What** | Per-sample clinical and demographic annotation |
| **Provenance / via** | TCGA/GDC via UCSC Xena — `TCGA-BRCA.clinical.tsv.gz` |
| **Format** | Gzip TSV, samples (rows) × attributes (columns) |
| **Key fields** | `sample`, `disease_type`, `primary_site`, `gender.demographic`, `race.demographic`, `age_at_index.demographic`, `vital_status.demographic`, `days_to_death.demographic`, tissue-source-site codes |
| **Used for** | Deriving the tumor/normal label and cohort manifest |
| **Credibility** | ★★★★★ (same TCGA/GDC provenance) |

## Dataset 3 — TCGA-BRCA molecular subtypes

| Field | Value |
|---|---|
| **What** | Curated molecular subtype + multi-omic cluster calls for TCGA breast tumors |
| **Provenance** | TCGA marker/PanCancer papers, distributed via UCSC Xena — `TCGA-BRCA.subtypes.tsv` |
| **Format** | Plain TSV, patients × attributes |
| **Key fields** | `BRCA_Subtype_PAM50` (Luminal A/B, Basal, HER2, Normal), `BRCA_Pathology`, `pathologic_stage`, `Tumor_Grade`, `DNA.Methylation Clusters`, `mRNA/miRNA/CNV/Protein Clusters` |
| **Used for** | Subtype comparisons (basal vs normal, luminal-A vs normal, basal vs non-basal) |
| **Credibility** | ★★★★★ (peer-reviewed TCGA consortium calls; PAM50 is the standard intrinsic-subtype classifier) |

## Dataset 4 — HM450 probe annotation (UCSC Xena probeMap)

| Field | Value |
|---|---|
| **What** | Probe → gene + genomic-coordinate map |
| **Provenance** | UCSC Xena probeMap resource — `HM450.hg38.manifest.gencode.v36.probeMap` |
| **Format** | TSV; fields: `#id, gene, chrom, chromStart, chromEnd, strand` |
| **Genome build** | hg38, GENCODE v36 |
| **Used for** | Baseline gene/coordinate lookup in the original pipeline |
| **Credibility** | ★★★★ Standard, but sparse (gene + coordinate only; no region/island context) |

## Dataset 5 — HM450 sesame / Zhou-lab hg38 manifest  *(annotation upgrade)*

| Field | Value |
|---|---|
| **What** | Rich probe annotation: signed distance-to-TSS, transcript context, CpG-island position |
| **Producer / provenance** | **Zhou Lab** (Wanding Zhou; Van Andel Institute / CHOP) — the *sesame* / InfiniumAnnotation project |
| **Reference** | Zhou, Laird & Shen 2017, *Nucleic Acids Research* 45(4):e22 |
| **Accessed via** | Zhou-lab GitHub `InfiniumAnnotation` — `HM450.hg38.manifest.gencode.v36.tsv.gz` |
| **Format** | Gzip TSV; fields incl. `CpG_chrm, CpG_beg, CpG_end, probe_strand, probeID, genesUniq, geneNames, transcriptIDs, distToTSS, CGI, CGIposition` |
| **Genome build** | hg38, GENCODE v36 |
| **Used for** | Phase 0 enriched annotation (functional region, promoter flag, island context) |
| **Credibility** | ★★★★★ The de-facto community standard for Infinium probe annotation |

## Dataset 6 — GSE66695  *(external validation + healthy baseline)*

| Field | Value |
|---|---|
| **What** | Genome-wide HM450 methylation of breast cancer vs normal |
| **Producer / provenance** | **Worsham Lab, Henry Ford Health System (Detroit, MI)** — contributors: M.J. Worsham, D. Chitale, G. Divine, I. Datta, K.M. Chen |
| **Repository / accession** | **NCBI GEO**, series **GSE66695** (title: "Genome-wide Scan for Methylation Profiles in Breast Cancer"); submitted 2015-03-09 |
| **Platform** | Illumina HumanMethylation450 BeadChip (**GPL13534**) |
| **Molecule / extraction** | Genomic DNA, **Qiagen DNeasy Kit** |
| **Processing** | Illumina **GenomeStudio V2011.1**; scan labels Cy5/Cy3 |
| **Format** | GEO series-matrix (gzip TSV): probes (`ID_REF`) × samples (`GSM…`), β-values, with a metadata header block |
| **Samples** | **120 total = 80 tumor + 40 normal** (labels verified across four metadata fields) |
| **Used for** | Validation 2 (independent replication) and the combined healthy baseline |
| **Credibility** | ★★★★ Peer-reviewed public dataset; smaller cohort; different lab/prep than TCGA → treat cross-cohort β-shifts as descriptive, not batch-corrected |
| **License / access** | Open (GEO public) |

## Dataset 7 — Longevity / Anti-Aging antibody-array catalog  *(supervisor-supplied gene sets)*

| Field | Value |
|---|---|
| **What** | Curated longevity/anti-aging **protein** target list, grouped into aging categories |
| **Producer / provenance** | Supervisor-supplied — `Longevity_AntiAging_AllBLG1-16.xlsx`; derived from **16 semi-quantitative antibody microarrays** (labeled BLG-1 … BLG-16 / "SA4 arrays"). **Vendor/manufacturer not yet confirmed — verify with supervisor.** |
| **Assay type** | **Antibody microarray (protein-level)** — NOT a methylation or sequencing assay; used here only as a *gene-set definition* |
| **Format** | Excel `.xlsx`; sheets = Summary, Full List, + 40 per-category sheets. Fields: `#, Protein / Target Name, Gene Symbol, UniProt ID, Gene ID (Entrez), Category, Description` |
| **Content** | **1,964 protein entries → 1,953 unique genes across 40 aging categories** (telomere, sirtuins, AMPK/FOXO/mTOR, autophagy, DNA repair, senescence, mitochondrial, FGF/FGF21-Klotho, stem cell, etc.) |
| **Used for** | Custom longevity gene sets for enrichment and the healthy-baseline site atlas |
| **Credibility** | ★★☆ **Weakest-provenance source.** Gene identities are solid (UniProt + Entrez verified), but the **category groupings are curatorial/vendor-defined, not peer-reviewed pathway definitions** (e.g. the "Telomere Maintenance" set includes ICAM1/2/3). Present as custom sets, not validated pathways. |

---

## Reference resources (not sample data — analytical knowledge bases / tools)

| Resource | Role | Provenance | Credibility |
|---|---|---|---|
| **KEGG** | pathway gene sets | Kanehisa Labs | ★★★★★ |
| **Reactome** | pathway gene sets | EMBL-EBI / OICR | ★★★★★ |
| **Gene Ontology (GO)** | functional gene sets | GO Consortium | ★★★★★ |
| **Enrichr** | delivery of the above GMT libraries | Ma'ayan Lab, Mount Sinai (Chen 2013; Kuleshov 2016) | ★★★★★ |
| **missMethyl (gometh/gsameth)** | probe-number-bias-corrected enrichment | Phipson, Maksimovic & Oshlack 2016, *Bioinformatics* | ★★★★★ |
| **methylGSA (methylRRA)** | rank-based methylation GSEA | Ren & Kuan 2019, *Bioinformatics* | ★★★★★ |

---

## Credibility summary

- **Top-tier, fully reproducible:** TCGA/UCSC-Xena (1–4), Zhou sesame manifest (5), GEO/GSE66695 (6),
  KEGG/Reactome/GO + missMethyl/methylGSA (reference resources). All primary findings rest on these.
- **Use with disclosure:** the supervisor longevity catalog (7) — real genes, but non-standard,
  vendor/curatorial category groupings; and the antibody-array **vendor is unconfirmed**.
- **Not used:** ArrayExpress, SRA, dbGaP-controlled data, or any raw sequencing.

## Data availability / accessions
- TCGA-BRCA: GDC (portal.gdc.cancer.gov) / UCSC Xena (xenabrowser.net) — project `TCGA-BRCA`.
- GSE66695: NCBI GEO — https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE66695 (PubMed ID to be confirmed on the GEO record).
- HM450 sesame manifest: github.com/zhou-lab/InfiniumAnnotation (Zhou et al. 2017, NAR 45:e22).
- Longevity catalog: internal (supervisor); antibody-array vendor to be confirmed.
