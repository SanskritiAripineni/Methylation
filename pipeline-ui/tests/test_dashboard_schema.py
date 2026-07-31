"""Holds both dashboard builders to the one contract.

    python tests/test_dashboard_schema.py

No test framework - there is none in this project and adding one is not
worth it for this. Exit code 0 means every check passed.

The check that matters is the last one: the published study and a run you
started must return the *same sections*. That is the thing that silently
broke before - one source grew a volcano, the other kept a cohort panel, and
the interface just hid whichever was missing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from dashboard import build, schema          # noqa: E402
from console_v4 import sources               # noqa: E402
from console_v7 import routes as v7_routes   # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  [pass] %s" % name)
    else:
        print("  [FAIL] %s%s" % (name, ("\n         " + detail) if detail else ""))
        FAILURES.append(name)


def check_model(label, model):
    problems = schema.problems(model)
    check("%s satisfies the contract" % label, not problems,
          "\n         ".join(problems))
    return model


# ---------------------------------------------------------------------------
print("\nthe published study")
ref = check_model("reference dashboard", build.from_reference(sources.Files()))

check("reference names itself", ref["source"]["kind"] == "reference")
check("reference has a report to show", ref["report"]["state"] == schema.OK)
check("reference states why it has no volcano",
      ref["volcano"]["state"] == schema.UNAVAILABLE and len(ref["volcano"]["reason"]) > 40,
      "reason was: %r" % ref["volcano"]["reason"])

v7_ref = v7_routes._published_dashboard()
check("V7 uses the published BRCA volcano without changing the shared schema",
      v7_ref["schema"] == schema.SCHEMA_VERSION
      and v7_ref["volcano"]["state"] == schema.OK
      and v7_ref["volcano"]["image_url"].endswith("/volcano.png"))
check("V7 uses the published BRCA PCA instead of inventing a ROC curve",
      v7_ref["roc"]["state"] == schema.OK and not v7_ref["roc"]["fpr"]
      and v7_ref["roc"]["image_url"].endswith("/pca.png"))
check("V7 uses BRCA pathway results",
      v7_ref["enrichment"]["state"] == schema.OK
      and len(v7_ref["enrichment"]["items"]) >= 4)

# ---------------------------------------------------------------------------
print("\nevery run on disk")
run_models = []
runs_dir = ROOT / "runs"
run_dirs = sorted([d for d in runs_dir.iterdir() if (d / "results.json").is_file()]) \
    if runs_dir.is_dir() else []

if not run_dirs:
    print("  (no run has results.json yet - start one and re-run this)")
for d in run_dirs:
    res = json.loads((d / "results.json").read_text(encoding="utf-8"))
    rec_path = d / "run_record.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.is_file() else {}
    snap = {"id": d.name, "label": rec.get("label") or d.name,
            "mode": rec.get("mode"), "tier_label": rec.get("mode"),
            "thresholds": rec.get("thresholds") or {}}
    has_report = (d / "run_report.html").is_file()
    files = [{"name": a.get("name"), "size": a.get("size")}
             for a in (rec.get("artifacts") or [])]
    run_models.append(check_model(
        "run %s" % d.name,
        build.from_run(res, snap,
                       report_url="/x/run_report.html" if has_report else None,
                       files=files, bundle_url="/x/bundle.zip" if files else None)))

# ---------------------------------------------------------------------------
print("\nthe two sources agree on shape")
if run_models:
    run = run_models[-1]
    check("same sections on both sources",
          set(schema.SECTIONS) <= set(ref) and set(schema.SECTIONS) <= set(run),
          "reference is missing %s; run is missing %s"
          % (sorted(set(schema.SECTIONS) - set(ref)),
             sorted(set(schema.SECTIONS) - set(run))))
    check("same top-level keys on both sources", set(ref) == set(run),
          "only in reference: %s / only in run: %s"
          % (sorted(set(ref) - set(run)), sorted(set(run) - set(ref))))
    check("both declare the same schema version",
          ref["schema"] == run["schema"] == schema.SCHEMA_VERSION)

    for name in sorted(schema.SECTIONS):
        a, b = ref[name], run[name]
        if set(a) != set(b):
            check("section %r has the same fields on both" % name, False,
                  "reference %s vs run %s" % (sorted(a), sorted(b)))
    check("every section has matching fields on both sources",
          all(set(ref[n]) == set(run[n]) for n in schema.SECTIONS))

# ---------------------------------------------------------------------------
print("\nthe shared algorithms behave the same on both shapes")

# The published study carries group means, a run does not. Same call, same
# ordering, same dedupe - the only difference is the fields that are there.
rows_with_means = [
    {"gene": "AAA", "probe_id": "cg1", "delta_beta": 0.10,
     "tumor_mean_beta": 0.8, "normal_mean_beta": 0.7, "direction": "hypermethylated"},
    {"gene": "BBB", "probe_id": "cg2", "delta_beta": -0.40,
     "tumor_mean_beta": 0.2, "normal_mean_beta": 0.6, "direction": "hypomethylated"},
    {"gene": "AAA", "probe_id": "cg3", "delta_beta": 0.30,
     "tumor_mean_beta": 0.9, "normal_mean_beta": 0.6, "direction": "hypermethylated"},
    {"gene": None, "probe_id": "cg4", "delta_beta": 0.99},
    {"gene": "nan", "probe_id": "cg5", "delta_beta": 0.98},
    {"gene": "CCC,DDD", "probe_id": "cg6", "delta_beta": 0.05},
]
rows_without = [{k: v for k, v in r.items()
                 if k not in ("tumor_mean_beta", "normal_mean_beta")}
                for r in rows_with_means]

a = build.top_movers(rows_with_means)
b = build.top_movers(rows_without)

check("movers drop rows with no gene", all(m["gene"] for m in a) and len(a) == 3,
      "got %s" % [m["gene"] for m in a])
check("movers keep one row per gene, the biggest change",
      next(m for m in a if m["gene"] == "AAA")["delta"] == 0.30)
check("movers sort by absolute change", [m["gene"] for m in a] == ["BBB", "AAA", "CCC"],
      "got %s" % [m["gene"] for m in a])
check("movers split a multi-gene name to the first",
      next(m for m in a if m["gene"] == "CCC")["probe"] == "cg6")
check("same order whether or not the source has group means",
      [m["gene"] for m in a] == [m["gene"] for m in b])
check("group means are None when absent, not missing",
      all("tumor" in m and "normal" in m for m in b)
      and all(m["tumor"] is None for m in b)
      and next(m for m in a if m["gene"] == "AAA")["tumor"] == 0.9)

check("direction always has all three slices",
      set(build.direction_counts({"ambiguous": 56})) == set(schema.DIRECTION_SLICES))
check("an absent slice counts as zero",
      build.direction_counts({"ambiguous": 56})["silencing"] == 0)
check("direction survives junk", build.direction_counts(None)
      == {s: 0 for s in schema.DIRECTION_SLICES})

check("column order is the same for both sources",
      build.order_columns(["fdr", "gene", "probe_id"])
      == build.order_columns(["probe_id", "fdr", "gene"])
      == ["probe_id", "gene", "fdr"])
check("an unknown engine column is kept, not dropped",
      "new_thing" in build.order_columns(["new_thing", "gene"]))

# ---------------------------------------------------------------------------
print("\na section can never be empty without saying why")
for label, model in [("reference", ref)] + [("run", m) for m in run_models[-1:]]:
    for name in schema.SECTIONS:
        sec = model[name]
        if sec["state"] != schema.OK and not sec["reason"]:
            check("%s.%s explains itself" % (label, name), False)
check("every non-ok section carries a reason", True)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print("FAILED - %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all checks passed")
