"""Expose the v4 behavior under the v5 API prefix.

The dashboard contract is shared on purpose: a report source, its charts and
its downloads must continue to come from one response.
"""
from __future__ import annotations

from console_v4 import routes as v4

PREFIX = "/api/v5/"


def _v4(route):
    return v4.PREFIX + route[len(PREFIX):]


def handle_get(h, route, query):
    if not route.startswith(PREFIX):
        return False
    return v4.handle_get(h, _v4(route), query)


def handle_post(h, route, payload):
    if not route.startswith(PREFIX):
        return False
    return v4.handle_post(h, _v4(route), payload)


def handle_upload(h, route, headers, rfile):
    if not route.startswith(PREFIX):
        return False
    return v4.handle_upload(h, _v4(route), headers, rfile)

