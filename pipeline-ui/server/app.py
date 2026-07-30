"""Local web server for the methylation pipeline builder.

Standard library only (plus the scientific stack the engine needs). Start with:

    python server/app.py            # then open http://127.0.0.1:8765
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from engine import catalog, runner  # noqa: E402

WEB = ROOT / "web"
SITE = WEB / "site"
DATA = ROOT / "data"

mimetypes.add_type("text/html", ".html")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


class Handler(SimpleHTTPRequestHandler):
    server_version = "MethylationBuilder/1.0"

    # -- plumbing ----------------------------------------------------------
    def log_message(self, fmt, *args):
        if "/api/runs/" in (self.path or "") and "poll" in (self.path or ""):
            return
        sys.stderr.write("  %s\n" % (fmt % args))

    def _send(self, code, body, content_type="application/json; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, code=200):
        self._send(code, json.dumps(payload, default=str))

    def _error(self, code, message):
        self._json({"error": message}, code=code)

    def _file(self, path, download_name=None):
        path = Path(path)
        if not path.is_file():
            return self._error(404, "Not found: %s" % path.name)
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        extra = {}
        if download_name:
            extra["Content-Disposition"] = 'attachment; filename="%s"' % download_name
        self._send(200, path.read_bytes(), ctype, extra)

    @staticmethod
    def _safe_join(base, rel):
        """Resolve rel under base, refusing anything that escapes it."""
        target = (base / unquote(rel).lstrip("/")).resolve()
        base = base.resolve()
        if base != target and base not in target.parents:
            return None
        return target

    # -- routes ------------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        route = url.path
        query = parse_qs(url.query)

        if route in ("/", "/index.html"):
            return self._file(WEB / "index.html")

        if route == "/api/catalog":
            return self._json({
                "nodes": catalog.NODES,
                "default_graph": catalog.DEFAULT_GRAPH,
                "sample_info": self._sample_info(),
            })

        if route == "/api/runs":
            return self._json({"runs": runner.list_runs()})

        if route.startswith("/api/runs/"):
            rest = route[len("/api/runs/"):]
            run_id, _, tail = rest.partition("/")
            run = runner.get_run(run_id)
            if run is None:
                return self._error(404, "Unknown run id.")
            if tail in ("", "status"):
                since = int(query.get("since", ["0"])[0])
                return self._json(run.snapshot(since))
            if tail == "download":
                return self._file(run.bundle(), download_name="methylation_run_%s.zip" % run.id)
            if tail == "file":
                name = query.get("path", [""])[0]
                target = self._safe_join(run.dir, name)
                if target is None:
                    return self._error(400, "Invalid path.")
                inline = query.get("inline", ["0"])[0] == "1"
                return self._file(target, download_name=None if inline else Path(name).name)
            return self._error(404, "Unknown run route.")

        if route.startswith("/site/"):
            target = self._safe_join(SITE, route[len("/site/"):])
            if target is None:
                return self._error(400, "Invalid path.")
            return self._file(target)

        if route.startswith("/data/"):
            target = self._safe_join(DATA, route[len("/data/"):])
            if target is None:
                return self._error(400, "Invalid path.")
            return self._file(target)

        target = self._safe_join(WEB, route.lstrip("/"))
        if target is None:
            return self._error(400, "Invalid path.")
        return self._file(target)

    def do_POST(self):
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            return self._error(400, "Bad JSON: %s" % exc)

        if url.path == "/api/run":
            graph = payload.get("graph") or {}
            if not graph.get("nodes"):
                return self._error(400, "The canvas is empty - drag some blocks in first.")
            runner.clear_old_runs()
            run = runner.start_run(graph, payload.get("label", "run"))
            return self._json({"run_id": run.id})

        return self._error(404, "Unknown endpoint.")

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _sample_info():
        path = DATA / "sample" / "sample_summary.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if not (DATA / "sample" / "sample_betas.tsv.gz").exists():
        print("Sample cohort missing - building it now...")
        from engine import make_sample_data
        make_sample_data.main()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = "http://%s:%d/" % (args.host, args.port)
    print("\n  Methylation pipeline builder")
    print("  serving  %s" % url)
    print("  runs go to  %s" % (ROOT / "runs"))
    print("  Ctrl-C to stop\n")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()
