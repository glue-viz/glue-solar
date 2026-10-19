# Upstream review (D89)

What glue-solar should send upstream, report, keep or drop, re-verified on 2026-10-19 against the latest releases and
mains: glue-core 1.27.0 and main 0039c22, glue-qt 0.4.2 and main 9780eaf9, astropy 8.0.2 and main a64a40b (WCSLIB
8.10), echo, mpl-scatter-density, matplotlib, fiasco main and irispy main. glue-solar main was 089a5b5. Every fault was
reproduced on both the release and main, or the row says why not.

The detail is in three sections, one table row per item with its re-verification, upstream status, recommendation and
the glue-solar code it retires: [glue-core](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/glue-core.md) (68 items),
[glue-qt](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/glue-qt.md) (40),
[astropy, WCSLIB and the rest](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/others.md) (35). Their reproducers are in
the folders beside them (the sections name them by their scratch paths; the files are the same). The brief the
reviewers followed is [BRIEF.md](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/BRIEF.md).

## In numbers

| Recommendation | glue-core | glue-qt | others | All |
| --- | --- | --- | --- | --- |
| UPSTREAM-PR | 52 | 29 | 8 | 89 |
| REPORT | 2 | 5 | 15 | 22 |
| WAIT | 6 | 3 | 6 | 15 |
| KEEP | 4 | 3 | 3 | 10 |
| DROP | 2 | 0 | 3 | 5 |

No upstream main fixes any glue-core or glue-qt fault in the register: glue main is 1.27.0 plus unrelated commits and
glue-qt main is 0.4.2 plus two. glue-qt main's CI has been red since 2026-02, which is why the user's drafts #68, #70,
#74 and #75 show failing jobs; #69 (the CI fix, approved) passes.

## Order to upstream

1. **Ready now, on the user's forks, each one commit with its test** (open as PRs):
   - glue `perf-g1a` … `perf-g10`: ten PRs, each applying cleanly to upstream main and needing a CHANGES line (the SJI
     frame step 105 → 39 ms with g1a; startup, hidden subsets, link removal, histograms, sessions).
   - glue drafts #2598 and #2599 (fix its codestyle): mergeable, waiting only on `py311-test-visual` (dhomeier's
     #2592). #2595 and #2597 after their amendments (time axes out of `wcs_autolink`; restore `preferred_cmap` and
     save Quantities instead of skipping meta).
   - glue-qt Fit tab: `fitter-settings` (one fitter per viewer, check boxes; also fixes Fit constraints being ignored),
     `fitter-settings-widget`, `fit-artists`: retire about 130 lines of `glue_patches.py`.
   - glue-qt `perf-q1` and `perf-q2` (the profile worker: 84 ms → 0.1 ms twice per point move; the quicklook spectrum
     about 250 ms sooner), `perf-q3` and `perf-q4` (icon caches: 45 ms → 0.2 ms per colormap combo; 473 icon loads →
     1), `perf-q5` and `perf-q6` (startup).
   - astropy `perf-a1-wcsaxes-pytest-import` (42 ms per process).
   - **astropy#19174, a comment** with a reproducer on astropy's own `tab-time-last-axis.fits`: 8 threads give wrong
     `all_pix2world` values in about 2,380 of 2,400 calls on 8.0.2 and on main; a lock gives none. The cause is
     WCSLIB's `tabx2s` writing scratch fields on the shared table (tab.c:1237-1247). Every glue-solar WCS lock waits
     on it; the plan's retirement test ("20 unlocked runs with 0 crashes") is too weak, as main corrupts silently.
2. **Small fixes to write** (2-10 lines each, a test each):
   - glue: `WCSLink`'s shared slicing lists, `ProfileViewerState._update_priority`, `DerivedComponent.datetime`, the
     FITS subset-mask importer's integer check, `axis_label`'s index (SST's '' and 'Hplt'), the FITS exporter's
     `blank`, an empty `AggregateSlice`.
   - glue-qt: `glue -x` (broken outright), a cancelled 'Add large data set?' breaking later viewers, playback outliving
     its viewer, the Table viewer's added rows and datetime search, missing tooltips, a slider move turning a Collapse
     into an int, Collapse dropping the range's last sample.
   - astropy: `FitInfoSubset.__getattr__` (1 line), the tie chain in `fitter_to_model_params_array` (about 3 lines),
     WCSAxes `grid(which='minor')`.
   - fiasco: the skip-name substring check (1 line).
3. **Medium PRs:**
   - glue sessions: `LinkSameWithUnits`, Quantity and `preferred_cmap` savers, the `stretch_global=False` restore crash
     and lost `stretch_parameters` (both new), `DerivedComponent.units` (glue-solar's units are lost in sessions
     today), a -TAB WCS saver, the path slicer's savers.
   - glue's image artists (crosshairs, the Pixel point; upstream #2054): about 120 lines of `glue_patches.py`.
   - glue's profiles and statistics: cached-profile y limits (R14), native-dtype reductions (R21: 435 MiB for a
     92 MiB float32 cube), padded slice-subset results, row-wise sampling (R32); then the link manager (R6, R12, R24).
   - glue-qt keys by `isinstance`, matplotlib's keys off the canvas, slider coalescing while dragging (R16), a closed
     viewer's dashboard widgets deleted (removed data stays alive today).
   - astropy: a -TAB `axis_correlation_matrix` from the tables (about 15 lines); WCSAxes tick placement, a memo then
     batched calls (R5: still 37 WCS calls per unchanged redraw on main).
4. **Reports, not PRs** (22, mostly astropy and WCSLIB): the SST -TAB `w.celestial` SIGSEGV, WCSAxes on one- and
   three-coordinate views, zero-size axes and unpickling, `parallel_fit_dask` resending every start array with each
   chunk, echo's combo match, mpl-scatter-density's resize hold, and the rest in the sections.
5. **Generic glue-solar features glue users would want**, after the above and on the user's call: the Fit tab's model
   builder (about 280 lines), Loop's range options (about 90), Blink (about 100), Follow/lock as a hover mode of
   glue's Pixel tool (about 90), keys (about 75), Save frames or movie (171), Save profiles (34), and smaller tools
   (per-frame limits, the color bar, the wavelength band, physical aspect, Measure, gamma stretches). Hide axes is
   glue#2128 (open). Some wait on glue-qt#72 (subtool menus) and glue#2603/glue-qt#73 (lines).

## Glue-solar changes now

- **Drop the gzip-to-bytes step** in `loaders/iris.py` (about 15 lines): irispy main reads a `.gz` once itself.
- **Strike from the plan's lists**: `translate_pixel`'s bare `Exception` (gone on main), the two WCSAxes cases that did
  not reproduce, irispy's `py314-devdeps` failure (fixed by irispy #259).
- **When glue releases its pytest plugin** (#2587, on main): drop `conftest.py`'s `CFG_DIR` setup.
- **Follow irispy main** again for #256 (dust found from the pipeline's bad-pixel table; `calculate_dust_mask` takes a
  cube), which glue-solar's dust removal calls.

## Keep in glue-solar

Ten items: solar and IRIS features (the quicklook recipe, the last-session keeper, the Doppler unit converter, the
mouse-over readout's ticks) and the user's decisions (D67's SST inverse, D70's sampling, D73's lock wrappers until
astropy#19174 is fixed). Their rows say why.
