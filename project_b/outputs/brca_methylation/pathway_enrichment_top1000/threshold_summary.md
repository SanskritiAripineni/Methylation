# Threshold Summary: pathway_enrichment_top1000

- command: `python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --min-abs-delta-beta 0.2 --top-n-probes 1000 --fdr-threshold 0.05 --comparisons tumor_vs_normal basal_vs_normal --output-name pathway_enrichment_top1000`

| comparison | significant probes | hyper probes | hypo probes | significant genes | hyper genes | hypo genes |
|---|---:|---:|---:|---:|---:|---:|
| tumor_vs_normal | 1000 | 718 | 282 | 852 | 648 | 215 |
| basal_vs_normal | 1000 | 744 | 256 | 676 | 484 | 200 |

## Top 15 Terms Per Library

### tumor_vs_normal

#### GO_BP

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 109 | 4.590e-25 | 2.482e-21 |
| combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 127 | 3.798e-24 | 2.054e-20 |
| combined | Regulation Of DNA-templated Transcription (GO:0006355) | 119 | 9.039e-22 | 2.444e-18 |
| hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 100 | 1.485e-21 | 4.015e-18 |
| combined | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 62 | 1.555e-12 | 2.802e-09 |
| hypermethylated | Embryonic Organ Morphogenesis (GO:0048562) | 13 | 1.631e-12 | 2.939e-09 |
| hypermethylated | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 51 | 9.933e-12 | 1.343e-08 |
| combined | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 72 | 1.523e-11 | 2.059e-08 |
| hypermethylated | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 60 | 2.237e-11 | 2.419e-08 |
| combined | Embryonic Organ Morphogenesis (GO:0048562) | 13 | 4.823e-11 | 5.215e-08 |
| combined | Nervous System Development (GO:0007399) | 36 | 2.082e-10 | 1.876e-07 |
| combined | Neuron Differentiation (GO:0030182) | 22 | 2.761e-10 | 2.133e-07 |
| hypermethylated | Endocrine System Development (GO:0035270) | 8 | 3.349e-09 | 3.018e-06 |
| hypermethylated | Neuron Differentiation (GO:0030182) | 18 | 4.322e-09 | 3.338e-06 |
| hypermethylated | Skeletal System Morphogenesis (GO:0048705) | 10 | 8.240e-09 | 5.569e-06 |

#### GO_MF

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 81 | 3.325e-31 | 3.814e-28 |
| hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 70 | 2.263e-30 | 2.483e-27 |
| hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 67 | 4.330e-30 | 2.483e-27 |
| hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 89 | 3.986e-29 | 1.524e-26 |
| hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 68 | 1.095e-28 | 3.140e-26 |
| combined | Sequence-Specific DNA Binding (GO:0043565) | 77 | 3.763e-28 | 2.158e-25 |
| combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 101 | 9.708e-28 | 3.712e-25 |
| combined | Double-Stranded DNA Binding (GO:0003690) | 73 | 1.353e-27 | 3.880e-25 |
| hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 77 | 1.118e-23 | 2.565e-21 |
| combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 89 | 2.547e-23 | 5.842e-21 |
| hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 73 | 1.015e-21 | 1.941e-19 |
| combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 84 | 4.341e-21 | 8.298e-19 |
| combined | Transcription Cis-Regulatory Region Binding (GO:0000976) | 45 | 5.739e-15 | 9.403e-13 |
| hypermethylated | Transcription Cis-Regulatory Region Binding (GO:0000976) | 36 | 8.305e-13 | 1.361e-10 |
| combined | DNA-binding Transcription Activator Activity, RNA Polymerase II-specific (GO:0001228) | 31 | 4.750e-10 | 6.811e-08 |

#### GO_CC

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Nucleus (GO:0005634) | 163 | 8.256e-09 | 3.913e-06 |
| combined | Intracellular Membrane-Bounded Organelle (GO:0043231) | 181 | 1.694e-08 | 4.015e-06 |
| hypermethylated | Nucleus (GO:0005634) | 125 | 3.045e-07 | 1.443e-04 |
| hypermethylated | Intracellular Membrane-Bounded Organelle (GO:0043231) | 135 | 3.451e-06 | 8.179e-04 |
| combined | GABA-ergic Synapse (GO:0098982) | 5 | 1.825e-05 | 2.884e-03 |
| hypermethylated | Collagen-Containing Extracellular Matrix (GO:0062023) | 20 | 2.364e-05 | 3.735e-03 |
| combined | Neuron Projection (GO:0043005) | 30 | 4.527e-05 | 4.384e-03 |
| combined | Collagen-Containing Extracellular Matrix (GO:0062023) | 23 | 4.624e-05 | 4.384e-03 |
| hypermethylated | GABA-ergic Synapse (GO:0098982) | 4 | 1.244e-04 | 1.474e-02 |
| combined | Intermediate Filament Cytoskeleton (GO:0045111) | 9 | 1.928e-04 | 1.523e-02 |
| hypermethylated | Postsynaptic Specialization Membrane (GO:0099634) | 5 | 6.449e-04 | 5.970e-02 |
| hypermethylated | Neuron Projection (GO:0043005) | 22 | 7.558e-04 | 5.970e-02 |
| hypermethylated | Intermediate Filament Cytoskeleton (GO:0045111) | 7 | 9.126e-04 | 6.179e-02 |
| hypermethylated | Polymeric Cytoskeletal Fiber (GO:0099513) | 13 | 1.358e-03 | 8.047e-02 |
| combined | Postsynaptic Specialization Membrane (GO:0099634) | 5 | 2.154e-03 | 1.458e-01 |

#### KEGG

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Maturity onset diabetes of the young | 6 | 9.050e-06 | 2.841e-03 |
| hypermethylated | MicroRNAs in cancer | 18 | 1.776e-05 | 2.841e-03 |
| combined | Maturity onset diabetes of the young | 6 | 4.187e-05 | 6.843e-03 |
| combined | Transcriptional misregulation in cancer | 15 | 5.364e-05 | 6.843e-03 |
| combined | MicroRNAs in cancer | 20 | 6.415e-05 | 6.843e-03 |
| combined | Type II diabetes mellitus | 7 | 1.396e-04 | 1.117e-02 |
| combined | Tight junction | 13 | 2.823e-04 | 1.807e-02 |
| hypermethylated | Transcriptional misregulation in cancer | 11 | 7.396e-04 | 7.889e-02 |
| hypermethylated | Type II diabetes mellitus | 5 | 1.809e-03 | 1.447e-01 |
| combined | Long-term depression | 6 | 3.673e-03 | 1.959e-01 |
| hypomethylated | Tight junction | 6 | 6.459e-04 | 2.067e-01 |
| combined | Insulin secretion | 7 | 5.524e-03 | 2.135e-01 |
| combined | Proteoglycans in cancer | 12 | 5.593e-03 | 2.135e-01 |
| combined | Neomycin, kanamycin and gentamicin biosynthesis | 2 | 6.260e-03 | 2.135e-01 |
| combined | MAPK signaling pathway | 15 | 6.672e-03 | 2.135e-01 |

#### Reactome

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuronal System R-HSA-112316 | 28 | 3.378e-07 | 6.142e-04 |
| combined | Developmental Biology R-HSA-1266738 | 47 | 7.372e-05 | 6.701e-02 |
| hypermethylated | Neuronal System R-HSA-112316 | 20 | 4.101e-05 | 7.456e-02 |
| hypermethylated | GPCR Downstream Signaling R-HSA-388396 | 26 | 9.355e-05 | 8.504e-02 |
| hypermethylated | Developmental Biology R-HSA-1266738 | 37 | 2.220e-04 | 1.028e-01 |
| hypermethylated | Signaling By GPCR R-HSA-372790 | 27 | 2.261e-04 | 1.028e-01 |
| hypermethylated | G Alpha (Z) Signaling Events R-HSA-418597 | 6 | 2.979e-04 | 1.083e-01 |
| combined | GPCR Downstream Signaling R-HSA-388396 | 30 | 2.678e-04 | 1.623e-01 |
| combined | Transmission Across Chemical Synapses R-HSA-112315 | 16 | 3.791e-04 | 1.723e-01 |
| hypermethylated | Neurotransmitter Receptors And Postsynaptic Signal Transmission R-HSA-112314 | 11 | 5.821e-04 | 1.764e-01 |
| combined | Neurotransmitter Receptors And Postsynaptic Signal Transmission R-HSA-112314 | 13 | 5.043e-04 | 1.834e-01 |
| hypermethylated | Transmission Across Chemical Synapses R-HSA-112315 | 13 | 7.422e-04 | 1.928e-01 |
| hypermethylated | Regulation Of Beta-Cell Development R-HSA-186712 | 5 | 9.386e-04 | 2.133e-01 |
| combined | Signaling By GPCR R-HSA-372790 | 31 | 7.881e-04 | 2.231e-01 |
| combined | Nef And Signal Transduction R-HSA-164944 | 3 | 8.589e-04 | 2.231e-01 |

### basal_vs_normal

#### GO_BP

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 70 | 3.729e-13 | 2.016e-09 |
| combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 87 | 4.363e-13 | 2.359e-09 |
| hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 66 | 4.176e-12 | 1.129e-08 |
| combined | Regulation Of DNA-templated Transcription (GO:0006355) | 79 | 8.478e-11 | 2.292e-07 |
| combined | Negative Regulation Of Transcription By RNA Polymerase II (GO:0000122) | 38 | 3.745e-08 | 6.749e-05 |
| combined | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 44 | 2.945e-07 | 3.614e-04 |
| combined | Chemical Synaptic Transmission (GO:0007268) | 20 | 3.342e-07 | 3.614e-04 |
| combined | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 42 | 5.391e-07 | 4.858e-04 |
| hypermethylated | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 34 | 4.344e-07 | 7.829e-04 |
| combined | Nervous System Development (GO:0007399) | 25 | 1.557e-06 | 1.203e-03 |
| hypermethylated | Neuron Differentiation (GO:0030182) | 13 | 9.904e-07 | 1.226e-03 |
| hypermethylated | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 34 | 1.252e-06 | 1.226e-03 |
| hypermethylated | Negative Regulation Of Transcription By RNA Polymerase II (GO:0000122) | 28 | 1.361e-06 | 1.226e-03 |
| combined | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 49 | 2.724e-06 | 1.841e-03 |
| hypermethylated | Sensory Organ Development (GO:0007423) | 8 | 4.281e-06 | 3.307e-03 |

#### GO_MF

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 72 | 7.697e-26 | 8.828e-23 |
| hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 51 | 7.473e-22 | 4.286e-19 |
| hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 50 | 5.164e-21 | 1.494e-18 |
| hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 48 | 5.209e-21 | 1.494e-18 |
| combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 79 | 1.884e-21 | 2.161e-18 |
| hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 59 | 6.463e-19 | 1.483e-16 |
| hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 58 | 9.851e-19 | 1.883e-16 |
| combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 56 | 5.981e-19 | 3.430e-16 |
| combined | Sequence-Specific DNA Binding (GO:0043565) | 53 | 6.548e-17 | 2.504e-14 |
| combined | Double-Stranded DNA Binding (GO:0003690) | 50 | 1.734e-16 | 4.973e-14 |
| combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 66 | 4.745e-16 | 1.044e-13 |
| combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 65 | 5.459e-16 | 1.044e-13 |
| hypermethylated | Transcription Cis-Regulatory Region Binding (GO:0000976) | 29 | 2.537e-11 | 4.156e-09 |
| combined | Transcription Cis-Regulatory Region Binding (GO:0000976) | 34 | 5.431e-11 | 8.899e-09 |
| hypermethylated | DNA-binding Transcription Activator Activity, RNA Polymerase II-specific (GO:0001228) | 19 | 4.075e-07 | 5.843e-05 |

#### GO_CC

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuron Projection (GO:0043005) | 25 | 9.292e-05 | 4.404e-02 |
| hypermethylated | Neuron Projection (GO:0043005) | 20 | 1.092e-04 | 5.178e-02 |
| combined | AMPA Glutamate Receptor Complex (GO:0032281) | 4 | 4.196e-04 | 9.945e-02 |
| combined | Actin-Based Cell Projection (GO:0098858) | 7 | 1.256e-03 | 1.868e-01 |
| combined | Dendrite Membrane (GO:0032590) | 4 | 1.801e-03 | 1.868e-01 |
| combined | Polymeric Cytoskeletal Fiber (GO:0099513) | 13 | 1.971e-03 | 1.868e-01 |
| combined | Voltage-Gated Calcium Channel Complex (GO:0005891) | 5 | 2.901e-03 | 2.105e-01 |
| combined | Ionotropic Glutamate Receptor Complex (GO:0008328) | 4 | 3.934e-03 | 2.105e-01 |
| combined | Postsynaptic Density Membrane (GO:0098839) | 4 | 3.934e-03 | 2.105e-01 |
| combined | Nuclear Stress Granule (GO:0097165) | 2 | 3.996e-03 | 2.105e-01 |
| combined | Postsynaptic Specialization Membrane (GO:0099634) | 4 | 6.044e-03 | 2.436e-01 |
| combined | Microvillus (GO:0005902) | 5 | 6.107e-03 | 2.436e-01 |
| combined | Dendrite (GO:0030425) | 12 | 6.168e-03 | 2.436e-01 |
| combined | Dendritic Spine Membrane (GO:0032591) | 2 | 8.167e-03 | 2.978e-01 |
| hypomethylated | Dendritic Spine Membrane (GO:0032591) | 2 | 7.444e-04 | 3.359e-01 |

#### KEGG

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Neuroactive ligand-receptor interaction | 16 | 1.791e-05 | 5.364e-03 |
| hypermethylated | Maturity onset diabetes of the young | 5 | 3.352e-05 | 5.364e-03 |
| combined | Neuroactive ligand-receptor interaction | 18 | 9.051e-05 | 2.578e-02 |
| combined | Maturity onset diabetes of the young | 5 | 1.611e-04 | 2.578e-02 |
| hypermethylated | Transcriptional misregulation in cancer | 8 | 4.559e-03 | 4.625e-01 |
| hypermethylated | Cardiac muscle contraction | 5 | 5.781e-03 | 4.625e-01 |
| hypermethylated | cAMP signaling pathway | 8 | 1.226e-02 | 7.846e-01 |
| combined | Transcriptional misregulation in cancer | 9 | 1.049e-02 | 8.942e-01 |
| combined | cAMP signaling pathway | 10 | 1.118e-02 | 8.942e-01 |
| hypermethylated | Bladder cancer | 3 | 1.927e-02 | 9.422e-01 |
| hypermethylated | Type I diabetes mellitus | 3 | 2.061e-02 | 9.422e-01 |
| hypomethylated | MicroRNAs in cancer | 6 | 8.261e-03 | 1.000e+00 |
| hypomethylated | Phototransduction | 2 | 1.150e-02 | 1.000e+00 |
| hypomethylated | Base excision repair | 2 | 1.593e-02 | 1.000e+00 |
| combined | Phototransduction | 3 | 1.722e-02 | 1.000e+00 |

#### Reactome

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Protein-protein Interactions At Synapses R-HSA-6794362 | 9 | 3.371e-05 | 6.128e-02 |
| hypermethylated | Class A/1 (Rhodopsin-like Receptors) R-HSA-373076 | 15 | 4.871e-05 | 6.709e-02 |
| hypermethylated | GPCR Ligand Binding R-HSA-500792 | 18 | 7.381e-05 | 6.709e-02 |
| hypermethylated | GPCR Downstream Signaling R-HSA-388396 | 21 | 1.535e-04 | 8.022e-02 |
| hypermethylated | Regulation Of Gene Expression In Beta Cells R-HSA-210745 | 4 | 1.821e-04 | 8.022e-02 |
| hypermethylated | Regulation Of Beta-Cell Development R-HSA-186712 | 5 | 2.509e-04 | 8.022e-02 |
| hypermethylated | Signaling By GPCR R-HSA-372790 | 22 | 2.648e-04 | 8.022e-02 |
| hypermethylated | Peptide Ligand-Binding Receptors R-HSA-375276 | 10 | 3.906e-04 | 1.014e-01 |
| hypomethylated | SUMOylation Of DNA Damage Response And Repair Proteins R-HSA-3108214 | 5 | 8.155e-05 | 1.483e-01 |
| hypermethylated | Phase 2 - Plateau Phase R-HSA-5576893 | 3 | 1.005e-03 | 2.284e-01 |
| combined | Regulation Of Gene Expression In Beta Cells R-HSA-210745 | 4 | 6.432e-04 | 2.932e-01 |
| combined | Neurexins And Neuroligins R-HSA-6794361 | 6 | 7.199e-04 | 2.932e-01 |
| combined | Negative Regulation Of Activity Of TFAP2 (AP-2) Family Transcription Factors R-HSA-8866904 | 3 | 9.136e-04 | 2.932e-01 |
| combined | GPCR Downstream Signaling R-HSA-388396 | 24 | 9.769e-04 | 2.932e-01 |
| combined | Regulation Of Beta-Cell Development R-HSA-186712 | 5 | 1.134e-03 | 2.932e-01 |

