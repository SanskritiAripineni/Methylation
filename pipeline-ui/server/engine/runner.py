"""Graph executor: topologically orders the blocks and runs them in sequence."""
from __future__ import annotations

import json
import shutil
import threading
import time
import traceback
import uuid
import zipfile
from collections import deque
from pathlib import Path

import pandas as pd

from . import catalog
from .nodes import REGISTRY

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"


class Run:
    """One execution of one graph. Holds logs, artifacts and the shared context."""

    def __init__(self, graph, label=""):
        self.id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.graph = graph
        self.label = label or "run"
        self.dir = RUNS_DIR / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.logs = []
        self.warnings = []
        self.stats = []
        self.node_status = {}
        self.status = "queued"
        self.error = None
        self.started = time.time()
        self.finished = None
        self.ctx = {}
        self._lock = threading.Lock()
        self._current = None

    # -- logging -----------------------------------------------------------
    def log(self, message, level="info"):
        with self._lock:
            self.logs.append({
                "t": round(time.time() - self.started, 2),
                "node": self._current,
                "level": level,
                "message": str(message),
            })

    def warn(self, message):
        with self._lock:
            self.warnings.append(str(message))
        self.log(message, level="warn")

    def stat(self, label, value):
        with self._lock:
            self.stats.append({"label": label, "value": value})

    # -- artifacts ---------------------------------------------------------
    def artifact_frame(self, name, frame, max_rows=50000):
        path = self.dir / name
        if isinstance(frame, pd.DataFrame) and len(frame) > max_rows:
            frame = frame.head(max_rows)
        frame.to_csv(path, sep="\t", index=False)
        return path

    def artifact_json(self, name, payload):
        path = self.dir / name
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path

    def artifact_text(self, name, body):
        path = self.dir / name
        path.write_text(body, encoding="utf-8")
        return path

    def files(self):
        out = []
        for p in sorted(self.dir.rglob("*")):
            if p.is_file() and p.name != "bundle.zip":
                out.append({"name": str(p.relative_to(self.dir)).replace("\\", "/"),
                            "size": p.stat().st_size})
        return out

    def bundle(self):
        zip_path = self.dir / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in self.files():
                z.write(self.dir / f["name"], f["name"])
        return zip_path

    # -- state for the UI --------------------------------------------------
    def snapshot(self, since=0):
        with self._lock:
            logs = self.logs[since:]
        payload = {
            "id": self.id,
            "status": self.status,
            "error": self.error,
            "logs": logs,
            "log_count": len(self.logs),
            "warnings": list(self.warnings),
            "stats": list(self.stats),
            "node_status": dict(self.node_status),
            "elapsed": round((self.finished or time.time()) - self.started, 2),
        }
        if self.status in ("done", "error"):
            payload["results"] = self.results()
        return payload

    def results(self):
        ctx = self.ctx
        res = {
            "run_name": ctx.get("run_name", ""),
            "data_provenance": ctx.get("data_provenance", ""),
            "qc": ctx.get("qc", {}),
            "volcano": ctx.get("volcano"),
            "roc": ctx.get("roc"),
            "model": ctx.get("model"),
            "mechanics_counts": ctx.get("mechanics_counts", {}),
            "region_mix": ctx.get("region_mix", {}),
            "enrichment_top": ctx.get("enrichment_top", []),
            "enrichment_null": ctx.get("enrichment_null", False),
            "report": ctx.get("report_path"),
            "files": self.files(),
            "stats": list(self.stats),
        }
        st = ctx.get("stats")
        if isinstance(st, pd.DataFrame) and len(st):
            cols = [c for c in ["probe_id", "gene", "chrom", "delta_beta", "abs_delta_beta",
                                "fdr", "direction", "functional_region",
                                "predicted_expression_effect"] if c in st.columns]
            top = st.sort_values("abs_delta_beta", ascending=False).head(25)[cols]
            res["top_markers"] = json.loads(top.to_json(orient="records"))
            res["top_marker_columns"] = cols
        panel = ctx.get("panel")
        if isinstance(panel, pd.DataFrame) and len(panel):
            cols = [c for c in ["panel_rank", "probe_id", "gene", "chrom", "delta_beta",
                                "fdr", "direction", "predicted_expression_effect"]
                    if c in panel.columns]
            res["panel"] = json.loads(panel.head(30)[cols].to_json(orient="records"))
            res["panel_columns"] = cols
        return res

    # -- execution ---------------------------------------------------------
    def execute(self):
        self.status = "running"
        try:
            order = topological_order(self.graph)
            if not order:
                raise ValueError("The canvas is empty - drag some blocks in first.")
            self.log("Executing %d blocks: %s" % (len(order), " -> ".join(n["type"] for n in order)))
            for node in order:
                fn = REGISTRY.get(node["type"])
                if fn is None:
                    self.warn("Unknown block type '%s' - skipped." % node["type"])
                    continue
                self._current = node["id"]
                self.node_status[node["id"]] = "running"
                params = catalog.merged_params(node["type"], node.get("params"))
                t0 = time.time()
                fn(self, params)
                self.node_status[node["id"]] = "done"
                self.log("%s finished in %.2fs" % (
                    catalog.NODES_BY_TYPE[node["type"]]["name"], time.time() - t0))
            self._current = None
            self.write_manifest(order)
            self.status = "done"
            self.log("Run complete.")
        except Exception as exc:  # surfaced verbatim in the UI log
            self.status = "error"
            self.error = "%s: %s" % (type(exc).__name__, exc)
            if self._current:
                self.node_status[self._current] = "error"
            self.log(self.error, level="error")
            self.log(traceback.format_exc(), level="error")
        finally:
            self.finished = time.time()
            try:
                self.bundle()
            except Exception:
                pass

    def write_manifest(self, order):
        manifest = {
            "run_id": self.id,
            "label": self.label,
            "status": self.status,
            "elapsed_seconds": round(time.time() - self.started, 2),
            "data_provenance": self.ctx.get("data_provenance", ""),
            "blocks": [
                {
                    "id": n["id"],
                    "type": n["type"],
                    "name": catalog.NODES_BY_TYPE[n["type"]]["name"],
                    "parameters": catalog.merged_params(n["type"], n.get("params")),
                }
                for n in order
            ],
            "edges": self.graph.get("edges", []),
            "headline_stats": self.stats,
            "warnings": self.warnings,
        }
        self.artifact_json("run_manifest.json", manifest)
        self.artifact_text("run_log.txt", "\n".join(
            "[%6.2fs] %-5s %s" % (l["t"], l["level"].upper(), l["message"]) for l in self.logs))


def topological_order(graph):
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = [e for e in graph.get("edges", [])
             if e.get("from") in nodes and e.get("to") in nodes]
    indeg = {nid: 0 for nid in nodes}
    adj = {nid: [] for nid in nodes}
    for e in edges:
        adj[e["from"]].append(e["to"])
        indeg[e["to"]] += 1

    queue = deque([nid for nid, d in indeg.items() if d == 0])
    order = []
    while queue:
        nid = queue.popleft()
        order.append(nodes[nid])
        for nxt in adj[nid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(nodes):
        raise ValueError("The graph contains a cycle - remove a connection and retry.")
    return order


# ---------------------------------------------------------------------------
# Registry of runs held in memory (prototype scope: single process)
# ---------------------------------------------------------------------------

_RUNS = {}
_RUNS_LOCK = threading.Lock()


def start_run(graph, label=""):
    run = Run(graph, label)
    with _RUNS_LOCK:
        _RUNS[run.id] = run
    thread = threading.Thread(target=run.execute, name="run-%s" % run.id, daemon=True)
    thread.start()
    return run


def get_run(run_id):
    with _RUNS_LOCK:
        return _RUNS.get(run_id)


def list_runs():
    with _RUNS_LOCK:
        runs = list(_RUNS.values())
    runs.sort(key=lambda r: r.started, reverse=True)
    return [{"id": r.id, "label": r.label, "status": r.status,
             "started": r.started, "elapsed": round((r.finished or time.time()) - r.started, 2)}
            for r in runs]


def clear_old_runs(keep=25):
    """Keep the runs directory from growing without bound."""
    if not RUNS_DIR.exists():
        return
    dirs = sorted([d for d in RUNS_DIR.iterdir() if d.is_dir()], key=lambda d: d.name, reverse=True)
    for d in dirs[keep:]:
        shutil.rmtree(d, ignore_errors=True)
