"""Make a user's files fit the pipeline, without touching the pipeline.

The engine expects one exact shape: a sample table with a `sample_barcode`
column and a `sample_class` column holding the literal values "tumor" and
"normal" (engine/nodes.py::_split_groups compares against those strings). Real
files almost never look like that - they have `sample_id` and `group`, holding
`case` and `control`.

Rather than edit the frozen engine, this translates on the way in: a
normalized copy is written next to the user's files, the originals are never
modified, and the mapping is reported in plain language so nobody has to guess
which group ended up as which side of the comparison.

Direction matters: delta-beta is computed as tumor minus normal, so which
group becomes "tumor" decides the sign of every result. That choice is made by
a stated rule and shown on screen - never silently.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import workspace

NORMALIZED = workspace.WORKSPACE / ".normalized"

# Words that mark the REFERENCE group - the one everything is compared against.
# It becomes "normal", so a positive delta-beta means "higher in the other group".
REFERENCE_WORDS = ("normal", "control", "ctrl", "healthy", "reference", "ref",
                   "baseline", "untreated", "wt", "wildtype", "wild_type",
                   "unaffected", "benign", "adjacent")

ID_NAMES = ("sample_barcode", "sample_id", "sample", "barcode", "id", "name", "title")
GROUP_NAMES = ("sample_class", "group", "condition", "phenotype", "class", "status",
               "label", "type", "diagnosis")


def _pick(columns, candidates):
    lower = {str(c).strip().lower(): c for c in columns}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def _pick_group(frame, id_col):
    """A group column: few distinct values, not the id, not a number."""
    named = _pick(frame.columns, GROUP_NAMES)
    if named and named != id_col:
        return named
    best = None
    for col in frame.columns:
        if col == id_col:
            continue
        vals = frame[col].dropna()
        if vals.empty or pd.api.types.is_numeric_dtype(vals):
            continue
        n = vals.nunique()
        if 2 <= n <= 6 and (best is None or n < best[1]):
            best = (col, n)
    return best[0] if best else None


def _split(values):
    """Decide which of two group labels is the reference side."""
    a, b = values
    def score(v):
        s = re.sub(r"[^a-z]+", "_", str(v).lower())
        return any(w in s.split("_") or w == s for w in REFERENCE_WORDS)
    a_ref, b_ref = score(a), score(b)
    if a_ref and not b_ref:
        return b, a, "matched the word '%s'" % a
    if b_ref and not a_ref:
        return a, b, "matched the word '%s'" % b
    # Nothing recognisable. Pick deterministically and say so loudly - the sign
    # of every difference depends on this.
    first, second = sorted([str(a), str(b)])
    return second, first, ("no recognisable control label, so the alphabetically first "
                           "value was used as the reference")


def normalize(paths, cfg):
    """Return (paths, report). `paths` is what the run should actually read."""
    manifest_path = paths.get("manifest")
    matrix_path = paths.get("matrix")
    report = {"changed": False, "notes": [], "mapping": {}, "warnings": []}
    if not manifest_path or not Path(manifest_path).is_file():
        return paths, report

    frame = pd.read_csv(manifest_path, sep="\t")
    id_col = _pick(frame.columns, ID_NAMES)
    group_col = _pick_group(frame, id_col)

    if id_col is None:
        report["warnings"].append(
            "No column in the sample list looks like a sample name. Looked for: %s."
            % ", ".join(ID_NAMES))
        return paths, report
    if group_col is None:
        report["warnings"].append(
            "No column in the sample list looks like a group. The run needs two groups "
            "to compare.")
        return paths, report

    out = frame.copy()
    renames = {}
    if id_col != "sample_barcode":
        renames[id_col] = "sample_barcode"
    if group_col != "sample_class":
        renames[group_col] = "sample_class"
    out = out.rename(columns=renames)

    # Keep the originals alongside, so nothing is lost from the record.
    for src, dst in renames.items():
        out["original_" + dst] = frame[src]

    labels = [str(v) for v in out["sample_class"].dropna().unique()]
    value_map = {}
    if len(labels) == 2 and set(labels) != {"tumor", "normal"}:
        case, ref, why = _split(labels)
        value_map = {case: "tumor", ref: "normal"}
        out["sample_class"] = out["sample_class"].astype(str).map(value_map).fillna(
            out["sample_class"].astype(str))
        report["mapping"]["groups"] = {"comparison": "%s vs %s" % (case, ref),
                                       "case": case, "reference": ref, "why": why}
        report["notes"].append(
            "'%s' is the comparison group and '%s' is the reference (%s). A positive "
            "difference means higher methylation in '%s'." % (case, ref, why, case))
        if "alphabetically" in why:
            report["warnings"].append(
                "Neither group name looks like a control, so '%s' was used as the reference. "
                "If that is backwards, every difference flips sign - rename the groups or "
                "check the direction before quoting anything." % ref)
    elif len(labels) > 2:
        report["warnings"].append(
            "The group column has %d values (%s). This pipeline compares exactly two; "
            "reduce it to two before running." % (len(labels), ", ".join(labels[:5])))
        return paths, report
    elif len(labels) < 2:
        report["warnings"].append(
            "The group column has only one value (%s). There is nothing to compare it to."
            % (labels[0] if labels else "none"))
        return paths, report

    if renames:
        report["mapping"]["columns"] = {v: k for k, v in renames.items()}
        report["notes"].append(
            "Read '%s' as the sample name and '%s' as the group."
            % (id_col, group_col))

    # Only the samples the matrix actually contains.
    if matrix_path and Path(matrix_path).is_file():
        with workspace.study._open_text(matrix_path) as fh:
            header = fh.readline().rstrip("\n\r")
        sep = "\t" if header.count("\t") >= header.count(",") else ","
        cols = set(c.strip() for c in header.split(sep)[1:])
        have = out["sample_barcode"].astype(str).isin(cols)
        if not have.all():
            missing = out.loc[~have, "sample_barcode"].astype(str).tolist()
            report["warnings"].append(
                "%d sample%s in the list %s not columns in the methylation table (%s%s). "
                "They will be ignored." % (
                    len(missing), "" if len(missing) == 1 else "s",
                    "is" if len(missing) == 1 else "are", ", ".join(missing[:4]),
                    "…" if len(missing) > 4 else ""))

    if not renames and not value_map:
        return paths, report        # already the shape the engine wants

    NORMALIZED.mkdir(parents=True, exist_ok=True)
    target = NORMALIZED / "samples_for_run.tsv"
    out.to_csv(target, sep="\t", index=False)
    report["changed"] = True
    report["path"] = str(target)
    report["counts"] = out["sample_class"].value_counts().to_dict()

    new_paths = dict(paths)
    new_paths["manifest"] = str(target)
    return new_paths, report


def describe(report):
    """One short paragraph for the interface."""
    if not report.get("changed") and not report.get("warnings"):
        return ""
    bits = list(report.get("notes", []))
    bits += report.get("warnings", [])
    return " ".join(bits)
