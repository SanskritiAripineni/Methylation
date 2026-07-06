# Threshold Summary: pathway_enrichment_top2000

- command: `python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --min-abs-delta-beta 0.2 --top-n-probes 2000 --fdr-threshold 0.05 --comparisons tumor_vs_normal basal_vs_normal --output-name pathway_enrichment_top2000`

| comparison | significant probes | hyper probes | hypo probes | significant genes | hyper genes | hypo genes |
|---|---:|---:|---:|---:|---:|---:|
| tumor_vs_normal | 2000 | 1315 | 685 | 1474 | 1045 | 463 |
| basal_vs_normal | 2000 | 1393 | 607 | 1187 | 762 | 441 |

## Top 15 Terms Per Library

### tumor_vs_normal

#### GO_BP

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 170 | 6.537e-37 | 3.535e-33 |
| combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 200 | 3.169e-32 | 1.713e-28 |
| hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 154 | 1.560e-30 | 4.217e-27 |
| combined | Regulation Of DNA-templated Transcription (GO:0006355) | 180 | 1.177e-25 | 3.181e-22 |
| combined | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 98 | 9.920e-17 | 1.788e-13 |
| hypermethylated | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 94 | 2.158e-16 | 3.889e-13 |
| combined | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 117 | 3.431e-16 | 4.637e-13 |
| hypermethylated | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 78 | 4.353e-16 | 5.885e-13 |
| combined | Nervous System Development (GO:0007399) | 56 | 8.900e-14 | 9.624e-11 |
| combined | Neuron Differentiation (GO:0030182) | 30 | 3.664e-11 | 3.302e-08 |
| hypermethylated | Embryonic Organ Morphogenesis (GO:0048562) | 14 | 4.149e-11 | 4.486e-08 |
| hypermethylated | Neuron Differentiation (GO:0030182) | 25 | 7.416e-11 | 6.683e-08 |
| hypermethylated | Endocrine System Development (GO:0035270) | 10 | 2.375e-10 | 1.835e-07 |
| combined | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 85 | 2.736e-10 | 1.961e-07 |
| combined | Endocrine System Development (GO:0035270) | 11 | 2.902e-10 | 1.961e-07 |

#### GO_MF

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 103 | 3.898e-41 | 4.471e-38 |
| combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 118 | 2.324e-38 | 2.665e-35 |
| hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 94 | 3.082e-37 | 1.375e-34 |
| hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 129 | 3.596e-37 | 1.375e-34 |
| hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 95 | 6.472e-35 | 1.856e-32 |
| combined | Double-Stranded DNA Binding (GO:0003690) | 104 | 3.413e-32 | 1.957e-29 |
| combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 147 | 5.617e-32 | 2.148e-29 |
| combined | Sequence-Specific DNA Binding (GO:0043565) | 107 | 6.684e-31 | 1.917e-28 |
| hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 113 | 8.633e-31 | 1.980e-28 |
| hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 107 | 4.923e-28 | 9.410e-26 |
| combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 131 | 2.312e-27 | 5.303e-25 |
| combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 124 | 1.071e-24 | 2.047e-22 |
| hypermethylated | Transcription Cis-Regulatory Region Binding (GO:0000976) | 58 | 4.558e-20 | 7.468e-18 |
| combined | Transcription Cis-Regulatory Region Binding (GO:0000976) | 69 | 8.249e-20 | 1.352e-17 |
| hypermethylated | DNA-binding Transcription Activator Activity, RNA Polymerase II-specific (GO:0001228) | 37 | 1.907e-11 | 2.734e-09 |

#### GO_CC

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Nucleus (GO:0005634) | 195 | 2.280e-09 | 1.080e-06 |
| combined | Nucleus (GO:0005634) | 256 | 6.496e-09 | 3.079e-06 |
| combined | Intracellular Membrane-Bounded Organelle (GO:0043231) | 285 | 2.362e-08 | 5.598e-06 |
| combined | Neuron Projection (GO:0043005) | 52 | 6.028e-08 | 9.524e-06 |
| hypermethylated | Intracellular Membrane-Bounded Organelle (GO:0043231) | 212 | 4.980e-08 | 1.180e-05 |
| combined | Calcium Channel Complex (GO:0034704) | 13 | 9.477e-07 | 9.762e-05 |
| combined | Dendrite (GO:0030425) | 30 | 1.030e-06 | 9.762e-05 |
| combined | Voltage-Gated Calcium Channel Complex (GO:0005891) | 11 | 6.167e-06 | 4.872e-04 |
| combined | Postsynaptic Density (GO:0014069) | 18 | 7.117e-05 | 4.820e-03 |
| combined | Postsynaptic Specialization Membrane (GO:0099634) | 8 | 1.449e-04 | 8.583e-03 |
| hypermethylated | Neuron Projection (GO:0043005) | 34 | 6.827e-05 | 1.079e-02 |
| combined | GABA-ergic Synapse (GO:0098982) | 5 | 2.423e-04 | 1.276e-02 |
| hypermethylated | Postsynaptic Specialization Membrane (GO:0099634) | 7 | 1.133e-04 | 1.343e-02 |
| combined | Tight Junction (GO:0070160) | 12 | 3.215e-04 | 1.524e-02 |
| combined | Ionotropic Glutamate Receptor Complex (GO:0008328) | 7 | 4.183e-04 | 1.652e-02 |

#### KEGG

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Transcriptional misregulation in cancer | 24 | 1.019e-06 | 3.261e-04 |
| hypomethylated | Long-term depression | 8 | 1.306e-06 | 4.179e-04 |
| hypomethylated | MAPK signaling pathway | 15 | 1.050e-05 | 1.680e-03 |
| hypermethylated | Maturity onset diabetes of the young | 7 | 1.175e-05 | 2.007e-03 |
| hypermethylated | Transcriptional misregulation in cancer | 18 | 1.254e-05 | 2.007e-03 |
| combined | Tight junction | 20 | 3.168e-05 | 5.068e-03 |
| combined | Maturity onset diabetes of the young | 7 | 1.032e-04 | 8.566e-03 |
| combined | Oxytocin signaling pathway | 18 | 1.319e-04 | 8.566e-03 |
| combined | Type II diabetes mellitus | 9 | 1.338e-04 | 8.566e-03 |
| combined | cAMP signaling pathway | 22 | 1.618e-04 | 8.629e-03 |
| hypomethylated | Tight junction | 10 | 8.706e-05 | 9.287e-03 |
| combined | Long-term depression | 10 | 2.108e-04 | 9.638e-03 |
| hypomethylated | Olfactory transduction | 14 | 1.564e-04 | 1.251e-02 |
| hypermethylated | cAMP signaling pathway | 18 | 1.215e-04 | 1.296e-02 |
| hypomethylated | Oxytocin signaling pathway | 9 | 2.653e-04 | 1.698e-02 |

#### Reactome

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuronal System R-HSA-112316 | 43 | 6.312e-09 | 1.147e-05 |
| hypermethylated | GPCR Downstream Signaling R-HSA-388396 | 41 | 1.602e-06 | 1.891e-03 |
| hypermethylated | Neuronal System R-HSA-112316 | 30 | 2.081e-06 | 1.891e-03 |
| hypermethylated | Signaling By GPCR R-HSA-372790 | 43 | 4.537e-06 | 2.750e-03 |
| combined | Developmental Biology R-HSA-1266738 | 76 | 5.011e-06 | 4.555e-03 |
| combined | Signal Transduction R-HSA-162582 | 147 | 1.098e-05 | 6.276e-03 |
| combined | GPCR Downstream Signaling R-HSA-388396 | 49 | 1.381e-05 | 6.276e-03 |
| hypomethylated | Neuronal System R-HSA-112316 | 18 | 4.044e-06 | 7.352e-03 |
| hypermethylated | Regulation Of Beta-Cell Development R-HSA-186712 | 8 | 2.439e-05 | 1.109e-02 |
| combined | Signaling By GPCR R-HSA-372790 | 52 | 3.078e-05 | 1.119e-02 |
| combined | Transmission Across Chemical Synapses R-HSA-112315 | 25 | 4.380e-05 | 1.327e-02 |
| hypomethylated | Sensory Perception R-HSA-9709957 | 20 | 1.688e-05 | 1.534e-02 |
| hypomethylated | Expression And Translocation Of Olfactory Receptors R-HSA-9752946 | 14 | 4.057e-05 | 2.408e-02 |
| hypomethylated | Olfactory Signaling Pathway R-HSA-381753 | 14 | 5.297e-05 | 2.408e-02 |
| combined | Regulation Of Beta-Cell Development R-HSA-186712 | 8 | 2.618e-04 | 6.798e-02 |

### basal_vs_normal

#### GO_BP

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 156 | 1.198e-23 | 6.477e-20 |
| hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 113 | 1.589e-21 | 8.593e-18 |
| hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 105 | 5.271e-19 | 1.425e-15 |
| combined | Regulation Of DNA-templated Transcription (GO:0006355) | 139 | 2.870e-18 | 7.759e-15 |
| combined | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 75 | 6.732e-12 | 1.213e-08 |
| combined | Neuron Differentiation (GO:0030182) | 27 | 3.583e-11 | 4.844e-08 |
| hypermethylated | Neuron Differentiation (GO:0030182) | 22 | 3.138e-11 | 5.655e-08 |
| combined | Chemical Synaptic Transmission (GO:0007268) | 33 | 1.781e-10 | 1.926e-07 |
| combined | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 85 | 9.343e-10 | 8.420e-07 |
| combined | Negative Regulation Of Transcription By RNA Polymerase II (GO:0000122) | 58 | 1.641e-09 | 1.267e-06 |
| combined | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 71 | 2.137e-09 | 1.445e-06 |
| hypermethylated | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 51 | 2.474e-09 | 3.344e-06 |
| combined | Anterograde Trans-Synaptic Signaling (GO:0098916) | 25 | 1.751e-08 | 1.052e-05 |
| combined | Brain Development (GO:0007420) | 22 | 3.368e-08 | 1.821e-05 |
| combined | Nervous System Development (GO:0007399) | 38 | 1.123e-07 | 5.521e-05 |

#### GO_MF

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 104 | 7.172e-34 | 8.227e-31 |
| combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 129 | 1.404e-31 | 1.611e-28 |
| hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 75 | 5.532e-30 | 3.173e-27 |
| combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 93 | 2.541e-29 | 1.457e-26 |
| hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 72 | 1.268e-27 | 3.750e-25 |
| hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 69 | 1.308e-27 | 3.750e-25 |
| hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 88 | 3.359e-26 | 7.706e-24 |
| combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 112 | 1.772e-25 | 5.787e-23 |
| combined | Sequence-Specific DNA Binding (GO:0043565) | 87 | 2.520e-25 | 5.787e-23 |
| combined | Double-Stranded DNA Binding (GO:0003690) | 83 | 2.522e-25 | 5.787e-23 |
| hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 85 | 5.475e-25 | 1.047e-22 |
| combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 109 | 1.120e-24 | 2.140e-22 |
| hypermethylated | Transcription Cis-Regulatory Region Binding (GO:0000976) | 43 | 2.154e-15 | 3.530e-13 |
| combined | Transcription Cis-Regulatory Region Binding (GO:0000976) | 53 | 1.760e-14 | 2.885e-12 |
| combined | DNA-binding Transcription Activator Activity, RNA Polymerase II-specific (GO:0001228) | 35 | 8.015e-09 | 1.149e-06 |

#### GO_CC

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Nucleus (GO:0005634) | 202 | 1.315e-06 | 6.234e-04 |
| combined | Neuron Projection (GO:0043005) | 41 | 2.869e-06 | 6.799e-04 |
| combined | Intracellular Membrane-Bounded Organelle (GO:0043231) | 222 | 1.081e-05 | 1.708e-03 |
| combined | Postsynaptic Specialization Membrane (GO:0099634) | 8 | 3.228e-05 | 3.825e-03 |
| hypermethylated | Neuron Projection (GO:0043005) | 29 | 1.410e-05 | 6.685e-03 |
| hypermethylated | Nucleus (GO:0005634) | 130 | 7.883e-05 | 1.868e-02 |
| hypermethylated | Postsynaptic Specialization Membrane (GO:0099634) | 6 | 1.533e-04 | 2.422e-02 |
| combined | Dendrite Membrane (GO:0032590) | 6 | 2.564e-04 | 2.431e-02 |
| combined | Dendrite (GO:0030425) | 21 | 3.297e-04 | 2.468e-02 |
| combined | Catenin Complex (GO:0016342) | 6 | 3.948e-04 | 2.468e-02 |
| combined | Actin Cytoskeleton (GO:0015629) | 24 | 4.165e-04 | 2.468e-02 |
| hypermethylated | GABA-ergic Synapse (GO:0098982) | 4 | 2.275e-04 | 2.696e-02 |
| combined | Synaptic Membrane (GO:0097060) | 6 | 5.854e-04 | 3.083e-02 |
| hypermethylated | Intracellular Membrane-Bounded Organelle (GO:0043231) | 142 | 4.194e-04 | 3.976e-02 |
| combined | Postsynaptic Density Membrane (GO:0098839) | 6 | 8.406e-04 | 3.985e-02 |

#### KEGG

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Maturity onset diabetes of the young | 8 | 7.911e-08 | 2.531e-05 |
| combined | Maturity onset diabetes of the young | 8 | 2.290e-06 | 7.327e-04 |
| hypermethylated | Neuroactive ligand-receptor interaction | 20 | 4.220e-05 | 6.753e-03 |
| combined | Transcriptional misregulation in cancer | 18 | 6.505e-05 | 1.041e-02 |
| hypermethylated | Transcriptional misregulation in cancer | 13 | 2.243e-04 | 2.392e-02 |
| combined | Neuroactive ligand-receptor interaction | 24 | 4.165e-04 | 4.423e-02 |
| combined | cAMP signaling pathway | 18 | 5.529e-04 | 4.423e-02 |
| hypomethylated | MicroRNAs in cancer | 12 | 5.393e-04 | 1.726e-01 |
| combined | MicroRNAs in cancer | 20 | 3.829e-03 | 2.450e-01 |
| combined | Arrhythmogenic right ventricular cardiomyopathy | 8 | 4.873e-03 | 2.484e-01 |
| combined | Inflammatory bowel disease | 7 | 5.434e-03 | 2.484e-01 |
| combined | Taste transduction | 8 | 7.222e-03 | 2.889e-01 |
| combined | Nicotine addiction | 5 | 8.691e-03 | 2.971e-01 |
| combined | Cell adhesion molecules | 11 | 9.283e-03 | 2.971e-01 |
| hypermethylated | Th1 and Th2 cell differentiation | 7 | 3.856e-03 | 3.085e-01 |

#### Reactome

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Protein-protein Interactions At Synapses R-HSA-6794362 | 14 | 7.333e-07 | 1.333e-03 |
| combined | Neurexins And Neuroligins R-HSA-6794361 | 10 | 1.578e-05 | 1.434e-02 |
| hypermethylated | GPCR Ligand Binding R-HSA-500792 | 25 | 2.332e-05 | 1.630e-02 |
| hypermethylated | Regulation Of Beta-Cell Development R-HSA-186712 | 7 | 2.611e-05 | 1.630e-02 |
| hypermethylated | Class A/1 (Rhodopsin-like Receptors) R-HSA-373076 | 20 | 2.798e-05 | 1.630e-02 |
| hypermethylated | GPCR Downstream Signaling R-HSA-388396 | 30 | 3.586e-05 | 1.630e-02 |
| hypermethylated | Signaling By GPCR R-HSA-372790 | 32 | 4.847e-05 | 1.762e-02 |
| hypermethylated | Regulation Of Gene Expression In Beta Cells R-HSA-210745 | 5 | 7.244e-05 | 2.041e-02 |
| hypermethylated | Protein-protein Interactions At Synapses R-HSA-6794362 | 9 | 8.141e-05 | 2.041e-02 |
| hypermethylated | Peptide Ligand-Binding Receptors R-HSA-375276 | 14 | 8.982e-05 | 2.041e-02 |
| combined | GPCR Downstream Signaling R-HSA-388396 | 40 | 6.768e-05 | 4.101e-02 |
| combined | Neuronal System R-HSA-112316 | 28 | 1.432e-04 | 6.394e-02 |
| combined | Signaling By GPCR R-HSA-372790 | 42 | 1.759e-04 | 6.394e-02 |
| hypermethylated | G Alpha (I) Signaling Events R-HSA-418594 | 17 | 5.142e-04 | 1.039e-01 |
| combined | Transcriptional Regulation Of Pluripotent Stem Cells R-HSA-452723 | 6 | 3.948e-04 | 1.074e-01 |

