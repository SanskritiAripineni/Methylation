"""Implementations of every pipeline block.

Each block is `fn(run, params) -> None` and mutates `run.ctx`. The algorithms mirror
project_b/scripts/run_brca_methylation_pipeline.py and its phase scripts: Welch
t-test per probe, Benjamini-Hochberg FDR, effect-size gate, promoter rule for the
direction call, stratified (optionally nested) CV for the classifier, and a
hypergeometric over-representation test against real GMT libraries.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "data" / "sample"
GENE_SETS = SAMPLE_DIR / "gene_sets"

HYPER = "hypermethylated"
HYPO = "hypomethylated"


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def benjamini_hochberg(p_values):
    """Identical procedure to the published pipeline's implementation."""
    p = np.asarray(p_values, dtype=float)
    out = np.full(p.shape, np.nan)
    ok = np.isfinite(p)
    if not ok.any():
        return out
    vals = p[ok]
    n = vals.size
    order = np.argsort(vals)
    ranked = vals[order]
    adj = ranked * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0.0, 1.0)
    restored = np.empty(n)
    restored[order] = adj
    out[ok] = restored
    return out


def resolve_path(value):
    p = Path(str(value)).expanduser()
    if not p.is_absolute():
        p = ROOT / p
    return p


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

def load_data(run, p):
    dataset = p.get("dataset", "sample_brca")
    if dataset == "custom":
        mpath, spath = p.get("matrix_path", "").strip(), p.get("manifest_path", "").strip()
        if not mpath or not spath:
            raise ValueError("Custom dataset needs both a matrix path and a manifest path.")
        run.log("Reading custom matrix: %s" % mpath)
        betas = pd.read_csv(resolve_path(mpath), sep="\t", index_col=0)
        manifest = pd.read_csv(resolve_path(spath), sep="\t")
        annotation = None
        ann_path = SAMPLE_DIR / "probe_annotation.tsv"
        if ann_path.exists():
            annotation = pd.read_csv(ann_path, sep="\t")
        run.ctx["data_provenance"] = "custom files supplied by the user"
    else:
        run.log("Reading bundled sample cohort (per-sample values are simulated - see PROVENANCE.md)")
        betas = pd.read_csv(SAMPLE_DIR / "sample_betas.tsv.gz", sep="\t", index_col=0)
        manifest = pd.read_csv(SAMPLE_DIR / "sample_manifest.tsv", sep="\t")
        annotation = pd.read_csv(SAMPLE_DIR / "probe_annotation.tsv", sep="\t")
        run.ctx["data_provenance"] = "bundled sample cohort (simulated per-sample values)"

    cap = int(p.get("max_probes", 0) or 0)
    if cap and cap < len(betas):
        betas = betas.iloc[:cap]
        run.log("Probe cap applied: kept first %s probes" % f"{cap:,}")

    manifest = manifest.set_index("sample_barcode", drop=False)
    shared = [s for s in betas.columns if s in manifest.index]
    if not shared:
        raise ValueError("No sample ids are shared between the matrix columns and the manifest.")
    betas = betas[shared]
    manifest = manifest.loc[shared]

    run.ctx["betas"] = betas
    run.ctx["manifest"] = manifest
    run.ctx["annotation"] = annotation
    run.ctx["n_probes_loaded"] = int(len(betas))

    counts = manifest["sample_class"].value_counts().to_dict()
    run.log("Loaded %s probes x %s samples (%s)" % (
        f"{len(betas):,}", f"{len(shared):,}",
        ", ".join("%s %s" % (v, k) for k, v in sorted(counts.items()))))
    run.stat("Probes loaded", len(betas))
    run.stat("Samples loaded", len(shared))


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def qc_filter(run, p):
    betas = run.ctx["betas"]
    manifest = run.ctx["manifest"]
    ann = run.ctx.get("annotation")
    n0_probes, n0_samples = betas.shape

    sample_missing = betas.isna().mean(axis=0)
    keep_samples = sample_missing[sample_missing <= float(p["max_sample_missingness"])].index
    dropped_samples = n0_samples - len(keep_samples)
    betas = betas[keep_samples]
    manifest = manifest.loc[keep_samples]

    probe_missing = betas.isna().mean(axis=1)
    keep_probes = probe_missing[probe_missing <= float(p["max_probe_missingness"])].index
    dropped_probes = n0_probes - len(keep_probes)
    betas = betas.loc[keep_probes]

    dropped_sex = 0
    if p.get("drop_sex_chromosomes") and ann is not None:
        sex_probes = set(ann.loc[ann["chrom"].isin(["chrX", "chrY"]), "probe_id"])
        before = len(betas)
        betas = betas.loc[[i for i in betas.index if i not in sex_probes]]
        dropped_sex = before - len(betas)

    counts = manifest["sample_class"].value_counts()
    min_n = int(p.get("min_group_n", 3))
    for group, n in counts.items():
        if n < min_n:
            raise ValueError("Group '%s' has only %d samples after QC (minimum %d)." % (group, n, min_n))

    run.ctx["betas"] = betas
    run.ctx["manifest"] = manifest
    run.ctx["qc"] = {
        "samples_dropped_missingness": int(dropped_samples),
        "probes_dropped_missingness": int(dropped_probes),
        "probes_dropped_sex_chromosome": int(dropped_sex),
        "samples_retained": int(betas.shape[1]),
        "probes_retained": int(betas.shape[0]),
    }
    run.artifact_frame("qc_sample_missingness.tsv",
                       sample_missing.rename("missing_fraction").reset_index()
                       .rename(columns={"index": "sample_barcode"}))
    run.log("QC: dropped %d samples, %d probes on missingness, %d sex-chromosome probes"
            % (dropped_samples, dropped_probes, dropped_sex))
    run.log("QC: %s probes x %s samples retained" % (f"{betas.shape[0]:,}", f"{betas.shape[1]:,}"))
    run.stat("Probes after QC", betas.shape[0])
    run.stat("Samples after QC", betas.shape[1])


def probe_filter(run, p):
    if not p.get("enabled"):
        run.log("Probe pre-filter disabled - every probe goes to the test (as published).")
        return
    betas = run.ctx["betas"]
    before = len(betas)
    variance = betas.var(axis=1, skipna=True)
    betas = betas.loc[variance[variance >= float(p["min_variance"])].index]
    top_n = int(p.get("top_n_variable", 0) or 0)
    if top_n and top_n < len(betas):
        keep = variance.loc[betas.index].sort_values(ascending=False).head(top_n).index
        betas = betas.loc[keep]
    run.ctx["betas"] = betas
    run.log("Pre-filter: %s -> %s probes (unsupervised, no labels used)"
            % (f"{before:,}", f"{len(betas):,}"))
    run.stat("Probes after pre-filter", len(betas))


def effect_filter(run, p):
    st = run.ctx["stats"]
    before = len(st)
    keep = st["abs_delta_beta"] >= float(p["min_abs_delta_beta"])
    direction = p.get("direction", "both")
    if direction == "hyper":
        keep &= st["direction"] == HYPER
    elif direction == "hypo":
        keep &= st["direction"] == HYPO
    min_n = int(p.get("min_group_n", 0) or 0)
    if min_n:
        largest = int(min(st["group_a_n"].max(), st["group_b_n"].max())) if len(st) else 0
        if largest < min_n:
            run.warn("'Min samples per group' is %d but the smaller group only has %d samples, "
                     "so every probe will be dropped. Lower it to %d or less."
                     % (min_n, largest, largest))
        keep &= (st["group_a_n"] >= min_n) & (st["group_b_n"] >= min_n)
    if "significant" in st.columns:
        keep &= st["significant"]
    st = st[keep].copy()
    run.ctx["stats"] = st
    run.log("Effect filter: %s -> %s probes (|delta-beta| >= %.2f, direction=%s, n>=%d)"
            % (f"{before:,}", f"{len(st):,}", float(p["min_abs_delta_beta"]), direction, min_n))
    run.stat("Probes passing effect filter", len(st))
    if st.empty:
        run.warn("No probe survived the effect filter. Loosen |delta-beta| or the FDR threshold.")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def _split_groups(run, p):
    manifest = run.ctx["manifest"]
    comparison = p.get("comparison", "tumor_vs_normal")
    subtype = p.get("subtype_label", "Basal")
    cls = manifest["sample_class"].astype(str)
    sub = manifest["subtype"].astype(str) if "subtype" in manifest.columns else pd.Series("", index=manifest.index)

    if comparison == "tumor_vs_normal":
        a = manifest.index[cls == "tumor"]
        b = manifest.index[cls == "normal"]
        return list(a), list(b), "tumor", "normal", "tumor_vs_normal"
    if comparison == "subtype_vs_normal":
        a = manifest.index[(cls == "tumor") & (sub == subtype)]
        b = manifest.index[cls == "normal"]
        return list(a), list(b), subtype, "normal", "%s_vs_normal" % subtype.lower()
    a = manifest.index[(cls == "tumor") & (sub == subtype)]
    b = manifest.index[(cls == "tumor") & (sub != subtype)]
    return list(a), list(b), subtype, "non_%s" % subtype, "%s_vs_rest" % subtype.lower()


def _vector_ttest(A, B, n_a, n_b, m_a, m_b, equal_var=False):
    """Welch (or Student) t-test across every row at once, NaN-aware."""
    with np.errstate(invalid="ignore", divide="ignore"):
        var_a = np.nanvar(A, axis=1, ddof=1)
        var_b = np.nanvar(B, axis=1, ddof=1)
        n_a = n_a.astype(float)
        n_b = n_b.astype(float)
        if equal_var:
            df = n_a + n_b - 2.0
            pooled = ((n_a - 1) * var_a + (n_b - 1) * var_b) / df
            se = np.sqrt(pooled * (1.0 / n_a + 1.0 / n_b))
        else:
            va, vb = var_a / n_a, var_b / n_b
            se = np.sqrt(va + vb)
            df = (va + vb) ** 2 / (va ** 2 / (n_a - 1) + vb ** 2 / (n_b - 1))
        t = (m_a - m_b) / se
        pv = 2.0 * stats.t.sf(np.abs(t), df)
    # A probe with zero variance in both groups carries no information.
    pv = np.where(np.isfinite(pv), pv, np.nan)
    return pv


def differential(run, p):
    betas = run.ctx["betas"]
    a_ids, b_ids, a_name, b_name, run_name = _split_groups(run, p)
    min_n = int(p.get("min_group_n", 3))
    if len(a_ids) < min_n or len(b_ids) < min_n:
        raise ValueError("Comparison '%s' needs >=%d samples per group; got %d vs %d."
                         % (run_name, min_n, len(a_ids), len(b_ids)))

    run.log("Comparison: %s (%s n=%d) vs (%s n=%d)" % (run_name, a_name, len(a_ids), b_name, len(b_ids)))
    A = betas[a_ids].to_numpy(dtype=float)
    B = betas[b_ids].to_numpy(dtype=float)

    a_n = np.sum(~np.isnan(A), axis=1)
    b_n = np.sum(~np.isnan(B), axis=1)
    a_mean = np.nanmean(np.where(np.isnan(A), np.nan, A), axis=1)
    b_mean = np.nanmean(np.where(np.isnan(B), np.nan, B), axis=1)
    testable = (a_n >= min_n) & (b_n >= min_n)

    test = p.get("test", "welch_t")
    pvals = np.full(len(betas), np.nan)
    idx = np.where(testable)[0]
    run.log("Testing %s probes with %s" % (f"{len(idx):,}", test))

    if test == "mannwhitney":
        for i in idx:
            x = A[i][~np.isnan(A[i])]
            y = B[i][~np.isnan(B[i])]
            try:
                pvals[i] = stats.mannwhitneyu(x, y, alternative="two-sided").pvalue
            except ValueError:
                pvals[i] = np.nan
    else:
        # Vectorised t-test. scipy's nan_policy="omit" falls back to masked arrays and
        # is orders of magnitude slower - which matters at 485k probes.
        pvals[idx] = _vector_ttest(A[idx], B[idx], a_n[idx], b_n[idx],
                                   a_mean[idx], b_mean[idx],
                                   equal_var=(test == "student_t"))

    delta = a_mean - b_mean
    st = pd.DataFrame({
        "probe_id": betas.index,
        "group_a_mean_beta": a_mean,
        "group_b_mean_beta": b_mean,
        "delta_beta": delta,
        "group_a_n": a_n,
        "group_b_n": b_n,
        "p_value": pvals,
    })
    st["abs_delta_beta"] = st["delta_beta"].abs()
    st["direction"] = np.where(st["delta_beta"] >= 0, HYPER, HYPO)
    st = st[np.isfinite(st["p_value"])].reset_index(drop=True)

    run.ctx["stats"] = st
    run.ctx["groups"] = {"a": a_ids, "b": b_ids, "a_name": a_name, "b_name": b_name, "run_name": run_name}
    run.ctx["run_name"] = run_name
    run.log("%s probes returned a finite p-value" % f"{len(st):,}")
    run.stat("Probes tested", len(st))


def multiple_testing(run, p):
    st = run.ctx["stats"].copy()
    method = p.get("method", "benjamini_hochberg")
    thr = float(p["fdr_threshold"])
    if method == "benjamini_hochberg":
        st["fdr"] = benjamini_hochberg(st["p_value"].to_numpy())
        label = "Benjamini-Hochberg FDR"
    elif method == "bonferroni":
        st["fdr"] = np.clip(st["p_value"] * len(st), 0.0, 1.0)
        label = "Bonferroni adjusted p"
    else:
        st["fdr"] = st["p_value"]
        label = "raw p-value (uncorrected)"
        run.warn("No multiple-testing correction: with this many probes most 'hits' will be false.")

    st["significant"] = st["fdr"] < thr
    st = st.sort_values(["fdr", "abs_delta_beta"], ascending=[True, False]).reset_index(drop=True)
    run.ctx["stats"] = st
    n_sig = int(st["significant"].sum())
    run.log("%s: %s of %s probes significant at %s < %.4g"
            % (label, f"{n_sig:,}", f"{len(st):,}", "adj-p", thr))
    run.stat("Significant probes", n_sig)
    run.ctx["volcano"] = _volcano_points(st)
    run.artifact_frame("differential_methylation.tsv", st)


def _volcano_points(st, max_points=4000):
    df = st[np.isfinite(st["fdr"]) & np.isfinite(st["delta_beta"])]
    if len(df) > max_points:
        sig = df[df["fdr"] < 0.05]
        rest = df[df["fdr"] >= 0.05]
        take_rest = max(0, max_points - min(len(sig), max_points))
        df = pd.concat([sig.head(max_points), rest.sample(min(len(rest), take_rest), random_state=0)])
    y = -np.log10(np.clip(df["fdr"].to_numpy(dtype=float), 1e-300, 1.0))
    return {
        "x": [round(float(v), 4) for v in df["delta_beta"]],
        "y": [round(float(v), 3) for v in y],
        "probe": list(df["probe_id"]),
    }


# ---------------------------------------------------------------------------
# Biology
# ---------------------------------------------------------------------------

def annotate(run, p):
    st = run.ctx["stats"]
    ann = run.ctx.get("annotation")
    if ann is None:
        run.warn("No probe annotation available - skipping annotation join.")
        return
    cols = ["probe_id", "gene", "chrom", "chromStart", "chromEnd", "strand",
            "functional_region", "is_promoter", "dist_to_tss", "cgi_relation",
            "cgi_id", "annotation_source"]
    merged = st.merge(ann[[c for c in cols if c in ann.columns]], on="probe_id", how="left")

    up, down = float(p["promoter_upstream"]), float(p["promoter_downstream"])
    if "dist_to_tss" in merged.columns:
        d = pd.to_numeric(merged["dist_to_tss"], errors="coerce")
        merged["is_promoter"] = (d >= -up) & (d <= down)

    if p.get("require_island"):
        before = len(merged)
        merged = merged[merged["cgi_relation"].isin(["Island", "N_Shore", "S_Shore"])]
        run.log("Island/shore restriction: %s -> %s probes" % (f"{before:,}", f"{len(merged):,}"))

    covered = merged["functional_region"].notna().mean() if len(merged) else 0.0
    run.ctx["stats"] = merged.reset_index(drop=True)
    run.log("Annotated %s probes (%.1f%% with region context, promoter window -%d..+%d bp)"
            % (f"{len(merged):,}", covered * 100, up, down))
    if len(merged):
        mix = merged["functional_region"].value_counts().head(6).to_dict()
        run.log("Region mix: " + ", ".join("%s %s" % (k, v) for k, v in mix.items()))
        run.ctx["region_mix"] = {str(k): int(v) for k, v in
                                 merged["functional_region"].value_counts().items()}
    run.stat("Probes annotated", len(merged))


def direction_label(run, p):
    st = run.ctx["stats"].copy()
    if "is_promoter" not in st.columns:
        run.warn("Annotation missing - every probe labelled ambiguous.")
        st["predicted_expression_effect"] = "ambiguous"
    else:
        promoter = st["is_promoter"].fillna(False).astype(bool)
        if p.get("include_shores") and "cgi_relation" in st.columns:
            promoter = promoter | st["cgi_relation"].isin(["N_Shore", "S_Shore"])
        hyper = st["direction"] == HYPER
        effect = np.where(promoter & hyper, "silencing",
                          np.where(promoter & ~hyper, "activation", "ambiguous"))
        if not p.get("strict_promoter_only"):
            body = (~promoter) & st.get("functional_region", pd.Series("", index=st.index)).eq("gene_body")
            effect = np.where(body & hyper, "silencing_weak",
                              np.where(body & ~hyper, "activation_weak", effect))
        st["predicted_expression_effect"] = effect
        st["mechanics_basis"] = np.where(
            promoter, np.where(hyper, "promoter_hypermethylation", "promoter_hypomethylation"),
            "outside_promoter")

    counts = st["predicted_expression_effect"].value_counts().to_dict()
    run.ctx["stats"] = st
    run.ctx["mechanics_counts"] = {str(k): int(v) for k, v in counts.items()}
    run.log("Direction of effect: " + ", ".join("%s %s" % (v, k) for k, v in counts.items()))
    for k in ("silencing", "activation", "ambiguous"):
        if k in counts:
            run.stat("Predicted %s" % k, int(counts[k]))
    run.artifact_frame("differential_with_mechanics.tsv", st)


# ---------------------------------------------------------------------------
# Panel and model
# ---------------------------------------------------------------------------

def panel_select(run, p):
    st = run.ctx["stats"].copy()
    if st.empty:
        raise ValueError("Nothing left to build a panel from - loosen the upstream filters.")

    rank_by = p.get("rank_by", "abs_delta_beta")
    if rank_by == "fdr":
        st = st.sort_values(["fdr", "abs_delta_beta"], ascending=[True, False])
    elif rank_by == "combined":
        score = st["abs_delta_beta"] * -np.log10(np.clip(st["fdr"], 1e-300, 1.0))
        st = st.assign(panel_score=score).sort_values("panel_score", ascending=False)
    else:
        st = st.sort_values(["abs_delta_beta", "fdr"], ascending=[False, True])

    max_per_gene = int(p.get("max_per_gene", 0) or 0)
    if max_per_gene and "gene" in st.columns:
        st = st[st["gene"].fillna("").eq("") | (st.groupby(st["gene"].fillna("")).cumcount() < max_per_gene)]

    top_n = int(p["top_n"])
    if p.get("balance_direction"):
        half = max(1, top_n // 2)
        panel = pd.concat([st[st["direction"] == HYPER].head(half),
                           st[st["direction"] == HYPO].head(top_n - half)])
        panel = panel.sort_values("abs_delta_beta", ascending=False)
    else:
        panel = st.head(top_n)

    panel = panel.reset_index(drop=True)
    panel.insert(0, "panel_rank", np.arange(1, len(panel) + 1))
    run.ctx["panel"] = panel
    counts = panel["direction"].value_counts().to_dict()
    run.log("Panel: %d probes (%s), ranked by %s"
            % (len(panel), ", ".join("%s %s" % (v, k) for k, v in counts.items()), rank_by))
    if len(panel):
        run.log("Strongest marker: %s |delta-beta|=%.3f" %
                (panel.iloc[0]["probe_id"], float(panel.iloc[0]["abs_delta_beta"])))
    run.stat("Panel size", len(panel))
    run.artifact_frame("candidate_biomarker_panel.tsv", panel)


def classifier(run, p):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, roc_curve
    from sklearn.model_selection import StratifiedKFold

    panel = run.ctx.get("panel")
    betas = run.ctx["betas"]
    groups = run.ctx["groups"]
    if panel is None or panel.empty:
        raise ValueError("The classifier needs a panel upstream.")

    ids = groups["a"] + groups["b"]
    y = np.array([1] * len(groups["a"]) + [0] * len(groups["b"]))
    n_feat = int(p["n_features"])
    folds = int(p["cv_folds"])
    seed = int(p["seed"])
    nested = bool(p.get("nested", True))

    universe = [i for i in betas.index if i in set(run.ctx["stats"]["probe_id"])]
    fixed = [i for i in panel["probe_id"].head(n_feat) if i in betas.index]
    if len(fixed) < 2:
        raise ValueError("Fewer than two panel probes are present in the matrix.")

    X_all = betas.loc[universe, ids].to_numpy(dtype=float).T
    X_all = np.where(np.isnan(X_all), np.nanmean(X_all, axis=0), X_all)
    uni_index = {pid: k for k, pid in enumerate(universe)}
    fixed_cols = [uni_index[i] for i in fixed]

    def make_model():
        if p.get("model") == "random_forest":
            return RandomForestClassifier(n_estimators=300, random_state=seed, n_jobs=-1)
        return LogisticRegression(max_iter=2000, random_state=seed)

    min_class = int(min((y == 1).sum(), (y == 0).sum()))
    folds = max(2, min(folds, min_class))
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)

    aucs, all_true, all_score, fold_rows = [], [], [], []
    for k, (tr, te) in enumerate(skf.split(X_all, y), start=1):
        if nested:
            a_tr = X_all[np.ix_(tr[y[tr] == 1], np.arange(X_all.shape[1]))]
            b_tr = X_all[np.ix_(tr[y[tr] == 0], np.arange(X_all.shape[1]))]
            delta = np.abs(a_tr.mean(axis=0) - b_tr.mean(axis=0))
            cols = list(np.argsort(delta)[::-1][:n_feat])
        else:
            cols = fixed_cols
        model = make_model()
        model.fit(X_all[np.ix_(tr, cols)], y[tr])
        score = model.predict_proba(X_all[np.ix_(te, cols)])[:, 1]
        auc = float(roc_auc_score(y[te], score)) if len(set(y[te])) > 1 else float("nan")
        aucs.append(auc)
        all_true.extend(y[te].tolist())
        all_score.extend(score.tolist())
        fold_rows.append({"fold": k, "n_train": len(tr), "n_test": len(te),
                          "n_features": len(cols), "roc_auc": auc})
        run.log("Fold %d/%d: AUC %.4f (%d features)" % (k, folds, auc, len(cols)))

    fpr, tpr, _ = roc_curve(all_true, all_score)
    aucs_arr = np.array(aucs, dtype=float)
    summary = {
        "model": p.get("model", "logistic_regression"),
        "feature_selection": "nested (re-selected inside each training fold)" if nested
        else "fixed panel from the full cohort - optimistic, see caveat",
        "n_features": n_feat,
        "cv_folds": folds,
        "roc_auc_mean": float(np.nanmean(aucs_arr)),
        "roc_auc_std": float(np.nanstd(aucs_arr)),
        "roc_auc_per_fold": [float(a) for a in aucs_arr],
    }
    run.ctx["model"] = summary
    run.ctx["roc"] = {"fpr": [round(float(v), 4) for v in fpr],
                      "tpr": [round(float(v), 4) for v in tpr]}
    if not nested:
        run.warn("Nested selection is off: features were chosen using all samples, so this AUC is optimistic.")
    run.log("Cross-validated ROC-AUC: %.4f +/- %.4f" % (summary["roc_auc_mean"], summary["roc_auc_std"]))
    run.stat("ROC-AUC", round(summary["roc_auc_mean"], 4))
    run.artifact_json("classifier_summary.json", summary)
    run.artifact_frame("cv_folds.tsv", pd.DataFrame(fold_rows))


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

def _load_gmt(name, min_size, max_size):
    path = GENE_SETS / ("%s.gmt" % name)
    if not path.exists():
        return {}
    sets = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        genes = {g.split(",")[0].strip().upper() for g in parts[2:] if g.strip()}
        if min_size <= len(genes) <= max_size:
            sets[parts[0]] = genes
    return sets


def _ora(hits, background, gene_sets, fdr_threshold):
    hits = {g.upper() for g in hits if g}
    background = {g.upper() for g in background if g} | hits
    N, K = len(background), len(hits)
    rows = []
    for term, genes in gene_sets.items():
        genes = genes & background
        n = len(genes)
        if n == 0:
            continue
        overlap = genes & hits
        k = len(overlap)
        if k == 0:
            continue
        pval = float(stats.hypergeom.sf(k - 1, N, n, K))
        expected = K * n / N if N else 0.0
        rows.append({
            "term": term, "overlap": k, "set_size": n, "hits_tested": K,
            "background_size": N, "expected": round(expected, 3),
            "odds_ratio": round(k / expected, 3) if expected else float("inf"),
            "p_value": pval, "genes": ";".join(sorted(overlap)[:40]),
        })
    if not rows:
        return pd.DataFrame(columns=["term", "overlap", "set_size", "p_value", "fdr", "significant"])
    df = pd.DataFrame(rows).sort_values("p_value").reset_index(drop=True)
    df["fdr"] = benjamini_hochberg(df["p_value"].to_numpy())
    df["significant"] = df["fdr"] < fdr_threshold
    return df


def enrichment(run, p):
    st = run.ctx["stats"]
    if "gene" not in st.columns:
        run.warn("No gene column - enrichment skipped. Put an Annotate node upstream.")
        return
    libraries = p.get("libraries") or []
    if isinstance(libraries, str):
        libraries = [libraries]
    min_size, max_size = int(p["min_set_size"]), int(p["max_set_size"])
    thr = float(p["fdr_threshold"])

    ann = run.ctx.get("annotation")
    background = set(ann["gene"].dropna().astype(str)) if ann is not None else set()
    background.discard("")
    if p.get("background") == "library_universe":
        background = set()
        run.warn("Background = library universe. The array-gene universe is the statistically correct choice.")

    sig = st[st["significant"]] if "significant" in st.columns else st
    subsets = {"all": sig}
    if p.get("split_direction"):
        subsets["hypermethylated"] = sig[sig["direction"] == HYPER]
        subsets["hypomethylated"] = sig[sig["direction"] == HYPO]

    results, top_terms = {}, []
    for lib in libraries:
        gene_sets = _load_gmt(lib, min_size, max_size)
        if not gene_sets:
            run.warn("Library %s not found or empty at the chosen size range." % lib)
            continue
        lib_bg = background or set().union(*gene_sets.values())
        run.log("%s: %d gene sets, background %s genes" % (lib, len(gene_sets), f"{len(lib_bg):,}"))
        for label, subset in subsets.items():
            genes = set(subset["gene"].dropna().astype(str)) - {""}
            if not genes:
                continue
            df = _ora(genes, lib_bg, gene_sets, thr)
            key = "%s__%s" % (lib, label)
            results[key] = df
            run.artifact_frame("enrichment_%s.tsv" % key, df)
            n_sig = int(df["significant"].sum()) if len(df) else 0
            run.log("  %s / %s: %d genes tested, %d terms at FDR < %.3g"
                    % (lib, label, len(genes), n_sig, thr))
            if label == "all" and len(df):
                for _, r in df.head(8).iterrows():
                    top_terms.append({"library": lib, "term": str(r["term"]),
                                      "overlap": int(r["overlap"]), "set_size": int(r["set_size"]),
                                      "fdr": float(r["fdr"]),
                                      "neg_log10_fdr": float(-np.log10(max(r["fdr"], 1e-300)))})

    run.ctx["enrichment"] = {k: v for k, v in results.items()}
    run.ctx["enrichment_top"] = sorted(top_terms, key=lambda r: r["fdr"])[:14]
    total_sig = sum(int(df["significant"].sum()) for df in results.values() if len(df))
    run.stat("Enriched terms (FDR<%.2g)" % thr, total_sig)
    if total_sig == 0:
        run.log("No gene set reached FDR < %.3g. That is a real result, not a failure - the "
                "top-ranked terms are still written out so you can see what came closest." % thr)
        run.ctx["enrichment_null"] = True
    run.warn("Array-design caveat: HM450 over-samples promoters of neuronal and developmental "
             "genes, which inflates those terms. Treat enrichment as exploratory.")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def report(run, p):
    from . import report as report_mod
    path = report_mod.build(run, p)
    run.ctx["report_path"] = path.name
    run.log("Report written: %s" % path.name)


REGISTRY = {
    "load_data": load_data,
    "qc_filter": qc_filter,
    "probe_filter": probe_filter,
    "differential": differential,
    "multiple_testing": multiple_testing,
    "effect_filter": effect_filter,
    "annotate": annotate,
    "direction_label": direction_label,
    "panel_select": panel_select,
    "classifier": classifier,
    "enrichment": enrichment,
    "report": report,
}
