"""console-v4: the studio, with one dashboard contract behind every screen.

What changed from v3 (frozen at tag ui-v3.1-studio, still running on 8767):

  * every panel is built through server/dashboard/, so the published study
    and your own run return the same shape and the same panels - a panel
    that has nothing to draw says why instead of disappearing
  * the ROC curve and the pathway enrichment, which v3 computed on every
    run and then discarded, are returned and drawn
  * one selection drives the report, the numbers, the charts and the
    downloads together; /api/v4/dashboard answers for whatever is selected,
    so the four cannot disagree about which run they are showing

What did not change: the engine, the readiness checks, the verdicts, the
run records on disk. v4 reuses console_v2's preview/runs/study and
console_v3's ingest/workspace exactly as they are - neither is edited.
"""
