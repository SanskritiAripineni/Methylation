"""Where the published study is read from.

Kept apart from dashboard/build.py on purpose: the builder should be
testable with fixtures, so it takes a reader and never touches a path.
"""
from __future__ import annotations

import csv
import json

from console_v2 import study

REF = study.ROOT / "data" / "reference"


def _cast(value):
    """TSV cells arrive as text. Numbers should come back as numbers, so the
    interface can format them - but an id like a probe name must stay text."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        f = float(value)
    except ValueError:
        return value
    return f if f == f else None            # NaN reads as "no value"


class Files:
    """.json(name) and .table(name), reading data/reference/."""

    def __init__(self, root=None):
        self.root = root or REF

    def json(self, name, default=None):
        path = self.root / name
        if not path.is_file():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return default

    def table(self, name, limit=None):
        """A TSV as a list of dicts. Returns [] when the file is not there -
        the builder turns that into a stated reason, not a crash."""
        path = self.root / name
        if not path.is_file():
            return []
        out = []
        with path.open(encoding="utf-8", newline="") as fh:
            for i, row in enumerate(csv.DictReader(fh, delimiter="\t")):
                if limit is not None and i >= limit:
                    break
                out.append({k: _cast(v) for k, v in row.items() if k})
        return out
