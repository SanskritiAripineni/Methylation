"""V7 API: a version-locked surface over the completed V6 behavior."""
from __future__ import annotations

from console_v6 import routes as v6
from console_v4 import sources
from dashboard import build

PREFIX = "/api/v7/"


def _published_dashboard():
    """Version 7's published-study view, using only real TCGA-BRCA assets.

    Older dashboard versions deliberately expose only the compact reference
    bundle. V7 also has access to the committed figures and pathway table from
    the completed analysis. Add them here so the enhancement cannot change the
    frozen V4-V6 response contract or mix in the simulated sample run.
    """
    files = sources.Files()
    model = build.from_reference(files)

    model["roc"].update({
        "state": "ok", "reason": "",
        "image_url": PREFIX + "published-figure/pca.png",
        "image_alt": "PCA plot of TCGA-BRCA tumour and adjacent-normal samples",
        "heading": "Do the BRCA samples separate?",
        "description": "Each dot is a real TCGA-BRCA sample. Tumour and adjacent-normal "
                       "tissue form distinct groups in the published PCA.",
        "caption": "Published TCGA-BRCA PCA. The exact ROC curve coordinates were not "
                   "retained; the leakage-safe 5-fold AUC is shown above.",
    })
    model["volcano"].update({
        "state": "ok", "reason": "",
        "image_url": PREFIX + "published-figure/volcano.png",
        "image_alt": "BRCA differential-methylation volcano plot",
        "caption": "Published TCGA-BRCA volcano plot generated from all 486,427 tested "
                   "DNA sites; the 15 most confident sites are labelled.",
    })

    enrichment = files.table("brca_pathway_enrichment.tsv") or []
    if enrichment:
        model["enrichment"].update({
            "state": "ok", "reason": "", "items": enrichment,
            "caption": "Actual TCGA-BRCA pathway output; bar length reflects "
                       "FDR-adjusted significance. These associations are exploratory: "
                       "the HM450 array's unequal probe coverage can inflate broad gene sets.",
        })
    return model


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
    if route == PREFIX + "dashboard":
        source = (query.get("source") or ["reference"])[0]
        if source == "reference":
            h._json(_published_dashboard())
            return True
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
