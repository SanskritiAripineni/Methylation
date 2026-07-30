"""Study config loading, input inspection and the reproducibility block.

The config file is the only place a threshold number lives. Nothing here
invents a default: if a value is absent from the config it is reported as
absent, never filled in.
"""
from __future__ import annotations

import gzip
import json
import platform
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
STUDIES_DIR = ROOT / "studies"

# Uploads above this go to the Local path field instead. Pushing a 400 MB
# matrix through a browser so the server can read its header is pointless.
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def list_studies():
    if not STUDIES_DIR.exists():
        return []
    out = []
    for d in sorted(STUDIES_DIR.iterdir()):
        cfg_path = d / "config.yaml"
        if cfg_path.is_file():
            try:
                cfg = load_config(d.name)
            except Exception as exc:
                out.append({"id": d.name, "label": d.name, "error": str(exc)})
                continue
            out.append({"id": cfg["id"], "label": cfg.get("label", cfg["id"]),
                        "tissue": cfg.get("tissue", "")})
    return out


def load_config(study_id):
    path = STUDIES_DIR / study_id / "config.yaml"
    if not path.is_file():
        raise FileNotFoundError("No study config at %s" % path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg.setdefault("id", study_id)
    return cfg


def resolve(rel):
    """Resolve a config path against the project root."""
    p = Path(rel)
    return p if p.is_absolute() else (ROOT / p)


# ---------------------------------------------------------------------------
# reproducibility block - detected, never typed
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def reproducibility():
    def ver(mod):
        try:
            return __import__(mod).__version__
        except Exception:
            return None

    commit, dirty = None, None
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
            stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(ROOT),
            stderr=subprocess.DEVNULL, text=True, timeout=5).strip())
    except Exception:
        pass

    return {
        "python": sys.version.split()[0],
        "platform": "%s %s" % (platform.system(), platform.release()),
        "packages": {name: ver(name) for name in
                     ("pandas", "numpy", "scipy", "sklearn", "statsmodels", "yaml")},
        "git_commit": commit,
        "git_dirty": dirty,
        # Named explicitly so nobody reads the blank as an oversight.
        "array_type": None,
        "array_type_note": "Not detectable from a beta matrix - no Sentrix ids, no control probes.",
        "annotation_version": None,
        "annotation_version_note": "The bundled probe annotation carries no version stamp.",
    }


# ---------------------------------------------------------------------------
# file sniffing
# ---------------------------------------------------------------------------

def _open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def sniff_table(path, max_scan_rows=200000):
    """Header + shape of a TSV/CSV without loading it into memory."""
    path = Path(path)
    info = {"path": str(path), "exists": path.is_file()}
    if not info["exists"]:
        return info
    info["size_bytes"] = path.stat().st_size

    # An unresolved Git-LFS pointer is a real 130-byte text file. It exists,
    # so every naive is_file() check passes and the read fails later.
    with open(path, "rb") as fh:
        head = fh.read(200)
    if head.startswith(b"version https://git-lfs"):
        info["lfs_pointer"] = True
        info["error"] = "Git-LFS pointer, not the file itself."
        return info

    try:
        with _open_text(path) as fh:
            first = fh.readline().rstrip("\n\r")
            sep = "\t" if first.count("\t") >= first.count(",") else ","
            info["separator"] = "tab" if sep == "\t" else "comma"
            info["columns"] = first.split(sep)
            info["n_columns"] = len(info["columns"])
            rows, first_col = 0, []
            for line in fh:
                rows += 1
                if rows <= 5:
                    first_col.append(line.split(sep, 1)[0])
                if rows >= max_scan_rows:
                    info["row_count_truncated"] = True
                    break
            info["n_rows"] = rows
            info["first_row_keys"] = first_col
    except Exception as exc:
        info["error"] = "%s: %s" % (type(exc).__name__, exc)
    return info


def _col(columns, *candidates):
    lower = {c.strip().lower(): c for c in (columns or [])}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


# ---------------------------------------------------------------------------
# capability matrix
# ---------------------------------------------------------------------------
# One line per capability, each with the consequence of its absence. The
# `not_applicable` rows come straight from the study config: they are things
# this pipeline structurally cannot do, which is different from a missing file.

def inspect_inputs(matrix_path=None, manifest_path=None, annotation_path=None,
                   study_id="brca_sim"):
    cfg = load_config(study_id)
    data = cfg.get("data", {})

    matrix = sniff_table(resolve(matrix_path or data.get("matrix_path", "")))
    manifest = sniff_table(resolve(manifest_path or data.get("manifest_path", "")))
    annot = sniff_table(resolve(annotation_path or data.get("annotation_path", "")))

    caps = []

    def cap(cid, label, state, required, detail, consequence):
        caps.append({"id": cid, "label": label, "state": state, "required": required,
                     "detail": detail, "consequence": consequence})

    # --- beta matrix -------------------------------------------------------
    if matrix.get("exists") and not matrix.get("error"):
        n_samples = max(0, matrix["n_columns"] - 1)
        cap("matrix", "Beta-value matrix (probes x samples)", "ok", True,
            "%s columns (%d samples + probe id), %s rows scanned." % (
                matrix["n_columns"], n_samples, f"{matrix['n_rows']:,}"),
            "Without it there is nothing to analyse.")
    else:
        cap("matrix", "Beta-value matrix (probes x samples)", "fail", True,
            matrix.get("error") or "Not found: %s" % matrix.get("path", "(unset)"),
            "Without it there is nothing to analyse.")

    # --- sample table ------------------------------------------------------
    id_col = _col(manifest.get("columns"), data.get("id_column", "sample_barcode"),
                  "sample_id", "barcode", "sample")
    group_col = _col(manifest.get("columns"), data.get("group_column", "sample_class"),
                     "group", "condition", "phenotype")
    if manifest.get("exists") and not manifest.get("error") and id_col:
        cap("manifest", "Sample table (id + group)", "ok", True,
            "%d rows, %d columns. Id column '%s'." % (
                manifest["n_rows"], manifest["n_columns"], id_col),
            "Without it the matrix columns cannot be tied to samples.")
    else:
        cap("manifest", "Sample table (id + group)", "fail", True,
            manifest.get("error") or (
                "No id column found among %s" % (manifest.get("columns") or "(file not found)")),
            "Without it the matrix columns cannot be tied to samples.")

    # --- group column ------------------------------------------------------
    if group_col:
        cap("group", "Group / phenotype column", "ok", True,
            "Column '%s'." % group_col,
            "Without it only QC runs. No differential test, no panel, no classifier.")
    else:
        cap("group", "Group / phenotype column", "fail", True,
            "Not found. Looked for '%s'." % data.get("group_column", "sample_class"),
            "Without it only QC runs. No differential test, no panel, no classifier.")

    # --- probe annotation --------------------------------------------------
    if annot.get("exists") and not annot.get("error"):
        has_gene = _col(annot.get("columns"), "gene", "gene_symbol")
        cap("annotation", "Probe annotation (gene / region)", "ok" if has_gene else "warn", False,
            "%s rows, columns: %s" % (f"{annot['n_rows']:,}",
                                      ", ".join(annot.get("columns", [])[:8])),
            "Absent: probes are still tested, but lose gene names, promoter context, "
            "the silencing/activation call and pathway enrichment.")
    else:
        cap("annotation", "Probe annotation (gene / region)", "warn", False,
            annot.get("error") or "Not found: %s" % annot.get("path", "(unset)"),
            "Absent: probes are still tested, but lose gene names, promoter context, "
            "the silencing/activation call and pathway enrichment.")

    # --- covariates --------------------------------------------------------
    present = [c for c in data.get("covariate_columns", [])
               if _col(manifest.get("columns"), c)]
    missing = [c for c in data.get("covariate_columns", []) if c not in present]
    cap("covariates", "Covariates (subtype, age, sex, purity)",
        "ok" if present else "warn", False,
        ("Present: %s." % ", ".join(present) if present else "None found.") +
        (" Missing: %s." % ", ".join(missing) if missing else ""),
        "The differential block does not adjust for any of them - they are recorded "
        "and cross-tabulated, not regressed out. Any hit may be a composition or "
        "subtype difference.")

    # --- batch -------------------------------------------------------------
    batch_present = [c for c in data.get("batch_columns", [])
                     if _col(manifest.get("columns"), c)]
    cap("batch", "Batch / slide / plate column",
        "ok" if batch_present else "fail_soft", False,
        "Found: %s." % ", ".join(batch_present) if batch_present else
        "None of %s present." % ", ".join(data.get("batch_columns", [])),
        "Absent: batch confounding cannot be assessed at all. This is the most "
        "common route to a confidently wrong methylation result, and without a "
        "batch column you cannot rule it in or out.")

    # --- structurally unavailable -----------------------------------------
    for key, spec in (cfg.get("not_applicable") or {}).items():
        caps.append({
            "id": "na_" + key,
            "label": spec.get("label", key),
            "state": "na",
            "required": False,
            "detail": (spec.get("reason") or "").strip(),
            "consequence": (spec.get("consequence") or "").strip(),
        })

    provides = {
        "differential": all(c["state"] in ("ok", "warn") for c in caps
                            if c["id"] in ("matrix", "manifest", "group")),
        "annotation_dependent": next(
            (c["state"] in ("ok",) for c in caps if c["id"] == "annotation"), False),
    }

    return {
        "study": cfg["id"],
        "files": {"matrix": matrix, "manifest": manifest, "annotation": annot},
        "columns": {"id": id_col, "group": group_col, "batch": batch_present},
        "capabilities": caps,
        "provides": provides,
        "blocking": [c["id"] for c in caps if c["state"] == "fail"],
    }


def upload_limit_message(size):
    return ("That file is %.0f MB. Uploads are capped at %d MB - use the Local path "
            "field instead, which reads the file where it already sits instead of "
            "copying it through the browser." % (size / 1048576, MAX_UPLOAD_BYTES // 1048576))
