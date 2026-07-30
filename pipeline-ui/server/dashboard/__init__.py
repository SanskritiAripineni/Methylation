"""The dashboard contract - one shape, every source.

Before this package there were two hand-written builders: one for the
published study, one for a run you started. They drifted. The published
study had a cohort panel and no volcano; a run had a volcano and no
cohort; the direction donut drew three slices for one and two for the
other; the ROC curve and the enrichment table were computed by every run
and then thrown away because no builder mentioned them.

So the panels appeared and disappeared depending on which source you were
looking at, and there was no way to tell "this source cannot produce that"
from "that panel is broken".

Everything a dashboard can show is now declared once, in schema.py. Both
builders in build.py fill in that same shape, and every section carries its
own state - so a panel that has nothing to draw says why instead of
vanishing. tests/test_dashboard_schema.py holds both builders to it.

Consumed by console_v4 and by every version after it. console_v3 is not
edited and keeps its own copy; v3 is frozen at tag ui-v3.1-studio.
"""
from . import schema          # noqa: F401
from . import build           # noqa: F401

SCHEMA_VERSION = schema.SCHEMA_VERSION
