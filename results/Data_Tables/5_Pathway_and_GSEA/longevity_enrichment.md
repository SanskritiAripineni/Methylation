# Phase 3 - Longevity Gene-Set ORA

## Method

Gene sets were selected from public Enrichr GMT libraries, cached locally, and tested with the same pure-Python one-sided hypergeometric ORA helper used by `run_pathway_enrichment.py`.
The query gate was `fdr < 0.05` and `abs_delta_beta >= 0.2` on the full `differential_methylation_mechanics.tsv` table.
Query genes were taken from Phase 0/1 gene annotation (`genes_all`, falling back to `gene`, with `gene_nearest` added when distinct).
Background universe: unique genes from `tumor_vs_normal/probe_missingness.tsv` rows where `retained == True`, matching the existing pathway pipeline. This gives `33010` background genes from `382924` retained probes.

## Counts

- gated CpGs: `31083`
- hypermethylated gated CpGs: `16623`
- hypomethylated gated CpGs: `14460`
- hypermethylated query genes before background intersection: `6435`
- hypomethylated query genes before background intersection: `6284`
- curated longevity sets: `14`

## Top ORA Results

| direction | term | n_genes | query_size | overlap_n | overlap_genes | p | adj_p |
|---|---|---|---|---|---|---|---|
| hypermethylated | kegg_pluripotency_stem_cell_signaling | 139 | 6368 | 55 | ACVR1,ACVR2A,AKT2,AKT3,APC,APC2,BMP4,BMPR1A,DLX5,ESRRB,FGF2,FGFR1,FZD10,FZD5,FZD7,HAND1,HOXA1,HOXD1,ID1,ID4,IGF1,INHBA,ISL1,JAK1,JAK3,JARID2,LEFTY2,LHX5,LIFR,MAPK3,MEIS1,MYF5,NANOG,NODAL,ONECUT1,OTX1,PAX6,PIK3CA,PIK3CD,PIK3R1,RIF1,SMAD3,SMAD4,SOX2,WNT1,WNT10A,WNT11,WNT16,WNT2,WNT3,WNT3A,WNT5B,WNT7B,WNT9B,ZFHX3 | 2.459e-08 | 3.442e-07 |
| hypermethylated | reactome_pluripotent_stem_cell_transcription | 28 | 6368 | 18 | CDX2,DKK1,EOMES,EPHA1,FOXD3,GATA6,GSC,HIF3A,LIN28A,NANOG,NR5A1,PBX1,PRDM14,SALL1,SALL4,SMAD4,SOX2,ZSCAN10 | 2.369e-07 | 1.658e-06 |
| hypermethylated | go_positive_regulation_stem_cell_differentiation | 17 | 6368 | 10 | FOXC1,HOXB4,LTBP2,NKX2-5,SOX5,SOX6,SOX9,TBX5,TCF15,TGFB2 | 3.615e-04 | 1.687e-03 |
| hypermethylated | kegg_ampk_signaling | 116 | 6368 | 35 | AKT2,AKT3,CAMKK2,CCNA1,CFTR,CPT1A,CPT1B,CPT1C,CREB3L1,CREB3L2,CREB5,CRTC2,EEF2K,GYS1,IGF1,LEP,LEPR,PFKFB2,PFKFB4,PFKP,PIK3CA,PIK3CD,PIK3R1,PPP2R2A,PPP2R2B,PPP2R2C,PPP2R3A,PPP2R5C,RAB8A,RPTOR,SCD5,STK11,STRADA,TBC1D1,TSC2 | 3.244e-03 | 1.136e-02 |
| hypermethylated | kegg_mtor_signaling | 150 | 6368 | 39 | AKT2,AKT3,ATP6V1B1,ATP6V1B2,ATP6V1E2,ATP6V1G2,BRAF,CLIP1,EIF4E1B,FNIP2,FZD10,FZD5,FZD7,IGF1,LRP5,MAPK3,PIK3CA,PIK3CD,PIK3R1,PRKCB,PRKCG,PRR5,RPTOR,SESN2,SGK1,SLC3A2,STK11,STRADA,TSC2,WNT1,WNT10A,WNT11,WNT16,WNT2,WNT3,WNT3A,WNT5B,WNT7B,WNT9B | 2.674e-02 | 7.487e-02 |
| hypomethylated | kegg_ampk_signaling | 116 | 6052 | 32 | ACACA,ADIPOR1,ADRA1A,AKT3,CCNA1,CCND1,CD36,CFTR,CREB5,EIF4EBP1,FOXO3,IGF1,IGF1R,INSR,LEPR,PDPK1,PFKFB2,PFKP,PIK3CB,PIK3CD,PIK3R1,PPARGC1A,PPP2CB,PPP2R2B,PPP2R3A,PPP2R5A,PRKAG2,RAB11B,RAB2A,RPTOR,SREBF1,STRADB | 9.209e-03 | 1.289e-01 |
| hypomethylated | go_positive_regulation_stem_cell_differentiation | 17 | 6052 | 7 | PTN,SIRT6,SOX5,SOX6,TBX5,TCF15,TGFB2 | 2.421e-02 | 1.695e-01 |
| hypermethylated | kegg_foxo_signaling | 126 | 6368 | 29 | AKT2,AKT3,BNIP3,BRAF,CCND2,CDKN1A,CREBBP,CSNK1E,EGFR,FOXG1,GRM1,HOMER1,IGF1,MAPK10,MAPK3,PIK3CA,PIK3CD,PIK3R1,S1PR1,SGK1,SMAD3,SMAD4,SOD2,STK11,TGFB2,TGFBR1,TGFBR2,TPTEP2-CSNK1E,USP7 | 1.707e-01 | 3.983e-01 |
| hypermethylated | reactome_telomere_extension_by_telomerase | 22 | 6368 | 6 | CCNA1,PIF1,RUVBL1,RUVBL2,TERF2,TERT | 2.393e-01 | 4.688e-01 |
| hypermethylated | reactome_telomere_maintenance | 85 | 6368 | 19 | CCNA1,CTC1,DAXX,DSCC1,H2AC14,H2BC14,H2BC15,H2BC3,PIF1,POLA2,POLD2,POLR2F,POLR2L,RUVBL1,RUVBL2,SLC19A1,TERF2,TERT,WRN | 2.752e-01 | 4.688e-01 |
| hypermethylated | reactome_foxo_mediated_transcription | 62 | 6368 | 14 | AKT2,AKT3,CDKN1A,CREBBP,FOXG1,NFYC,NPY,NR3C1,PLXNA4,POMC,SMAD3,SMAD4,STK11,YWHAG | 3.014e-01 | 4.688e-01 |
| hypermethylated | go_negative_regulation_stem_cell_differentiation | 12 | 6368 | 3 | HES5,NOTCH1,TCF15 | 4.164e-01 | 5.830e-01 |
| hypermethylated | reactome_mtor_signaling | 40 | 6368 | 8 | AKT2,EEF2K,EIF4G1,FKBP1A,RPTOR,STK11,STRADA,TSC2 | 5.180e-01 | 6.592e-01 |
| hypermethylated | reactome_transcriptional_activation_mitochondrial_biogenesis | 49 | 6368 | 8 | CHD9,CREBBP,CRTC1,CRTC2,MEF2C,MEF2D,NR1D1,RXRA | 7.543e-01 | 8.481e-01 |
| hypermethylated | reactome_lkb1_ampk_mtor_energy_regulation | 28 | 6368 | 4 | RPTOR,STK11,STRADA,TSC2 | 8.168e-01 | 8.481e-01 |
| hypermethylated | reactome_mitochondrial_biogenesis | 84 | 6368 | 13 | ATP5MC2,ATP5PB,CHCHD6,CHD9,CREBBP,CRTC1,CRTC2,MEF2C,MEF2D,MICOS10,NR1D1,RXRA,TMEM11 | 8.481e-01 | 8.481e-01 |
| hypomethylated | kegg_foxo_signaling | 126 | 6052 | 26 | AKT3,C8orf44-SGK3,CCND1,CCND2,CCNG2,EGF,EGFR,FOXO3,GRB2,GRM1,HOMER1,IGF1,IGF1R,IL6,INSR,MAPK10,MAPK13,NLK,PDPK1,PIK3CB,PIK3CD,PIK3R1,PRKAG2,SOS2,TGFB2,TNFSF10 | 2.843e-01 | 9.286e-01 |
| hypomethylated | kegg_pluripotency_stem_cell_signaling | 139 | 6052 | 28 | AKT3,APC2,BMPR1B,COMMD3-BMI1,ESRRB,FGFR2,GRB2,IGF1,IGF1R,INHBB,JARID2,KAT6A,LEFTY1,LIFR,MAPK13,MEIS1,NODAL,PCGF3,PIK3CB,PIK3CD,PIK3R1,POU5F1,REST,SMAD2,SMAD9,WNT5B,WNT7A,ZFHX3 | 3.224e-01 | 9.286e-01 |
| hypomethylated | reactome_pluripotent_stem_cell_transcription | 28 | 6052 | 6 | DPPA4,EPHA1,FOXP1,PBX1,SALL1,SMAD2 | 4.094e-01 | 9.286e-01 |
| hypomethylated | reactome_foxo_mediated_transcription | 62 | 6052 | 12 | AKT3,CCNG2,FOXO3,HDAC1,NFYC,NPY,PLXNA4,PPARGC1A,SMAD2,SREBF1,YWHAG,YWHAZ | 4.687e-01 | 9.286e-01 |

## Significant Results

| direction | term | overlap_n | overlap_genes | p | adj_p |
|---|---|---|---|---|---|
| hypermethylated | kegg_pluripotency_stem_cell_signaling | 55 | ACVR1,ACVR2A,AKT2,AKT3,APC,APC2,BMP4,BMPR1A,DLX5,ESRRB,FGF2,FGFR1,FZD10,FZD5,FZD7,HAND1,HOXA1,HOXD1,ID1,ID4,IGF1,INHBA,ISL1,JAK1,JAK3,JARID2,LEFTY2,LHX5,LIFR,MAPK3,MEIS1,MYF5,NANOG,NODAL,ONECUT1,OTX1,PAX6,PIK3CA,PIK3CD,PIK3R1,RIF1,SMAD3,SMAD4,SOX2,WNT1,WNT10A,WNT11,WNT16,WNT2,WNT3,WNT3A,WNT5B,WNT7B,WNT9B,ZFHX3 | 2.459e-08 | 3.442e-07 |
| hypermethylated | reactome_pluripotent_stem_cell_transcription | 18 | CDX2,DKK1,EOMES,EPHA1,FOXD3,GATA6,GSC,HIF3A,LIN28A,NANOG,NR5A1,PBX1,PRDM14,SALL1,SALL4,SMAD4,SOX2,ZSCAN10 | 2.369e-07 | 1.658e-06 |
| hypermethylated | go_positive_regulation_stem_cell_differentiation | 10 | FOXC1,HOXB4,LTBP2,NKX2-5,SOX5,SOX6,SOX9,TBX5,TCF15,TGFB2 | 3.615e-04 | 1.687e-03 |
| hypermethylated | kegg_ampk_signaling | 35 | AKT2,AKT3,CAMKK2,CCNA1,CFTR,CPT1A,CPT1B,CPT1C,CREB3L1,CREB3L2,CREB5,CRTC2,EEF2K,GYS1,IGF1,LEP,LEPR,PFKFB2,PFKFB4,PFKP,PIK3CA,PIK3CD,PIK3R1,PPP2R2A,PPP2R2B,PPP2R2C,PPP2R3A,PPP2R5C,RAB8A,RPTOR,SCD5,STK11,STRADA,TBC1D1,TSC2 | 3.244e-03 | 1.136e-02 |

## Null Or Non-Significant Sets

reactome_telomere_maintenance, reactome_telomere_extension_by_telomerase, reactome_mitochondrial_biogenesis, reactome_transcriptional_activation_mitochondrial_biogenesis, go_negative_regulation_stem_cell_differentiation, kegg_foxo_signaling, kegg_mtor_signaling, reactome_mtor_signaling, reactome_lkb1_ampk_mtor_energy_regulation, reactome_foxo_mediated_transcription

## Artifact And Interpretation Caveat

The HM450 array is enriched for CpG-island/promoter probes and has a known neuronal/developmental probe-composition artifact that can inflate developmental and neural terms. This analysis partially controls for array composition by testing against the retained HM450 analyzable gene background rather than the whole genome, but it is not a full probe-number-bias correction such as missMethyl/gometh. Treat these enrichments as hypothesis-generating methylation associations, not causal longevity mechanisms or measured RNA-expression effects.
