# Threshold Summary: pathway_enrichment_d040

- command: `python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --min-abs-delta-beta 0.4 --fdr-threshold 0.05 --comparisons tumor_vs_normal basal_vs_normal --output-name pathway_enrichment_d040`

| comparison | significant probes | hyper probes | hypo probes | significant genes | hyper genes | hypo genes |
|---|---:|---:|---:|---:|---:|---:|
| tumor_vs_normal | 823 | 612 | 211 | 721 | 561 | 169 |
| basal_vs_normal | 1016 | 753 | 263 | 690 | 493 | 205 |

## Top 15 Terms Per Library

### tumor_vs_normal

#### GO_BP

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 92 | 1.423e-20 | 7.692e-17 |
| combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 107 | 2.182e-20 | 1.180e-16 |
| combined | Regulation Of DNA-templated Transcription (GO:0006355) | 98 | 2.420e-17 | 6.544e-14 |
| hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 83 | 5.426e-17 | 1.467e-13 |
| combined | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 53 | 4.537e-11 | 8.176e-08 |
| combined | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 62 | 1.952e-10 | 2.639e-07 |
| hypermethylated | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 44 | 2.937e-10 | 5.293e-07 |
| hypermethylated | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 52 | 4.612e-10 | 6.234e-07 |
| combined | Nervous System Development (GO:0007399) | 32 | 6.496e-10 | 7.024e-07 |
| combined | Neuron Differentiation (GO:0030182) | 19 | 3.535e-09 | 3.186e-06 |
| combined | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 50 | 5.604e-09 | 4.328e-06 |
| combined | Eye Development (GO:0001654) | 11 | 1.565e-08 | 1.058e-05 |
| hypermethylated | Eye Development (GO:0001654) | 10 | 1.816e-08 | 1.964e-05 |
| hypermethylated | Neuron Differentiation (GO:0030182) | 16 | 2.266e-08 | 2.042e-05 |
| hypermethylated | Embryonic Organ Morphogenesis (GO:0048562) | 9 | 4.494e-08 | 3.471e-05 |

#### GO_MF

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 68 | 4.306e-26 | 4.939e-23 |
| hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 59 | 4.056e-25 | 4.652e-22 |
| hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 56 | 1.610e-24 | 9.231e-22 |
| hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 57 | 1.734e-23 | 6.631e-21 |
| combined | Sequence-Specific DNA Binding (GO:0043565) | 64 | 4.180e-23 | 2.397e-20 |
| combined | Double-Stranded DNA Binding (GO:0003690) | 60 | 3.579e-22 | 1.119e-19 |
| combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 83 | 3.902e-22 | 1.119e-19 |
| hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 72 | 5.269e-22 | 1.511e-19 |
| combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 73 | 1.460e-18 | 3.349e-16 |
| hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 62 | 1.004e-17 | 2.304e-15 |
| combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 69 | 7.453e-17 | 1.425e-14 |
| hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 58 | 8.458e-16 | 1.617e-13 |
| combined | Transcription Cis-Regulatory Region Binding (GO:0000976) | 40 | 4.045e-14 | 6.628e-12 |
| hypermethylated | Transcription Cis-Regulatory Region Binding (GO:0000976) | 33 | 1.635e-12 | 2.679e-10 |
| combined | DNA-binding Transcription Activator Activity, RNA Polymerase II-specific (GO:0001228) | 25 | 6.091e-08 | 8.733e-06 |

#### GO_CC

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Intracellular Membrane-Bounded Organelle (GO:0043231) | 155 | 7.671e-08 | 2.476e-05 |
| combined | Nucleus (GO:0005634) | 138 | 1.045e-07 | 2.476e-05 |
| hypermethylated | Nucleus (GO:0005634) | 105 | 1.006e-05 | 2.494e-03 |
| hypermethylated | Collagen-Containing Extracellular Matrix (GO:0062023) | 19 | 1.052e-05 | 2.494e-03 |
| combined | Collagen-Containing Extracellular Matrix (GO:0062023) | 21 | 3.330e-05 | 5.262e-03 |
| hypermethylated | Intracellular Membrane-Bounded Organelle (GO:0043231) | 115 | 3.589e-05 | 5.670e-03 |
| hypermethylated | GABA-ergic Synapse (GO:0098982) | 4 | 7.116e-05 | 8.432e-03 |
| combined | GABA-ergic Synapse (GO:0098982) | 4 | 1.857e-04 | 2.201e-02 |
| combined | Neuron Projection (GO:0043005) | 25 | 2.392e-04 | 2.267e-02 |
| hypomethylated | Intracellular Membrane-Bounded Organelle (GO:0043231) | 41 | 3.280e-04 | 1.555e-01 |
| hypermethylated | Postsynaptic Specialization Membrane (GO:0099634) | 4 | 3.119e-03 | 2.353e-01 |
| hypermethylated | AMPA Glutamate Receptor Complex (GO:0032281) | 3 | 3.261e-03 | 2.353e-01 |
| hypermethylated | Polymeric Cytoskeletal Fiber (GO:0099513) | 11 | 3.695e-03 | 2.353e-01 |
| hypermethylated | Neuron Projection (GO:0043005) | 18 | 3.971e-03 | 2.353e-01 |
| combined | AMPA Glutamate Receptor Complex (GO:0032281) | 3 | 6.528e-03 | 3.946e-01 |

#### KEGG

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Maturity onset diabetes of the young | 6 | 3.962e-06 | 1.268e-03 |
| combined | Maturity onset diabetes of the young | 6 | 1.634e-05 | 5.228e-03 |
| hypermethylated | MicroRNAs in cancer | 16 | 3.785e-05 | 6.056e-03 |
| combined | MicroRNAs in cancer | 18 | 6.838e-05 | 1.094e-02 |
| combined | Transcriptional misregulation in cancer | 13 | 1.340e-04 | 1.429e-02 |
| combined | Type II diabetes mellitus | 6 | 4.073e-04 | 3.258e-02 |
| hypermethylated | Transcriptional misregulation in cancer | 10 | 8.861e-04 | 7.646e-02 |
| hypermethylated | Type II diabetes mellitus | 5 | 9.558e-04 | 7.646e-02 |
| combined | cAMP signaling pathway | 12 | 2.189e-03 | 1.177e-01 |
| combined | Insulin secretion | 7 | 2.207e-03 | 1.177e-01 |
| hypermethylated | Neomycin, kanamycin and gentamicin biosynthesis | 2 | 2.767e-03 | 1.771e-01 |
| hypermethylated | Morphine addiction | 6 | 3.857e-03 | 2.057e-01 |
| combined | Neomycin, kanamycin and gentamicin biosynthesis | 2 | 4.511e-03 | 2.062e-01 |
| combined | Tight junction | 9 | 8.839e-03 | 3.053e-01 |
| combined | GABAergic synapse | 6 | 9.998e-03 | 3.053e-01 |

#### Reactome

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuronal System R-HSA-112316 | 24 | 1.882e-06 | 3.421e-03 |
| hypermethylated | Neuronal System R-HSA-112316 | 18 | 6.028e-05 | 1.096e-01 |
| hypermethylated | GPCR Downstream Signaling R-HSA-388396 | 22 | 4.284e-04 | 2.402e-01 |
| hypermethylated | Regulation Of Beta-Cell Development R-HSA-186712 | 5 | 4.895e-04 | 2.402e-01 |
| hypermethylated | Transmission Across Chemical Synapses R-HSA-112315 | 12 | 6.768e-04 | 2.402e-01 |
| hypermethylated | Neurotransmitter Receptors And Postsynaptic Signal Transmission R-HSA-112314 | 10 | 7.101e-04 | 2.402e-01 |
| hypermethylated | Signaling By GPCR R-HSA-372790 | 23 | 7.927e-04 | 2.402e-01 |
| hypermethylated | G Alpha (Z) Signaling Events R-HSA-418597 | 5 | 1.167e-03 | 3.031e-01 |
| combined | GPCR Downstream Signaling R-HSA-388396 | 26 | 4.679e-04 | 3.192e-01 |
| combined | Nef And Signal Transduction R-HSA-164944 | 3 | 5.267e-04 | 3.192e-01 |
| hypermethylated | Nuclear Receptor Transcription Pathway R-HSA-383280 | 5 | 1.691e-03 | 3.843e-01 |
| combined | Signaling By GPCR R-HSA-372790 | 27 | 1.096e-03 | 4.280e-01 |
| combined | Neurotransmitter Receptors And Postsynaptic Signal Transmission R-HSA-112314 | 11 | 1.351e-03 | 4.280e-01 |
| combined | Regulation Of Beta-Cell Development R-HSA-186712 | 5 | 1.490e-03 | 4.280e-01 |
| combined | Signal Transduction R-HSA-162582 | 72 | 1.882e-03 | 4.280e-01 |

### basal_vs_normal

#### GO_BP

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 89 | 2.066e-13 | 1.117e-09 |
| hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 71 | 3.128e-13 | 1.692e-09 |
| hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 67 | 3.363e-12 | 9.092e-09 |
| combined | Regulation Of DNA-templated Transcription (GO:0006355) | 81 | 3.920e-11 | 1.060e-07 |
| combined | Negative Regulation Of Transcription By RNA Polymerase II (GO:0000122) | 39 | 2.141e-08 | 3.859e-05 |
| combined | Chemical Synaptic Transmission (GO:0007268) | 21 | 1.054e-07 | 1.425e-04 |
| combined | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 44 | 1.415e-07 | 1.531e-04 |
| combined | Nervous System Development (GO:0007399) | 27 | 1.976e-07 | 1.582e-04 |
| combined | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 45 | 2.048e-07 | 1.582e-04 |
| hypermethylated | Neuron Differentiation (GO:0030182) | 14 | 1.914e-07 | 3.107e-04 |
| hypermethylated | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 35 | 2.298e-07 | 3.107e-04 |
| combined | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 51 | 9.745e-07 | 6.587e-04 |
| combined | Neuron Differentiation (GO:0030182) | 15 | 1.969e-06 | 1.183e-03 |
| hypermethylated | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 34 | 1.885e-06 | 1.753e-03 |
| hypermethylated | Negative Regulation Of Transcription By RNA Polymerase II (GO:0000122) | 28 | 1.945e-06 | 1.753e-03 |

#### GO_MF

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 73 | 4.673e-26 | 5.360e-23 |
| hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 52 | 2.796e-22 | 1.604e-19 |
| combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 81 | 4.317e-22 | 4.951e-19 |
| hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 49 | 1.823e-21 | 5.570e-19 |
| hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 51 | 1.942e-21 | 5.570e-19 |
| combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 58 | 6.847e-20 | 3.927e-17 |
| hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 60 | 3.514e-19 | 8.060e-17 |
| hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 59 | 5.250e-19 | 1.004e-16 |
| combined | Sequence-Specific DNA Binding (GO:0043565) | 55 | 7.984e-18 | 3.052e-15 |
| combined | Double-Stranded DNA Binding (GO:0003690) | 51 | 8.799e-17 | 2.239e-14 |
| combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 68 | 1.048e-16 | 2.239e-14 |
| combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 67 | 1.171e-16 | 2.239e-14 |
| combined | Transcription Cis-Regulatory Region Binding (GO:0000976) | 36 | 5.105e-12 | 8.365e-10 |
| hypermethylated | Transcription Cis-Regulatory Region Binding (GO:0000976) | 30 | 7.776e-12 | 1.274e-09 |
| combined | DNA-binding Transcription Activator Activity, RNA Polymerase II-specific (GO:0001228) | 24 | 1.119e-07 | 1.604e-05 |

#### GO_CC

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuron Projection (GO:0043005) | 25 | 1.278e-04 | 6.057e-02 |
| hypermethylated | Neuron Projection (GO:0043005) | 20 | 1.397e-04 | 6.621e-02 |
| combined | AMPA Glutamate Receptor Complex (GO:0032281) | 4 | 4.535e-04 | 1.075e-01 |
| combined | Postsynaptic Specialization Membrane (GO:0099634) | 5 | 8.559e-04 | 1.352e-01 |
| combined | Actin-Based Cell Projection (GO:0098858) | 7 | 1.412e-03 | 1.672e-01 |
| combined | Dendrite Membrane (GO:0032590) | 4 | 1.942e-03 | 1.672e-01 |
| combined | Polymeric Cytoskeletal Fiber (GO:0099513) | 13 | 2.354e-03 | 1.672e-01 |
| combined | GABA-ergic Synapse (GO:0098982) | 3 | 2.764e-03 | 1.672e-01 |
| combined | Voltage-Gated Calcium Channel Complex (GO:0005891) | 5 | 3.167e-03 | 1.672e-01 |
| combined | Synaptic Membrane (GO:0097060) | 4 | 3.333e-03 | 1.672e-01 |
| combined | Nuclear Stress Granule (GO:0097165) | 2 | 4.160e-03 | 1.672e-01 |
| combined | Ionotropic Glutamate Receptor Complex (GO:0008328) | 4 | 4.232e-03 | 1.672e-01 |
| combined | Postsynaptic Density Membrane (GO:0098839) | 4 | 4.232e-03 | 1.672e-01 |
| combined | Microvillus (GO:0005902) | 5 | 6.648e-03 | 2.424e-01 |
| combined | Dendrite (GO:0030425) | 12 | 7.208e-03 | 2.440e-01 |

#### KEGG

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Neuroactive ligand-receptor interaction | 16 | 2.240e-05 | 5.856e-03 |
| hypermethylated | Maturity onset diabetes of the young | 5 | 3.660e-05 | 5.856e-03 |
| combined | Neuroactive ligand-receptor interaction | 18 | 1.169e-04 | 2.837e-02 |
| combined | Maturity onset diabetes of the young | 5 | 1.773e-04 | 2.837e-02 |
| hypermethylated | Transcriptional misregulation in cancer | 8 | 5.083e-03 | 4.992e-01 |
| hypermethylated | Cardiac muscle contraction | 5 | 6.239e-03 | 4.992e-01 |
| hypermethylated | cAMP signaling pathway | 8 | 1.357e-02 | 8.683e-01 |
| hypermethylated | Bladder cancer | 3 | 2.022e-02 | 9.886e-01 |
| hypermethylated | Type I diabetes mellitus | 3 | 2.163e-02 | 9.886e-01 |
| hypermethylated | Arrhythmogenic right ventricular cardiomyopathy | 4 | 2.475e-02 | 9.900e-01 |
| hypomethylated | MicroRNAs in cancer | 6 | 9.268e-03 | 1.000e+00 |
| combined | Transcriptional misregulation in cancer | 9 | 1.187e-02 | 1.000e+00 |
| hypomethylated | Phototransduction | 2 | 1.205e-02 | 1.000e+00 |
| combined | cAMP signaling pathway | 10 | 1.275e-02 | 1.000e+00 |
| hypomethylated | Base excision repair | 2 | 1.669e-02 | 1.000e+00 |

#### Reactome

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Protein-protein Interactions At Synapses R-HSA-6794362 | 10 | 5.725e-06 | 1.041e-02 |
| hypermethylated | Class A/1 (Rhodopsin-like Receptors) R-HSA-373076 | 15 | 5.993e-05 | 8.463e-02 |
| hypermethylated | GPCR Ligand Binding R-HSA-500792 | 18 | 9.311e-05 | 8.463e-02 |
| hypermethylated | Regulation Of Gene Expression In Beta Cells R-HSA-210745 | 4 | 1.954e-04 | 8.965e-02 |
| hypermethylated | GPCR Downstream Signaling R-HSA-388396 | 21 | 1.973e-04 | 8.965e-02 |
| hypermethylated | Regulation Of Beta-Cell Development R-HSA-186712 | 5 | 2.732e-04 | 9.933e-02 |
| combined | Neurexins And Neuroligins R-HSA-6794361 | 7 | 1.111e-04 | 1.010e-01 |
| hypermethylated | Signaling By GPCR R-HSA-372790 | 22 | 3.407e-04 | 1.032e-01 |
| hypermethylated | Peptide Ligand-Binding Receptors R-HSA-375276 | 10 | 4.509e-04 | 1.171e-01 |
| hypomethylated | SUMOylation Of DNA Damage Response And Repair Proteins R-HSA-3108214 | 5 | 9.165e-05 | 1.666e-01 |
| hypermethylated | Phase 2 - Plateau Phase R-HSA-5576893 | 3 | 1.060e-03 | 2.346e-01 |
| hypermethylated | Protein-protein Interactions At Synapses R-HSA-6794362 | 6 | 1.180e-03 | 2.346e-01 |
| hypermethylated | Neuronal System R-HSA-112316 | 14 | 1.290e-03 | 2.346e-01 |
| hypermethylated | G Alpha (I) Signaling Events R-HSA-418594 | 12 | 1.721e-03 | 2.845e-01 |
| combined | Regulation Of Gene Expression In Beta Cells R-HSA-210745 | 4 | 6.947e-04 | 2.983e-01 |

