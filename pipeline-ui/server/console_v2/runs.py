"""Tiered runs: plan / demo / full.

Wraps the frozen engine runner by subclassing it. Nothing in engine/ is
modified. What this adds:

  * a run id that contains the tier, so a rehearsal is never mistaken for a
    result in a folder listing
  * per-step records keyed by step NAME, not index (inserting a step must not
    silently re-key every historical timing)
  * a single-slot queue, so "waiting behind run X" is a real answer
  * a durable history file used for measured time estimates
  * a computed verdict derived from the run record
"""
from __future__ import annotations

import json
import threading
import time
import traceback
import uuid
from pathlib import Path

import pandas as pd

from engine import catalog, runner
from engine.nodes import REGISTRY

from . import study

ROOT = study.ROOT
HISTORY = runner.RUNS_DIR / "history_v2.jsonl"   # a file, so clear_old_runs() ignores it

MODES = ("plan", "demo", "full")


# ---------------------------------------------------------------------------
# graph construction
# ---------------------------------------------------------------------------

def _apply_threshold(params_by_node, spec, value):
    """Write a config threshold into the node parameter it maps to."""
    target = spec.get("maps_to")
    if not target or "." not in target:
        return None
    node_type, key = target.split(".", 1)
    if spec.get("invert"):
        value = round(1.0 - float(value), 6)
    params_by_node.setdefault(node_type, {})[key] = value
    return "%s.%s = %s" % (node_type, key, value)


def build_graph(cfg, thresholds, mode, n_per_class, work_dir, paths=None):
    """Return (graph, demo_adjustments, resolved_inputs)."""
    tcfg = cfg.get("thresholds", {})
    per_type = {}
    for key, spec in tcfg.items():
        value = thresholds.get(key, spec.get("default"))
        _apply_threshold(per_type, spec, value)

    data = cfg.get("data", {})
    paths = {k: v for k, v in (paths or {}).items() if v}
    resolved = {
        "matrix": str(study.resolve(paths.get("matrix") or data.get("matrix_path", ""))),
        "manifest": str(study.resolve(paths.get("manifest") or data.get("manifest_path", ""))),
        "annotation": str(study.resolve(paths.get("annotation") or data.get("annotation_path", ""))),
        "user_supplied": bool(paths),
    }

    adjustments = []

    # effect_filter.min_group_n is a cohort-size gate, and the block ships with
    # it at 30 - the size of the published cohort. On any smaller study it
    # silently drops EVERY probe and the run dies two steps later with
    # "nothing left to build a panel from". Tie it to the minimum-group-size
    # threshold the user actually controls instead. On the published cohort
    # (90 vs 40) this changes nothing: both groups clear 30 and 3 alike.
    ef_default = int(catalog.merged_params("effect_filter", {}).get("min_group_n", 0) or 0)
    floor_spec = tcfg.get("min_samples_per_class") or {}
    floor = int(thresholds.get("min_samples_per_class", floor_spec.get("default", 3)))
    if ef_default != floor:
        per_type.setdefault("effect_filter", {})["min_group_n"] = floor
        adjustments.append({
            "param": "effect_filter.min_group_n",
            "from": ef_default, "to": floor,
            "why": "This is a cohort-size gate, not an effect threshold. Left at %d it drops "
                   "every probe in any study with fewer than %d samples per group. It now "
                   "follows the minimum group size you set. No effect-size, FDR or QC "
                   "threshold is changed." % (ef_default, ef_default),
            "silent_on_published_cohort": True,
        })

    if mode == "demo":
        # The subset is written into the run's own working copy; the bundled
        # cohort on disk is never touched.
        sub_matrix, sub_manifest, picked = _write_demo_subset(
            cfg, n_per_class, work_dir, thresholds,
            matrix_path=resolved["matrix"], manifest_path=resolved["manifest"])
        resolved["matrix"] = str(sub_matrix)
        resolved["manifest"] = str(sub_manifest)
        resolved["demo_samples"] = picked

        # The subset is smaller than the cohort's own minimum, so the same
        # cohort-size gate has to come down with it.
        if floor > n_per_class:
            per_type.setdefault("effect_filter", {})["min_group_n"] = n_per_class
        for key in ("min_samples_per_class",):
            spec = tcfg.get(key) or {}
            want = int(thresholds.get(key, spec.get("default", 3)))
            if want > n_per_class:
                per_type.setdefault("differential", {})["min_group_n"] = n_per_class
                per_type.setdefault("qc_filter", {})["min_group_n"] = n_per_class
                adjustments.append({
                    "param": "min_samples_per_class",
                    "from": want, "to": n_per_class,
                    "why": "The subset has %d per class, so the run would refuse to start "
                           "at %d." % (n_per_class, want),
                })

    nodes, edges = [], []
    default_nodes = {n["id"]: n for n in catalog.DEFAULT_GRAPH["nodes"]}
    for step in cfg.get("steps", []):
        base = default_nodes.get(step["node"], {})
        params = dict(base.get("params") or {})
        params.update(per_type.get(step["type"], {}))
        if step["type"] == "load_data":
            params["dataset"] = "custom"
            params["matrix_path"] = resolved["matrix"]
            params["manifest_path"] = resolved["manifest"]
            params["max_probes"] = 0        # never subset probes - see config
        nodes.append({"id": step["node"], "type": step["type"],
                      "x": base.get("x", 40), "y": base.get("y", 60), "params": params})
    edges = [dict(e) for e in catalog.DEFAULT_GRAPH["edges"]]
    return {"nodes": nodes, "edges": edges}, adjustments, resolved


def _write_demo_subset(cfg, n_per_class, work_dir, thresholds,
                       matrix_path=None, manifest_path=None):
    """Subset SAMPLES only, into the run's own directory.

    Probes are never subset: the effect-size ranking, the multiple-testing
    burden and the classifier's feature pool all depend on the full probe set,
    so a probe subset would invalidate exactly the steps the rehearsal exists
    to test.
    """
    data = cfg.get("data", {})
    demo = cfg.get("demo", {})
    id_col = data.get("id_column", "sample_barcode")
    group_col = data.get("group_column", "sample_class")

    manifest = pd.read_csv(study.resolve(manifest_path or data["manifest_path"]), sep="\t")
    betas = pd.read_csv(study.resolve(matrix_path or data["matrix_path"]), sep="\t", index_col=0)

    # Samples that the call-rate gate would drop anyway are excluded from the
    # draw, so the rehearsal does not fail on QC by luck. Recorded, because it
    # means the demo is not a test of sample QC.
    call_rate = 1.0 - betas.isna().mean(axis=0)
    spec = (cfg.get("thresholds", {}).get("sample_call_rate_min") or {})
    floor = float(thresholds.get("sample_call_rate_min", spec.get("default", 0.75)))
    eligible = set(call_rate[call_rate >= floor].index)

    picked = []
    strata = [c for c in demo.get("stratify_by", []) if c in manifest.columns]
    for cls, block in manifest.groupby(group_col, sort=True):
        block = block[block[id_col].isin(eligible)]
        if strata:
            # spread across strata deterministically rather than taking the head
            block = block.sort_values(strata + [id_col])
            step = max(1, len(block) // max(1, n_per_class))
            chosen = block.iloc[::step].head(n_per_class)
            if len(chosen) < n_per_class:
                chosen = block.head(n_per_class)
        else:
            chosen = block.sort_values(id_col).head(n_per_class)
        if len(chosen) < n_per_class:
            raise ValueError(
                "Class '%s' has only %d samples that pass the %.2f call-rate floor, "
                "but the demo needs %d. Both classes must survive the subset or every "
                "downstream model fails to fit - lower the demo size or the call-rate "
                "floor." % (cls, len(chosen), floor, n_per_class))
        picked.extend(chosen[id_col].tolist())

    classes = manifest.set_index(id_col).loc[picked, group_col].nunique()
    if classes < 2:
        raise ValueError("The subset kept only one class. A differential test needs two.")

    work_dir.mkdir(parents=True, exist_ok=True)
    sub_manifest = work_dir / "demo_sample_manifest.tsv"
    sub_matrix = work_dir / "demo_sample_betas.tsv"
    manifest[manifest[id_col].isin(picked)].to_csv(sub_manifest, sep="\t", index=False)
    betas[picked].to_csv(sub_matrix, sep="\t")
    return sub_matrix, sub_manifest, picked


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------

class V2Run(runner.Run):
    def __init__(self, cfg, mode, opts):
        self.mode = mode
        self.cfg = cfg
        self.opts = dict(opts or {})
        self.study_id = cfg["id"]
        self.thresholds = dict(opts.get("thresholds") or {})
        self.n_per_class = int(opts.get("n_per_class")
                               or cfg.get("demo", {}).get("n_per_class_default", 3))
        self.source_label = opts.get("source_label", "")
        self.paths = {k: v for k, v in (opts.get("paths") or {}).items() if v}
        self.validated_by = opts.get("validated_by")
        self.display_label = opts.get("name") or "%s %s" % (cfg.get("label", cfg["id"]), mode)

        super().__init__({"nodes": [], "edges": []}, self.display_label)

        # Re-stamp the id so the tier is visible in any folder listing.
        stale = self.dir
        self.id = "%s-%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), mode, uuid.uuid4().hex[:6])
        self.dir = runner.RUNS_DIR / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        try:
            stale.rmdir()
        except OSError:
            pass

        self.steps = [{"node": s["node"], "name": s["name"], "type": s["type"],
                       "state": "pending", "seconds": None, "reason": None,
                       "caveat": s.get("caveat")}
                      for s in cfg.get("steps", [])]
        self.demo_adjustments = []
        self.resolved_inputs = {}
        self.waiting_behind = None
        self.cancel_requested = False
        self.cancel_outcome = None
        self._cancel = threading.Event()

    # -- helpers -----------------------------------------------------------
    def _step(self, node_id):
        for s in self.steps:
            if s["node"] == node_id:
                return s
        return None

    def request_cancel(self):
        self.cancel_requested = True
        self._cancel.set()
        if self.status == "queued":
            self.status = "cancelled"
            self.cancel_outcome = "Stopped before it started - it was still queued."
            self.finished = time.time()
            self._finish_record()
            return self.cancel_outcome
        running = next((s["name"] for s in self.steps if s["state"] == "running"), None)
        self.cancel_outcome = (
            "Cancelling. '%s' is mid-step and will finish; nothing after it will start."
            % running) if running else "Cancelling after the current step."
        return self.cancel_outcome

    # -- execution ---------------------------------------------------------
    def execute(self):
        self.status = "running"
        self.waiting_behind = None
        try:
            graph, adjustments, resolved = build_graph(
                self.cfg, self.thresholds, self.mode, self.n_per_class, self.dir,
                paths=self.paths)
            self.graph = graph
            self.demo_adjustments = adjustments
            self.resolved_inputs = resolved
            for adj in adjustments:
                self.warn("Demo adjustment: %s %s -> %s. %s"
                          % (adj["param"], adj["from"], adj["to"], adj["why"]))

            order = runner.topological_order(graph)

            if self.mode == "plan":
                self._write_commands(order, resolved)
                for s in self.steps:
                    s["state"] = "skipped"
                    s["reason"] = "Plan tier resolves paths and parameters; it executes nothing."
                self.status = "done"
                self.log("Plan complete. commands.txt written. Nothing was executed.")
                return

            self.log("Executing %d steps in %s mode." % (len(order), self.mode))
            for node in order:
                if self._cancel.is_set():
                    for s in self.steps:
                        if s["state"] == "pending":
                            s["state"] = "skipped"
                            s["reason"] = "Cancelled by the user before this step started."
                    self.status = "cancelled"
                    self.cancel_outcome = "Stopped after '%s'." % (
                        next((s["name"] for s in reversed(self.steps)
                              if s["state"] == "done"), "the first step"))
                    self.log(self.cancel_outcome, level="warn")
                    return

                step = self._step(node["id"])
                fn = REGISTRY.get(node["type"])
                if fn is None:
                    if step:
                        step["state"] = "skipped"
                        step["reason"] = "No implementation registered for '%s'." % node["type"]
                    self.warn("Unknown block type '%s' - skipped." % node["type"])
                    continue

                self._current = node["id"]
                self.node_status[node["id"]] = "running"
                if step:
                    step["state"] = "running"
                params = catalog.merged_params(node["type"], node.get("params"))
                t0 = time.time()
                fn(self, params)
                if node["type"] == "load_data":
                    self._restate_provenance()
                dt = round(time.time() - t0, 2)
                self.node_status[node["id"]] = "done"
                if step:
                    step["state"] = "done"
                    step["seconds"] = dt
                self.log("%s finished in %.2fs" % (
                    catalog.NODES_BY_TYPE[node["type"]]["name"], dt))

            self._current = None
            self.write_manifest(order)
            self.status = "done"
            self.log("Run complete.")
        except Exception as exc:
            self.status = "error"
            self.error = "%s: %s" % (type(exc).__name__, exc)
            if self._current:
                self.node_status[self._current] = "error"
                step = self._step(self._current)
                if step:
                    step["state"] = "failed"
                    step["reason"] = self.error
            for s in self.steps:
                if s["state"] == "pending":
                    s["state"] = "skipped"
                    s["reason"] = "An earlier step failed."
            self.log(self.error, level="error")
            self.log(traceback.format_exc(), level="error")
        finally:
            self.finished = time.time()
            if self.mode != "plan":
                try:
                    self.bundle()
                except Exception:
                    pass
            self._finish_record()

    def _restate_provenance(self):
        """Say what the data actually is, in the string the report renders.

        Every tier hands load_data explicit paths, so the engine's own label is
        always "custom files supplied by the user" - which on the bundled
        cohort is false, and worse, makes the report show its green
        user-supplied callout instead of the red simulated-data warning.
        Restate it from the study config, which knows.
        """
        data = self.cfg.get("data", {})
        simulated = "SIMULATED" in (data.get("provenance") or "").upper()
        if self.resolved_inputs.get("user_supplied"):
            base = "user-supplied files: %s" % Path(self.resolved_inputs["matrix"]).name
        elif simulated:
            base = ("bundled study cohort - per-sample values are SIMULATED; per-probe "
                    "group means for 500 reference probes are real")
        else:
            base = "bundled study cohort (%s)" % self.cfg.get("label", self.study_id)
        if self.mode == "demo":
            base += " · DEMO SUBSET, %d samples per class - a rehearsal, not a result" % self.n_per_class
        self.ctx["data_provenance"] = base
        self.log("Data provenance: %s" % base)

    def _write_commands(self, order, resolved):
        lines = [
            "# Plan for %s" % self.id,
            "# study: %s   mode: plan   generated: %s" % (
                self.study_id, time.strftime("%Y-%m-%d %H:%M:%S")),
            "# Nothing below was executed. Every path was resolved and checked.",
            "",
            "## resolved inputs",
        ]
        for key, value in resolved.items():
            if key == "demo_samples":
                continue
            exists = Path(value).is_file() if value else False
            lines.append("%-12s %s   [%s]" % (key, value, "found" if exists else "MISSING"))
        lines += ["", "## steps"]
        for i, node in enumerate(order, 1):
            spec = catalog.NODES_BY_TYPE[node["type"]]
            params = catalog.merged_params(node["type"], node.get("params"))
            lines.append("%2d. %-32s (%s)" % (i, spec["name"], node["type"]))
            for k, v in sorted(params.items()):
                lines.append("      %-24s %s" % (k, v))
        self.artifact_text("commands.txt", "\n".join(lines) + "\n")
        self.log("Wrote commands.txt (%d steps)." % len(order))

    # -- record ------------------------------------------------------------
    def verdict(self):
        return compute_verdict(self)

    def record(self):
        return {
            "run_id": self.id,
            "study": self.study_id,
            "mode": self.mode,
            "label": self.display_label,
            "source_label": self.source_label,
            "status": self.status,
            "error": self.error,
            "started": self.started,
            "elapsed": round((self.finished or time.time()) - self.started, 2),
            "steps": self.steps,
            "thresholds": {k: (self.thresholds.get(k, (v or {}).get("default")))
                           for k, v in (self.cfg.get("thresholds") or {}).items()},
            "n_per_class": self.n_per_class if self.mode == "demo" else None,
            "demo_adjustments": self.demo_adjustments,
            "resolved_inputs": self.resolved_inputs,
            "validated_by": self.validated_by,
            "provenance": self.mode if self.mode in ("plan", "demo") else "full",
            "data_provenance": self.ctx.get("data_provenance", ""),
            "warnings": list(self.warnings),
            "reproducibility": study.reproducibility(),
            "verdict": self.verdict(),
            "artifacts": self._artifacts(),
        }

    def _artifacts(self):
        """Only collect an artifact if the step that produces it succeeded.

        Otherwise a skipped report step still 'produces' the repo's committed
        report, dated before the run existed.
        """
        produced_by = {
            "run_report.html": "report",
            "differential_methylation.tsv": "differential",
            "differential_with_mechanics.tsv": "direction_label",
            "candidate_biomarker_panel.tsv": "panel_select",
            "classifier_summary.json": "classifier",
            "cv_folds.tsv": "classifier",
            "qc_sample_missingness.tsv": "qc_filter",
        }
        ok_types = {s["type"] for s in self.steps if s["state"] == "done"}
        out = []
        for f in self.files():
            owner = produced_by.get(f["name"])
            if owner and owner not in ok_types:
                continue
            out.append(f)
        return out

    def _finish_record(self):
        try:
            rec = self.record()
            self.artifact_json("run_record.json", rec)
            append_history(rec)
        except Exception:
            pass
        # Charts and tables, written to disk so an earlier run can still be
        # opened after the server restarts. In-memory state does not survive,
        # and "your results are gone" is not an acceptable answer.
        try:
            if self.status == "done" and self.mode != "plan":
                self.artifact_json("results.json", self.results())
        except Exception:
            pass

    # -- UI snapshot -------------------------------------------------------
    def snapshot(self, since=0):
        payload = super().snapshot(since)
        payload.update({
            "mode": self.mode,
            "study": self.study_id,
            "label": self.display_label,
            "source_label": self.source_label,
            "steps": self.steps,
            "demo_adjustments": self.demo_adjustments,
            "resolved_inputs": self.resolved_inputs,
            "validated_by": self.validated_by,
            "waiting_behind": self.waiting_behind,
            "cancel_requested": self.cancel_requested,
            "cancel_outcome": self.cancel_outcome,
            "verdict": self.verdict(),
            "n_per_class": self.n_per_class if self.mode == "demo" else None,
            # Wall clock, not the sum of finished steps: a 15-minute step must
            # not display as 0m and read as a hang.
            "elapsed_wall": round((self.finished or time.time()) - self.started, 2),
        })
        if self.status in ("done", "error", "cancelled"):
            payload["artifacts"] = self._artifacts()
            payload["has_report"] = any(a["name"] == "run_report.html"
                                        for a in payload["artifacts"])
        return payload


# ---------------------------------------------------------------------------
# verdict - computed from the record, never typed
# ---------------------------------------------------------------------------

LEVELS = {
    "plan": "Plan only - nothing was executed.",
    "demo": "Rehearsal on a sample subset. Not a result.",
    "research-only": "Research use only. One or more conditions below limit what this supports.",
    "verified-research": "Full cohort, no limiting condition detected.",
}


def compute_verdict(run):
    cfg = run.cfg
    caveat = (cfg.get("verdict", {}).get("standing_caveat") or "").strip()
    reasons = []

    if run.mode == "plan":
        return {"level": "plan", "summary": LEVELS["plan"], "reasons": [], "caveat": caveat}

    data = cfg.get("data", {})
    user_data = bool(run.resolved_inputs.get("user_supplied"))
    if not user_data and "SIMULATED" in (data.get("provenance") or "").upper():
        reasons.append("The per-sample values in this cohort are simulated. "
                       "Per-probe group means for 500 reference probes are real; "
                       "every individual value is drawn, not measured.")
    if user_data:
        reasons.append("Run on files supplied by you. Nothing here has checked where they "
                       "came from, how they were normalized, or whether the groups are "
                       "balanced for anything other than what is listed in the sample table.")
    if not data.get("batch_columns") or not any(
            c in (run.resolved_inputs.get("batch_present") or []) for c in data.get("batch_columns", [])):
        reasons.append("No batch/slide/plate column, so batch confounding cannot be "
                       "assessed - not ruled out, unassessable.")
    if run.demo_adjustments:
        reasons.append("Parameters were adjusted for the subset: "
                       + "; ".join("%s %s->%s" % (a["param"], a["from"], a["to"])
                                   for a in run.demo_adjustments))
    if run.mode == "demo":
        return {"level": "demo", "summary": LEVELS["demo"], "reasons": reasons, "caveat": caveat}
    if run.status != "done":
        reasons.append("The run did not complete: %s" % (run.error or run.status))

    # The custom-dataset branch of load_data reads probe_annotation.tsv from a
    # hard-coded path inside the script; no step declares it as an input.
    reasons.append("Probe annotation is read from a path fixed inside load_data(), "
                   "not from a declared input - what it read cannot be verified from "
                   "the run record.")
    reasons.append("No independent validation cohort: the classifier is "
                   "cross-validated within this cohort only.")

    level = "research-only" if reasons else "verified-research"
    return {"level": level, "summary": LEVELS[level], "reasons": reasons, "caveat": caveat}


# ---------------------------------------------------------------------------
# registry + single-slot queue
# ---------------------------------------------------------------------------

_RUNS = {}
_LOCK = threading.Lock()
_SLOT = threading.Lock()
_ACTIVE = {"id": None}


def start_run(cfg, mode, opts):
    if mode not in MODES:
        raise ValueError("Unknown mode '%s'." % mode)
    if mode == "full" and not opts.get("validated_by"):
        raise ValueError("A Full run needs validated_by: the id of a demo run of this "
                         "study that finished successfully.")
    run = V2Run(cfg, mode, opts)
    with _LOCK:
        _RUNS[run.id] = run
    if _ACTIVE["id"]:
        run.waiting_behind = _ACTIVE["id"]
    threading.Thread(target=_serialised, args=(run,), name="v2-%s" % run.id,
                     daemon=True).start()
    return run


def _serialised(run):
    with _SLOT:
        if run.status == "cancelled":
            return
        _ACTIVE["id"] = run.id
        try:
            run.execute()
        finally:
            _ACTIVE["id"] = None


def get_run(run_id):
    with _LOCK:
        return _RUNS.get(run_id)


def active_run_id():
    return _ACTIVE["id"]


def list_runs(include_rehearsals=False, study_id=None):
    """Demo and plan runs are hidden unless the caller explicitly asks.

    A demo finishes and is instantly the newest run, so anything that opens
    "the latest run" would open the rehearsal.
    """
    with _LOCK:
        runs = list(_RUNS.values())
    runs.sort(key=lambda r: r.started, reverse=True)
    out = []
    for r in runs:
        if study_id and r.study_id != study_id:
            continue
        if r.mode in ("demo", "plan") and not include_rehearsals:
            continue
        out.append({
            "id": r.id, "label": r.display_label, "mode": r.mode,
            "status": r.status, "started": r.started,
            "elapsed": round((r.finished or time.time()) - r.started, 2),
            "verdict": r.verdict()["level"],
            "is_rehearsal": r.mode in ("demo", "plan"),
            "source_label": r.source_label,
        })
    return out


def successful_demo(study_id):
    with _LOCK:
        runs = list(_RUNS.values())
    demos = [r for r in runs
             if r.study_id == study_id and r.mode == "demo" and r.status == "done"]
    demos.sort(key=lambda r: r.started, reverse=True)
    return demos[0].id if demos else _history_demo(study_id)


# ---------------------------------------------------------------------------
# history -> measured estimates
# ---------------------------------------------------------------------------

def append_history(rec):
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    slim = {
        "run_id": rec["run_id"], "study": rec["study"], "mode": rec["mode"],
        "status": rec["status"], "started": rec["started"], "elapsed": rec["elapsed"],
        # keyed by NAME: inserting a step must not re-key historical timings
        "step_seconds": {s["name"]: s["seconds"] for s in rec["steps"]
                         if s.get("seconds") is not None},
    }
    with open(HISTORY, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(slim) + "\n")


def read_history(study_id=None, mode=None):
    if not HISTORY.is_file():
        return []
    out = []
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if study_id and rec.get("study") != study_id:
            continue
        if mode and rec.get("mode") != mode:
            continue
        out.append(rec)
    return out


def _history_demo(study_id):
    for rec in reversed(read_history(study_id, "demo")):
        if rec.get("status") == "done":
            return rec["run_id"]
    return None


def _median(values):
    values = sorted(v for v in values if isinstance(v, (int, float)))
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return round(values[mid], 2)
    return round((values[mid - 1] + values[mid]) / 2.0, 2)


def estimates(study_id, mode):
    """Median of this project's own completed runs in the SAME mode.

    Never averages a demo's timings with a full run's. No history returns
    null, and the UI says so, rather than showing a number nobody stands
    behind.
    """
    done = [r for r in read_history(study_id, mode) if r.get("status") == "done"]
    if not done:
        return {"basis": "none", "n_runs": 0, "total_seconds": None, "per_step": {}}
    per_step = {}
    names = {name for r in done for name in r.get("step_seconds", {})}
    for name in names:
        per_step[name] = _median([r["step_seconds"].get(name) for r in done])
    return {
        "basis": "median of %d completed %s run%s of this study"
                 % (len(done), mode, "" if len(done) == 1 else "s"),
        "n_runs": len(done),
        "total_seconds": _median([r.get("elapsed") for r in done]),
        "per_step": per_step,
    }
