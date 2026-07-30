"""Node catalog for the methylation pipeline builder.

This is the single source of truth for:
  * which blocks appear in the drag-and-drop palette,
  * which parameters each block exposes (and their defaults / ranges),
  * which block implementation runs for a given node type.

Defaults mirror the published pipeline (project_b/scripts/*) so that the
default graph reproduces the real analysis settings.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Parameter helpers
# ---------------------------------------------------------------------------


def num(key, label, default, lo, hi, step, help_text, unit=""):
    return {
        "key": key,
        "label": label,
        "type": "number",
        "default": default,
        "min": lo,
        "max": hi,
        "step": step,
        "unit": unit,
        "help": help_text,
    }


def choice(key, label, default, options, help_text):
    return {
        "key": key,
        "label": label,
        "type": "choice",
        "default": default,
        "options": options,
        "help": help_text,
    }


def flag(key, label, default, help_text):
    return {"key": key, "label": label, "type": "bool", "default": default, "help": help_text}


def text(key, label, default, help_text, placeholder=""):
    return {
        "key": key,
        "label": label,
        "type": "text",
        "default": default,
        "placeholder": placeholder,
        "help": help_text,
    }


def multi(key, label, default, options, help_text):
    return {
        "key": key,
        "label": label,
        "type": "multi",
        "default": default,
        "options": options,
        "help": help_text,
    }


# ---------------------------------------------------------------------------
# Node catalog
# ---------------------------------------------------------------------------

NODES = [
    # -- inputs --------------------------------------------------------------
    {
        "type": "load_data",
        "name": "Load dataset",
        "group": "Input",
        "icon": "DB",
        "color": "#2e75b6",
        "summary": "Reads a beta-value matrix (probes x samples) plus the sample manifest.",
        "detail": (
            "Beta values run 0-1: the fraction of DNA molecules methylated at that CpG site. "
            "The manifest supplies each sample's tumor/normal label and PAM50 subtype."
        ),
        "inputs": [],
        "outputs": ["betas"],
        "params": [
            choice(
                "dataset",
                "Dataset",
                "sample_brca",
                [
                    {"value": "sample_brca", "label": "Bundled sample cohort (fast)"},
                    {"value": "custom", "label": "Custom files on disk"},
                ],
                "The bundled cohort is a small surrogate matrix calibrated to the real "
                "TCGA-BRCA per-probe statistics. Pick 'custom' to point at the real matrix.",
            ),
            text(
                "matrix_path",
                "Matrix path",
                "",
                "Only used when Dataset = custom. TSV/TSV.GZ, probes in rows, samples in columns.",
                "data/raw/TCGA-BRCA.methylation450.tsv.gz",
            ),
            text(
                "manifest_path",
                "Manifest path",
                "",
                "Only used when Dataset = custom. Needs sample_barcode + sample_class columns.",
                "data/raw/TCGA-BRCA.clinical.tsv.gz",
            ),
            num("max_probes", "Probe cap", 0, 0, 500000, 500,
                "Optional smoke-test limit on probes loaded. 0 = no cap."),
        ],
    },
    # -- QC ------------------------------------------------------------------
    {
        "type": "qc_filter",
        "name": "QC filter",
        "group": "Filters",
        "icon": "QC",
        "color": "#0f8a7a",
        "summary": "Drops samples and probes with too much missing data, before any testing.",
        "detail": (
            "Missingness filters are unsupervised - they never look at the tumor/normal "
            "label, so they cannot leak group information into the result."
        ),
        "inputs": ["betas"],
        "outputs": ["betas"],
        "params": [
            num("max_sample_missingness", "Max sample missingness", 0.25, 0.0, 1.0, 0.01,
                "Drop a sample if more than this fraction of its probes are missing.", "fraction"),
            num("max_probe_missingness", "Max probe missingness", 0.10, 0.0, 1.0, 0.01,
                "Drop a probe if more than this fraction of samples are missing it.", "fraction"),
            flag("drop_sex_chromosomes", "Drop chrX / chrY", True,
                 "Sex-chromosome probes carry a strong sex signal unrelated to tumour biology."),
            num("min_group_n", "Min samples per group", 3, 2, 200, 1,
                "Abort if either group falls below this after filtering."),
        ],
    },
    {
        "type": "probe_filter",
        "name": "Probe pre-filter",
        "group": "Filters",
        "icon": "PF",
        "color": "#0f8a7a",
        "summary": "Optional unsupervised probe reduction by variance, before testing.",
        "detail": (
            "Ranking by variance uses no group labels, so it stays leakage-free. "
            "Leave off to test every probe, as the published run did."
        ),
        "inputs": ["betas"],
        "outputs": ["betas"],
        "params": [
            flag("enabled", "Enable pre-filter", False, "Off by default: the published run tested all probes."),
            num("min_variance", "Min variance", 0.0, 0.0, 0.25, 0.001,
                "Drop probes whose beta variance across samples is below this."),
            num("top_n_variable", "Keep top-N variable", 0, 0, 500000, 100,
                "Keep only the N most variable probes. 0 = keep all that pass min variance."),
        ],
    },
    # -- statistics ----------------------------------------------------------
    {
        "type": "differential",
        "name": "Differential test",
        "group": "Statistics",
        "icon": "DM",
        "color": "#c0392b",
        "summary": "Per-probe group comparison producing delta-beta and a raw p-value.",
        "detail": (
            "Delta-beta is the difference in mean methylation between the two groups, in "
            "beta units. 0.20 means a 20-percentage-point shift."
        ),
        "inputs": ["betas"],
        "outputs": ["stats"],
        "params": [
            choice(
                "comparison",
                "Comparison",
                "tumor_vs_normal",
                [
                    {"value": "tumor_vs_normal", "label": "Tumor vs normal"},
                    {"value": "subtype_vs_normal", "label": "Subtype vs normal"},
                    {"value": "subtype_vs_subtype", "label": "Subtype vs rest"},
                ],
                "Which two groups to contrast.",
            ),
            choice(
                "subtype_label",
                "Subtype",
                "Basal",
                [
                    {"value": "Basal", "label": "Basal"},
                    {"value": "LumA", "label": "LumA"},
                    {"value": "LumB", "label": "LumB"},
                    {"value": "Her2", "label": "Her2"},
                ],
                "Used only by the two subtype comparisons.",
            ),
            choice(
                "test",
                "Test",
                "welch_t",
                [
                    {"value": "welch_t", "label": "Welch t-test (unequal variance)"},
                    {"value": "student_t", "label": "Student t-test (equal variance)"},
                    {"value": "mannwhitney", "label": "Mann-Whitney U (rank based)"},
                ],
                "Welch matches the published pipeline. Mann-Whitney makes no normality assumption.",
            ),
            num("min_group_n", "Min samples per probe", 3, 2, 200, 1,
                "A probe needs at least this many non-missing values in each group to be tested."),
        ],
    },
    {
        "type": "multiple_testing",
        "name": "Multiple-testing correction",
        "group": "Statistics",
        "icon": "FDR",
        "color": "#c0392b",
        "summary": "Turns hundreds of thousands of raw p-values into an FDR.",
        "detail": (
            "Testing ~485,000 probes at p<0.05 would return ~24,000 false hits by chance. "
            "Benjamini-Hochberg controls the expected proportion of false positives."
        ),
        "inputs": ["stats"],
        "outputs": ["stats"],
        "params": [
            choice(
                "method",
                "Method",
                "benjamini_hochberg",
                [
                    {"value": "benjamini_hochberg", "label": "Benjamini-Hochberg (FDR)"},
                    {"value": "bonferroni", "label": "Bonferroni (FWER, strict)"},
                    {"value": "none", "label": "None (raw p-values)"},
                ],
                "BH matches the published pipeline.",
            ),
            num("fdr_threshold", "Significance threshold", 0.05, 0.0001, 0.5, 0.005,
                "Adjusted-p cutoff used to call a probe significant."),
        ],
    },
    {
        "type": "effect_filter",
        "name": "Effect-size filter",
        "group": "Filters",
        "icon": "dB",
        "color": "#0f8a7a",
        "summary": "Keeps only probes whose methylation shift is large enough to matter.",
        "detail": (
            "Statistical significance is not the same as biological size. With ~888 samples "
            "a 2-point shift can be highly significant and still meaningless."
        ),
        "inputs": ["stats"],
        "outputs": ["stats"],
        "params": [
            num("min_abs_delta_beta", "Min |delta-beta|", 0.20, 0.0, 0.9, 0.01,
                "Published threshold is 0.20 (a 20-percentage-point shift)."),
            choice(
                "direction",
                "Keep direction",
                "both",
                [
                    {"value": "both", "label": "Both"},
                    {"value": "hyper", "label": "Hypermethylated only"},
                    {"value": "hypo", "label": "Hypomethylated only"},
                ],
                "Hyper = more methylated in the first group; hypo = less.",
            ),
            num("min_group_n", "Min samples per group", 30, 0, 500, 1,
                "Published marker tables required >=30 tumour and >=30 normal per probe."),
        ],
    },
    # -- biology -------------------------------------------------------------
    {
        "type": "annotate",
        "name": "Annotate sites",
        "group": "Biology",
        "icon": "AN",
        "color": "#7d4fbf",
        "summary": "Attaches gene, coordinate, functional region and CpG-island context.",
        "detail": (
            "Region context is what separates a promoter hit (interpretable) from a "
            "gene-body hit (ambiguous)."
        ),
        "inputs": ["stats"],
        "outputs": ["stats"],
        "params": [
            num("promoter_upstream", "Promoter window upstream", 1500, 0, 5000, 100,
                "Bases upstream of the TSS still counted as promoter.", "bp"),
            num("promoter_downstream", "Promoter window downstream", 500, 0, 5000, 100,
                "Bases downstream of the TSS still counted as promoter.", "bp"),
            flag("require_island", "Require CpG island / shore", False,
                 "Restrict to island or shore context only."),
        ],
    },
    {
        "type": "direction_label",
        "name": "Direction of effect",
        "group": "Biology",
        "icon": "->",
        "color": "#7d4fbf",
        "summary": "Applies the promoter rule: silencing, activation, or ambiguous.",
        "detail": (
            "Promoter + hyper = predicted silencing. Promoter + hypo = predicted activation. "
            "Outside a promoter the consequence is not predictable, so it is labelled ambiguous."
        ),
        "inputs": ["stats"],
        "outputs": ["stats"],
        "params": [
            flag("strict_promoter_only", "Only label promoter sites", True,
                 "Off would extrapolate to gene bodies, which the data does not support."),
            flag("include_shores", "Treat shores as promoter-like", False,
                 "Shores flank islands; some regulatory effect, weaker evidence."),
        ],
    },
    # -- panel + model -------------------------------------------------------
    {
        "type": "panel_select",
        "name": "Biomarker panel",
        "group": "Panel & model",
        "icon": "PA",
        "color": "#e08a1e",
        "summary": "Picks a ranked, de-duplicated marker set from the surviving probes.",
        "detail": "The panel is what a diagnostic assay would actually measure.",
        "inputs": ["stats"],
        "outputs": ["panel"],
        "params": [
            num("top_n", "Panel size", 100, 5, 1000, 5, "How many probes to keep."),
            choice(
                "rank_by",
                "Rank by",
                "abs_delta_beta",
                [
                    {"value": "abs_delta_beta", "label": "Effect size (|delta-beta|)"},
                    {"value": "fdr", "label": "Statistical confidence (FDR)"},
                    {"value": "combined", "label": "Combined score"},
                ],
                "Published panel ranks by effect size, breaking ties on FDR.",
            ),
            flag("balance_direction", "Balance hyper / hypo", False,
                 "Force an even split between the two directions."),
            num("max_per_gene", "Max probes per gene", 0, 0, 20, 1,
                "Limits panel redundancy. 0 = no limit."),
        ],
    },
    {
        "type": "classifier",
        "name": "Classifier + validation",
        "group": "Panel & model",
        "icon": "ML",
        "color": "#e08a1e",
        "summary": "Cross-validated tumour/normal classifier scored by ROC-AUC.",
        "detail": (
            "Nested CV re-selects the features inside each training fold, so the test fold "
            "never influenced feature choice. That is the leakage-free number."
        ),
        "inputs": ["panel", "betas"],
        "outputs": ["model"],
        "params": [
            choice(
                "model",
                "Model",
                "logistic_regression",
                [
                    {"value": "logistic_regression", "label": "Logistic regression"},
                    {"value": "random_forest", "label": "Random forest"},
                ],
                "The published model is L2 logistic regression.",
            ),
            num("n_features", "Features used", 25, 2, 200, 1, "Top-N panel probes fed to the model."),
            num("cv_folds", "CV folds", 5, 2, 10, 1, "Stratified k-fold."),
            flag("nested", "Nested feature selection", True,
                 "ON = honest estimate. OFF reuses full-cohort rankings and inflates AUC."),
            num("seed", "Random seed", 42, 0, 99999, 1, "Fixed seed keeps runs reproducible."),
        ],
    },
    # -- enrichment ----------------------------------------------------------
    {
        "type": "enrichment",
        "name": "Pathway enrichment",
        "group": "Biology",
        "icon": "GS",
        "color": "#7d4fbf",
        "summary": "Over-representation test of the hit genes against curated gene sets.",
        "detail": (
            "Reported with the array-design caveat: HM450 over-samples promoters of "
            "neuronal and developmental genes, which inflates those terms."
        ),
        "inputs": ["stats"],
        "outputs": ["enrichment"],
        "params": [
            multi(
                "libraries",
                "Gene-set libraries",
                ["KEGG_2021_Human", "longevity_gene_sets"],
                [
                    {"value": "KEGG_2021_Human", "label": "KEGG 2021 Human"},
                    {"value": "Reactome_2022", "label": "Reactome 2022"},
                    {"value": "GO_Biological_Process_2023", "label": "GO Biological Process 2023"},
                    {"value": "longevity_gene_sets", "label": "Longevity (curated)"},
                ],
                "Real GMT libraries shipped with this app; no network call is made.",
            ),
            choice(
                "background",
                "Background universe",
                "array_universe",
                [
                    {"value": "array_universe", "label": "Genes on the array (correct)"},
                    {"value": "library_universe", "label": "Genes in the library"},
                ],
                "Using all genes as background is the classic mistake; array universe is correct.",
            ),
            flag("split_direction", "Split hyper / hypo", True, "Run each direction separately."),
            num("min_set_size", "Min gene-set size", 5, 1, 200, 1, "Ignore very small sets."),
            num("max_set_size", "Max gene-set size", 500, 10, 5000, 10, "Ignore very broad sets."),
            num("fdr_threshold", "Term FDR threshold", 0.05, 0.0001, 0.5, 0.005, "Cutoff for reporting a term."),
        ],
    },
    # -- output --------------------------------------------------------------
    {
        "type": "report",
        "name": "Generate report",
        "group": "Output",
        "icon": "RP",
        "color": "#173a5c",
        "summary": "Builds a standalone HTML report plus all downloadable tables.",
        "detail": "The report is self-contained and matches the published site's layout.",
        "inputs": ["stats", "panel", "model", "enrichment"],
        "outputs": [],
        "params": [
            text("title", "Report title", "BRCA Methylation - Pipeline Run", "Heading shown at the top."),
            flag("include_caveats", "Include caveats section", True,
                 "Keeps the dataset limitations attached to the numbers."),
            flag("include_volcano", "Include volcano plot", True, "Interactive volcano in the report."),
            flag("include_tables", "Include result tables", True, "Top markers, panel, enrichment."),
            flag("include_methods", "Include methods + parameters", True,
                 "Records the exact parameter values this run used."),
        ],
    },
]

NODES_BY_TYPE = {n["type"]: n for n in NODES}

# The graph the builder loads on first open - the published pipeline.
DEFAULT_GRAPH = {
    "nodes": [
        {"id": "n1", "type": "load_data", "x": 40, "y": 60, "params": {}},
        {"id": "n2", "type": "qc_filter", "x": 40, "y": 200, "params": {}},
        {"id": "n3", "type": "differential", "x": 40, "y": 340, "params": {}},
        {"id": "n4", "type": "multiple_testing", "x": 330, "y": 340, "params": {}},
        {"id": "n5", "type": "effect_filter", "x": 620, "y": 340, "params": {}},
        {"id": "n6", "type": "annotate", "x": 620, "y": 200, "params": {}},
        {"id": "n7", "type": "direction_label", "x": 620, "y": 60, "params": {}},
        {"id": "n8", "type": "panel_select", "x": 910, "y": 60, "params": {}},
        {"id": "n9", "type": "classifier", "x": 910, "y": 200, "params": {}},
        {"id": "n10", "type": "enrichment", "x": 910, "y": 340, "params": {}},
        {"id": "n11", "type": "report", "x": 1200, "y": 200, "params": {}},
    ],
    "edges": [
        {"from": "n1", "to": "n2"},
        {"from": "n2", "to": "n3"},
        {"from": "n3", "to": "n4"},
        {"from": "n4", "to": "n5"},
        {"from": "n5", "to": "n6"},
        {"from": "n6", "to": "n7"},
        {"from": "n7", "to": "n8"},
        {"from": "n8", "to": "n9"},
        {"from": "n7", "to": "n10"},
        {"from": "n9", "to": "n11"},
        {"from": "n10", "to": "n11"},
    ],
}


def defaults_for(node_type):
    node = NODES_BY_TYPE.get(node_type)
    if not node:
        return {}
    return {p["key"]: p["default"] for p in node["params"]}


def merged_params(node_type, params):
    merged = defaults_for(node_type)
    merged.update(params or {})
    return merged
