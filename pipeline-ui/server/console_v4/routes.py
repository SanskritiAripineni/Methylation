"""HTTP routes for the v4 studio, mounted under /api/v4/.

Only two things differ from v3, and everything else is handed straight to
console_v3.routes so the checks, the gate, the history and the upload path
stay exactly what they already were:

  GET /api/v4/dashboard?source=reference
  GET /api/v4/dashboard?source=run&id=<run_id>

      One request answers for the whole selection - the report to show, the
      numbers, every chart, and the file list. In v3 the report came from one
      object and the charts from a second fetch with no guard between them,
      so clicking two runs quickly left the header describing one run and the
      charts drawing another. There is now nothing to disagree: it is one
      response, and it carries the selection it was built for.

v3's own routes are untouched and still mounted at /api/v3/.
"""
from __future__ import annotations

from engine import runner

from console_v2 import runs as runs_mod
from console_v2 import study
from console_v3 import routes as v3

from dashboard import build, schema

from . import sources

PREFIX = "/api/v4/"

# Reused from v3 rather than restated, so the plain-language tier names cannot
# drift between the two interfaces.
TIERS = v3.TIERS


def _file_url(run_id, name, inline=False):
    from urllib.parse import quote
    return "/api/v4/runs/%s/file?path=%s%s" % (run_id, quote(name),
                                               "&inline=1" if inline else "")


def _run_dashboard(run_id, study_id):
    """The dashboard for one run, live or read back from disk."""
    cfg = study.load_config(study_id)
    run = runs_mod.get_run(run_id)

    if run is not None and run.status == "done":
        est = runs_mod.estimates(run.study_id, run.mode)
        snap = v3._decorate(run.snapshot(0), cfg, est)
        res = run.results()
        artifacts = snap.get("artifacts") or []
    else:
        rec = v3._archived(run_id)
        if rec is None:
            return None
        snap = {
            "id": rec.get("run_id", run_id),
            "label": rec.get("label"),
            "mode": rec.get("mode"),
            "tier_label": TIERS.get(rec.get("mode"), {}).get("label", rec.get("mode")),
            "thresholds": rec.get("thresholds") or {},
        }
        res = rec.get("results")
        artifacts = rec.get("artifacts") or []

    names = {a.get("name") for a in artifacts}
    report_url = _file_url(snap["id"], "run_report.html", inline=True) \
        if "run_report.html" in names else None

    files = [{"name": a.get("name"), "size": a.get("size"),
              "url": _file_url(snap["id"], a.get("name") or "")} for a in artifacts]
    bundle_url = "/api/v4/runs/%s/download" % snap["id"] \
        if (runner.RUNS_DIR / snap["id"] / "bundle.zip").is_file() or run is not None else None

    return build.from_run(res, snap, report_url=report_url,
                          files=files, bundle_url=bundle_url)


def handle_get(h, route, query):
    if not route.startswith(PREFIX):
        return False
    rest = route[len(PREFIX):]
    study_id = v3._q(query, "study", "brca_sim")

    if rest == "dashboard":
        source = v3._q(query, "source", "reference")
        if source == "reference":
            h._json(build.from_reference(sources.Files()))
            return True
        if source == "run":
            run_id = v3._q(query, "id", "")
            if not run_id:
                h._error(400, "Ask for a run by id: ?source=run&id=<run_id>")
                return True
            model = _run_dashboard(run_id, study_id)
            if model is None:
                h._error(404, "That run is not on disk any more.")
                return True
            h._json(model)
            return True
        h._error(400, "source must be 'reference' or 'run'.")
        return True

    if rest == "schema":
        # So the interface can refuse a payload it was not written against
        # instead of rendering half a dashboard.
        h._json({"schema": schema.SCHEMA_VERSION,
                 "sections": sorted(schema.SECTIONS),
                 "states": list(schema.STATES)})
        return True

    # Everything else is v3's, unchanged, answered under v3's own prefix.
    return v3.handle_get(h, v3.PREFIX + rest, query)


def handle_post(h, route, payload):
    if not route.startswith(PREFIX):
        return False
    return v3.handle_post(h, v3.PREFIX + route[len(PREFIX):], payload)


def handle_upload(h, route, headers, rfile):
    if route != PREFIX + "upload":
        return False
    return v3.handle_upload(h, v3.PREFIX + "upload", headers, rfile)
