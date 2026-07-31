"""V6 API: v5 behavior plus a local-folder workspace source."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from console_v3 import routes as v3
from console_v3 import workspace
from console_v5 import routes as v5

PREFIX = "/api/v6/"
SUPPORTED = {".tsv", ".csv", ".txt", ".gz"}
SAMPLE_RESULTS = Path(__file__).resolve().parents[2] / "Results" / "BRCA_Sample_Run"

RESULT_NOTES = {
    "README.md": "Guide to these files and the simulated-data warning.",
    "bundle.zip": "Every BRCA sample-run output in one download.",
    "run_report.html": "Complete one-page report with charts and explanations.",
    "candidate_biomarker_panel.tsv": "The 100-site candidate biomarker panel.",
    "differential_methylation.tsv": "Results for every CpG site tested.",
    "differential_with_mechanics.tsv": "Effect-filtered sites with gene interpretation.",
    "classifier_summary.json": "Internal classifier and cross-validation summary.",
    "cv_folds.tsv": "Fold-by-fold internal cross-validation scores.",
    "qc_sample_missingness.tsv": "Sample-level quality-control results.",
    "results.json": "Machine-readable data used to build the report.",
    "run_record.json": "Run provenance, settings, caveats and headline counts.",
    "run_manifest.json": "Manifest of the files used and produced by the run.",
    "run_log.txt": "Plain-text execution log for all pipeline steps.",
}

RESULT_ORDER = [
    "run_report.html", "bundle.zip", "README.md",
    "candidate_biomarker_panel.tsv", "differential_methylation.tsv",
    "differential_with_mechanics.tsv", "classifier_summary.json",
    "cv_folds.tsv", "qc_sample_missingness.tsv", "results.json",
    "run_record.json", "run_manifest.json", "run_log.txt",
]


def _v5(route):
    return v5.PREFIX + route[len(PREFIX):]


def _result_url(name, inline=False):
    from urllib.parse import quote
    return "%s/sample-results/file?path=%s%s" % (
        PREFIX.rstrip("/"), quote(name), "&inline=1" if inline else "")


def _sample_results():
    """Describe the saved BRCA demonstration package shown in Runs & Files."""
    if not SAMPLE_RESULTS.is_dir():
        return {"state": "unavailable", "reason": "The BRCA sample-results folder is missing."}

    files = [p for p in SAMPLE_RESULTS.iterdir() if p.is_file()]
    order = {name: i for i, name in enumerate(RESULT_ORDER)}
    files.sort(key=lambda p: (order.get(p.name, len(order)), p.name.lower()))
    items = []
    for path in files:
        note = RESULT_NOTES.get(path.name)
        if note is None and path.name.startswith("enrichment_"):
            note = "Pathway-enrichment output for this BRCA sample run."
        items.append({
            "name": path.name,
            "size": path.stat().st_size,
            "note": note or "Output produced by the BRCA sample run.",
            "url": _result_url(path.name),
        })
    return {
        "state": "ok",
        "run_id": "20260731-062458-full-8217f9",
        "title": "BRCA breast tumor vs normal sample results",
        "subtitle": "%d attached files from the complete bundled-cohort run." % len(items),
        "report_url": _result_url("run_report.html", inline=True),
        "bundle_url": _result_url("bundle.zip"),
        "downloads": {"state": "ok", "items": items},
    }


def _local_folder(raw_path):
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("Enter a folder path.")
    folder = Path(raw_path.strip()).expanduser().resolve(strict=True)
    if not folder.is_dir():
        raise ValueError("That path is not a folder.")

    workspace_dir = workspace.WORKSPACE.resolve()
    if folder == workspace_dir or workspace_dir in folder.parents:
        raise ValueError("Choose the folder that contains your source data, not the project workspace.")

    candidates = [p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in SUPPORTED][:50]
    if not candidates:
        raise ValueError("No TSV, CSV, TXT or GZ files were found in that folder.")

    identified = [(source, workspace.identify(source)) for source in candidates]
    usable = [(source, info) for source, info in identified if info.get("ok")]
    if not usable:
        details = "; ".join("%s: %s" % (i.get("name"), i.get("label"))
                            for _, i in identified[:4])
        raise ValueError("The files were found but none was recognised as methylation data, "
                         "a sample list or site information. %s" % details)

    workspace.clear()
    workspace.WORKSPACE.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for source, _ in usable:
            target = workspace.WORKSPACE / workspace._safe_name(source.name)
            if target.exists():
                target.unlink()
            try:
                os.link(source, target)
            except OSError:
                try:
                    target.symlink_to(source)
                except OSError:
                    if source.stat().st_size > workspace.MAX_BYTES:
                        raise ValueError("%s is too large to copy and this drive cannot link it. "
                                         "Move the folder onto the same drive as the project."
                                         % source.name)
                    shutil.copy2(source, target)
            created.append(target)
    except Exception:
        workspace.clear()
        raise

    ws = workspace.current()
    ready = workspace.readiness(ws["roles"])
    _, ingest_report = v3._run_paths("brca_sim")
    return {"source_path": str(folder), "linked": len(created),
            "workspace": ws, "readiness": ready, "ingest": ingest_report}


def handle_get(h, route, query):
    if not route.startswith(PREFIX):
        return False
    if route == PREFIX + "sample-results":
        h._json(_sample_results())
        return True
    if route == PREFIX + "sample-results/file":
        name = v3._q(query, "path", "")
        target = h._safe_join(SAMPLE_RESULTS, name)
        if target is None:
            h._error(400, "Invalid result-file path.")
            return True
        inline = v3._q(query, "inline", "0") == "1"
        h._file(target, download_name=None if inline else Path(name).name)
        return True
    return v5.handle_get(h, _v5(route), query)


def handle_post(h, route, payload):
    if not route.startswith(PREFIX):
        return False
    if route == PREFIX + "workspace/local":
        try:
            result = _local_folder(payload.get("path"))
        except (OSError, ValueError) as exc:
            h._error(400, str(exc))
            return True
        h._json(result)
        return True
    return v5.handle_post(h, _v5(route), payload)


def handle_upload(h, route, headers, rfile):
    if not route.startswith(PREFIX):
        return False
    return v5.handle_upload(h, _v5(route), headers, rfile)
