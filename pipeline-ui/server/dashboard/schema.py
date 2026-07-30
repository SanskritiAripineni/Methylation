"""What a dashboard is allowed to contain, declared once.

Every panel on the Results tab is a *section*, and every section carries a
state as well as its data:

    ok           there is something to draw
    empty        the step ran and honestly produced nothing
    unavailable  this source cannot produce this panel at all

The three are not interchangeable, and collapsing them is how the old code
went wrong. "No pathway was enriched" is a finding. "The published bundle
does not store every probe, so no volcano can be drawn from it" is a
property of the source. "Nothing here" - the old behaviour of hiding the
panel - told the reader neither, and looked identical to a bug.

Sections never disappear. A section that is `empty` or `unavailable`
renders as itself, with `reason` shown in place of the chart.
"""
from __future__ import annotations

# Bump when a section is added or a field changes meaning. The interface
# checks this and refuses a payload it was not written against, rather than
# rendering half a dashboard.
SCHEMA_VERSION = 4

OK, EMPTY, UNAVAILABLE = "ok", "empty", "unavailable"
STATES = (OK, EMPTY, UNAVAILABLE)

# Every section the Results tab knows how to draw, and the fields each one
# carries. A builder that omits one gets the blank (unavailable) version;
# a builder that invents one fails the contract test.
SECTIONS = {
    "cards":       ("items",),
    "movers":      ("items",),
    "direction":   ("counts",),
    "validation":  ("folds", "model"),
    "roc":         ("fpr", "tpr"),
    "volcano":     ("x", "y", "probe"),
    "cohort":      ("subtypes", "tumor", "normal", "age"),
    "enrichment":  ("items",),
    "table":       ("rows", "columns"),
    "panel":       ("rows", "columns"),
    "thresholds":  ("used",),
    "report":      ("url", "variants"),
    # The Downloads tab is part of the same contract on purpose. It used to be
    # filled from a different object than the charts, which is exactly how it
    # ended up listing one run's files under another run's heading.
    "downloads":   ("items", "bundle_url"),
}

_EMPTY_FIELD = {
    "items": list, "counts": dict, "folds": list, "model": dict,
    "fpr": list, "tpr": list, "x": list, "y": list, "probe": list,
    "subtypes": dict, "tumor": lambda: None, "normal": lambda: None,
    "age": dict, "rows": list, "columns": list, "used": dict,
    "url": lambda: None, "variants": list, "bundle_url": lambda: None,
}

# The direction donut always has these three slices. A source that reports
# only the ones it saw gets the rest filled with 0 - pandas' value_counts
# drops a category with no members, and a missing key there means "none of
# these", not "not measured". `unavailable` is how "not measured" is said.
DIRECTION_SLICES = ("silencing", "activation", "ambiguous")


def _blank(name):
    fields = SECTIONS[name]
    out = {"state": UNAVAILABLE, "reason": "Not built by this source."}
    for f in fields:
        out[f] = _EMPTY_FIELD[f]()
    return out


def section(name, state, reason="", **data):
    """One section, with every declared field present whether used or not."""
    if name not in SECTIONS:
        raise KeyError("unknown section %r - add it to SECTIONS first" % name)
    if state not in STATES:
        raise ValueError("bad state %r for section %r" % (state, name))
    unknown = set(data) - set(SECTIONS[name])
    if unknown:
        raise KeyError("section %r has no field(s) %s" % (name, sorted(unknown)))
    out = _blank(name)
    out["state"] = state
    out["reason"] = reason
    out.update(data)
    return out


def ok(name, **data):
    return section(name, OK, "", **data)


def empty(name, reason):
    """The step ran; there was genuinely nothing to show. That is a result."""
    return section(name, EMPTY, reason)


def unavailable(name, reason):
    """This source cannot produce this panel. Say so, do not hide the panel."""
    return section(name, UNAVAILABLE, reason)


def blank(source):
    """A complete dashboard with every section present and unavailable.

    Builders start here and fill in what they have, so a section can never
    be missing by accident - only unavailable on purpose.
    """
    model = {"schema": SCHEMA_VERSION, "source": source, "extra_stats": []}
    for name in SECTIONS:
        model[name] = _blank(name)
    return model


SOURCE_FIELDS = ("kind", "id", "title", "subtitle", "tier_label", "caveat")


def source(kind, id, title, subtitle="", tier_label="", caveat=""):
    """Who this dashboard belongs to.

    Every label on screen - the report header, the dashboard title, the
    downloads line - is derived from this one object, so they cannot
    disagree about which run you are looking at.
    """
    if kind not in ("reference", "run"):
        raise ValueError("source kind must be 'reference' or 'run', got %r" % kind)
    return {"kind": kind, "id": id, "title": title, "subtitle": subtitle,
            "tier_label": tier_label, "caveat": caveat}


# ---------------------------------------------------------------------------
# the contract test's other half
# ---------------------------------------------------------------------------

def problems(model):
    """Everything wrong with a built dashboard, as plain sentences.

    Returns [] for a valid one. Used by tests/test_dashboard_schema.py so
    the two builders cannot drift apart again without something failing.
    """
    out = []
    if not isinstance(model, dict):
        return ["dashboard is %s, not a dict" % type(model).__name__]

    if model.get("schema") != SCHEMA_VERSION:
        out.append("schema is %r, expected %r" % (model.get("schema"), SCHEMA_VERSION))

    src = model.get("source")
    if not isinstance(src, dict):
        out.append("source is missing")
    else:
        for f in SOURCE_FIELDS:
            if f not in src:
                out.append("source has no %r" % f)
        if src.get("kind") not in ("reference", "run"):
            out.append("source kind is %r" % src.get("kind"))
        if not src.get("title"):
            out.append("source has an empty title - the header would be blank")

    if not isinstance(model.get("extra_stats"), list):
        out.append("extra_stats is not a list")

    for name, fields in SECTIONS.items():
        sec = model.get(name)
        if not isinstance(sec, dict):
            out.append("section %r is missing" % name)
            continue
        if sec.get("state") not in STATES:
            out.append("section %r has state %r" % (name, sec.get("state")))
        if sec.get("state") in (EMPTY, UNAVAILABLE) and not sec.get("reason"):
            out.append("section %r is %s with no reason - the panel would be "
                       "blank with no explanation" % (name, sec.get("state")))
        for f in fields:
            if f not in sec:
                out.append("section %r has no field %r" % (name, f))

    d = model.get("direction") or {}
    if d.get("state") == OK:
        counts = d.get("counts") or {}
        missing = [s for s in DIRECTION_SLICES if s not in counts]
        if missing:
            out.append("direction is ok but has no %s - the donut would draw a "
                       "different number of slices per source" % ", ".join(missing))

    for name in ("table", "panel"):
        sec = model.get(name) or {}
        if sec.get("state") == OK and not sec.get("columns"):
            out.append("section %r is ok but declares no columns" % name)

    roc = model.get("roc") or {}
    if roc.get("state") == OK and len(roc.get("fpr") or []) != len(roc.get("tpr") or []):
        out.append("roc fpr and tpr are different lengths")

    v = model.get("volcano") or {}
    if v.get("state") == OK:
        n = len(v.get("x") or [])
        if len(v.get("y") or []) != n:
            out.append("volcano x and y are different lengths")

    return out
