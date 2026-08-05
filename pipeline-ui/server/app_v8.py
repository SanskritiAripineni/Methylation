"""Server for MRKTechSolutions Methylation Version 8.

    python server/app_v8.py
    open http://127.0.0.1:8773/

Version 7 is untouched and still runs, on its own port, from its own files:

    python server/app_v7.py          # http://127.0.0.1:8772/

A V8 server also serves V7's page unchanged at /studio-v7.html, the same way
V7 serves V6. Nothing in this file writes to a V7 file.

What V8 fixes:

  * The Runs tab no longer blanks. Selecting a run that is already loaded is
    drawn from what the page already has instead of being torn down and
    refetched. See web/studio-v8.js.

  * Run history stops resetting on its own, when the host gives it somewhere
    durable to write. See console_v8/store.py.

  * Upload & Settings is a collapsible sidebar rather than a fourth page.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import app as v1  # noqa: E402
import app_v7 as v7  # noqa: E402
from console_v2 import runs as runs_mod  # noqa: E402
from console_v8 import routes as v8_routes  # noqa: E402
from console_v8 import store  # noqa: E402
from engine import runner  # noqa: E402


class Handler(v7.Handler):
    server_version = "MethylationStudio/8.0"

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/studio-v8", "/studio-v8.html"):
            return self._file(v1.WEB / "studio-v8.html")
        try:
            if v8_routes.handle_get(self, url.path, parse_qs(url.query)):
                return
        except Exception as exc:
            return self._error(500, "%s: %s" % (type(exc).__name__, exc))
        return super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        try:
            if v8_routes.handle_upload(self, url.path, self.headers, self.rfile):
                return
        except Exception as exc:
            return self._error(500, "%s: %s" % (type(exc).__name__, exc))

        if url.path.startswith(v8_routes.PREFIX):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError as exc:
                return self._error(400, "Bad JSON: %s" % exc)
            try:
                if v8_routes.handle_post(self, url.path, payload):
                    return
            except Exception as exc:
                return self._error(500, "%s: %s" % (type(exc).__name__, exc))
            return self._error(404, "Unknown v8 endpoint.")
        return super().do_POST()


def prepare():
    """Everything that has to be true before the first request. Also the test seam."""
    if not (ROOT / "data" / "sample" / "sample_betas.tsv.gz").exists():
        print("Example data missing - building it now...")
        from engine import make_sample_data
        make_sample_data.main()

    # Order matters: point the engine at durable storage first, so the restored
    # demonstration run lands there rather than on the disk that gets wiped.
    where = store.activate(runner, runs_mod)
    v7.restore_saved_sample_run(runs_dir=runner.RUNS_DIR)
    return where


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    # A managed host tells the process where to listen through the environment.
    # Defaulting to those values means the same command works locally and on
    # Render without a second start command to keep in step.
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT") or 8773))
    ap.add_argument("--host", default=os.environ.get("HOST")
                    or ("0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"))
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    where = prepare()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    base = "http://%s:%d" % ("127.0.0.1" if args.host == "0.0.0.0" else args.host, args.port)
    print("\n  MRKTechSolutions Methylation Version 8")
    print("  open       %s/" % base)
    print("  version 7  %s/studio-v7.html" % base)
    print("  runs       %s%s" % (where["path"],
                                 "" if where["durable"] else "  (temporary - see /api/v8/storage)"))
    if where["migrated"]:
        print("  moved      %d earlier run(s) into durable storage" % where["migrated"])
    print("  Ctrl-C to stop\n")
    if not args.no_browser and not os.environ.get("PORT"):
        threading.Timer(0.8, lambda: webbrowser.open(base + "/")).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()
