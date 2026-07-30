"""HTTP routes for the studio interface, mounted under /api/v3/."""
from __future__ import annotations

import json
import time
from pathlib import Path

from engine import runner

from console_v2 import preview as preview_mod
from console_v2 import runs as runs_mod
from console_v2 import study

from . import workspace

PREFIX = "/api/v3/"

# Plain names for the three tiers. The tier itself is unchanged - this is
# only what the buttons say.
TIERS = {
    "plan": {"label": "Check my files", "blurb": "Reads your files and checks every setting. "
                                                 "Runs no analysis. Takes seconds."},
    "demo": {"label": "Quick test run", "blurb": "Runs every step on a few samples so you can "
                                                 "see the whole thing work before committing."},
    "full": {"label": "Full analysis", "blurb": "The real result. Uses every sample."},
}


def _q(query, key, default=None):
    vals = query.get(key)
    return vals[0] if vals else default


def _json_arg(query, key):
    raw = _q(query, key)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# progress
# ---------------------------------------------------------------------------

def _progress(snap, est):
    """Step N of M, elapsed, and a measured time-left (or nothing at all)."""
    steps = snap.get("steps") or []
    total = len(steps)
    done = sum(1 for s in steps if s["state"] in ("done", "skipped"))
    running = next((i for i, s in enumerate(steps) if s["state"] == "running"), None)
    index = (running + 1) if running is not None else done

    per_step = (est or {}).get("per_step") or {}
    remaining, basis = None, None
    if per_step:
        pending = [s for s in steps if s["state"] in ("pending", "running")]
        known = [per_step[s["name"]] for s in pending if per_step.get(s["name"]) is not None]
        if known and len(known) == len(pending):
            remaining = round(sum(known), 1)
            basis = est.get("basis")

    current = None
    if running is not None:
        current = steps[running]
    elif snap.get("status") in ("running", "queued") and steps:
        current = steps[min(done, total - 1)]

    return {
        "index": index, "total": total,
        "percent": round(100.0 * done / total) if total else 0,
        "current": current,
        "elapsed": snap.get("elapsed_wall"),
        "remaining": remaining,
        "remaining_basis": basis,
        "remaining_note": None if remaining is not None else
        "No time estimate yet - this project has no finished run of this kind to measure.",
    }


def _friendly_steps(cfg, steps):
    by_node = {s["node"]: s for s in cfg.get("steps", [])}
    out = []
    for s in steps or []:
        meta = by_node.get(s["node"], {})
        item = dict(s)
        item["friendly"] = meta.get("friendly") or s["name"]
        item["plain"] = meta.get("plain") or ""
        out.append(item)
    return out


def _decorate(snap, cfg, est):
    snap = dict(snap)
    snap["steps"] = _friendly_steps(cfg, snap.get("steps"))
    snap["progress"] = _progress(snap, est)
    snap["tier_label"] = TIERS.get(snap.get("mode"), {}).get("label", snap.get("mode"))
    return snap


# ---------------------------------------------------------------------------
# history, read from disk so it survives a restart
# ---------------------------------------------------------------------------

def history(include_tests=True):
    out = []
    if not runner.RUNS_DIR.exists():
        return out
    for d in sorted(runner.RUNS_DIR.iterdir(), reverse=True):
        rec_path = d / "run_record.json"
        if not d.is_dir() or not rec_path.is_file():
            continue
        try:
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rec.get("mode") in ("demo", "plan") and not include_tests:
            continue
        out.append({
            "id": rec.get("run_id", d.name),
            "label": rec.get("label") or d.name,
            "mode": rec.get("mode"),
            "tier_label": TIERS.get(rec.get("mode"), {}).get("label", rec.get("mode")),
            "status": rec.get("status"),
            "started": rec.get("started"),
            "when": time.strftime("%d %b %Y, %H:%M", time.localtime(rec.get("started") or 0)),
            "elapsed": rec.get("elapsed"),
            "verdict": (rec.get("verdict") or {}).get("level"),
            "is_test": rec.get("mode") in ("demo", "plan"),
            "has_report": (d / "run_report.html").is_file(),
            "has_results": (d / "results.json").is_file(),
            "source_label": rec.get("source_label") or "",
            "thresholds": rec.get("thresholds") or {},
        })
    return out


def _archived(run_id):
    """A finished run read back from disk (the in-memory object may be gone)."""
    d = runner.RUNS_DIR / run_id
    rec_path = d / "run_record.json"
    if not rec_path.is_file():
        return None
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    res_path = d / "results.json"
    rec["results"] = json.loads(res_path.read_text(encoding="utf-8")) if res_path.is_file() else None
    rec["files"] = rec.get("artifacts") or []
    return rec


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------

def handle_get(h, route, query):
    if not route.startswith(PREFIX):
        return False
    rest = route[len(PREFIX):]
    study_id = _q(query, "study", "brca_sim")

    if rest == "setup":
        cfg = study.load_config(study_id)
        ws = workspace.current()
        h._json({
            "study": {"id": cfg["id"], "label": cfg.get("label"), "tissue": cfg.get("tissue")},
            "example": {
                "label": "Example data (breast tumour vs normal)",
                "blurb": "130 samples already bundled with this project. Good for learning the "
                         "interface. The per-sample values in it are simulated, so it is not a "
                         "source of real findings.",
                "n_samples": 130,
            },
            "presets": cfg.get("presets", []),
            "thresholds": cfg.get("thresholds", {}),
            "steps": [{"node": s["node"], "friendly": s.get("friendly", s["name"]),
                       "plain": s.get("plain", ""), "name": s["name"]}
                      for s in cfg.get("steps", [])],
            "tiers": TIERS,
            "workspace": ws,
            "readiness": workspace.readiness(ws["roles"]),
            "standing_caveat": (cfg.get("verdict", {}).get("standing_caveat") or "").strip(),
        })
        return True

    if rest == "workspace":
        ws = workspace.current()
        h._json({"workspace": ws, "readiness": workspace.readiness(ws["roles"])})
        return True

    if rest == "history":
        h._json({"runs": history(include_tests=_q(query, "include_tests", "1") == "1")})
        return True

    if rest == "check":
        # One sentence, plus the full v2 check list for anyone who wants it.
        mode = _q(query, "mode", "demo")
        try:
            p = preview_mod.preview(study_id, mode,
                                    thresholds=_json_arg(query, "thresholds"),
                                    n_per_class=_q(query, "n_per_class"),
                                    paths=_json_arg(query, "paths"))
        except Exception as exc:
            h._json({"ok": False, "headline": "Could not check the inputs.",
                     "detail": "%s: %s" % (type(exc).__name__, exc), "checks": []})
            return True
        fails = [c for c in p["checks"] if c["state"] == "fail"]
        warns = [c for c in p["checks"] if c["state"] == "warn"]
        if fails:
            headline = fails[0]["detail"].split("\n")[0]
        elif warns:
            headline = "Good to go. %d thing%s worth knowing about — see the details." % (
                len(warns), "" if len(warns) == 1 else "s")
        else:
            headline = "Everything checks out."
        h._json({
            "ok": p["can_start"], "headline": headline,
            "fix": fails[0]["fix"] if fails else "",
            "checks": p["checks"], "warn_count": len(warns),
            "estimate": p["estimates"], "steps": p["steps"],
        })
        return True

    if rest.startswith("runs/"):
        run_id, _, sub = rest[len("runs/"):].partition("/")
        cfg = study.load_config(study_id)
        run = runs_mod.get_run(run_id)

        if sub in ("", "status"):
            if run is not None:
                est = runs_mod.estimates(run.study_id, run.mode)
                h._json(_decorate(run.snapshot(int(_q(query, "since", "0") or 0)), cfg, est))
                return True
            rec = _archived(run_id)
            if rec is None:
                h._error(404, "That run is not on disk any more.")
                return True
            est = runs_mod.estimates(rec.get("study", study_id), rec.get("mode", "full"))
            snap = {
                "id": rec["run_id"], "status": rec["status"], "mode": rec["mode"],
                "label": rec["label"], "steps": rec["steps"], "logs": [], "log_count": 0,
                "elapsed_wall": rec["elapsed"], "verdict": rec["verdict"],
                "artifacts": rec.get("artifacts") or [], "results": rec.get("results"),
                "source_label": rec.get("source_label", ""),
                "demo_adjustments": rec.get("demo_adjustments") or [],
                "has_report": any(a["name"] == "run_report.html"
                                  for a in (rec.get("artifacts") or [])),
                "archived": True,
            }
            h._json(_decorate(snap, cfg, est))
            return True

        if sub == "results":
            if run is not None and run.status == "done":
                h._json(run.results())
                return True
            rec = _archived(run_id)
            if rec and rec.get("results"):
                h._json(rec["results"])
                return True
            h._error(404, "No saved results for that run.")
            return True

        if sub == "log":
            since = int(_q(query, "since", "0") or 0)
            if run is not None:
                h._json({"lines": run.logs[since:], "count": len(run.logs), "status": run.status})
                return True
            path = runner.RUNS_DIR / run_id / "run_log.txt"
            if path.is_file():
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                h._json({"lines": [{"t": 0, "level": "info", "message": l} for l in lines[since:]],
                         "count": len(lines), "status": "done"})
                return True
            h._error(404, "No log for that run.")
            return True

        if sub == "download":
            if run is not None:
                h._file(run.bundle(), download_name="methylation_%s.zip" % run.id)
                return True
            path = runner.RUNS_DIR / run_id / "bundle.zip"
            if path.is_file():
                h._file(path, download_name="methylation_%s.zip" % run_id)
                return True
            h._error(404, "No download bundle for that run.")
            return True

        if sub == "file":
            name = _q(query, "path", "")
            base = run.dir if run is not None else (runner.RUNS_DIR / run_id)
            target = h._safe_join(base, name)
            if target is None:
                h._error(400, "Invalid path.")
                return True
            h._file(target, download_name=None if _q(query, "inline") == "1" else Path(name).name)
            return True

        h._error(404, "Unknown run route.")
        return True

    return False


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------

def handle_post(h, route, payload):
    if not route.startswith(PREFIX):
        return False
    rest = route[len(PREFIX):]

    if rest == "workspace/clear":
        ws = workspace.clear()
        h._json({"workspace": ws, "readiness": workspace.readiness(ws["roles"])})
        return True

    if rest == "runs":
        study_id = payload.get("study", "brca_sim")
        mode = payload.get("mode", "demo")
        use_example = bool(payload.get("use_example"))
        cfg = study.load_config(study_id)

        paths = {}
        if not use_example:
            roles = workspace.current()["roles"]
            ready = workspace.readiness(roles)
            if not ready["ready"]:
                h._error(400, ready["message"])
                return True
            paths = {"matrix": roles.get("matrix"), "manifest": roles.get("manifest"),
                     "annotation": roles.get("annotation")}

        try:
            gate = preview_mod.preview(study_id, mode,
                                       thresholds=payload.get("thresholds") or {},
                                       n_per_class=payload.get("n_per_class"),
                                       paths=paths)
        except Exception as exc:
            h._error(500, "Could not check the inputs: %s" % exc)
            return True
        if not gate["can_start"]:
            blocking = [c for c in gate["checks"] if c["state"] == "fail"]
            h._error(409, blocking[0]["detail"].split("\n")[0] if blocking
                     else "Blocked: %s" % ", ".join(gate["blocking"]))
            return True

        opts = dict(payload)
        opts["paths"] = paths
        opts.setdefault("source_label",
                        "example data" if use_example else "files you dropped in")
        if mode == "full" and not opts.get("validated_by"):
            opts["validated_by"] = runs_mod.successful_demo(study_id)
        try:
            run = runs_mod.start_run(cfg, mode, opts)
        except Exception as exc:
            h._error(400, str(exc))
            return True
        h._json({"run_id": run.id, "mode": run.mode, "waiting_behind": run.waiting_behind})
        return True

    if rest.startswith("runs/") and rest.endswith("/cancel"):
        run = runs_mod.get_run(rest[len("runs/"):-len("/cancel")])
        if run is None:
            h._error(404, "That run is not running any more.")
            return True
        h._json({"outcome": run.request_cancel(), "status": run.status})
        return True

    return False


def handle_upload(h, route, headers, rfile):
    if route != PREFIX + "upload":
        return False
    length = int(headers.get("Content-Length") or 0)
    if length > workspace.MAX_BYTES:
        h._error(413, "That file is %.0f MB. The limit through the browser is %d MB - for "
                      "anything bigger, put it on this machine and use the file path instead."
                 % (length / 1048576, workspace.MAX_BYTES // 1048576))
        return True
    name = headers.get("X-Filename", "dropped.tsv")
    stored = workspace.store(name, rfile.read(length))
    ws = workspace.current()
    h._json({"file": workspace.identify(stored), "workspace": ws,
             "readiness": workspace.readiness(ws["roles"])})
    return True
