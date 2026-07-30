"""Dropped files: stored, identified, and reported in plain language.

A file's role is worked out from its own contents, never from its name -
"data.tsv" tells you nothing, and guessing from the name is how a sample list
ends up being read as a methylation matrix.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from console_v2 import study

WORKSPACE = study.ROOT / "workspace"
MAX_BYTES = study.MAX_UPLOAD_BYTES

SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(name):
    name = SAFE.sub("_", Path(name).name).strip("._") or "file"
    return name[:120]


def store(filename, data):
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    target = WORKSPACE / _safe_name(filename)
    target.write_bytes(data)
    return target


def identify(path):
    """Return {role, label, detail, ok} for one dropped file."""
    info = study.sniff_table(path)
    out = {"name": Path(path).name, "path": str(path), "ok": False,
           "role": "unknown", "size_bytes": info.get("size_bytes", 0)}

    if info.get("lfs_pointer"):
        out["label"] = "Not the actual file"
        out["detail"] = ("This is a Git-LFS placeholder, not the data. It looks like a real "
                         "file but it only holds a pointer.")
        return out
    if info.get("error"):
        out["label"] = "Could not read it"
        out["detail"] = info["error"]
        return out

    cols = [str(c).strip() for c in info.get("columns", [])]
    lower = [c.lower() for c in cols]
    n_rows = info.get("n_rows", 0)

    # A sample list: one row per sample, an id column and a group column.
    id_like = next((c for c in ("sample_barcode", "sample_id", "barcode", "sample", "id")
                    if c in lower), None)
    group_like = next((c for c in ("sample_class", "group", "condition", "phenotype",
                                   "class", "status") if c in lower), None)
    # A probe annotation: one row per site, with gene/chromosome columns.
    ann_like = ("gene" in lower or "gene_symbol" in lower) and \
               any(c in lower for c in ("chrom", "chr", "chromosome"))

    if ann_like and "probe_id" in lower:
        out.update(role="annotation", ok=True, label="Site information",
                   detail="%s sites, with gene and chromosome for each." % f"{n_rows:,}")
        return out
    if id_like and group_like:
        out.update(role="manifest", ok=True, label="Sample list",
                   detail="%d samples, grouped by '%s'." % (n_rows, cols[lower.index(group_like)]))
        return out
    if len(cols) > 5 and n_rows > 50 and not group_like:
        out.update(role="matrix", ok=True, label="Methylation data",
                   detail="%s sites across %d samples." % (f"{n_rows:,}", len(cols) - 1))
        return out
    if id_like:
        out.update(role="manifest", ok=True, label="Sample list",
                   detail="%d samples. No group column found yet - the run needs one to compare "
                          "two groups." % n_rows)
        return out

    out["label"] = "Not recognised"
    out["detail"] = ("%d columns, %s rows. It does not look like a methylation table, a sample "
                     "list or a site annotation." % (len(cols), f"{n_rows:,}"))
    return out


def current():
    """Everything currently in the workspace, newest first per role."""
    if not WORKSPACE.exists():
        return {"files": [], "roles": {}}
    files = []
    for p in sorted(WORKSPACE.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if p.is_file() and p.name != "state.json":
            files.append(identify(p))
    roles = {}
    for f in files:
        if f["ok"] and f["role"] not in roles:
            roles[f["role"]] = f["path"]
    return {"files": files, "roles": roles}


def clear():
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE, ignore_errors=True)
    return current()


def readiness(roles):
    """One plain sentence about whether these files can be run."""
    if not roles:
        return {"ready": False,
                "message": "Drop in your files, or use the example data to see how it works."}
    if "matrix" not in roles:
        return {"ready": False,
                "message": "Still need the methylation data - the big table with one row per site."}
    if "manifest" not in roles:
        return {"ready": False,
                "message": "Still need the sample list - which sample is in which group."}
    extra = "" if "annotation" in roles else \
        " No site information file, so results will not carry gene names."
    return {"ready": True, "message": "Ready to run." + extra}
