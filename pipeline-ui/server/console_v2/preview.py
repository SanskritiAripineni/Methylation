"""Readiness preview: graded checks, the step plan, and measured estimates.

Grading contract, enforced here and relied on by the frontend:

    ok    - nothing to do
    warn  - shown, never swallowed, NEVER blocks Start
    fail  - blocks Start

Every check carries a `fix`: a command or an action, not a restatement of the
problem.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from engine import catalog

from . import runs as runs_mod
from . import study

try:
    import psutil
except Exception:                      # pragma: no cover - psutil is optional
    psutil = None

# Peak resident memory is roughly this multiple of the raw float64 matrix:
# the loaded frame, the QC-filtered copy, the boolean masks and the two
# per-group arrays the t-test builds all coexist.
MEM_FACTOR = 4.0
PROBE_SCAN_CAP = 400000


def _check(cid, label, state, detail, fix=""):
    return {"id": cid, "label": label, "state": state, "detail": detail, "fix": fix}


def _read_ids(path, cap=PROBE_SCAN_CAP):
    """First column of a (possibly gzipped) table, without loading it all."""
    ids, truncated = [], False
    with study._open_text(path) as fh:
        header = fh.readline()
        sep = "\t" if header.count("\t") >= header.count(",") else ","
        for i, line in enumerate(fh):
            if i >= cap:
                truncated = True
                break
            ids.append(line.split(sep, 1)[0].strip())
    return ids, truncated, header.rstrip("\n\r").split(sep)


def preview(study_id, mode="demo", thresholds=None, n_per_class=None, paths=None):
    cfg = study.load_config(study_id)
    thresholds = dict(thresholds or {})
    paths = {k: v for k, v in (paths or {}).items() if v}
    tcfg = cfg.get("thresholds", {})
    data = cfg.get("data", {})
    demo_cfg = cfg.get("demo", {})
    n_per_class = int(n_per_class or demo_cfg.get("n_per_class_default", 3))

    def thr(key, fallback=None):
        spec = tcfg.get(key) or {}
        return thresholds.get(key, spec.get("default", fallback))

    checks = []
    checks.append(_check("config", "Study config loads", "ok",
                         "studies/%s/config.yaml parsed; %d thresholds, %d steps."
                         % (study_id, len(tcfg), len(cfg.get("steps", []))), ""))

    matrix_path = study.resolve(paths.get("matrix") or data.get("matrix_path", ""))
    manifest_path = study.resolve(paths.get("manifest") or data.get("manifest_path", ""))
    annot_path = study.resolve(paths.get("annotation") or data.get("annotation_path", ""))
    if paths:
        checks.append(_check("source", "Input source", "warn",
                             "Running against user-supplied paths, not the bundled cohort:\n"
                             "%s\n%s" % (matrix_path, manifest_path),
                             "Confirm these are the files you mean. Every check below is run "
                             "against them, not against the study defaults."))

    m_info = study.sniff_table(matrix_path)
    a_info = study.sniff_table(annot_path)

    # --- inputs present ----------------------------------------------------
    missing = [str(p) for p in (matrix_path, manifest_path) if not Path(p).is_file()]
    if missing:
        checks.append(_check("inputs", "Input files present", "fail",
                             "Not found: %s" % ", ".join(missing),
                             "Point the Local path field at the real files, or restore the "
                             "bundled cohort with: python server/engine/make_sample_data.py"))
        return _bail(cfg, mode, checks, study_id, n_per_class)

    for name, info in (("matrix", m_info), ("annotation", a_info)):
        if info.get("lfs_pointer"):
            checks.append(_check("lfs_" + name, "%s is a real file" % name.title(), "fail",
                                 "%s is an unresolved Git-LFS pointer (%d bytes), not the data. "
                                 "It exists, so a naive existence check passes."
                                 % (info["path"], info.get("size_bytes", 0)),
                                 "git lfs install && git lfs pull"))

    manifest = pd.read_csv(manifest_path, sep="\t")
    probe_ids, probes_truncated, matrix_cols = _read_ids(matrix_path)
    matrix_samples = [c.strip() for c in matrix_cols[1:]]
    n_probes = len(probe_ids)

    checks.append(_check("data", "Data present", "ok",
                         "%s probes x %s samples in the matrix; %d rows in the sample table.%s"
                         % (f"{n_probes:,}", f"{len(matrix_samples):,}", len(manifest),
                            " (probe scan capped at %s)" % f"{PROBE_SCAN_CAP:,}"
                            if probes_truncated else ""), ""))

    id_col = data.get("id_column", "sample_barcode")
    group_col = data.get("group_column", "sample_class")

    # --- sample overlap (the local equivalent of sample sheet <-> IDAT) -----
    if id_col not in manifest.columns:
        checks.append(_check("sample_overlap", "Sample table matches the matrix", "fail",
                             "The sample table has no '%s' column. Columns: %s"
                             % (id_col, ", ".join(map(str, manifest.columns))),
                             "Rename the sample id column to '%s', or set data.id_column "
                             "in studies/%s/config.yaml." % (id_col, study_id)))
    else:
        sheet_ids = set(manifest[id_col].astype(str))
        mat_ids = set(matrix_samples)
        shared = sheet_ids & mat_ids
        only_sheet = sorted(sheet_ids - mat_ids)[:8]
        only_matrix = sorted(mat_ids - sheet_ids)[:8]
        if not shared:
            checks.append(_check("sample_overlap", "Sample table matches the matrix", "fail",
                                 "No id is shared. Sample table starts %s; matrix columns "
                                 "start %s." % (sorted(sheet_ids)[:3], sorted(mat_ids)[:3]),
                                 "These are two different cohorts, or the matrix is "
                                 "transposed. Check that the matrix has probes as rows."))
        elif only_sheet or only_matrix:
            checks.append(_check("sample_overlap", "Sample table matches the matrix", "warn",
                                 "%d of %d ids shared. In the sample table only: %s. In the "
                                 "matrix only: %s." % (len(shared), len(sheet_ids | mat_ids),
                                                       only_sheet or "none", only_matrix or "none"),
                                 "The run keeps the intersection and silently drops the rest. "
                                 "Remove the unmatched rows/columns if that is not what you want."))
        else:
            checks.append(_check("sample_overlap", "Sample table matches the matrix", "ok",
                                 "All %d ids match." % len(shared), ""))

    # --- probe annotation coverage ----------------------------------------
    # This is this pipeline's version of an array/manifest mismatch: an
    # annotation table that does not cover the matrix rows silently strips
    # genes, regions and the direction-of-effect call.
    if not Path(annot_path).is_file():
        checks.append(_check("annotation", "Probe annotation covers the matrix", "warn",
                             "No annotation table at %s." % annot_path,
                             "Probes are still tested but lose gene, region, direction and "
                             "enrichment. Supply a probe_id -> gene/chrom/region table."))
    else:
        ann = pd.read_csv(annot_path, sep="\t", usecols=lambda c: c in ("probe_id", "chrom", "gene"))
        ann_ids = set(ann["probe_id"].astype(str)) if "probe_id" in ann.columns else set()
        covered = len(set(probe_ids) & ann_ids)
        frac = covered / max(1, n_probes)
        if frac < 0.01:
            checks.append(_check("annotation", "Probe annotation covers the matrix", "fail",
                                 "The annotation covers %.1f%% of the matrix probes (%d of %s). "
                                 "This is the wrong annotation for this matrix - probes would be "
                                 "silently stripped of gene and region."
                                 % (frac * 100, covered, f"{n_probes:,}"),
                                 "Use the annotation built for this array/matrix. The bundled "
                                 "one is data/sample/probe_annotation.tsv."))
        elif frac < 0.95:
            checks.append(_check("annotation", "Probe annotation covers the matrix", "warn",
                                 "%.1f%% of matrix probes are annotated (%s of %s). The "
                                 "remainder are tested but carry no gene, region or "
                                 "direction-of-effect call."
                                 % (frac * 100, f"{covered:,}", f"{n_probes:,}"),
                                 "Acceptable for a mixed matrix. Extend the annotation if you "
                                 "need gene-level or pathway output for every probe."))
        else:
            checks.append(_check("annotation", "Probe annotation covers the matrix", "ok",
                                 "%.1f%% of matrix probes annotated." % (frac * 100), ""))

    # --- group column ------------------------------------------------------
    fail_below = int((tcfg.get("min_samples_per_class") or {}).get("fail_below", 3))
    warn_below = int((tcfg.get("min_samples_per_class") or {}).get("warn_below", 5))
    want = int(thr("min_samples_per_class", 3))
    if group_col not in manifest.columns:
        checks.append(_check("groups", "Group column and class sizes", "fail",
                             "No '%s' column in the sample table." % group_col,
                             "Add a group column, or set data.group_column in the study config."))
        counts = {}
    else:
        counts = manifest[group_col].astype(str).value_counts().to_dict()
        effective = {k: (min(v, n_per_class) if mode == "demo" else v) for k, v in counts.items()}
        detail = ", ".join("%s n=%d" % (k, v) for k, v in sorted(effective.items()))
        if mode == "demo":
            detail += " (after the demo subset; the cohort holds %s)" % ", ".join(
                "%s=%d" % kv for kv in sorted(counts.items()))
        if len(counts) < 2:
            checks.append(_check("groups", "Group column and class sizes", "fail",
                                 "Only one class present (%s). A differential test needs two."
                                 % detail,
                                 "Add the comparison group to the sample table, or pick a "
                                 "different group column."))
        elif any(v < fail_below for v in effective.values()):
            thin = [k for k, v in effective.items() if v < fail_below]
            checks.append(_check("groups", "Group column and class sizes", "fail",
                                 "%s. Class(es) %s are below the %d-sample floor - the model "
                                 "cannot fit." % (detail, ", ".join(thin), fail_below),
                                 "Lower min_samples_per_class (it will still not fit below 2), "
                                 "or add samples to %s." % ", ".join(thin)))
        elif any(v < warn_below for v in effective.values()) or want < warn_below:
            thin = [k for k, v in effective.items() if v < warn_below]
            checks.append(_check("groups", "Group column and class sizes", "warn",
                                 "%s. %s below %d per class: the model fits, but there is "
                                 "essentially no power to detect a %.2f effect, so 'no "
                                 "significant probes' would not be informative."
                                 % (detail, ", ".join(thin) or "Threshold set", warn_below,
                                    float(thr("delta_beta_min", 0.2))),
                                 "Proceed if this is a rehearsal. For a real result, raise the "
                                 "per-class count above %d." % warn_below))
        else:
            checks.append(_check("groups", "Group column and class sizes", "ok", detail, ""))

    # --- batch confound ----------------------------------------------------
    batch_present = [c for c in data.get("batch_columns", []) if c in manifest.columns]
    if not batch_present:
        checks.append(_check("batch", "Batch / slide confounding", "warn",
                             "No batch column (looked for %s), so batch confounding cannot be "
                             "assessed. This is the most common way a methylation study "
                             "produces a confident wrong answer, and here it is unassessable "
                             "rather than ruled out."
                             % ", ".join(data.get("batch_columns", [])),
                             "Add the slide/plate/Sentrix column to the sample table and list "
                             "it under data.batch_columns in the study config."))
    else:
        col = batch_present[0]
        tab = pd.crosstab(manifest[col], manifest[group_col])
        single = [str(i) for i, row in tab.iterrows() if (row > 0).sum() < 2]
        rendered = tab.to_string()
        if single:
            checks.append(_check("batch", "Batch / slide confounding", "fail",
                                 "%s %s contain only one class, so batch and group cannot be "
                                 "separated:\n%s" % (col, ", ".join(single), rendered),
                                 "Rebalance the batches, or accept that any hit may be a batch "
                                 "effect and drop this run to research-only deliberately."))
        else:
            checks.append(_check("batch", "Batch / slide confounding", "ok",
                                 "Every %s carries both classes:\n%s" % (col, rendered), ""))

    # covariate confound, shown even when a batch column is absent
    for cov in data.get("covariate_columns", []):
        if cov in manifest.columns and manifest[cov].nunique() <= 8 and group_col in manifest.columns:
            tab = pd.crosstab(manifest[cov], manifest[group_col])
            single = [str(i) for i, row in tab.iterrows() if (row > 0).sum() < 2]
            if single:
                checks.append(_check("confound_" + cov, "Covariate '%s' vs group" % cov, "warn",
                                     "%s occur in only one group, so '%s' is partly collinear "
                                     "with the contrast:\n%s" % (", ".join(single), cov,
                                                                 tab.to_string()),
                                     "The differential block does not adjust for covariates. "
                                     "Read any hit in this stratum as group-or-%s, not group." % cov))
            break

    # --- sex check ---------------------------------------------------------
    sex_col = data.get("sex_column")
    drop_sex = bool(thr("exclude_sex_chromosomes", True))
    if sex_col not in (manifest.columns if hasattr(manifest, "columns") else []):
        checks.append(_check("sex", "Sex check (predicted vs recorded)", "warn",
                             "No '%s' column recorded." % sex_col,
                             "Add it if you have it; without it a sample mix-up cannot be "
                             "caught this way."))
    else:
        n_sex = manifest[sex_col].nunique()
        if drop_sex:
            checks.append(_check("sex", "Sex check (predicted vs recorded)", "warn",
                                 "Recorded sex is present (%d level%s: %s) but chrX/chrY probes "
                                 "are dropped by the QC filter, so predicted sex cannot be "
                                 "computed and the two cannot be compared."
                                 % (n_sex, "" if n_sex == 1 else "s",
                                    ", ".join(map(str, manifest[sex_col].unique()[:4]))),
                                 "Turn off 'Drop chrX / chrY probes' for one QC run if you want "
                                 "this check to mean something."))
        else:
            checks.append(_check("sex", "Sex check (predicted vs recorded)", "ok",
                                 "chrX/chrY retained; recorded sex available for comparison.", ""))

    # --- simulated cohort --------------------------------------------------
    if "SIMULATED" in (data.get("provenance") or "").upper():
        checks.append(_check("simulated", "Cohort is measured data", "warn",
                             "Per-sample values in this cohort are SIMULATED. Per-probe "
                             "tumour/normal means for 500 reference probes are real; every "
                             "individual sample value was drawn to match them. The algorithms "
                             "are real, the numbers are a demonstration.",
                             "Point Local path at a real beta matrix. Any run on this cohort "
                             "is capped at research-only regardless of what else passes."))

    # --- resources ---------------------------------------------------------
    n_eff_samples = (n_per_class * max(2, len(counts))) if mode == "demo" else len(matrix_samples)
    raw_bytes = n_probes * max(1, n_eff_samples) * 8
    peak = raw_bytes * MEM_FACTOR
    avail = psutil.virtual_memory().available if psutil else None
    disk_free = shutil.disk_usage(str(study.ROOT)).free
    def _gb(n):
        return "%.2f GB" % (n / 1e9) if n >= 1e8 else "%.0f MB" % (n / 1e6)

    mem_txt = ("%s peak estimated (%s probes x %d samples x 8 bytes x %.0f for the "
               "concurrent copies)" % (_gb(peak), f"{n_probes:,}", n_eff_samples, MEM_FACTOR))
    if avail and peak > avail * 0.8:
        checks.append(_check("memory", "Memory headroom", "fail",
                             "%s, against %s available." % (mem_txt, _gb(avail)),
                             "Run the demo tier instead, or free memory. A beta matrix is far "
                             "cheaper than an RGChannelSet, but it still holds several full "
                             "copies at once."))
    else:
        checks.append(_check("memory", "Memory headroom", "ok",
                             "%s, against %s available." % (
                                 mem_txt, _gb(avail) if avail else "unknown"),
                             ""))
    if disk_free < 2e9:
        checks.append(_check("disk", "Disk headroom", "warn",
                             "%.2f GB free where runs/ lives." % (disk_free / 1e9),
                             "Old runs are pruned to the newest 25. Free space or move runs/."))
    else:
        checks.append(_check("disk", "Disk headroom", "ok",
                             "%.1f GB free." % (disk_free / 1e9), ""))

    # --- queue -------------------------------------------------------------
    active = runs_mod.active_run_id()
    if active:
        checks.append(_check("queue", "Queue", "warn",
                             "One run is executing (%s). This one starts when it finishes - "
                             "runs are serialised so they cannot fight over memory." % active,
                             "Wait, or cancel %s from the run list." % active))
    else:
        checks.append(_check("queue", "Queue", "ok", "Nothing else is running.", ""))

    # --- step wiring -------------------------------------------------------
    checks.extend(_wiring_checks(cfg))

    # --- tier-specific -----------------------------------------------------
    if mode == "demo":
        eligible = _eligible_counts(matrix_path, manifest, id_col, group_col,
                                    float(thr("sample_call_rate_min", 0.75)))
        short = {k: v for k, v in eligible.items() if v < n_per_class}
        if short:
            checks.append(_check("demo_subset", "Demo subset is possible", "fail",
                                 "%s have fewer than %d samples above the %.2f call-rate floor: %s. "
                                 "Both classes must survive the subset or every downstream model "
                                 "fails to fit." % (", ".join(short), n_per_class,
                                                    float(thr("sample_call_rate_min", 0.75)),
                                                    ", ".join("%s=%d" % kv for kv in short.items())),
                                 "Lower the demo size to %d, or lower the call-rate floor."
                                 % max(2, min(eligible.values()) if eligible else 2)))
        else:
            checks.append(_check("demo_subset", "Demo subset is possible", "ok",
                                 "%s eligible above the call-rate floor; taking %d per class. "
                                 "Samples are subset, probes are not."
                                 % (", ".join("%s=%d" % kv for kv in sorted(eligible.items())),
                                    n_per_class), ""))
        ef = int(catalog.merged_params("effect_filter", {}).get("min_group_n", 0) or 0)
        if ef > n_per_class:
            checks.append(_check("demo_adjust", "Demo parameter adjustments", "warn",
                                 "effect_filter.min_group_n will be lowered from %d to %d for "
                                 "this rehearsal. It is a cohort-size gate, not an effect "
                                 "threshold: left at %d it drops every probe on a %d-per-class "
                                 "subset and the run finishes empty but green. |Δβ|, FDR and "
                                 "every QC threshold are unchanged." % (ef, n_per_class, ef, n_per_class),
                                 "Nothing to do. The adjustment is recorded in the run record "
                                 "and shown on the verdict."))
        if n_per_class <= fail_below:
            checks.append(_check("demo_slack", "Demo has QC slack", "warn",
                                 "%d per class with a %d-sample floor leaves no slack: if the QC "
                                 "filter drops one sample the run fails."
                                 % (n_per_class, fail_below),
                                 "Raise the demo size to %d for a rehearsal that survives one "
                                 "QC drop." % (fail_below + 2)))

    if mode == "full":
        demo_id = runs_mod.successful_demo(study_id)
        if demo_id:
            checks.append(_check("demo_gate", "Validated by a demo run", "ok",
                                 "Demo %s of this study completed. The full run will record "
                                 "validated_by: %s." % (demo_id, demo_id), ""))
        else:
            checks.append(_check("demo_gate", "Validated by a demo run", "fail",
                                 "No successful demo run of this study exists yet.",
                                 "Run the Demo tier first. It exercises every step with the "
                                 "same thresholds in minutes."))

    return _assemble(cfg, mode, checks, study_id, n_per_class)


def _eligible_counts(matrix_path, manifest, id_col, group_col, floor):
    betas = pd.read_csv(matrix_path, sep="\t", index_col=0)
    call_rate = 1.0 - betas.isna().mean(axis=0)
    good = set(call_rate[call_rate >= floor].index)
    if id_col not in manifest.columns or group_col not in manifest.columns:
        return {}
    sub = manifest[manifest[id_col].astype(str).isin(good)]
    return sub[group_col].astype(str).value_counts().to_dict()


def _wiring_checks(cfg):
    """Consumed-but-unproduced intermediates, and unverifiable inputs.

    The worst bug class on the previous project: a step reads something no
    earlier step wrote, silently falls back to a stale copy on disk, and the
    run succeeds with someone else's numbers.
    """
    out = []
    produced, consumed_early = set(), []
    for step in cfg.get("steps", []):
        spec = catalog.NODES_BY_TYPE.get(step["type"])
        if not spec:
            continue
        for want in spec.get("inputs", []):
            if want not in produced:
                consumed_early.append((step["name"], want))
        produced.update(spec.get("outputs", []))

    if consumed_early:
        out.append(_check("wiring", "Every step's input is produced upstream", "warn",
                          "; ".join("'%s' reads '%s' which no earlier step produces"
                                    % (name, key) for name, key in consumed_early),
                          "Reorder or reconnect those steps. Left as is, the step falls back "
                          "to whatever is already in memory or on disk."))
    else:
        out.append(_check("wiring", "Every step's input is produced upstream", "ok",
                          "%d steps; every declared input is produced by an earlier step."
                          % len(cfg.get("steps", [])), ""))

    # Real, and specific to this engine: the custom-dataset branch of
    # load_data() reads probe_annotation.tsv from a path fixed in the script.
    out.append(_check("unverifiable", "Inputs that cannot be verified", "warn",
                      "load_data() reads the probe annotation from a path hard-coded inside "
                      "the script (data/sample/probe_annotation.tsv) whenever a custom matrix "
                      "is supplied. No step declares it as an input, so what it actually read "
                      "cannot be checked from the run record - only that it ran.",
                      "Treat annotation-derived output (gene names, promoter context, "
                      "direction of effect, enrichment) as unverified for custom matrices. "
                      "To fix properly, add an annotation_path parameter to the load block."))
    return out


def _step_plan(cfg, mode, est):
    plan = []
    for step in cfg.get("steps", []):
        runs_here = bool(step.get("runs", True))
        reason = step.get("skip_reason")
        if mode == "plan":
            runs_here, reason = False, "Plan tier resolves paths and parameters; it executes nothing."
        plan.append({
            "node": step["node"], "name": step["name"], "type": step["type"],
            "runs": runs_here, "reason": reason, "caveat": step.get("caveat"),
            "estimate_seconds": (est.get("per_step") or {}).get(step["name"]),
        })
    return plan


def _assemble(cfg, mode, checks, study_id, n_per_class):
    est = runs_mod.estimates(study_id, mode)
    blocking = [c for c in checks if c["state"] == "fail"]
    return {
        "study": study_id,
        "mode": mode,
        "n_per_class": n_per_class if mode == "demo" else None,
        "checks": checks,
        "can_start": not blocking,                 # ONLY fail blocks
        "blocking": [c["id"] for c in blocking],
        "warn_count": sum(1 for c in checks if c["state"] == "warn"),
        "steps": _step_plan(cfg, mode, est),
        "estimates": est,
        "reproducibility": study.reproducibility(),
        "thresholds": cfg.get("thresholds", {}),
        "not_applicable": cfg.get("not_applicable", {}),
        "standing_caveat": (cfg.get("verdict", {}).get("standing_caveat") or "").strip(),
    }


def _bail(cfg, mode, checks, study_id, n_per_class):
    return _assemble(cfg, mode, checks, study_id, n_per_class)


# ---------------------------------------------------------------------------
# "what does this threshold do to the real data"
# ---------------------------------------------------------------------------

def threshold_effect(study_id, key, value, run_id=None):
    """Measure a candidate threshold against real numbers, or refuse.

    If the selected run already applied a stricter cutoff, the looser value
    cannot be previewed: those probes were never scored. Say that instead of
    interpolating.
    """
    cfg = study.load_config(study_id)
    spec = (cfg.get("thresholds") or {}).get(key)
    if not spec:
        return {"available": False,
                "reason": "'%s' is not a threshold of this study." % key}

    run = runs_mod.get_run(run_id) if run_id else None
    stats = run.ctx.get("stats") if run is not None else None

    if key in ("delta_beta_min", "fdr_max"):
        if stats is None or not len(stats):
            return {"available": False,
                    "reason": "No completed run is selected, so there are no scored probes to "
                              "count against. Run the demo tier and this will fill in."}
        applied = float(run.thresholds.get(key, spec.get("default")))
        value = float(value)
        stricter_already = (value < applied) if spec.get("direction") == "higher_is_stricter" \
            else (value > applied)
        if stricter_already:
            return {"available": False,
                    "reason": "Run %s was filtered at %s = %s. Probes outside that cutoff were "
                              "dropped before this table was written, so a looser value cannot "
                              "be previewed - they were never scored."
                              % (run.id, key, applied)}
        col = "abs_delta_beta" if key == "delta_beta_min" else "fdr"
        if col not in stats.columns:
            return {"available": False,
                    "reason": "Run %s did not write a '%s' column." % (run.id, col)}
        if key == "delta_beta_min":
            n = int((stats[col] >= value).sum())
        else:
            n = int((stats[col] <= value).sum())
        return {"available": True, "value": value, "n": n, "of": int(len(stats)),
                "text": "%s of %s probes in run %s pass %s = %s."
                        % (f"{n:,}", f"{len(stats):,}", run.id, key, value)}

    if key == "sample_call_rate_min":
        data = cfg.get("data", {})
        betas = pd.read_csv(study.resolve(data["matrix_path"]), sep="\t", index_col=0)
        rate = 1.0 - betas.isna().mean(axis=0)
        n = int((rate >= float(value)).sum())
        return {"available": True, "value": value, "n": n, "of": int(len(rate)),
                "text": "%d of %d samples in the cohort have a call rate >= %.2f."
                        % (n, len(rate), float(value))}

    if key == "min_samples_per_class":
        data = cfg.get("data", {})
        manifest = pd.read_csv(study.resolve(data["manifest_path"]), sep="\t")
        counts = manifest[data.get("group_column", "sample_class")].value_counts().to_dict()
        ok = [k for k, v in counts.items() if v >= int(value)]
        return {"available": True, "value": value,
                "text": "%d of %d classes clear %s (%s)."
                        % (len(ok), len(counts), value,
                           ", ".join("%s=%d" % kv for kv in sorted(counts.items())))}

    return {"available": False,
            "reason": "No measurement is defined for '%s'; it is applied at run time." % key}
