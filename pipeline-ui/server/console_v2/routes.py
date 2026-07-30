"""HTTP routes for console-v2, mounted under /api/v2/.

`handle_get` / `handle_post` return True when they have answered the request.
Anything they do not recognise falls through to the frozen v1 handler.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import preview as preview_mod
from . import runs as runs_mod
from . import study

PREFIX = "/api/v2/"


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
# GET
# ---------------------------------------------------------------------------

def handle_get(h, route, query):
    if not route.startswith(PREFIX):
        return False
    rest = route[len(PREFIX):]

    if rest == "studies":
        h._json({"studies": study.list_studies()})
        return True

    if rest == "active":
        active = runs_mod.active_run_id()
        h._json({"active": active,
                 "run": runs_mod.get_run(active).snapshot(0) if active else None})
        return True

    if rest.startswith("studies/"):
        tail = rest[len("studies/"):]
        study_id, _, sub = tail.partition("/")
        try:
            cfg = study.load_config(study_id)
        except Exception as exc:
            h._error(404, str(exc))
            return True

        if sub == "":
            h._json({
                "id": cfg["id"], "label": cfg.get("label"), "tissue": cfg.get("tissue"),
                "consumes": cfg.get("consumes", {}),
                "data": {k: v for k, v in (cfg.get("data") or {}).items()},
                "thresholds": cfg.get("thresholds", {}),
                "not_applicable": cfg.get("not_applicable", {}),
                "demo": cfg.get("demo", {}),
                "steps": cfg.get("steps", []),
                "standing_caveat": (cfg.get("verdict", {}).get("standing_caveat") or "").strip(),
                "reproducibility": study.reproducibility(),
            })
            return True

        if sub == "preview":
            mode = _q(query, "mode", "demo")
            try:
                h._json(preview_mod.preview(
                    study_id, mode,
                    thresholds=_json_arg(query, "thresholds"),
                    n_per_class=_q(query, "n_per_class"),
                    paths=_json_arg(query, "paths")))
            except Exception as exc:
                h._error(500, "%s: %s" % (type(exc).__name__, exc))
            return True

        if sub == "threshold-effect":
            try:
                h._json(preview_mod.threshold_effect(
                    study_id, _q(query, "key"), _q(query, "value"), _q(query, "run")))
            except Exception as exc:
                h._json({"available": False, "reason": "%s: %s" % (type(exc).__name__, exc)})
            return True

        h._error(404, "Unknown study route.")
        return True

    if rest == "runs":
        h._json({"runs": runs_mod.list_runs(
            include_rehearsals=_q(query, "include_rehearsals") == "1",
            study_id=_q(query, "study"))})
        return True

    if rest.startswith("runs/"):
        run_id, _, sub = rest[len("runs/"):].partition("/")
        run = runs_mod.get_run(run_id)
        if run is None:
            h._error(404, "Unknown run id. Runs are held in memory; restarting the "
                          "server clears them.")
            return True

        if sub in ("", "status"):
            h._json(run.snapshot(int(_q(query, "since", "0") or 0)))
            return True

        if sub == "log":
            since = int(_q(query, "since", "0") or 0)
            h._json({"lines": run.logs[since:], "count": len(run.logs),
                     "status": run.status})
            return True

        if sub == "record":
            h._json(run.record())
            return True

        if sub == "download":
            h._file(run.bundle(), download_name="methylation_%s.zip" % run.id)
            return True

        if sub == "file":
            name = _q(query, "path", "")
            target = h._safe_join(run.dir, name)
            if target is None:
                h._error(400, "Invalid path.")
                return True
            inline = _q(query, "inline") == "1"
            h._file(target, download_name=None if inline else Path(name).name)
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

    if rest == "inputs/inspect":
        try:
            h._json(study.inspect_inputs(
                matrix_path=payload.get("matrix_path"),
                manifest_path=payload.get("manifest_path"),
                annotation_path=payload.get("annotation_path"),
                study_id=payload.get("study", "brca_sim")))
        except Exception as exc:
            h._error(400, "%s: %s" % (type(exc).__name__, exc))
        return True

    if rest == "runs":
        study_id = payload.get("study", "brca_sim")
        mode = payload.get("mode", "demo")
        try:
            cfg = study.load_config(study_id)
        except Exception as exc:
            h._error(404, str(exc))
            return True

        # Re-run the gate server-side. A UI that enables Start is not authority.
        try:
            gate = preview_mod.preview(study_id, mode,
                                       thresholds=payload.get("thresholds") or {},
                                       n_per_class=payload.get("n_per_class"),
                                       paths=payload.get("paths") or {})
        except Exception as exc:
            h._error(500, "Readiness check failed: %s: %s" % (type(exc).__name__, exc))
            return True
        if not gate["can_start"]:
            h._error(409, "Blocked by: %s" % ", ".join(gate["blocking"]))
            return True

        opts = dict(payload)
        if mode == "full" and not opts.get("validated_by"):
            opts["validated_by"] = runs_mod.successful_demo(study_id)
        try:
            run = runs_mod.start_run(cfg, mode, opts)
        except Exception as exc:
            h._error(400, str(exc))
            return True
        h._json({"run_id": run.id, "mode": run.mode,
                 "waiting_behind": run.waiting_behind})
        return True

    if rest.startswith("runs/") and rest.endswith("/cancel"):
        run_id = rest[len("runs/"):-len("/cancel")]
        run = runs_mod.get_run(run_id)
        if run is None:
            h._error(404, "Unknown run id.")
            return True
        h._json({"outcome": run.request_cancel(), "status": run.status})
        return True

    return False


def handle_upload(h, route, headers, rfile):
    """Raw-body upload: the size cap is enforced before anything is read."""
    if route != PREFIX + "uploads/inspect":
        return False
    length = int(headers.get("Content-Length") or 0)
    if length > study.MAX_UPLOAD_BYTES:
        h._error(413, study.upload_limit_message(length))
        return True
    name = headers.get("X-Filename", "upload.tsv")
    tmp = study.ROOT / "runs" / ".uploads"
    tmp.mkdir(parents=True, exist_ok=True)
    target = tmp / Path(name).name
    target.write_bytes(rfile.read(length))
    h._json({"stored": str(target), "table": study.sniff_table(target),
             "note": "Parsed server-side. Nothing here is added to a run until you "
                     "point a source at it."})
    return True
