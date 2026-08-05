"""V8 API: V7's behaviour, plus one new endpoint and one honest answer.

Everything V7 answers, V8 answers the same way — the dashboard contract, the
published-study view, the run history, uploads. Two things are added:

  GET /api/v8/storage

      Where finished runs are being kept and whether that place survives a
      restart. The Runs tab prints this. See console_v8/store.py for why.

  GET /api/v8/runs/<id>  (inherited, but now trustworthy for old runs)

      Unchanged in shape. It is listed here because the V8 interface stops
      re-selecting a run every time this endpoint reports "done", which is what
      made results flash and vanish. That fix is in the page, not the server;
      the endpoint is the thing it stopped over-reacting to.
"""
from __future__ import annotations

from console_v7 import routes as v7

from . import store

PREFIX = "/api/v8/"


def _v7(route):
    return v7.PREFIX + route[len(PREFIX):]


def _rewrite_urls(value):
    """Keep links the V8 page is given on the V8 surface."""
    if isinstance(value, str):
        return value.replace(v7.PREFIX, PREFIX)
    if isinstance(value, list):
        return [_rewrite_urls(item) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite_urls(item) for key, item in value.items()}
    return value


class _Capture:
    """Collect a delegated handler's JSON instead of writing it to the socket.

    The V6/V7 handlers take the request handler and call `_json` on it. To
    rewrite what they produced, V8 hands them a stand-in, keeps the payload,
    and sends the rewritten version itself. Anything that is not JSON — a file
    download, an error — goes straight through to the real handler.
    """

    def __init__(self, real):
        self._real = real
        self.payload = None
        self.sent = False

    def _json(self, obj, status=200):
        self.payload = obj
        self.status = status
        self.sent = True

    def __getattr__(self, name):
        return getattr(self._real, name)


def handle_get(h, route, query):
    if not route.startswith(PREFIX):
        return False

    if route == PREFIX + "storage":
        h._json(store.describe())
        return True

    # sample-results carries V7-prefixed URLs; move them onto /api/v8/ so the
    # V8 page never has to know which version produced a link.
    if route == PREFIX + "sample-results":
        capture = _Capture(h)
        if v7.handle_get(capture, _v7(route), query) and capture.sent:
            h._json(_rewrite_urls(capture.payload))
            return True
        return True

    return v7.handle_get(h, _v7(route), query)


def handle_post(h, route, payload):
    if not route.startswith(PREFIX):
        return False
    return v7.handle_post(h, _v7(route), payload)


def handle_upload(h, route, headers, rfile):
    if not route.startswith(PREFIX):
        return False
    return v7.handle_upload(h, _v7(route), headers, rfile)
