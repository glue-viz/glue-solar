# Code-quality review of main (c930a4a), 2026-11-11

Six reviewers each read one group of modules in full (all 17,400 lines of non-test source, plus packaging, docs and
the shape of the test suite). The findings below were then checked against the code, and where it says so against
real data or CI logs. Nothing on main was changed. Lenses, in the user's order: correct, lean, well structured,
readable by an outside contributor. The plan items that carry these findings are in `IRIS_GLUE_GAP_PLAN.md` (WP0,
milestone Q). On main since #410 (2026-11-11): findings 1 to 9 and 12, and from finding 17 the DKIST actions'
move and the DKIST WCS's rename.

What this repo does: glue-solar is a plugin for glue, a desktop program for looking at linked scientific datasets. It
adds readers for solar data (IRIS, SST, DKIST, sunpy maps), a "quicklook" tab of linked viewers, viewer tools,
analysis actions, and about thirty patches of glue, glue-qt and astropy. Load assumed: one scientist on one desktop,
files up to 20 GB read lazily, worker threads beside the Qt thread, no server and no untrusted input.

## Must fix

1. **A saved session with an extra dataset on a quicklook panel will not open** (`glue_solar/quicklook.py:2364-2398`)
   - **What this is:** A session saves each quicklook as a recipe. `_reopen` rebuilds the tab, then writes each saved
     panel and layer state back.
   - **Problem:** `_recipe` saves every layer of a panel, but `_reopen` never adds a dataset the user dragged on. If
     that dataset was the panel's reference data (step 1 of the user guide's blink recipe), line 2388 raises
     `ValueError: ... is not in valid choices` and the whole session fails to open. Otherwise the dataset is silently
     gone. 'Show this window's panels' fails the same way, after it has closed the old panels.
   - **Fix:** In `_reopen`, before `panel.state.update_from_dict(state)`, add each saved layer that is a `Data` and
     not yet on the panel. About 4 lines and one test.
   - **If we skip it:** A user who follows the documented blink recipe and saves cannot open that session again.

2. **Opening another window's panels hides every region you drew** (`glue_solar/quicklook.py:2174-2190`, `2527-2542`)
   - **What this is:** `_show_point` runs as a quicklook opens. It keeps the point on its own panels and hides other
     subsets on the new panels.
   - **Problem:** `open_window` calls it again for every panel of the file, so the "hide other subsets" branch also
     runs on panels that were already open. Draw a rectangle on the map, tick another window in the Panels list: the
     region and its mean spectrum vanish from all four old panels.
   - **Fix:** Give `_show_point` the list of viewers to clean and pass only the new ones from `open_window`. 2 lines
     changed.
   - **If we skip it:** Regions disappear for no reason the user can see, and must be re-ticked panel by panel.

3. **The browser closes with nothing loaded** (`glue_solar/sources/loaders/iris.py:1669-1682`)
   - **What this is:** `_loaded` ends a load in the observation browser and closes the dialog.
   - **Problem:** It calls `accept()` even when nothing was read. Press Load then Stop before the first file is done,
     or press Load with nothing ticked: the dialog closes, and the scan and every tick are lost.
   - **Fix:** `if error or not loaded:` show the message (`error or "Nothing was loaded"`) and stay open. 2 lines.
   - **If we skip it:** The user rescans a folder of hundreds of files to try again.

4. **Browser messages are written into the progress bar** (`glue_solar/sources/loaders/iris.py:1424-1675`,
   `iris_loader.ui:233-239`)
   - **What this is:** Every browser message (no such folder, a failed read, "Extracted 2 archives") is set as the
     progress bar's text format.
   - **Problem:** Qt replaces `%p`, `%v` and `%m` in that text, so a path such as `/data/100%valid` is shown wrong. A
     normal reader error is wider than the bar and is cut at both ends. And Qt's macOS style never draws progress-bar
     text, so on the Mac app these messages may not show at all (not run on a Mac: check this first).
   - **Fix:** Add a word-wrapped `QLabel` under the bar and send the messages there. About 10 lines of `.ui`, 6 call
     sites, and the 13 test assertions that read `progress.format()`.
   - **If we skip it:** A load that fails can look like a load that did nothing.

5. **Blink un-hides layers you had hidden** (`glue_solar/tools.py:2535-2569`, `2815-2819`)
   - **What this is:** Blink flips an Image viewer between two datasets and hides the layers of the one it left.
   - **Problem:** Each flip, and Stop, sets `visible = True` on every layer of the dataset and its subsets, not only
     the ones the flip hid. Untick two subset layers, blink twice, stop: both are ticked again.
   - **Fix:** `_position` also records which layers were visible; `_show_position` and `blink(False)` re-show only
     those. About 2 lines.
   - **If we skip it:** Blinking undoes the user's layer choices each time.

6. **DKIST files that arrive after the dataset is opened are never noticed** (`glue_solar/sources/dkist.py:479-495`,
   `786-790`)
   - **What this is:** `_present` records which FITS files of a DKIST dataset are on disk. Color limits sample those
     frames, and 'Download these frames…' offers the others.
   - **Problem:** `_present` is filled once at load. Only glue-solar's own download updates it. Files that a Globus
     transfer from an earlier session delivers are drawn, but color limits stay NaN and the download dialog still
     offers every file, until the dataset is opened again.
   - **Fix:** In `_sample`, check the files again before listing frames, and do not cache a sample or noise level
     taken while files were missing. About 6 lines.
   - **If we skip it:** A dataset that finished downloading looks blank until glue is restarted.

7. **A big cube dropped on the quicklook's spectrum panel is profiled whole** (`glue_solar/quicklook.py:1904`, `1880`)
   - **What this is:** `_profile` sets `viewer.large_data_size = None` so adding its own raster skips glue's 'Add
     large data set?' prompt. `hidden_cube_profile` adds other large cubes hidden, so glue never reads them whole.
   - **Problem:** The `None` is never reset, and `hidden_cube_profile` only acts when the value is not `None`. An SST
     cube dragged onto an IRIS quicklook's spectrum panel is added visible with no prompt. The code's own docstring
     measures that at 30 s and 11 GB.
   - **Fix:** `del viewer.large_data_size` after the `add_data` call. 1 line.
   - **If we skip it:** One drag can freeze the app or exhaust memory on a 24 GB Mac.

## Should fix

8. **Five small faults with one-line fixes**
   - **What this is:** Edge cases in the browser, the readers and two tools.
   - **Problem:** (a) A half-downloaded `.tar.gz` raises `EOFError`, which `_extract` does not catch, so the message
     names no file and the folder is not rescanned (`sources/loaders/iris.py:1301`). (b) `MainWindowTool.switch`'s
     guard reads `self.viewer._closed` after the viewer is `None`, and raises in the one case it exists for
     (`tools.py:2520`). (c) `is_iris_fits` claims any file whose TELESCOP is IRIS, so a Level 3 file fails in the
     IRIS reader and never reaches glue's FITS reader (`sources/iris.py:97`). (d) `read_sunpy_map` crashes on a FITS
     file with two image HDUs, because sunpy returns a list (`sources/maps.py:88`). (e) The frame-time label takes the
     exposure's min and max over every pixel of the frame, 37 ms a slider step at 4096 x 4096; the time two lines
     above it is already unbroadcast (`tools.py:517`).
   - **Fix:** (a) add `EOFError` to the `except`; (b) `if self.viewer is not None:`; (c) also require
     `DATA_LEV == 2`; (d) one `Data` per map; (e) `unbroadcast(data[exposure, view])`.
   - **If we skip it:** Each is rare, but each ends in a traceback or a stall the user cannot explain.

9. **Renaming a dataset makes a restored quicklook forget its panel settings** (`glue_solar/quicklook.py:2133`,
   `2365`, `2379-2386`)
   - **What this is:** `_reopen` matches saved panels to rebuilt ones by their title text.
   - **Problem:** Generic and DKIST quicklooks build titles from the dataset's label. Rename the dataset, save,
     restore: limits and colormap are back to defaults and panels that were turned off come back on.
   - **Fix:** Key panels by what the title stands for (role, dataset, n-th of that pair) instead of the text. About 6
     lines.
   - **If we skip it:** Sessions of renamed data restore half-reset.

10. **Features that ride on a bug-fix switch will vanish when glue fixes the bug** (`glue_solar/glue_patches.py:326-427`)
    - **What this is:** Each patch installs only while a probe finds the upstream fault.
    - **Problem:** Later PRs added unrelated behaviour to two gated patches. The always-on Undo patch needs
      `_solar_made`, which only the gated Redo patch records: when glue fixes Redo, Undo again deletes every subset
      made since. The DKIST mosaic tile click lives inside the gated Pixel-click patch and goes with it. The axis
      label and WCS link patches may carry the same risk (not checked against the fork branches).
    - **Fix:** Install `apply_subset_state` and the Pixel-click wrapper always, and gate only the branch the probe
      tests. About 3 lines.
    - **If we skip it:** A glue release that fixes one bug silently breaks two glue-solar features.

11. **The app-check test never runs in CI** (`glue_solar/tests/test_app_smoke_imports.py:7-10`)
    - **What this is:** A test added after a rename broke the macOS app's start-up check unseen (#336, #344).
    - **Problem:** It finds `packaging/macos/smoke.py` relative to its own file. tox installs the package, so the path
      points into `site-packages` and the test is skipped. The CI log of run 41347691789 shows SKIPPED in py313,
      py314 and py313-online.
    - **Fix:** Take the path from `request.config.rootpath`. About 4 lines.
    - **If we skip it:** The next rename breaks the app build unseen again.

12. **Two beliefs about a stack's wavelengths** (`glue_solar/sources/moments.py:82`, `doppler.py:32-35`,
    `calibration.py:203-214`)
    - **What this is:** Before calling irispy, each analysis keeps only the wavelength pixels it needs.
    - **Problem:** Line moments, red-blue, bursts, Mg II features and fit maps use scan 0's wavelengths for every scan
      of a stack. Doppler and calibration use each scan's own. With a scan shifted by a third of a sample the first
      group gives other numbers than the scan alone. Real data do not do this: all scans share one grid in the six
      multi-file observations on the Linux machine (2,725 files, checked 2026-11-11).
    - **Fix:** Refuse a stack whose scans' wavelength axes differ, where the stack is made, and delete the per-scan
      code in doppler. About +5, -11 lines. The user decides, as this touches D59's wording.
    - **If we skip it:** No wrong numbers today; the code keeps two rules and one untested branch.

13. **Code kept for old sessions, against D69**
    - **What this is:** Fallbacks for sessions saved by earlier glue-solar.
    - **Problem:** D69 says old sessions need not open, yet seven branches remain: `sources/dkist.py:579`, `:705`;
      `sources/loaders/iris.py:374`; `tools.py:1164-1166`; `quicklook.py:1154` (with the comment at 89-90), `:1606`,
      `:1590`. Two tests exist only to exercise them.
    - **Fix:** Delete them. About -13 lines and two test edits.
    - **If we skip it:** Each new reader has to work out that these branches cannot happen.

14. **Dead code and unused config**
    - **What this is:** Leftovers from earlier PRs and from the package template.
    - **Problem:** `_add_session_colormaps` and the map loader's `_add_colormap` call do nothing since `setup()`
      lists every sunpy colormap (`__init__.py:76-84`, `maps.py:75`). `GaussianConstantFitter.set_constraint` has no
      caller in the app since #314 (`fitters.py:288-296`).
      `load_entry`'s `stack` parameter is never passed (`sources/loaders/iris.py:1238`). `.flake8` is read by nothing.
      tox's `oldestdeps` factor has no env since D104. The doctest plugin and its six settings collect zero doctests.
    - **Fix:** Delete each. The register rows for the first two go or are reworded. Not `"epsilon": 1e-12`
      (`fitters.py:447`): a reviewer's synthetic fit converged without it, but the upstream review's others row
      24 found the documented C II recipe does not on astropy 8.0.2, so try that recipe first.
    - **If we skip it:** Readers and the register keep describing code that does not run.

15. **Copies that must change together**
    - **What this is:** The same logic written in two or three modules.
    - **Problem:** `LazyData.__gluestate__` and `DKISTData.__gluestate__` are the same 13-line record of glue's saver
      (`loaders/lazy.py:228-255`, `dkist.py:537-562`). Two helpers raise the open-file limit with different targets
      (`lazy.py:24-39`, `dkist.py:62-80`). "The pixel axes a world type varies along" is written out in
      `dkist.py:618`, `tools.py:1020` and `quicklook.py:923`.
    - **Fix:** One function each, in `lazy.py` and beside `_HPC`. About -34 lines.
    - **If we skip it:** A change in glue's saver must be found and made twice.

16. **The GUI module is everyone's helper library** (`glue_solar/quicklook.py`, `glue_solar/sources/moments.py`)
    - **What this is:** Small helpers that say what a dataset is (its role, wavelengths, window, time axis), and the
      shared dialog and worker helpers of the analysis actions.
    - **Problem:** The first group (292 lines, no Qt, no use of the rest of quicklook.py) lives in the 3,416-line Qt
      module, so nine modules import the GUI for it and the loader needs function-level imports to avoid a cycle.
      The second group (about 230 lines) lives in the line-moments module, so ten modules import moments for it and
      moments imports two of them back inside functions.
    - **Fix:** Move each group to its own leaf module. No lines added; about 22 import lines change. quicklook.py
      keeps `nearest`, `observation_key` and `sji_to_raster` in `__all__`, as the docs cite those paths.
    - **If we skip it:** The import tangle (one 10-module cycle through function-level imports) stays.

17. **Files that hold the wrong things**
    - **What this is:** Where a newcomer looks for code.
    - **Problem:** Half of `sources/iris.py` (lines 395-816) is three DKIST actions, with their other halves in
      `dkist.py`. `sources/loaders/iris.py` (1,682 lines, no docstring) holds the WCS wrapper and lock, the readers,
      `link_hpc` for every instrument and the browser dialog. `tools.py` holds the path-diagram family (640 lines),
      a data class and two session savers among the toolbar tools. `GlueWCS` (DKIST) and `_GlueWCS` (IRIS) differ by
      one underscore and are both used in the same functions.
    - **Fix:** One move per PR: DKIST actions to `sources/dkist_actions.py`; paths to `glue_solar/paths.py`; rename
      the DKIST class. Splitting `loaders/iris.py` into coordinates, linking, browser and readers is the largest and
      changes saved class paths, which D69 allows.
    - **If we skip it:** The code works; the cost is paid by every person who has to find something.

18. **Comments point at a plan nobody else can open**
    - **What this is:** References such as "(D73)" in comments and docstrings.
    - **Problem:** main cites decision numbers 310 times in source, 199 in tests and 39 in docs. They resolve only on
      this branch, and 42 land in the published API pages. About 60 other tags (`P8`, `F173`, `206-7`, `wp0-…`,
      "user, 2026-10-23") resolve nowhere. At least four cite the wrong decision. 28 comments say "glue 1.27.0" for
      faults still present in 1.28.0, the floor. 17 comments start with `ponytail:`, a tool's marker.
    - **Fix:** Where the sentence already gives the reason, delete the tag. Keep only references a reader can open: a
      PR or issue with its repository, or `docs/dev_guide/workarounds.rst`. Comment edits only.
    - **If we skip it:** A glue maintainer reading a patch to upstream it cannot tell why it is written as it is.

19. **The README and install docs describe an older package**
    - **What this is:** The first things an outside reader sees.
    - **Problem:** The README still says the plugin "provides a reader for solar data". README and `docs/index.rst`
      say PyQt6 6.11; `pyproject.toml` says 6.12.0. The macOS build recipe pins five packages below the floors. Four
      modules have no docstring, two have a wrong one, and the API reference omits the module the scripting guide
      imports from.
    - **Fix:** Rewrite the README's nine lines, drop version numbers from prose, update the five pins, add the
      docstrings and one automodapi entry. About 30 lines.
    - **If we skip it:** The GitHub landing page undersells and misdescribes the package.

20. **The workaround register has gaps**
    - **What this is:** `docs/dev_guide/workarounds.rst` lists every patch of an upstream package with its switch.
    - **Problem:** About eleven overrides have no entry (four in `tools.py`, two in `loaders/iris.py`, five in
      `glue_patches.py`, `lines.py` and `__init__.py`). Two probes cannot see the fix their row names. Nothing ties
      the register to the code.
    - **Fix:** Add the entries, reword the two rows, and add a 6-line test that the `needs_*` names in the register
      and in `glue_patches.py` match.
    - **If we skip it:** The register drifts from the code it is meant to retire.

## Left out

About 90 smaller findings: misleading names, unused parameters, near-copies of a few lines, template leftovers. Three
larger ones were left out as the code does what a test pins: a saved path takes frame 0's pointing, the path
crosshair moves every other slider on 4-D and 5-D data as glue-core's does, and test modules import 58 helpers from
each other instead of from `tests/helpers.py`.

Checked and found sound: all 24 `needs_*` probes report their fault on the installed releases, so no probed patch can
go yet; every register entry has code behind it; no top-level dead code in `tools.py`; file handles and memory maps
are freed after a stopped load; `nearest` agrees with brute force on 3,000 random cases.

Verdict: healthy for one user, with seven bugs a user can hit today; fix 1 to 7 first, then 11.
Lean: about -130 lines and -1 dependency (`pytest-doctestplus`) possible from findings 12 to 15.
Not checked: nothing was run on macOS, on a real SST cube or on DKIST data beyond dkist's packaged samples; the test
suite was not run (the env has no pytest); individual tests were not re-reviewed (done 2026-10-31, #408); the fixes
above were tried only in memory, not against the suite.
