"""Local server for the locked MRKTechSolutions Methylation Version 7.

    python server/app_v7.py
    open http://127.0.0.1:8772/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import app as v1  # noqa: E402
import app_v6 as v6  # noqa: E402
from console_v7 import routes as v7_routes  # noqa: E402

SAVED_SAMPLE_RUN_ID = "20260731-062458-full-8217f9"
SAVED_SAMPLE_RUN = ROOT / "Results" / "BRCA_Sample_Run"
RUNS_DIR = ROOT / "runs"
PUBLISHED_FIGURES = ROOT.parent / "results" / "Figures"
PUBLISHED_FIGURE_NAMES = {"pca.png", "volcano.png"}


def restore_saved_sample_run(source=SAVED_SAMPLE_RUN, runs_dir=RUNS_DIR):
    """Make the bundled BRCA run selectable on fresh hosted instances.

    Generated runs are intentionally gitignored. The approved demonstration
    run is committed under Results/, so a new Render filesystem needs this
    small restoration step before history and dashboard routes can see it.
    Existing local or hosted runs are never overwritten.
    """
    source = Path(source)
    target = Path(runs_dir) / SAVED_SAMPLE_RUN_ID
    if (target / "run_record.json").is_file():
        return False
    if not (source / "run_record.json").is_file():
        return False
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, target / path.name)
    return True


class Handler(v6.Handler):
    server_version = "MethylationStudio/7.0"

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/studio-v7", "/studio-v7.html"):
            return self._file(v1.WEB / "studio-v7.html")
        figure_prefix = "/api/v7/published-figure/"
        if url.path.startswith(figure_prefix):
            name = url.path[len(figure_prefix):]
            if name not in PUBLISHED_FIGURE_NAMES:
                return self._error(404, "Unknown published-study figure.")
            return self._file(PUBLISHED_FIGURES / name)
        try:
            if v7_routes.handle_get(self, url.path, parse_qs(url.query)):
                return
        except Exception as exc:
            return self._error(500, "%s: %s" % (type(exc).__name__, exc))
        return super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        try:
            if v7_routes.handle_upload(self, url.path, self.headers, self.rfile):
                return
        except Exception as exc:
            return self._error(500, "%s: %s" % (type(exc).__name__, exc))

        if url.path.startswith(v7_routes.PREFIX):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError as exc:
                return self._error(400, "Bad JSON: %s" % exc)
            try:
                if v7_routes.handle_post(self, url.path, payload):
                    return
            except Exception as exc:
                return self._error(500, "%s: %s" % (type(exc).__name__, exc))
            return self._error(404, "Unknown v7 endpoint.")
        return super().do_POST()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8772)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if not (ROOT / "data" / "sample" / "sample_betas.tsv.gz").exists():
        print("Example data missing - building it now...")
        from engine import make_sample_data
        make_sample_data.main()

    restore_saved_sample_run()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    base = "http://%s:%d" % (args.host, args.port)
    print("\n  MRKTechSolutions Methylation Version 7 - locked hosting candidate")
    print("  open       %s/" % base)
    print("  version 6  %s/studio-v6.html" % base)
    print("  Ctrl-C to stop\n")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(base + "/")).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()
