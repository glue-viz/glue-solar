# Code-quality review of main: the findings left

From the review of main at c930a4a on 2026-11-11: six reviewers each read one group of modules in full, and the
findings were checked against the code. Lenses, in the user's order: correct, lean, well structured, readable by an
outside contributor. This file lists only what is still to do; the plan items that carry it are in
`IRIS_GLUE_GAP_PLAN.md` (WP0, milestone Q), under the numbers the findings keep. File and line numbers are those of
c930a4a.

What this repo does: glue-solar is a plugin for glue, a desktop program for looking at linked scientific datasets. It
adds readers for solar data (IRIS, SST, DKIST, sunpy maps), a "quicklook" tab of linked viewers, viewer tools,
analysis actions, and about thirty patches of glue, glue-qt and astropy. Load assumed: one scientist on one desktop,
files up to 20 GB read lazily, worker threads beside the Qt thread, no server and no untrusted input.

## To do

17. **Files that hold the wrong things**
    - **What this is:** Where a newcomer looks for code.
    - **Problem:** `sources/loaders/iris.py` (about 1,700 lines, no docstring) holds the WCS wrapper and lock, the
      readers, `link_hpc` for every instrument and the browser dialog. `tools.py` holds the path-diagram family (640
      lines), a data class and two session savers among the toolbar tools.
    - **Fix:** One move per PR: `loaders/iris.py` into coordinates, linking, browser and readers, once the
      follow-irispy PR is on main, which changes saved class paths, as D69 allows; the paths to `glue_solar/paths.py`
      on the user's word.
    - **If we skip it:** The code works; the cost is paid by every person who has to find something.

## Left out

About 90 smaller findings: misleading names, unused parameters, near-copies of a few lines, template leftovers. Three
larger ones were left out as the code does what a test pins: a saved path takes frame 0's pointing, the path
crosshair moves every other slider on 4-D and 5-D data as glue-core's does, and test modules import 58 helpers from
each other instead of from `tests/helpers.py`.

From the design review of main at 8efa58d on 2026-11-18: about 35 smaller findings, not listed; and one not
reproduced, to try on macOS: a quit while an analysis runs destroying its thread while it is running.
