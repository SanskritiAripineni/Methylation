# Versions

Every interface this project has shipped is still here and still runs. None of
them is edited once it is tagged — a new version is a new set of files beside
the old ones, and each server subclasses the one before it.

To go back to any version exactly as it was:

```bash
git checkout ui-v3.1-studio
```

| # | Tag | Port | Start with | What it is |
|---|-----|------|------------|------------|
| 1 | `ui-v1-baseline` | 8765 | `server/app.py` | The original drag-and-drop pipeline builder. `web/index.html`, `web/builder.js`, `web/builder.css`, `engine/report.py`. |
| 2 | `ui-v2-sidebar-launcher` | 8766 | `server/app_v2.py` | The sidebar launcher. Adds the graded readiness check list, run history and verdicts. `console_v2/`, `web/console-v2.*`. |
| 3 | `ui-v3-studio` | 8767 | `server/app_v3.py` | The studio — plain language on top of v2's checks. Adds the workspace so an upload can actually be run, history that survives a restart, and a measured time-left. `console_v3/`, `web/studio.*`. |
| 3.1 | `ui-v3.1-studio` | 8767 | `server/app_v3.py` | **The freeze point.** v3 as it stood before the v4 work started. Same files as v3; the tag exists so there is a named commit to come back to. |
| 4 | `ui-v4-dashboard` | 8769 | `server/app_v4.py` | One dashboard contract behind every screen. `dashboard/`, `console_v4/`, `web/studio-v4.*`, `web/viz-v4.js`. |
| 5 | `ui-v5-neo-shell` | 8770 | `server/app_v5.py` | Neoantigen-style console header and palette, a header-level breast/sample selector, and one responsive report layout for every source. `console_v5/`, `web/studio-v5.*`, `web/report-v5.*`. |
| 6 | `ui-v6-brca-results` | 8771 | `server/app_v6.py` | Removes the secondary product name from the header, adds explicit cohort/repeat/local-folder/upload sources, restores the complete report, and attaches BRCA outputs in Runs & Files. `console_v6/`, `web/studio-v6.*`. |
| 7 | `ui-v7-hosting-ready` | 8772 | `server/app_v7.py` | **Locked hosting candidate.** A version-isolated copy of the completed V6 experience with its own page, assets, API prefix and server entry point. `console_v7/`, `web/studio-v7.*`. |
| 8 | `ui-v8-persistent-runs` *(not cut yet)* | 8773 | `server/app_v8.py` | The Runs tab stops blanking, run history stops resetting on hosts that can keep it, and Upload & Settings becomes a collapsible sidebar. `console_v8/`, `web/studio-v8.*`. |

V8 lives on `codex/ui-v8` and is deliberately **not tagged yet** — a tag is
what freezes a version against further edits, so it is cut once V8 is
approved, not when it is written.

Older versions stay reachable from a newer server: v4 on 8769 still serves
v3 at `/studio.html`, v2 at `/console-v2.html` and v1 at `/index.html`.

V5 on 8770 also serves V4 unchanged at `/studio-v4.html`.

V6 on 8771 serves V5 unchanged at `/studio-v5.html`.

V7 on 8772 serves V6 unchanged at `/studio-v6.html`.

V8 on 8773 serves V7 unchanged at `/studio-v7.html`.

## What v8 changed

### 1. Results in the Runs tab stopped disappearing

Clicking a finished run loaded it **twice**. `openRun()` started a poll and a
selection together; the poll came back "done", and the poller's finished-branch
selected the same run again. Every selection began by blanking every panel:

```
t+0ms    blank      select #1, from the click
t+118ms  16 files   the dashboard arrives
t+120ms  blank      select #2, from the poller — same run, nothing new to show
t+201ms  16 files   the same dashboard arrives again
```

Locally that second blank is 80ms and reads as a flicker. On a host that
sleeps between visits it is seconds long, and when that second request is the
one that fails, the screen stays empty — for a run whose results were on
screen a moment earlier.

Two changes, neither of which weakens v4's generation guard:

* **A loaded selection is kept.** `state.cache` in `web/studio-v8.js` holds the
  dashboard for every selection the page has read. Re-selecting one paints
  from it immediately. A finished run and the published study are immutable,
  so a cache hit is not stale — it is the bytes the server would resend.
* **The poller no longer takes over the screen for a run that was already
  finished when it was clicked.** It selects only when the run it was watching
  has just *become* finished, and re-reads that one explicitly, because that
  run's dashboard did not exist the last time the page looked.

Measured on the same six alternating clicks between two runs:

| | panels blanked | panels painted |
|---|---|---|
| v7 | 12 | 12 (each run drawn twice) |
| v8 | 0 | 6 (each run drawn once) |

A failed re-check now keeps what is on screen and says so in one line, instead
of replacing a real result with an error.

### 2. Run history stopped resetting on its own

`runs/` is gitignored and sits on the container's own filesystem. A free Render
instance rebuilds that filesystem on every redeploy and after every sleep, so
runs vanished overnight — and because `restore_saved_sample_run()` put the
bundled demonstration run back, the list looked *almost* right and was missing
exactly the runs someone had started themselves.

`console_v8/store.py` resolves where runs are kept before the server starts:

* `METHYLATION_DATA_DIR`, if set and writable — attach a Render disk, point
  this at its mount path, and history survives a restart. Runs already on the
  ephemeral disk are copied across once, on the first start.
* Otherwise a disk mounted at `/var/data`, `/data` or `/mnt/data`.
* Otherwise the old location, **and the Runs tab says so.** `GET
  /api/v8/storage` answers with where runs live and whether that survives a
  restart; the interface prints it. Losing a run is bad. Losing one while the
  screen implies it was saved is worse.

`app_v8.py` also defaults its host and port to `$PORT`/`$HOST` when they are
set, so the same command runs locally and on a managed host.

### 3. Upload & Settings is a sidebar

V7 had two controls for one panel: a permanent 390px column *and* a "Upload &
Settings" item in the top nav which, on a narrow screen, replaced the whole
right-hand side and, on a wide screen, appeared to do nothing.

There is one control now — a toggle in the header. Wide: the sidebar collapses
and the report, results or run files get the width. Narrow: it is a drawer
over the work, with a scrim and Escape to close, so the tab being read is
still behind it rather than replaced by it. The choice is remembered in
`localStorage`; until one is made, it opens on a wide screen and stays shut on
a narrow one.

### What v8 deliberately did not touch

The engine, the pipeline, the dashboard contract, the readiness checks, the
verdicts, and `web/viz-v4.js`. V8 reuses `console_v7` — and through it every
package back to `console_v2` — exactly as it is. No V7 file is edited; V7 runs
from its own files on its own port, and V8 serves V7's page unchanged.

## What v7 changed

V7 freezes the approved V6 interface as a separate hosting target. Its page,
stylesheet, script, API prefix and server launcher are version-specific, so
future development can continue without changing the release tagged
`ui-v7-hosting-ready`.

Hosted V7 restores the committed BRCA demonstration run from `Results/` into a
fresh server's run history so the sample selector remains available on
ephemeral hosts. The two result sources stay separate: the published-study
selection uses the real TCGA-BRCA PCA, the interactive plotting data embedded
in the completed BRCA report and BRCA pathway outputs, while the sample
selection uses only its own run artifacts. The BRCA volcano overlays all 1,536
saved high-change sites on the report's 4,500-point background sample, keeps
the published ±0.20 cutoffs, and reveals the gene, probe, location, change and
FDR on hover without overlapping labels.

## What v6 changed

**1. One brand in the header.** The secondary “Methylation Studio” text is
removed. The header now shows MRKTechSolutions, Version 6, navigation and the
active report-source selector.

**2. Explicit data access choices.** The first step now offers the bundled
study cohort, an earlier run, a local folder path, or browser file upload. A
local folder is scanned for the methylation matrix, sample list and optional
site annotation; supported files stay in place and are linked into the local
workspace when possible.

**3. The original one-page report stays the report.** The published breast
selection embeds `Results_Presentation.html` with its full visualization set.
A sample or uploaded selection embeds that run's generated `run_report.html`.

**4. BRCA sample outputs are attached in Runs & Files.** The saved bundled-
cohort run has permanent links to its complete report, ZIP archive and every
individual output file, with the simulated-data warning kept beside them.

## What v5 changed

**1. The selector moved into the product header.** The breast published study
and the latest completed sample or uploaded run are chosen in one persistent
control. The selection continues to drive the report, results and files as one
unit through the shared dashboard contract.

**2. One report composition.** `web/report-v5.*` renders the same fixed section
order for either source. Content comes from the selected dashboard; sections
that are empty or unavailable stay in place and explain why.

**3. A compact scientific-console shell.** The navigation, density, border
radii and ink-blue palette follow the Neoantigen console visual system. The
unused bottom loading panel is gone; source changes use the small status in the
selection bar instead.

## What v4 changed, and why

**1. One dashboard contract.** `server/dashboard/schema.py` declares every panel
the Results tab can show. Both the published study and a run you started are
built through it, so they return the same sections in the same shape.

Before, two hand-written builders drifted: the published study had a cohort
panel and no volcano, a run had a volcano and no cohort, the direction donut
drew three slices for one source and two for the other, and the ROC curve and
the pathway enrichment were computed by every run and then discarded because
no builder mentioned them. The interface hid whichever panel was missing, so
a panel that could not exist looked exactly like a panel that was broken.

Every section now carries its own state — `ok`, `empty` (the step ran and
found nothing, which is a result) or `unavailable` (this source cannot produce
it) — and a panel that has nothing to draw says which, in a sentence, in
place of the chart. `tests/test_dashboard_schema.py` holds both builders to it.

**2. One selection.** `GET /api/v4/dashboard` answers for the whole screen at
once — the report, the numbers, the charts and the file list. Every load
carries the generation it started in, and a response that arrives after the
selection has moved on is dropped instead of drawn.

Before, the report was set synchronously and the charts were fetched
separately with no guard between them. Clicking one run and then another
before the first landed left the header describing one analysis and the charts
drawing a different one.

**3. The visualizations are fixed functions.** `web/viz-v4.js` holds one pure
function per panel, and it is *shared* — v5 imports it rather than copying it.
Forking the chart code per version is what let the two sources drift apart in
the first place. Only the shell (`studio-v*.html/css/js`) forks per version.

**4. Runs, progress and files are one screen.** Picking a run, watching it and
taking its files used to be three separate places — a list crammed into the
sidebar, a progress strip above the tabs, and a Downloads tab — and none of
them was where you were looking. They are now the **Runs & files** tab: the
run list on the left, and on the right what step it is on, how long is left,
every step by name with its own timing, and the file table with download
links.

The sidebar is now only the three things you do *before* pressing go. The tab
carries a live step counter (`4/11`) so a run stays visible from any tab, and
a run in flight shows its own progress bar in the list. History is read from
`run_record.json`, which is written when a run *finishes*, so the run
happening right now is inserted at the top from the poller — otherwise the
list would claim nothing was running while the bar above it said otherwise.

**5. The colour scheme.** The interface greys were perfectly neutral (chroma
0.000); they are now tinted toward one low-chroma ink-indigo, which is what
makes the screen read as designed rather than default. Contrast went up:
`--muted` moved from 4.93:1 to 5.78:1 against the page.

The data pair changed from red/green to red/blue. Measured under the Machado
deuteranopia simulation, `#c0392b` against `#1a7a3a` sits at OKLab ΔE 6.1 —
inside the band where colour may only carry meaning alongside a second
channel. The volcano plot encodes direction by colour alone, so it was
unreadable for a deuteranopic reader. `#c0392b` against `#2a78d6` measures
26.1 and passes every check. Two hues on screen, and nothing louder than
before.

## What v4 deliberately did not touch

The engine, the readiness checks, the verdicts, the run records on disk, and
the whole left-hand column of the studio. v4 reuses `console_v2`'s
preview/runs/study and `console_v3`'s ingest/workspace exactly as they are —
neither package is edited.

## Known, not fixed

The published study's *report* (`web/site/Results_Presentation.html`, authored
by hand) and its *dashboard numbers* (`data/reference/*.tsv`) are independent
sources, and nothing checks that they agree. A run you started does not have
this problem — its report and its `results.json` come from the same run.

V5 does not embed that independent document. It composes both published and
run reports directly from the selected dashboard, so the report shown in V5
and the V5 results tab share one source.

## Version 5 implementation checklist

1. Tag the current one first: `git tag ui-v4-<name>` and push it.
2. Branch: `git checkout -b feature/ui-v5`.
3. New shell only — `server/app_v5.py` subclassing v4's handler,
   `console_v5/`, `web/studio-v5.*`, a new port in `.claude/launch.json`.
4. **Import `dashboard/` and `web/viz-v4.js`. Do not copy them.** If a chart
   needs to change, change it there and let both versions get it.
5. Add a row to the table above.
