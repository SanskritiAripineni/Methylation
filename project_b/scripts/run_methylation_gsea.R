#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(AnnotationDbi)
  library(IlluminaHumanMethylation450kanno.ilmn12.hg19)
  library(IlluminaHumanMethylation450kmanifest)
  library(jsonlite)
  library(methylGSA)
  library(minfi)
  library(missMethyl)
  library(org.Hs.eg.db)
  library(reactome.db)
})

FDR_THRESHOLD <- 0.05
MIN_ABS_DELTA_BETA <- 0.20
PROJECT_ROOT_SENTINEL <- file.path("project_b", "brca_local_inputs.json")
SUPERVISOR_ARRAY_FOCUS_TERMS <- c(
  "14. FGF Family",
  "09. IGF / Insulin Signaling",
  "16. Wnt Signaling",
  "13. TGF-beta Signaling",
  "15. ECM / Skin Aging"
)

find_project_root <- function(start = getwd()) {
  current <- normalizePath(start, mustWork = TRUE)
  repeat {
    if (file.exists(file.path(current, PROJECT_ROOT_SENTINEL))) {
      return(current)
    }
    parent <- dirname(current)
    if (identical(parent, current)) {
      stop("Could not locate project root containing ", PROJECT_ROOT_SENTINEL)
    }
    current <- parent
  }
}

resolve_project_b_path <- function(path_value, project_b_dir) {
  if (grepl("^/", path_value)) {
    return(normalizePath(path_value, mustWork = FALSE))
  }
  normalizePath(file.path(project_b_dir, path_value), mustWork = FALSE)
}

write_tsv <- function(x, path) {
  write.table(x, path, sep = "\t", quote = FALSE, row.names = FALSE, na = "")
}

read_gmt_symbols <- function(path) {
  lines <- readLines(path, warn = FALSE)
  sets <- list()
  descriptions <- character()
  for (line in lines[nzchar(lines)]) {
    parts <- strsplit(line, "\t", fixed = TRUE)[[1]]
    if (length(parts) < 3) next
    term <- parts[[1]]
    descriptions[[term]] <- parts[[2]]
    sets[[term]] <- unique(parts[-c(1, 2)])
  }
  attr(sets, "descriptions") <- descriptions
  sets
}

map_symbol_sets_to_entrez <- function(symbol_sets) {
  all_symbols <- sort(unique(unlist(symbol_sets, use.names = FALSE)))
  entrez <- AnnotationDbi::mapIds(
    org.Hs.eg.db,
    keys = all_symbols,
    column = "ENTREZID",
    keytype = "SYMBOL",
    multiVals = "first"
  )
  mapped <- list()
  rows <- list()
  for (term in names(symbol_sets)) {
    symbols <- symbol_sets[[term]]
    ids <- unname(entrez[symbols])
    keep <- !is.na(ids) & nzchar(ids)
    mapped[[term]] <- sort(unique(ids[keep]))
    rows[[term]] <- data.frame(
      term = term,
      symbol = symbols,
      entrez_id = ifelse(is.na(ids), NA_character_, ids),
      mapped = keep,
      stringsAsFactors = FALSE
    )
  }
  list(sets = mapped, mapping = do.call(rbind, rows))
}

read_entrez_sets_tsv <- function(path) {
  df <- read.delim(path, check.names = FALSE, stringsAsFactors = FALSE)
  sets <- list()
  for (i in seq_len(nrow(df))) {
    ids <- unlist(strsplit(df$entrez_ids[[i]], ",", fixed = TRUE), use.names = FALSE)
    ids <- sort(unique(trimws(ids[nzchar(trimws(ids))])))
    if (length(ids)) sets[[df$set_name[[i]]]] <- ids
  }
  sets
}

load_reactome_entrez_sets <- function() {
  ids_by_pathway <- as.list(reactome.db::reactomePATHID2EXTID)
  names_by_pathway <- as.list(reactome.db::reactomePATHID2NAME)
  human_ids <- grep("^R-HSA-", names(ids_by_pathway), value = TRUE)
  valid_entrez <- keys(org.Hs.eg.db, keytype = "ENTREZID")
  sets <- list()
  rows <- list()
  for (pathway_id in human_ids) {
    original_ids <- sort(unique(as.character(ids_by_pathway[[pathway_id]])))
    original_ids <- original_ids[nzchar(original_ids)]
    ids <- intersect(original_ids, valid_entrez)
    if (!length(ids)) next
    raw_name <- names_by_pathway[[pathway_id]]
    pathway_name <- if (length(raw_name)) raw_name[[1]] else pathway_id
    pathway_name <- sub("^Homo sapiens: ", "", pathway_name)
    pathway_name <- iconv(pathway_name, from = "", to = "ASCII//TRANSLIT", sub = "")
    term <- paste0("reactome:", pathway_name, " [", pathway_id, "]")
    sets[[term]] <- ids
    rows[[term]] <- data.frame(
      term = term,
      reactome_id = pathway_id,
      n_original_members = length(original_ids),
      n_entrez = length(ids),
      stringsAsFactors = FALSE
    )
  }
  list(sets = sets, metadata = do.call(rbind, rows))
}

as_result_table <- function(res, term_col = "term") {
  df <- as.data.frame(res, stringsAsFactors = FALSE)
  df[[term_col]] <- rownames(df)
  rownames(df) <- NULL
  df[, c(term_col, setdiff(names(df), term_col)), drop = FALSE]
}

add_method_columns <- function(df, method, collection, direction) {
  df$method <- method
  df$collection <- collection
  df$direction <- direction
  df[, c("method", "collection", "direction", setdiff(names(df), c("method", "collection", "direction"))), drop = FALSE]
}

run_gometh_collection <- function(sig_cpg, all_cpg, collection, direction, anno, output_dir) {
  message("Running missMethyl gometh: ", collection, " / ", direction)
  res <- missMethyl::gometh(
    sig.cpg = sig_cpg,
    all.cpg = all_cpg,
    collection = collection,
    array.type = "450K",
    plot.bias = FALSE,
    prior.prob = TRUE,
    anno = anno,
    equiv.cpg = TRUE,
    fract.counts = TRUE,
    genomic.features = "ALL",
    sig.genes = FALSE
  )
  df <- add_method_columns(as_result_table(res), "missMethyl_gometh", collection, direction)
  write_tsv(df, file.path(output_dir, paste0("missmethyl_gometh_", tolower(collection), "_", direction, ".tsv")))
  df
}

run_gsameth_collection <- function(sig_cpg, all_cpg, sets, collection_name, direction, anno, output_dir) {
  message("Running missMethyl gsameth: ", collection_name, " / ", direction)
  res <- missMethyl::gsameth(
    sig.cpg = sig_cpg,
    all.cpg = all_cpg,
    collection = sets,
    array.type = "450K",
    plot.bias = FALSE,
    prior.prob = TRUE,
    anno = anno,
    equiv.cpg = TRUE,
    fract.counts = TRUE,
    genomic.features = "ALL",
    sig.genes = FALSE
  )
  df <- add_method_columns(as_result_table(res), "missMethyl_gsameth", collection_name, direction)
  write_tsv(df, file.path(output_dir, paste0("missmethyl_gsameth_", collection_name, "_", direction, ".tsv")))
  df
}

run_methylrra_collection <- function(pvals, sets, collection_name, direction, output_dir,
                                     minsize = 5, maxsize = 1000, gs_idtype = "ENTREZID") {
  message("Running methylGSA methylRRA GSEA: ", collection_name, " / ", direction)
  set.seed(20260706)
  res <- methylGSA::methylRRA(
    cpg.pval = pvals,
    array.type = "450K",
    group = "all",
    method = "GSEA",
    GS.list = sets,
    GS.idtype = gs_idtype,
    minsize = minsize,
    maxsize = maxsize
  )
  df <- add_method_columns(as_result_table(res, term_col = "term"), "methylGSA_methylRRA_GSEA", collection_name, direction)
  write_tsv(df, file.path(output_dir, paste0("methylgsa_methylrra_gsea_", collection_name, "_", direction, ".tsv")))
  df
}

run_methylrra_builtin <- function(pvals, gs_type, direction, output_dir, minsize = 10, maxsize = 1000) {
  message("Running methylGSA methylRRA GSEA built-in: ", gs_type, " / ", direction)
  set.seed(20260706)
  res <- methylGSA::methylRRA(
    cpg.pval = pvals,
    array.type = "450K",
    group = "all",
    method = "GSEA",
    GS.list = NULL,
    GS.idtype = "ENTREZID",
    GS.type = gs_type,
    minsize = minsize,
    maxsize = maxsize
  )
  df <- add_method_columns(as_result_table(res, term_col = "term"), "methylGSA_methylRRA_GSEA", gs_type, direction)
  write_tsv(df, file.path(output_dir, paste0("methylgsa_methylrra_gsea_", tolower(gs_type), "_", direction, ".tsv")))
  df
}

sig_terms <- function(df, pcol) {
  if (!nrow(df) || !(pcol %in% names(df))) return(character())
  sort(unique(df$term[!is.na(df[[pcol]]) & df[[pcol]] < FDR_THRESHOLD]))
}

split_result_name <- function(nm) {
  for (direction in c("hypermethylated", "hypomethylated", "all")) {
    suffix <- paste0("_", direction)
    if (endsWith(nm, suffix)) {
      collection <- substr(nm, 1, nchar(nm) - nchar(suffix))
      return(list(collection = collection, direction = direction))
    }
  }
  stop("Cannot parse result name: ", nm)
}

summarize_result_tables <- function(miss_results, methyl_results) {
  out <- list()
  for (nm in names(miss_results)) {
    terms <- sig_terms(miss_results[[nm]], "FDR")
    parsed <- split_result_name(nm)
    collection <- tolower(parsed$collection)
    direction <- parsed$direction
    miss_method <- if (collection %in% c("go", "kegg")) "gometh" else "gsameth"
    key <- paste("missMethyl", miss_method, collection, direction, sep = "_")
    out[[key]] <- list(
      p_adjust_column = "FDR",
      n_significant = length(terms),
      significant_terms = I(as.character(terms))
    )
  }
  for (nm in names(methyl_results)) {
    terms <- sig_terms(methyl_results[[nm]], "padj")
    parsed <- split_result_name(nm)
    collection <- tolower(parsed$collection)
    direction <- parsed$direction
    key <- paste("methylGSA", collection, direction, sep = "_")
    out[[key]] <- list(
      p_adjust_column = "padj",
      n_significant = length(terms),
      significant_terms = I(as.character(terms))
    )
  }
  out
}

fmt_p <- function(x) {
  ifelse(is.na(x), "NA", formatC(x, format = "e", digits = 3))
}

split_genes <- function(value) {
  if (length(value) == 0 || is.na(value)) return(character())
  genes <- trimws(unlist(strsplit(as.character(value), "[;,]", perl = TRUE), use.names = FALSE))
  genes[nzchar(genes)]
}

load_background_genes <- function(out_dir) {
  background <- read.delim(file.path(out_dir, "tumor_vs_normal", "probe_missingness.tsv"), check.names = FALSE, stringsAsFactors = FALSE)
  retained <- tolower(as.character(background$retained)) %in% c("true", "1", "yes")
  retained_df <- background[retained, , drop = FALSE]
  genes <- sort(unique(unlist(lapply(retained_df$gene, split_genes), use.names = FALSE)))
  list(genes = genes, retained_probe_count = nrow(retained_df))
}

load_query_gene_sets_for_ora <- function(mech_df) {
  sig <- mech_df[
    !is.na(mech_df$fdr) & mech_df$fdr < FDR_THRESHOLD &
      !is.na(mech_df$abs_delta_beta) & mech_df$abs_delta_beta >= MIN_ABS_DELTA_BETA,
    ,
    drop = FALSE
  ]
  gene_sets <- list(hypermethylated = character(), hypomethylated = character())
  for (i in seq_len(nrow(sig))) {
    row <- sig[i, , drop = FALSE]
    genes <- split_genes(row$genes_all)
    if (!length(genes)) genes <- split_genes(row$gene)
    nearest <- trimws(as.character(row$gene_nearest))
    if (!is.na(nearest) && nzchar(nearest) && !(nearest %in% genes)) {
      genes <- c(genes, nearest)
    }
    direction <- as.character(row$direction)
    if (direction %in% names(gene_sets)) {
      gene_sets[[direction]] <- c(gene_sets[[direction]], genes)
    }
  }
  list(
    sig_cpgs = sig,
    gene_sets = list(
      hypermethylated = sort(unique(gene_sets$hypermethylated)),
      hypomethylated = sort(unique(gene_sets$hypomethylated))
    )
  )
}

run_uncorrected_ora <- function(query_genes, background_genes, gene_sets, direction, library_label) {
  query <- intersect(unique(query_genes), background_genes)
  universe_size <- length(background_genes)
  query_size <- length(query)
  rows <- list()
  if (!query_size) {
    return(data.frame(
      library = character(),
      direction = character(),
      term = character(),
      n_genes = integer(),
      query_size = integer(),
      background_size = integer(),
      overlap_n = integer(),
      overlap_genes = character(),
      p = numeric(),
      adj_p = numeric(),
      stringsAsFactors = FALSE
    ))
  }
  for (term in names(gene_sets)) {
    term_background <- intersect(unique(gene_sets[[term]]), background_genes)
    if (!length(term_background)) next
    overlap <- sort(intersect(query, term_background))
    overlap_n <- length(overlap)
    p_value <- if (overlap_n) {
      phyper(overlap_n - 1, length(term_background), universe_size - length(term_background), query_size, lower.tail = FALSE)
    } else {
      1
    }
    rows[[term]] <- data.frame(
      library = library_label,
      direction = direction,
      term = term,
      n_genes = length(term_background),
      query_size = query_size,
      background_size = universe_size,
      overlap_n = overlap_n,
      overlap_genes = paste(overlap, collapse = ","),
      p = p_value,
      stringsAsFactors = FALSE
    )
  }
  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out$adj_p <- p.adjust(out$p, method = "BH")
  out[order(out$adj_p, out$p, -out$overlap_n), , drop = FALSE]
}

make_comparison <- function(ora, miss_long, methyl_long, methyl_all) {
  miss_key <- miss_long[, c("term", "direction", "P.DE", "FDR", "N", "DE"), drop = FALSE]
  names(miss_key) <- c("term", "direction", "missmethyl_p", "missmethyl_fdr", "missmethyl_n_genes", "missmethyl_de_genes")

  methyl_dir_key <- methyl_long[, c("term", "direction", "pvalue", "padj", "NES", "Size", "core_enrichment"), drop = FALSE]
  names(methyl_dir_key) <- c("term", "direction", "methylgsa_direction_p", "methylgsa_direction_padj", "methylgsa_direction_nes", "methylgsa_size", "methylgsa_direction_core")

  methyl_all_key <- methyl_all[, c("term", "pvalue", "padj", "NES", "core_enrichment"), drop = FALSE]
  names(methyl_all_key) <- c("term", "methylgsa_all_p", "methylgsa_all_padj", "methylgsa_all_nes", "methylgsa_all_core")

  out <- merge(ora, miss_key, by = c("term", "direction"), all.x = TRUE, sort = FALSE)
  out <- merge(out, methyl_dir_key, by = c("term", "direction"), all.x = TRUE, sort = FALSE)
  out <- merge(out, methyl_all_key, by = "term", all.x = TRUE, sort = FALSE)
  out$ora_significant <- !is.na(out$adj_p) & out$adj_p < FDR_THRESHOLD
  out$missmethyl_significant <- !is.na(out$missmethyl_fdr) & out$missmethyl_fdr < FDR_THRESHOLD
  out$methylgsa_direction_significant <- !is.na(out$methylgsa_direction_padj) & out$methylgsa_direction_padj < FDR_THRESHOLD
  out$methylgsa_all_significant <- !is.na(out$methylgsa_all_padj) & out$methylgsa_all_padj < FDR_THRESHOLD
  out <- out[order(out$direction, out$adj_p, out$term), ]
  rownames(out) <- NULL
  out
}

make_supervisor_arrays_comparison <- function(ora, miss_long, methyl_long, methyl_all) {
  comparison <- make_comparison(ora, miss_long, methyl_long, methyl_all)
  comparison$collection_note <- "supervisor antibody-array categories"
  comparison
}

make_supervisor_focus_verdict <- function(supervisor_comparison) {
  focus <- supervisor_comparison[
    supervisor_comparison$term %in% SUPERVISOR_ARRAY_FOCUS_TERMS &
      supervisor_comparison$direction == "hypermethylated",
    ,
    drop = FALSE
  ]
  focus$survives_missmethyl_bias_correction <- !is.na(focus$missmethyl_fdr) & focus$missmethyl_fdr < FDR_THRESHOLD
  focus$rank_based_support_all_pvalues <- !is.na(focus$methylgsa_all_padj) & focus$methylgsa_all_padj < FDR_THRESHOLD
  focus$rank_based_support_hyper_direction <- !is.na(focus$methylgsa_direction_padj) & focus$methylgsa_direction_padj < FDR_THRESHOLD
  focus$verdict <- ifelse(
    focus$survives_missmethyl_bias_correction,
    "survives missMethyl bias correction",
    ifelse(
      focus$rank_based_support_all_pvalues | focus$rank_based_support_hyper_direction,
      "rank-based support only",
      "collapses after methylation-aware testing"
    )
  )
  focus[order(match(focus$term, SUPERVISOR_ARRAY_FOCUS_TERMS)), , drop = FALSE]
}

write_methods_readme <- function(path, counts, package_versions, supervisor_arrays_count = NULL, tiny_supervisor_sets = NULL) {
  lines <- c(
    "# Methylation-aware GSEA provenance",
    "",
    "This directory replaces the Phase 3 pure-Python ORA interpretation layer with methylation-aware enrichment while leaving the Phase 3 ORA outputs untouched as the comparison baseline.",
    "",
    "## Install",
    "",
    "R 4.4.2 and Bioconductor 3.20 were used for this run. From the repository root:",
    "",
    "```r",
    "install.packages(\"BiocManager\", repos = \"https://cloud.r-project.org\")",
    "BiocManager::install(c(",
    "  \"missMethyl\",",
    "  \"methylGSA\",",
    "  \"IlluminaHumanMethylation450kanno.ilmn12.hg19\",",
    "  \"IlluminaHumanMethylation450kmanifest\",",
    "  \"org.Hs.eg.db\",",
    "  \"reactome.db\"",
    "), ask = FALSE, update = FALSE)",
    "install.packages(\"ggtangle\", repos = \"https://cloud.r-project.org\")",
    "```",
    "",
    "If source builds fail for CRAN dependencies on macOS, rerun the same `BiocManager::install()` command with `type = \"binary\"` for CRAN dependencies, then rerun the Bioconductor install. This run required that for several CRAN dependencies before the 450K annotation packages were built from source.",
    "",
    "## Run",
    "",
    "```bash",
    "LC_ALL=C Rscript project_b/scripts/run_methylation_gsea.R",
    "```",
    "",
    "The script discovers `project_b/brca_local_inputs.json`, reads `outputs/brca_methylation/differential_methylation.tsv`, `outputs/brca_methylation/differential_methylation_mechanics.tsv`, the Phase 3 curated `pathway_enrichment_longevity/longevity_gene_sets.gmt`, and the supervisor antibody-array catalog in `outputs/brca_methylation/gsea/longevity_arrays/`, then writes only to `outputs/brca_methylation/gsea/`.",
    "",
    "## Methods",
    "",
    paste0("- Significant CpGs for missMethyl used the same Phase 3/ORA gate: FDR < ", FDR_THRESHOLD, " and |delta_beta| >= ", MIN_ABS_DELTA_BETA, ", split into hypermethylated and hypomethylated directions."),
    "- The missMethyl universe (`all.cpg`) starts from every probe ID in `differential_methylation.tsv` and is restricted to CpGs present in the native Illumina 450K hg19 annotation because missMethyl models probe-number bias through that annotation.",
    "- missMethyl `gometh()` was run for built-in GO and KEGG collections. `gsameth()` was run for custom Reactome, curated longevity, and supervisor-array collections, with custom missMethyl sets represented as Entrez Gene IDs.",
    "- methylGSA `methylRRA(method = \"GSEA\")` was run on per-CpG p-values for all valid tested CpGs. The `all` run is the strict threshold-free rank test; hyper/hypo companion runs keep the same CpG universe but set opposite-direction CpGs to p = 1 to provide direction-specific checks without a significance threshold. The supervisor-array methylRRA run uses the original gene symbols from the GMT.",
    "- `supervisor_arrays_ora_all.tsv` is an uncorrected hypergeometric ORA baseline using the same Phase 3 gene-level query gate and retained-probe gene background as the original ORA layer.",
    "- methylGSA retrieves built-in KEGG annotations through KEGG REST during the run. The curated longevity comparison remains pinned to the Phase 3 GMT on disk.",
    "- missMethyl uses hg19 gene annotation for enrichment. This is acceptable here because the enrichment test is gene-membership based and does not alter the Phase 0/Phase 2 hg38 site maps or coordinate-level biological claims.",
    "- Methylation enrichment does not imply expression repression except for promoter-context CpGs. Body/intergenic methylation remains mechanistically ambiguous.",
    "",
    "## Probe accounting",
    "",
    paste0("- Raw tested probe IDs: ", counts$all_cpg_raw),
    paste0("- Native 450K-annotated CpGs used by missMethyl: ", counts$all_cpg_annotated),
    paste0("- Probe IDs outside native 450K annotation/control/non-CpG IDs excluded from missMethyl universe: ", counts$all_cpg_unannotated),
    paste0("- CpGs with finite p-values used by methylGSA: ", counts$methylgsa_pvals),
    paste0("- Hypermethylated significant CpGs used by missMethyl: ", counts$sig_hyper),
    paste0("- Hypomethylated significant CpGs used by missMethyl: ", counts$sig_hypo),
    if (!is.null(supervisor_arrays_count)) paste0("- Supervisor antibody-array categories tested: ", supervisor_arrays_count) else NULL,
    if (!is.null(tiny_supervisor_sets) && length(tiny_supervisor_sets)) paste0("- Supervisor categories with fewer than 5 Entrez-mapped genes: ", paste(tiny_supervisor_sets, collapse = "; ")) else NULL,
    "",
    "## Package versions",
    "",
    paste0("- ", names(package_versions), ": ", unname(package_versions))
  )
  writeLines(lines, path)
}

write_comparison_md <- function(path, comparison, summary_lists, terc_rows, supervisor_focus = NULL, supervisor_summary_lists = NULL) {
  stem_rows <- comparison[grepl("pluripot|stem_cell", comparison$term), ]
  stem_ora_sig <- stem_rows[stem_rows$ora_significant, ]
  stem_survived <- stem_ora_sig[stem_ora_sig$missmethyl_significant | stem_ora_sig$methylgsa_direction_significant | stem_ora_sig$methylgsa_all_significant, ]
  longevity_focus <- comparison[grepl("telomere|mitochondrial|foxo|mtor|ampk", comparison$term, ignore.case = TRUE), ]
  longevity_changed <- longevity_focus[
    longevity_focus$ora_significant != longevity_focus$missmethyl_significant |
      longevity_focus$ora_significant != longevity_focus$methylgsa_all_significant,
  ]

  stem_sentence <- if (nrow(stem_survived)) {
    paste0(
      "At least one ORA stem/pluripotency term remained significant after methylation-aware testing: ",
      paste(stem_survived$term, collapse = ", "), "."
    )
  } else if (nrow(stem_ora_sig)) {
    "The ORA stem/pluripotency signal did not survive methylation-aware correction in missMethyl or threshold-free methylRRA at FDR < 0.05."
  } else {
    "No ORA stem/pluripotency term was significant in the Phase 3 baseline table."
  }

  longevity_sentence <- if (nrow(longevity_changed)) {
    paste0(
      "Some longevity-family verdicts changed after bias-aware/rank testing: ",
      paste(unique(longevity_changed$term), collapse = ", "), "."
    )
  } else {
    "The telomere, mitochondrial, FoxO, mTOR, and AMPK verdicts did not gain new FDR < 0.05 support after methylation-aware testing."
  }

  terc_sentence <- if (nrow(terc_rows)) {
    paste0(
      "TERC appears in methylGSA leading-edge/core-enrichment text for: ",
      paste(unique(terc_rows$term), collapse = ", "),
      ". See `gsea_vs_ora.tsv` for the associated adjusted p-values."
    )
  } else {
    "TERC did not surface as a leading-edge/core-enrichment gene in the curated longevity methylRRA results."
  }

  top_table <- comparison[
    order(
      -as.integer(comparison$ora_significant),
      comparison$missmethyl_fdr,
      comparison$methylgsa_all_padj,
      na.last = TRUE
    ),
  ]
  top_table <- head(top_table[, c(
    "term", "direction", "adj_p", "missmethyl_fdr", "methylgsa_direction_padj",
    "methylgsa_all_padj", "ora_significant", "missmethyl_significant", "methylgsa_all_significant"
  )], 14)

  table_lines <- c(
    "| term | direction | ORA adj-p | missMethyl FDR | methylRRA direction padj | methylRRA all padj | ORA sig | missMethyl sig | methylRRA all sig |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
  )
  if (nrow(top_table)) {
    for (i in seq_len(nrow(top_table))) {
      row_line <- paste(
        top_table$term[[i]],
        top_table$direction[[i]],
        fmt_p(top_table$adj_p[[i]]),
        fmt_p(top_table$missmethyl_fdr[[i]]),
        fmt_p(top_table$methylgsa_direction_padj[[i]]),
        fmt_p(top_table$methylgsa_all_padj[[i]]),
        top_table$ora_significant[[i]],
        top_table$missmethyl_significant[[i]],
        top_table$methylgsa_all_significant[[i]],
        sep = " | "
      )
      table_lines <- c(table_lines, paste0("| ", row_line, " |"))
    }
  }

  supervisor_lines <- character()
  if (!is.null(supervisor_focus) && nrow(supervisor_focus)) {
    survived <- supervisor_focus$term[supervisor_focus$survives_missmethyl_bias_correction]
    rank_only <- supervisor_focus$term[
      !supervisor_focus$survives_missmethyl_bias_correction &
        (supervisor_focus$rank_based_support_all_pvalues | supervisor_focus$rank_based_support_hyper_direction)
    ]
    collapsed <- supervisor_focus$term[
      !supervisor_focus$survives_missmethyl_bias_correction &
        !(supervisor_focus$rank_based_support_all_pvalues | supervisor_focus$rank_based_support_hyper_direction)
    ]
    focus_table_lines <- c(
      "| set | ORA p | ORA adj-p | missMethyl FDR | methylRRA hyper padj | methylRRA all padj | verdict |",
      "|---|---:|---:|---:|---:|---:|---|"
    )
    for (i in seq_len(nrow(supervisor_focus))) {
      row_line <- paste(
        supervisor_focus$term[[i]],
        fmt_p(supervisor_focus$p[[i]]),
        fmt_p(supervisor_focus$adj_p[[i]]),
        fmt_p(supervisor_focus$missmethyl_fdr[[i]]),
        fmt_p(supervisor_focus$methylgsa_direction_padj[[i]]),
        fmt_p(supervisor_focus$methylgsa_all_padj[[i]]),
        supervisor_focus$verdict[[i]],
        sep = " | "
      )
      focus_table_lines <- c(focus_table_lines, paste0("| ", row_line, " |"))
    }
    supervisor_lines <- c(
      "",
      "## Supervisor Arrays",
      "",
      "The supervisor-array collection contains custom antibody/protein-array categories. These are not canonical pathway definitions, and some groupings are biologically loose; for example, the telomere category includes ICAM genes. Several categories are very small, including `03. FOXO Pathway` with 2 Entrez-mapped genes and `11. NAD+ Metabolism` with 4, so null results for these sets have low power.",
      "",
      paste0("- Focus sets surviving missMethyl probe-bias correction: ", ifelse(length(survived), paste(survived, collapse = ", "), "none")),
      paste0("- Focus sets with rank-based methylRRA support only: ", ifelse(length(rank_only), paste(rank_only, collapse = ", "), "none")),
      paste0("- Focus sets collapsing after methylation-aware testing: ", ifelse(length(collapsed), paste(collapsed, collapse = ", "), "none")),
      "",
      "### FGF / IGF / Wnt / TGF-beta / ECM Focus",
      "",
      focus_table_lines,
      "",
      "Full supervisor-array comparison: `supervisor_arrays_gsea_vs_ora.tsv`."
    )
    if (!is.null(supervisor_summary_lists)) {
      supervisor_lines <- c(
        supervisor_lines,
        "",
        "### Supervisor Array Significant Sets",
        "",
        paste0("- ORA hypermethylated: ", ifelse(length(supervisor_summary_lists$ora_hyper), paste(supervisor_summary_lists$ora_hyper, collapse = ", "), "none")),
        paste0("- ORA hypomethylated: ", ifelse(length(supervisor_summary_lists$ora_hypo), paste(supervisor_summary_lists$ora_hypo, collapse = ", "), "none")),
        paste0("- missMethyl hypermethylated: ", ifelse(length(supervisor_summary_lists$miss_hyper), paste(supervisor_summary_lists$miss_hyper, collapse = ", "), "none")),
        paste0("- missMethyl hypomethylated: ", ifelse(length(supervisor_summary_lists$miss_hypo), paste(supervisor_summary_lists$miss_hypo, collapse = ", "), "none")),
        paste0("- methylRRA all p-values: ", ifelse(length(supervisor_summary_lists$methyl_all), paste(supervisor_summary_lists$methyl_all, collapse = ", "), "none")),
        paste0("- methylRRA hyper-direction p-values: ", ifelse(length(supervisor_summary_lists$methyl_hyper), paste(supervisor_summary_lists$methyl_hyper, collapse = ", "), "none")),
        paste0("- methylRRA hypo-direction p-values: ", ifelse(length(supervisor_summary_lists$methyl_hypo), paste(supervisor_summary_lists$methyl_hypo, collapse = ", "), "none"))
      )
    }
  }

  lines <- c(
    "# ORA versus methylation-aware GSEA",
    "",
    "Phase 3 ORA is kept as the baseline. The new columns compare that thresholded gene-list hypergeometric result with missMethyl probe-number-bias correction and methylGSA/methylRRA rank-based GSEA.",
    "",
    "## Verdict",
    "",
    paste0("- Stem-cell/pluripotency: ", stem_sentence),
    paste0("- Longevity families: ", longevity_sentence),
    paste0("- TERC/rank-based check: ", terc_sentence),
    "",
    "These are methylation enrichment results only. They do not prove expression repression, and promoter/body context must still be used before assigning a silencing or activation mechanism.",
    "",
    "## Significant curated longevity sets",
    "",
    paste0("- ORA hypermethylated: ", ifelse(length(summary_lists$ora_hyper), paste(summary_lists$ora_hyper, collapse = ", "), "none")),
    paste0("- ORA hypomethylated: ", ifelse(length(summary_lists$ora_hypo), paste(summary_lists$ora_hypo, collapse = ", "), "none")),
    paste0("- missMethyl hypermethylated: ", ifelse(length(summary_lists$miss_hyper), paste(summary_lists$miss_hyper, collapse = ", "), "none")),
    paste0("- missMethyl hypomethylated: ", ifelse(length(summary_lists$miss_hypo), paste(summary_lists$miss_hypo, collapse = ", "), "none")),
    paste0("- methylRRA all p-values: ", ifelse(length(summary_lists$methyl_all), paste(summary_lists$methyl_all, collapse = ", "), "none")),
    paste0("- methylRRA hyper-direction p-values: ", ifelse(length(summary_lists$methyl_hyper), paste(summary_lists$methyl_hyper, collapse = ", "), "none")),
    paste0("- methylRRA hypo-direction p-values: ", ifelse(length(summary_lists$methyl_hypo), paste(summary_lists$methyl_hypo, collapse = ", "), "none")),
    "",
    "`methylRRA all p-values` is the undirected threshold-free rank test and is repeated on both direction rows in `gsea_vs_ora.tsv`; use the hyper/hypo methylRRA columns for direction-specific rank checks.",
    "",
    "## Comparison Table",
    "",
    table_lines,
    "",
    "Full per-set comparison: `gsea_vs_ora.tsv`.",
    supervisor_lines
  )
  writeLines(lines, path)
}

main <- function() {
  project_root <- find_project_root()
  project_b_dir <- file.path(project_root, "project_b")
  config_path <- file.path(project_b_dir, "brca_local_inputs.json")
  config <- jsonlite::fromJSON(config_path)
  out_dir <- resolve_project_b_path(config$output_dir, project_b_dir)
  gsea_dir <- file.path(out_dir, "gsea")
  dir.create(gsea_dir, showWarnings = FALSE, recursive = TRUE)

  diff_path <- file.path(out_dir, "differential_methylation.tsv")
  mechanics_path <- file.path(out_dir, "differential_methylation_mechanics.tsv")
  phase3_dir <- file.path(out_dir, "pathway_enrichment_longevity")
  gmt_path <- file.path(phase3_dir, "longevity_gene_sets.gmt")
  ora_path <- file.path(phase3_dir, "longevity_ora_all.tsv")
  supervisor_arrays_dir <- file.path(gsea_dir, "longevity_arrays")
  supervisor_arrays_gmt_path <- file.path(supervisor_arrays_dir, "longevity_arrays_gene_sets.gmt")
  supervisor_arrays_entrez_path <- file.path(supervisor_arrays_dir, "longevity_arrays_entrez.tsv")

  message("Reading differential methylation inputs")
  diff_df <- read.delim(diff_path, check.names = FALSE, stringsAsFactors = FALSE)
  mech_df <- read.delim(mechanics_path, check.names = FALSE, stringsAsFactors = FALSE)
  ora_df <- read.delim(ora_path, check.names = FALSE, stringsAsFactors = FALSE)

  message("Loading native 450K annotation")
  anno <- minfi::getAnnotation(IlluminaHumanMethylation450kanno.ilmn12.hg19)
  anno_cpg <- rownames(anno)
  all_cpg_raw <- unique(diff_df$probe_id)
  all_cpg <- intersect(all_cpg_raw, anno_cpg)

  mech_df$p_value <- as.numeric(mech_df$p_value)
  mech_df$fdr <- as.numeric(mech_df$fdr)
  mech_df$delta_beta <- as.numeric(mech_df$delta_beta)
  mech_df$abs_delta_beta <- as.numeric(mech_df$abs_delta_beta)
  mech_valid <- mech_df[mech_df$probe_id %in% all_cpg, ]

  sig_base <- !is.na(mech_valid$fdr) &
    mech_valid$fdr < FDR_THRESHOLD &
    !is.na(mech_valid$abs_delta_beta) &
    mech_valid$abs_delta_beta >= MIN_ABS_DELTA_BETA
  sig_hyper <- unique(mech_valid$probe_id[sig_base & mech_valid$direction == "hypermethylated"])
  sig_hypo <- unique(mech_valid$probe_id[sig_base & mech_valid$direction == "hypomethylated"])

  p_df <- mech_valid[!is.na(mech_valid$p_value) & is.finite(mech_valid$p_value) & mech_valid$p_value >= 0 & mech_valid$p_value <= 1, ]
  p_df <- p_df[!duplicated(p_df$probe_id), ]
  pvals <- pmax(p_df$p_value, .Machine$double.xmin)
  names(pvals) <- p_df$probe_id
  hyper_pvals <- ifelse(p_df$delta_beta > 0, pvals, 1)
  names(hyper_pvals) <- p_df$probe_id
  hypo_pvals <- ifelse(p_df$delta_beta < 0, pvals, 1)
  names(hypo_pvals) <- p_df$probe_id

  counts <- list(
    all_cpg_raw = length(all_cpg_raw),
    all_cpg_annotated = length(all_cpg),
    all_cpg_unannotated = length(setdiff(all_cpg_raw, all_cpg)),
    methylgsa_pvals = length(pvals),
    sig_hyper = length(sig_hyper),
    sig_hypo = length(sig_hypo)
  )

  symbol_sets <- read_gmt_symbols(gmt_path)
  mapped_longevity <- map_symbol_sets_to_entrez(symbol_sets)
  longevity_sets <- mapped_longevity$sets[lengths(mapped_longevity$sets) > 0]
  supervisor_symbol_sets <- read_gmt_symbols(supervisor_arrays_gmt_path)
  supervisor_entrez_sets <- read_entrez_sets_tsv(supervisor_arrays_entrez_path)
  tiny_supervisor_sets <- names(supervisor_entrez_sets)[lengths(supervisor_entrez_sets) < 5]
  reactome <- load_reactome_entrez_sets()
  reactome_sets <- reactome$sets

  write_tsv(mapped_longevity$mapping, file.path(gsea_dir, "longevity_symbol_to_entrez_mapping.tsv"))
  write_tsv(reactome$metadata, file.path(gsea_dir, "reactome_custom_collection_metadata.tsv"))

  background <- load_background_genes(out_dir)
  ora_query <- load_query_gene_sets_for_ora(mech_df)
  supervisor_ora_frames <- list()
  for (direction in c("hypermethylated", "hypomethylated")) {
    supervisor_ora_frames[[direction]] <- run_uncorrected_ora(
      ora_query$gene_sets[[direction]],
      background$genes,
      supervisor_symbol_sets,
      direction,
      "SupervisorArrays"
    )
    write_tsv(supervisor_ora_frames[[direction]], file.path(gsea_dir, paste0("supervisor_arrays_ora_", direction, ".tsv")))
  }
  supervisor_ora <- do.call(rbind, supervisor_ora_frames)
  supervisor_ora <- supervisor_ora[order(supervisor_ora$direction, supervisor_ora$adj_p, supervisor_ora$p, -supervisor_ora$overlap_n), , drop = FALSE]
  rownames(supervisor_ora) <- NULL
  write_tsv(supervisor_ora, file.path(gsea_dir, "supervisor_arrays_ora_all.tsv"))

  miss_results <- list()
  for (direction in c("hypermethylated", "hypomethylated")) {
    sig <- if (direction == "hypermethylated") sig_hyper else sig_hypo
    miss_results[[paste("GO", direction, sep = "_")]] <- run_gometh_collection(sig, all_cpg, "GO", direction, anno, gsea_dir)
    miss_results[[paste("KEGG", direction, sep = "_")]] <- run_gometh_collection(sig, all_cpg, "KEGG", direction, anno, gsea_dir)
    miss_results[[paste("longevity", direction, sep = "_")]] <- run_gsameth_collection(sig, all_cpg, longevity_sets, "longevity", direction, anno, gsea_dir)
    miss_results[[paste("supervisor_arrays", direction, sep = "_")]] <- run_gsameth_collection(sig, all_cpg, supervisor_entrez_sets, "supervisor_arrays", direction, anno, gsea_dir)
    miss_results[[paste("reactome", direction, sep = "_")]] <- run_gsameth_collection(sig, all_cpg, reactome_sets, "reactome", direction, anno, gsea_dir)
  }

  methyl_results <- list()
  for (direction in c("all", "hypermethylated", "hypomethylated")) {
    pv <- switch(direction, all = pvals, hypermethylated = hyper_pvals, hypomethylated = hypo_pvals)
    methyl_results[[paste("longevity", direction, sep = "_")]] <- run_methylrra_collection(pv, longevity_sets, "longevity", direction, gsea_dir, minsize = 5, maxsize = 1000)
    methyl_results[[paste("supervisor_arrays", direction, sep = "_")]] <- run_methylrra_collection(pv, supervisor_symbol_sets, "supervisor_arrays", direction, gsea_dir, minsize = 2, maxsize = 1000, gs_idtype = "SYMBOL")
    methyl_results[[paste("reactome", direction, sep = "_")]] <- run_methylrra_collection(pv, reactome_sets, "reactome", direction, gsea_dir, minsize = 10, maxsize = 1000)
    methyl_results[[paste("GO", direction, sep = "_")]] <- run_methylrra_builtin(pv, "GO", direction, gsea_dir, minsize = 10, maxsize = 1000)
    methyl_results[[paste("KEGG", direction, sep = "_")]] <- run_methylrra_builtin(pv, "KEGG", direction, gsea_dir, minsize = 10, maxsize = 1000)
  }

  miss_longevity <- do.call(rbind, list(
    miss_results[["longevity_hypermethylated"]],
    miss_results[["longevity_hypomethylated"]]
  ))
  methyl_longevity_dir <- do.call(rbind, list(
    methyl_results[["longevity_hypermethylated"]],
    methyl_results[["longevity_hypomethylated"]]
  ))
  methyl_longevity_all <- methyl_results[["longevity_all"]]
  comparison <- make_comparison(ora_df, miss_longevity, methyl_longevity_dir, methyl_longevity_all)
  write_tsv(comparison, file.path(gsea_dir, "gsea_vs_ora.tsv"))

  miss_supervisor <- do.call(rbind, list(
    miss_results[["supervisor_arrays_hypermethylated"]],
    miss_results[["supervisor_arrays_hypomethylated"]]
  ))
  methyl_supervisor_dir <- do.call(rbind, list(
    methyl_results[["supervisor_arrays_hypermethylated"]],
    methyl_results[["supervisor_arrays_hypomethylated"]]
  ))
  methyl_supervisor_all <- methyl_results[["supervisor_arrays_all"]]
  supervisor_comparison <- make_supervisor_arrays_comparison(supervisor_ora, miss_supervisor, methyl_supervisor_dir, methyl_supervisor_all)
  write_tsv(supervisor_comparison, file.path(gsea_dir, "supervisor_arrays_gsea_vs_ora.tsv"))
  supervisor_focus <- make_supervisor_focus_verdict(supervisor_comparison)
  write_tsv(supervisor_focus, file.path(gsea_dir, "supervisor_arrays_focus_verdict.tsv"))

  summary_lists <- list(
    ora_hyper = sig_terms(ora_df[ora_df$direction == "hypermethylated", ], "adj_p"),
    ora_hypo = sig_terms(ora_df[ora_df$direction == "hypomethylated", ], "adj_p"),
    miss_hyper = sig_terms(miss_longevity[miss_longevity$direction == "hypermethylated", ], "FDR"),
    miss_hypo = sig_terms(miss_longevity[miss_longevity$direction == "hypomethylated", ], "FDR"),
    methyl_all = sig_terms(methyl_longevity_all, "padj"),
    methyl_hyper = sig_terms(methyl_longevity_dir[methyl_longevity_dir$direction == "hypermethylated", ], "padj"),
    methyl_hypo = sig_terms(methyl_longevity_dir[methyl_longevity_dir$direction == "hypomethylated", ], "padj")
  )
  summary_lists_json <- lapply(summary_lists, function(x) I(as.character(unname(x))))

  supervisor_summary_lists <- list(
    ora_hyper = sig_terms(supervisor_ora[supervisor_ora$direction == "hypermethylated", ], "adj_p"),
    ora_hypo = sig_terms(supervisor_ora[supervisor_ora$direction == "hypomethylated", ], "adj_p"),
    miss_hyper = sig_terms(miss_supervisor[miss_supervisor$direction == "hypermethylated", ], "FDR"),
    miss_hypo = sig_terms(miss_supervisor[miss_supervisor$direction == "hypomethylated", ], "FDR"),
    methyl_all = sig_terms(methyl_supervisor_all, "padj"),
    methyl_hyper = sig_terms(methyl_supervisor_dir[methyl_supervisor_dir$direction == "hypermethylated", ], "padj"),
    methyl_hypo = sig_terms(methyl_supervisor_dir[methyl_supervisor_dir$direction == "hypomethylated", ], "padj")
  )
  supervisor_summary_lists_json <- lapply(supervisor_summary_lists, function(x) I(as.character(unname(x))))

  terc_rows <- comparison[
    grepl("TERC", paste(comparison$methylgsa_all_core, comparison$methylgsa_direction_core), fixed = TRUE),
  ]

  package_versions <- c(
    R = paste(R.version$major, R.version$minor, sep = "."),
    missMethyl = as.character(packageVersion("missMethyl")),
    methylGSA = as.character(packageVersion("methylGSA")),
    IlluminaHumanMethylation450kanno.ilmn12.hg19 = as.character(packageVersion("IlluminaHumanMethylation450kanno.ilmn12.hg19")),
    IlluminaHumanMethylation450kmanifest = as.character(packageVersion("IlluminaHumanMethylation450kmanifest")),
    org.Hs.eg.db = as.character(packageVersion("org.Hs.eg.db")),
    reactome.db = as.character(packageVersion("reactome.db"))
  )

  write_methods_readme(
    file.path(gsea_dir, "README.md"),
    counts,
    package_versions,
    supervisor_arrays_count = length(supervisor_symbol_sets),
    tiny_supervisor_sets = tiny_supervisor_sets
  )
  write_comparison_md(
    file.path(gsea_dir, "gsea_vs_ora.md"),
    comparison,
    summary_lists,
    terc_rows,
    supervisor_focus = supervisor_focus,
    supervisor_summary_lists = supervisor_summary_lists
  )

  summary <- list(
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    thresholds = list(fdr = FDR_THRESHOLD, abs_delta_beta = MIN_ABS_DELTA_BETA),
    counts = counts,
    package_versions = as.list(package_versions),
    curated_longevity_significant_sets = summary_lists_json,
    supervisor_arrays_significant_sets = supervisor_summary_lists_json,
    supervisor_arrays_focus_verdict = supervisor_focus,
    supervisor_arrays_counts = list(
      categories = length(supervisor_symbol_sets),
      categories_with_entrez = length(supervisor_entrez_sets),
      tiny_categories_lt_5_entrez = I(as.character(tiny_supervisor_sets)),
      ora_background_genes = length(background$genes),
      ora_retained_background_probes = background$retained_probe_count,
      ora_hyper_query_genes = length(ora_query$gene_sets$hypermethylated),
      ora_hypo_query_genes = length(ora_query$gene_sets$hypomethylated)
    ),
    significant_sets_by_output = summarize_result_tables(miss_results, methyl_results),
    verdict_inputs = list(
      stem_pluripotency_rows = comparison[grepl("pluripot|stem_cell", comparison$term), ],
      terc_core_rows = terc_rows
    )
  )
  writeLines(jsonlite::toJSON(summary, pretty = TRUE, auto_unbox = TRUE, na = "null"), file.path(gsea_dir, "gsea_summary.json"))
  capture.output(sessionInfo(), file = file.path(gsea_dir, "r_session_info.txt"))
}

main()
