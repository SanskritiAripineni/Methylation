"""V7 API: a version-locked surface over the completed V6 behavior."""
from __future__ import annotations

from console_v6 import routes as v6

PREFIX = "/api/v7/"


def _v6(route):
    return v6.PREFIX + route[len(PREFIX):]


def _rewrite_urls(value):
    """Keep saved-result links on the V7 API surface."""
    if isinstance(value, str):
        return value.replace(v6.PREFIX, PREFIX)
    if isinstance(value, list):
        return [_rewrite_urls(item) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite_urls(item) for key, item in value.items()}
    return value


def handle_get(h, route, query):
    if not route.startswith(PREFIX):
        return False
    if route == PREFIX + "sample-results":
        h._json(_rewrite_urls(v6._sample_results()))
        return True
    return v6.handle_get(h, _v6(route), query)


def handle_post(h, route, payload):
    if not route.startswith(PREFIX):
        return False
    return v6.handle_post(h, _v6(route), payload)


def handle_upload(h, route, headers, rfile):
    if not route.startswith(PREFIX):
        return False
    return v6.handle_upload(h, _v6(route), headers, rfile)
