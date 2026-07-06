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
                                     minsize = 5, maxsize = 1000) {
  message("Running methylGSA methylRRA GSEA: ", collection_name, " / ", direction)
  set.seed(20260706)
  res <- methylGSA::methylRRA(
    cpg.pval = pvals,
    array.type = "450K",
    group = "all",
    method = "GSEA",
    GS.list = sets,
    GS.idtype = "ENTREZID",
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

summarize_result_tables <- function(miss_results, methyl_results) {
  out <- list()
  for (nm in names(miss_results)) {
    terms <- sig_terms(miss_results[[nm]], "FDR")
    parts <- strsplit(nm, "_", fixed = TRUE)[[1]]
    collection <- tolower(parts[[1]])
    direction <- paste(parts[-1], collapse = "_")
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
    parts <- strsplit(nm, "_", fixed = TRUE)[[1]]
    collection <- tolower(parts[[1]])
    direction <- paste(parts[-1], collapse = "_")
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

write_methods_readme <- function(path, counts, package_versions) {
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
    "The script discovers `project_b/brca_local_inputs.json`, reads `outputs/brca_methylation/differential_methylation.tsv`, `outputs/brca_methylation/differential_methylation_mechanics.tsv`, and the Phase 3 curated `pathway_enrichment_longevity/longevity_gene_sets.gmt`, then writes only to `outputs/brca_methylation/gsea/`.",
    "",
    "## Methods",
    "",
    paste0("- Significant CpGs for missMethyl used the same Phase 3/ORA gate: FDR < ", FDR_THRESHOLD, " and |delta_beta| >= ", MIN_ABS_DELTA_BETA, ", split into hypermethylated and hypomethylated directions."),
    "- The missMethyl universe (`all.cpg`) starts from every probe ID in `differential_methylation.tsv` and is restricted to CpGs present in the native Illumina 450K hg19 annotation because missMethyl models probe-number bias through that annotation.",
    "- missMethyl `gometh()` was run for built-in GO and KEGG collections. `gsameth()` was run for custom Reactome and curated longevity collections, with custom sets represented as Entrez Gene IDs.",
    "- methylGSA `methylRRA(method = \"GSEA\")` was run on per-CpG p-values for all valid tested CpGs. The `all` run is the strict threshold-free rank test; hyper/hypo companion runs keep the same CpG universe but set opposite-direction CpGs to p = 1 to provide direction-specific checks without a significance threshold.",
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
    "",
    "## Package versions",
    "",
    paste0("- ", names(package_versions), ": ", unname(package_versions))
  )
  writeLines(lines, path)
}

write_comparison_md <- function(path, comparison, summary_lists, terc_rows) {
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
    "Full per-set comparison: `gsea_vs_ora.tsv`."
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
  reactome <- load_reactome_entrez_sets()
  reactome_sets <- reactome$sets

  write_tsv(mapped_longevity$mapping, file.path(gsea_dir, "longevity_symbol_to_entrez_mapping.tsv"))
  write_tsv(reactome$metadata, file.path(gsea_dir, "reactome_custom_collection_metadata.tsv"))

  miss_results <- list()
  for (direction in c("hypermethylated", "hypomethylated")) {
    sig <- if (direction == "hypermethylated") sig_hyper else sig_hypo
    miss_results[[paste("GO", direction, sep = "_")]] <- run_gometh_collection(sig, all_cpg, "GO", direction, anno, gsea_dir)
    miss_results[[paste("KEGG", direction, sep = "_")]] <- run_gometh_collection(sig, all_cpg, "KEGG", direction, anno, gsea_dir)
    miss_results[[paste("longevity", direction, sep = "_")]] <- run_gsameth_collection(sig, all_cpg, longevity_sets, "longevity", direction, anno, gsea_dir)
    miss_results[[paste("reactome", direction, sep = "_")]] <- run_gsameth_collection(sig, all_cpg, reactome_sets, "reactome", direction, anno, gsea_dir)
  }

  methyl_results <- list()
  for (direction in c("all", "hypermethylated", "hypomethylated")) {
    pv <- switch(direction, all = pvals, hypermethylated = hyper_pvals, hypomethylated = hypo_pvals)
    methyl_results[[paste("longevity", direction, sep = "_")]] <- run_methylrra_collection(pv, longevity_sets, "longevity", direction, gsea_dir, minsize = 5, maxsize = 1000)
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

  write_methods_readme(file.path(gsea_dir, "README.md"), counts, package_versions)
  write_comparison_md(file.path(gsea_dir, "gsea_vs_ora.md"), comparison, summary_lists, terc_rows)

  summary <- list(
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    thresholds = list(fdr = FDR_THRESHOLD, abs_delta_beta = MIN_ABS_DELTA_BETA),
    counts = counts,
    package_versions = as.list(package_versions),
    curated_longevity_significant_sets = summary_lists_json,
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
