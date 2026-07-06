# START HERE — BRCA DNA-Methylation Project Results

A guide to what's in this folder and what to open first. Everything here is derived from
**TCGA-BRCA (888 samples)** and **GSE66695 (120 samples)**, both **Illumina HM450 array** data.

---

## 🖥 Best for presenting — open the one-page overview (HTML)

**`Results_Presentation.html`** — double-click to open in any web browser. A single, self-contained
page with everything in plain English: what we did, the hyper/hypo numbers, the site locations, the
figures (volcano / PCA / heatmap), the FGF2 example, and a map of where every result file lives.
Nothing to install; works offline.

## 📄 If you have 5 minutes — open the Reports (Word)

`Reports/` (read in this order):

1. **`0_Dataset_Overview.docx`** — what data we used, where it came from, how credible it is.
2. **`1_Methylation_Pipeline_and_Validation.docx`** — *plain English*: how the whole analysis
   works and the two independent checks proving the result is real.
3. **`2_Gene_and_Site_Level_Findings.docx`** — *plain English*: hyper/hypo-methylation at the
   gene and single-site level, including the FGF2 finding.

*(`0_Dataset_Overview_details.md` is the long technical version of the dataset document.)*

## 📊 If you want to explore the data — open the Dashboard

`Dashboard/Longevity_Methylation_Atlas.xlsx` — an interactive Excel workbook: an Overview sheet
plus one sheet per longevity category (telomere, stem-cell, mitochondrial, FGF, FGF21-Klotho).
Every CpG site is color-coded by its healthy-tissue methylation state: 🟢 unmethylated/active ·
🟡 intermediate · 🔴 methylated/silenced.

## 🖼 Figures

`Figures/` — `volcano.png` (effect vs. confidence for every site), `pca.png` (tumor vs. normal
separate cleanly), `heatmap.png` (top markers).

## 🔢 The numbers behind the reports

`Data_Tables/` — organized to match the analysis flow:

| Folder | What's inside |
|---|---|
| `1_Differential_Methylation` | Marker tables + the 100-gene candidate panel + summary counts |
| `2_Validation` | Leakage audit (Validation 1) |
| `3_Site_Annotation` | Probe → region/promoter/island annotation coverage |
| `4_Biomarker_Panel_and_Sites` | The 20-CpG panel + per-gene site-map narrative |
| `5_Pathway_and_GSEA` | Pathway enrichment + the bias-corrected GSEA verdict |
| `6_Healthy_Baseline_Atlas` | Healthy-tissue site atlas: category summary + per-category tables |

*(Very large raw tables — e.g. the full 486k-probe differential-methylation matrix — stay in
`project_b/outputs/` and are regenerable from the scripts; only the small, presentable tables are
copied here.)*

---

## The one-paragraph takeaway

Breast tumors carry a **strong, real, reproducible** DNA-methylation signature (near-perfect
tumor/normal separation, validated internally *and* in an independent cohort). We mapped every
change to its exact gene and site, and predicted ~99,000 gene-silencing and ~61,000 gene-activating
events. The **confident findings are at the site level** (e.g. the FGF2 promoter is unmethylated/
active in healthy tissue and becomes silenced in tumor). Broad **pathway-level** longevity claims
did **not** survive rigorous statistical correction, so we report those honestly as a negative
result and lead with the solid site-level evidence.
