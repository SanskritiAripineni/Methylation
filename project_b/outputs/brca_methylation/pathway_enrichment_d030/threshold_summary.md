# Threshold Summary: pathway_enrichment_d030

- command: `python3 project_b/scripts/run_pathway_enrichment.py --config project_b/brca_local_inputs.json --min-abs-delta-beta 0.3 --fdr-threshold 0.05 --comparisons tumor_vs_normal basal_vs_normal --output-name pathway_enrichment_d030`

| comparison | significant probes | hyper probes | hypo probes | significant genes | hyper genes | hypo genes |
|---|---:|---:|---:|---:|---:|---:|
| tumor_vs_normal | 6717 | 3899 | 2818 | 3796 | 2370 | 1656 |
| basal_vs_normal | 5265 | 3232 | 2033 | 2623 | 1467 | 1254 |

## Top 15 Terms Per Library

### tumor_vs_normal

#### GO_BP

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 312 | 9.068e-48 | 4.903e-44 |
| hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 291 | 5.354e-42 | 1.448e-38 |
| combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 407 | 4.282e-41 | 2.315e-37 |
| combined | Regulation Of DNA-templated Transcription (GO:0006355) | 379 | 3.009e-35 | 8.135e-32 |
| hypermethylated | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 194 | 3.674e-28 | 6.622e-25 |
| hypermethylated | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 156 | 6.368e-26 | 8.608e-23 |
| combined | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 258 | 1.011e-25 | 1.593e-22 |
| combined | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 210 | 1.179e-25 | 1.593e-22 |
| hypermethylated | Neuron Differentiation (GO:0030182) | 52 | 1.132e-20 | 1.224e-17 |
| combined | Neuron Differentiation (GO:0030182) | 62 | 1.365e-18 | 1.289e-15 |
| combined | Nervous System Development (GO:0007399) | 111 | 1.431e-18 | 1.289e-15 |
| hypermethylated | Generation Of Neurons (GO:0048699) | 45 | 5.531e-16 | 4.985e-13 |
| combined | Chemical Synaptic Transmission (GO:0007268) | 76 | 9.395e-16 | 6.884e-13 |
| combined | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 189 | 1.019e-15 | 6.884e-13 |
| hypermethylated | Negative Regulation Of DNA-templated Transcription (GO:0045892) | 134 | 5.927e-15 | 4.578e-12 |

#### GO_MF

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 180 | 1.973e-56 | 2.263e-53 |
| hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 173 | 2.250e-51 | 1.290e-48 |
| hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 164 | 9.779e-51 | 3.739e-48 |
| hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 230 | 1.336e-48 | 3.831e-46 |
| combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 215 | 1.782e-47 | 2.044e-44 |
| hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 209 | 1.511e-43 | 3.467e-41 |
| combined | Double-Stranded DNA Binding (GO:0003690) | 193 | 6.922e-41 | 3.970e-38 |
| combined | Sequence-Specific DNA Binding (GO:0043565) | 203 | 1.832e-40 | 7.004e-38 |
| hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 197 | 1.026e-38 | 1.962e-36 |
| combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 282 | 2.816e-38 | 8.074e-36 |
| combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 259 | 2.319e-35 | 5.319e-33 |
| combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 246 | 1.418e-31 | 2.711e-29 |
| hypermethylated | Transcription Cis-Regulatory Region Binding (GO:0000976) | 102 | 1.810e-26 | 2.966e-24 |
| combined | Transcription Cis-Regulatory Region Binding (GO:0000976) | 126 | 5.156e-23 | 8.449e-21 |
| hypermethylated | DNA-binding Transcription Activator Activity, RNA Polymerase II-specific (GO:0001228) | 63 | 3.535e-13 | 5.068e-11 |

#### GO_CC

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuron Projection (GO:0043005) | 135 | 2.618e-20 | 1.241e-17 |
| hypermethylated | Neuron Projection (GO:0043005) | 93 | 3.237e-16 | 1.534e-13 |
| hypermethylated | Nucleus (GO:0005634) | 408 | 9.927e-13 | 2.353e-10 |
| hypermethylated | Intracellular Membrane-Bounded Organelle (GO:0043231) | 458 | 1.995e-12 | 3.152e-10 |
| combined | Dendrite (GO:0030425) | 68 | 7.724e-12 | 1.831e-09 |
| combined | Intracellular Membrane-Bounded Organelle (GO:0043231) | 671 | 1.331e-10 | 2.102e-08 |
| combined | Nucleus (GO:0005634) | 584 | 1.508e-09 | 1.509e-07 |
| combined | Postsynaptic Density (GO:0014069) | 43 | 1.592e-09 | 1.509e-07 |
| hypomethylated | Neuron Projection (GO:0043005) | 61 | 4.918e-10 | 2.331e-07 |
| combined | Potassium Channel Complex (GO:0034705) | 29 | 3.984e-09 | 3.147e-07 |
| combined | Postsynaptic Specialization Membrane (GO:0099634) | 18 | 1.161e-08 | 7.860e-07 |
| combined | Postsynaptic Density Membrane (GO:0098839) | 16 | 7.601e-08 | 4.504e-06 |
| combined | Collagen-Containing Extracellular Matrix (GO:0062023) | 74 | 1.099e-07 | 5.657e-06 |
| combined | Voltage-Gated Potassium Channel Complex (GO:0008076) | 25 | 1.194e-07 | 5.657e-06 |
| hypermethylated | Collagen-Containing Extracellular Matrix (GO:0062023) | 54 | 8.503e-08 | 9.825e-06 |

#### KEGG

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuroactive ligand-receptor interaction | 76 | 1.001e-10 | 3.204e-08 |
| hypermethylated | Neuroactive ligand-receptor interaction | 54 | 1.490e-09 | 4.769e-07 |
| hypomethylated | Olfactory transduction | 43 | 2.098e-09 | 6.713e-07 |
| combined | Rap1 signaling pathway | 53 | 9.354e-09 | 1.238e-06 |
| combined | Nicotine addiction | 18 | 1.161e-08 | 1.238e-06 |
| combined | MAPK signaling pathway | 63 | 1.081e-07 | 8.648e-06 |
| combined | PI3K-Akt signaling pathway | 69 | 2.484e-07 | 1.522e-05 |
| combined | Calcium signaling pathway | 53 | 2.854e-07 | 1.522e-05 |
| combined | cAMP signaling pathway | 48 | 1.462e-06 | 6.682e-05 |
| combined | Pathways in cancer | 92 | 1.721e-06 | 6.885e-05 |
| hypermethylated | Maturity onset diabetes of the young | 11 | 6.907e-07 | 8.386e-05 |
| hypermethylated | cAMP signaling pathway | 36 | 7.862e-07 | 8.386e-05 |
| combined | Arrhythmogenic right ventricular cardiomyopathy | 23 | 4.472e-06 | 1.580e-04 |
| combined | Ras signaling pathway | 49 | 4.938e-06 | 1.580e-04 |
| combined | Axon guidance | 41 | 5.665e-06 | 1.648e-04 |

#### Reactome

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuronal System R-HSA-112316 | 104 | 2.678e-19 | 4.868e-16 |
| combined | Signal Transduction R-HSA-162582 | 405 | 6.393e-19 | 5.811e-16 |
| hypermethylated | Neuronal System R-HSA-112316 | 73 | 8.720e-16 | 1.585e-12 |
| hypermethylated | Signal Transduction R-HSA-162582 | 268 | 4.001e-15 | 3.637e-12 |
| hypomethylated | Sensory Perception R-HSA-9709957 | 63 | 2.417e-12 | 4.394e-09 |
| hypermethylated | Signaling By GPCR R-HSA-372790 | 93 | 1.035e-10 | 6.274e-08 |
| combined | Transmission Across Chemical Synapses R-HSA-112315 | 61 | 2.854e-10 | 1.730e-07 |
| hypomethylated | Olfactory Signaling Pathway R-HSA-381753 | 42 | 2.802e-10 | 2.504e-07 |
| hypomethylated | Signal Transduction R-HSA-162582 | 182 | 4.132e-10 | 2.504e-07 |
| hypomethylated | Expression And Translocation Of Olfactory Receptors R-HSA-9752946 | 40 | 1.519e-09 | 6.902e-07 |
| hypermethylated | Transmission Across Chemical Synapses R-HSA-112315 | 44 | 2.836e-09 | 1.289e-06 |
| combined | Signaling By GPCR R-HSA-372790 | 124 | 4.030e-09 | 1.477e-06 |
| combined | Developmental Biology R-HSA-1266738 | 176 | 4.062e-09 | 1.477e-06 |
| combined | Signaling By Receptor Tyrosine Kinases R-HSA-9006934 | 98 | 6.013e-09 | 1.660e-06 |
| combined | Cell-Cell Communication R-HSA-1500931 | 36 | 6.393e-09 | 1.660e-06 |

### basal_vs_normal

#### GO_BP

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 202 | 2.838e-33 | 1.535e-29 |
| hypermethylated | Regulation Of DNA-templated Transcription (GO:0006355) | 192 | 4.708e-31 | 1.273e-27 |
| combined | Regulation Of Transcription By RNA Polymerase II (GO:0006357) | 288 | 1.111e-29 | 6.005e-26 |
| combined | Regulation Of DNA-templated Transcription (GO:0006355) | 263 | 7.454e-24 | 2.015e-20 |
| combined | Nervous System Development (GO:0007399) | 89 | 1.553e-18 | 2.799e-15 |
| combined | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 148 | 2.467e-18 | 3.334e-15 |
| hypermethylated | Positive Regulation Of Transcription By RNA Polymerase II (GO:0045944) | 101 | 3.616e-18 | 6.518e-15 |
| combined | Chemical Synaptic Transmission (GO:0007268) | 64 | 4.350e-17 | 4.705e-14 |
| hypermethylated | Chemical Synaptic Transmission (GO:0007268) | 47 | 6.453e-17 | 8.723e-14 |
| hypermethylated | Nervous System Development (GO:0007399) | 59 | 1.651e-15 | 1.659e-12 |
| hypermethylated | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 115 | 1.841e-15 | 1.659e-12 |
| combined | Positive Regulation Of DNA-templated Transcription (GO:0045893) | 169 | 2.643e-14 | 2.381e-11 |
| hypermethylated | Synapse Assembly (GO:0007416) | 20 | 4.139e-12 | 3.197e-09 |
| hypermethylated | Anterograde Trans-Synaptic Signaling (GO:0098916) | 33 | 1.191e-11 | 8.047e-09 |
| combined | Synapse Assembly (GO:0007416) | 25 | 1.060e-11 | 8.186e-09 |

#### GO_MF

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 184 | 1.544e-54 | 1.771e-51 |
| hypermethylated | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 129 | 2.219e-46 | 1.272e-43 |
| hypermethylated | Sequence-Specific DNA Binding (GO:0043565) | 127 | 9.449e-45 | 3.613e-42 |
| hypermethylated | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 160 | 2.670e-44 | 7.655e-42 |
| hypermethylated | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 157 | 1.042e-43 | 2.389e-41 |
| hypermethylated | Double-Stranded DNA Binding (GO:0003690) | 119 | 7.024e-43 | 1.343e-40 |
| combined | RNA Polymerase II Transcription Regulatory Region Sequence-Specific DNA Binding (GO:0000977) | 229 | 7.017e-41 | 8.048e-38 |
| combined | Sequence-Specific Double-Stranded DNA Binding (GO:1990837) | 161 | 2.979e-38 | 1.709e-35 |
| combined | Double-Stranded DNA Binding (GO:0003690) | 149 | 1.030e-35 | 3.937e-33 |
| combined | Sequence-Specific DNA Binding (GO:0043565) | 156 | 3.391e-35 | 9.661e-33 |
| combined | RNA Polymerase II Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000978) | 205 | 4.211e-35 | 9.661e-33 |
| combined | Cis-Regulatory Region Sequence-Specific DNA Binding (GO:0000987) | 199 | 1.084e-33 | 2.072e-31 |
| hypermethylated | Transcription Cis-Regulatory Region Binding (GO:0000976) | 78 | 9.416e-26 | 1.543e-23 |
| combined | Transcription Cis-Regulatory Region Binding (GO:0000976) | 98 | 5.722e-21 | 9.376e-19 |
| hypermethylated | DNA-binding Transcription Activator Activity, RNA Polymerase II-specific (GO:0001228) | 57 | 4.447e-19 | 6.376e-17 |

#### GO_CC

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuron Projection (GO:0043005) | 90 | 2.125e-12 | 1.007e-09 |
| hypermethylated | Neuron Projection (GO:0043005) | 58 | 1.643e-10 | 7.789e-08 |
| combined | Nucleus (GO:0005634) | 415 | 3.701e-08 | 8.772e-06 |
| combined | Intracellular Membrane-Bounded Organelle (GO:0043231) | 467 | 9.750e-08 | 1.541e-05 |
| combined | Postsynaptic Density (GO:0014069) | 31 | 2.449e-07 | 2.902e-05 |
| combined | Dendrite (GO:0030425) | 44 | 5.994e-07 | 5.682e-05 |
| hypermethylated | Nucleus (GO:0005634) | 245 | 4.787e-07 | 9.299e-05 |
| hypermethylated | Intracellular Membrane-Bounded Organelle (GO:0043231) | 276 | 5.885e-07 | 9.299e-05 |
| combined | Asymmetric Synapse (GO:0032279) | 27 | 1.329e-06 | 1.050e-04 |
| combined | Actin Cytoskeleton (GO:0015629) | 48 | 7.442e-06 | 5.039e-04 |
| hypomethylated | Asymmetric Synapse (GO:0032279) | 18 | 1.139e-06 | 5.296e-04 |
| hypomethylated | Postsynaptic Density (GO:0014069) | 19 | 2.235e-06 | 5.296e-04 |
| combined | Potassium Channel Complex (GO:0034705) | 19 | 9.321e-06 | 5.523e-04 |
| combined | Postsynaptic Specialization Membrane (GO:0099634) | 12 | 1.197e-05 | 6.302e-04 |
| hypermethylated | Dendrite (GO:0030425) | 28 | 8.486e-06 | 1.006e-03 |

#### KEGG

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| hypermethylated | Maturity onset diabetes of the young | 12 | 2.885e-10 | 9.231e-08 |
| combined | Maturity onset diabetes of the young | 13 | 1.768e-08 | 5.659e-06 |
| hypomethylated | Olfactory transduction | 32 | 5.625e-07 | 1.800e-04 |
| hypermethylated | Transcriptional misregulation in cancer | 23 | 3.433e-06 | 4.276e-04 |
| hypermethylated | Neuroactive ligand-receptor interaction | 33 | 4.009e-06 | 4.276e-04 |
| combined | Morphine addiction | 20 | 1.360e-05 | 1.901e-03 |
| combined | Transcriptional misregulation in cancer | 31 | 2.006e-05 | 1.901e-03 |
| combined | Tight junction | 29 | 2.376e-05 | 1.901e-03 |
| combined | Arrhythmogenic right ventricular cardiomyopathy | 17 | 5.091e-05 | 2.814e-03 |
| combined | Glutamatergic synapse | 22 | 6.644e-05 | 2.814e-03 |
| combined | Nicotine addiction | 11 | 6.875e-05 | 2.814e-03 |
| combined | Neuroactive ligand-receptor interaction | 45 | 7.035e-05 | 2.814e-03 |
| combined | cAMP signaling pathway | 33 | 1.051e-04 | 3.736e-03 |
| hypermethylated | Dilated cardiomyopathy | 14 | 5.092e-05 | 4.073e-03 |
| combined | MicroRNAs in cancer | 41 | 1.783e-04 | 5.707e-03 |

#### Reactome

| direction | term | overlap_n | p | adj_p |
|---|---|---|---|---|
| combined | Neuronal System R-HSA-112316 | 67 | 7.349e-11 | 1.336e-07 |
| combined | Signal Transduction R-HSA-162582 | 257 | 2.822e-08 | 2.565e-05 |
| combined | GPCR Downstream Signaling R-HSA-388396 | 84 | 4.993e-08 | 3.026e-05 |
| hypermethylated | Neuronal System R-HSA-112316 | 42 | 1.767e-08 | 3.212e-05 |
| hypermethylated | Regulation Of Beta-Cell Development R-HSA-186712 | 12 | 6.845e-08 | 6.222e-05 |
| hypermethylated | GPCR Downstream Signaling R-HSA-388396 | 55 | 1.078e-07 | 6.535e-05 |
| hypermethylated | Signaling By GPCR R-HSA-372790 | 59 | 1.531e-07 | 6.960e-05 |
| combined | Signaling By GPCR R-HSA-372790 | 89 | 2.302e-07 | 1.046e-04 |
| hypermethylated | Signal Transduction R-HSA-162582 | 153 | 6.841e-07 | 2.487e-04 |
| combined | Developmental Biology R-HSA-1266738 | 123 | 9.392e-07 | 3.415e-04 |
| hypermethylated | Nuclear Receptor Transcription Pathway R-HSA-383280 | 12 | 1.699e-06 | 5.148e-04 |
| combined | Protein-protein Interactions At Synapses R-HSA-6794362 | 20 | 2.337e-06 | 7.083e-04 |
| hypomethylated | Olfactory Signaling Pathway R-HSA-381753 | 30 | 5.644e-07 | 1.026e-03 |
| hypermethylated | Developmental Biology R-HSA-1266738 | 76 | 4.658e-06 | 1.210e-03 |
| combined | Regulation Of Beta-Cell Development R-HSA-186712 | 13 | 5.195e-06 | 1.316e-03 |

