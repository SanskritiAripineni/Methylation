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


def _v5(route):
    return v5.PREFIX + route[len(PREFIX):]


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

