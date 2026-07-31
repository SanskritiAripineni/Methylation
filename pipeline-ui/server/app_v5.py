"""Local web server for Methylation Studio Version 5.

    python server/app_v5.py
    open http://127.0.0.1:8770/

Version 4 remains available at /studio-v4.html and through app_v4.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import app as v1  # noqa: E402
import app_v4 as v4  # noqa: E402
from console_v5 import routes as v5_routes  # noqa: E402


class Handler(v4.Handler):
    server_version = "MethylationStudio/5.0"

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/studio-v5", "/studio-v5.html"):
            return self._file(v1.WEB / "studio-v5.html")
        try:
            if v5_routes.handle_get(self, url.path, parse_qs(url.query)):
                return
        except Exception as exc:
            return self._error(500, "%s: %s" % (type(exc).__name__, exc))
        return super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        try:
            if v5_routes.handle_upload(self, url.path, self.headers, self.rfile):
                return
        except Exception as exc:
            return self._error(500, "%s: %s" % (type(exc).__name__, exc))

        if url.path.startswith(v5_routes.PREFIX):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError as exc:
                return self._error(400, "Bad JSON: %s" % exc)
            try:
                if v5_routes.handle_post(self, url.path, payload):
                    return
            except Exception as exc:
                return self._error(500, "%s: %s" % (type(exc).__name__, exc))
            return self._error(404, "Unknown v5 endpoint.")

        return super().do_POST()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if not (ROOT / "data" / "sample" / "sample_betas.tsv.gz").exists():
        print("Example data missing - building it now...")
        from engine import make_sample_data
        make_sample_data.main()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    base = "http://%s:%d" % (args.host, args.port)
    print("\n  Methylation Studio Version 5")
    print("  open       %s/" % base)
    print("  version 4  %s/studio-v4.html" % base)
    print("  runs go to %s" % (ROOT / "runs"))
    print("  Ctrl-C to stop\n")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(base + "/")).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()

