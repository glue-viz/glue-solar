# CRISPEX and IRIS-SolarSoft feature map

Companion to [IRIS_GLUE_GAP_PLAN.md](IRIS_GLUE_GAP_PLAN.md), generated on 2026-09-27 from the
plan's checkboxes and the verified review in
[IRIS_PLAN_PROTOTYPES/review_20260927/](IRIS_PLAN_PROTOTYPES/review_20260927/README.md).
Each of the 203 features from CRISPEX and the IRIS SolarSoft quicklook tools maps to one or more plan
checkboxes, to 'Available today' (with how to do it in Glue), or to an exclusion. The source
citations and Glue evidence for every row are in `review_20260927/features.json`. Updated on
2026-09-29 to the trimmed plan's keys, and on 2026-09-30 for the user's exclusions. The plan no longer lists feature IDs, so this file is the
feature-to-checkbox map: update it when checkbox keys or feature lists change. The plan is
authoritative.

Columns: IRIS = relevant to IRIS data; Priority = review priority for an IRIS-first CRISPEX
quicklook (must/should/could/wont); Milestone and Where = the owning checkbox (M4 = upstreaming,
after the glue-solar work).

Summary: Available: 35, Excluded: 25, M0: 25, M1: 42, M2: 20, M3: 52, M4: 4.

## IRIS raster/SJI semantics, reference cubes & time sync

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F103 | Reference cube (REFCUBE) incl. dual-cube mode | yes | should | M1 | `wp4-context-reference` (WP4, M1) |  |
| F104 | Load reference and SJI cubes at runtime (File > Open) | yes | should | M1 | `wp4-context-reference` (WP4, M1) |  |
| F105 | Slit-jaw / context cubes (SJICUBE, up to six) | yes | must | — | Available today | The IRIS browser lists every SJI (keyed by TDESC1) and aligned AIA cutout of an observation, with no channel limit (glue_solar/sources/loaders/scan.py:164-165,174-175; loaders/iris.py:121-125,240-242 at 236f0a8). Each loads as a Data with an irissji/sdoaia colormap and can be opened from the data collection. Multi-SJI coordination is wp4-sji-panels and wp4-time-sync; docs are in wp9-m0-browsing-recipes. |
| F106 | SJI-formatted AIA / Hinode context cubes | yes | should | M1 | `wp4-context-reference` (WP4, M1) |  |
| F107 | Reference image window | yes | should | M1 | `wp4-context-reference` (WP4, M1) |  |
| F108 | Reference detailed-spectrum and spectrum-time windows | yes | should | M1 | `wp4-m1-multi-window` (WP4, M1) |  |
| F109 | Slit-jaw image windows | yes | must | M0 | `wp4-sji-panels` (WP4, M0); `wp4-slit-point-overlay` (WP4, M0) |  |
| F110 | Main vs reference (two-stream) blink | yes | could | M3 | `wp5-m3-reference-blink` (WP5, M3) |  |
| F111 | Master time selection (Main / Reference / SJI) | yes | must | M0 | `wp4-time-sync` (WP4, M0) |  |
| F112 | Raster timing offset | yes | should | M0 | `wp4-time-sync` (WP4, M0) |  |
| F113 | Per-raster-step 'Local' timing readout | yes | should | M1 | `wp11-cursor-readout` (WP11, M1) |  |
| F114 | Assemble repeated rasters into a 4D time series | yes | must | — | Available today | Tick 'Stack sequential raster scans' in the browser (iris_loader.ui:107-112), or call raster_data(files, stack=True). Either gives a (scan, step, slit, wavelength) float memmap with a per-pixel datetime64 Time (loaders/iris.py:104-113,153-175; stack_spectrograms.py at 236f0a8). The scan-0 WCS limit is wp1-stack-per-scan-wcs, and per-scan exposure times are an `Exposure time` component (#64). |
| F115 | Multiple raster files with a file slider (per-scan coordinates) | yes | could | M3 | `wp1-stack-per-scan-wcs` (WP1, M3) |  |
| F116 | Multi-exposure-per-position programs (NEXP_PRP > 1) | yes | could | M3 | `wp1-nexp-prp` (WP1, M3) |  |
| F117 | Per-exposure readouts (exposure time, PZT offsets, pointing) | yes | should | — | Available today | Every IRIS dataset has an `Exposure time` component (stacks per scan) and SJIs keep pztx/pzty, xcenix/ycenix and the slit position in meta; the Frame time tool shows '<UTC> · exp N s' with the SJI pointing in its tooltip (#64). |
| F118 | Nearest-in-time SJI panel with consistency check | yes | should | M0 | `wp4-sji-panels` (WP4, M0) |  |
| F119 | SHOW MOVIE from the raster-browser SJI panel | yes | could | M3 | `wp4-playback-extras` (WP4, M3) |  |
| F120 | xsji_image single-channel SJI viewer | yes | should | M3 | `wp11-north-up` (WP11, M3) |  |
| F121 | SJI thumbnails that open the SJI viewer | yes | could | — | Available today | The browser lists each observation's SJI channels as checkboxes (loaders/iris.py:240,262-267), and loaded channels open from the data collection. wp4-sji-panels makes the preset open every selected channel. Thumbnails are deliberately not built, per the plan's 'No IDL clone' non-goal. |
| F122 | iris_sji2map SJI map-movie | yes | wont | — | Available today | SJI files load as 3D Glue cubes with a gWCS time axis (loaders/iris.py:121-142). The time slider and playback replace a map-array movie. irispy SJICube.to_maps exists if a sunpy map sequence is ever needed. |
| F123 | Detector view (iris_xdetector) and CCD layout thumbnails | yes | wont | — | Excluded | detector mosaic (confirmed non-goal) |

## Export (images, movies, data)

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F178 | Image export: snapshot, all frames, line scan | yes | should | M2 | `wp12-sequence-export` (WP12, M2) |  |
| F179 | Movie export (MPEG) | yes | should | M2 | `wp12-sequence-export` (WP12, M2) |  |
| F180 | PostScript/JPG export in every IDL quicklook viewer | yes | could | — | Available today | In any viewer, use toolbar Save → 'Save plot to file' (mpl:save → matplotlib save_figure, glue_qt/viewers/matplotlib/toolbar.py:66-75@0.4.2). A probe in the iris-plan env found these Agg file types: avif, eps, gif, jpeg, jpg, pdf, pgf, png, ps, raw, rgba, svg, svgz, tif, tiff, webp. Docs item wp9-m0-browsing-recipes documents this; the plan's 'No IDL clone' non-goal excludes only the IDL PostScript-device workflow. |
| F181 | Export options (overlays, scale bar, numbering) | yes | could | M3 | `wp12-export-annotations` (WP12, M3) |  |
| F182 | Output file formats (IDL save + raster images; no FITS) | yes | could | M2 | `wp12-derived-data-export` (WP12, M2) |  |
| F183 | Default output file naming | no | wont | M3 | `wp12-export-annotations` (WP12, M3) |  |
| F184 | Light-curve export (.cint) | yes | could | M3 | `wp12-profile-values-export` (WP12, M3) |  |
| F185 | Save space-time diagram (.csav) | yes | could | M2 | `wp12-path-persist` (WP12, M2) |  |
| F186 | Save path for later retrieval (.clsav) | yes | could | M2 | `wp12-path-persist` (WP12, M2) |  |
| F187 | Saving moment products is not available in the IDL quicklook | yes | could | M2 | `wp12-derived-data-export` (WP12, M2) |  |
| F188 | Level-3 FITS generation (non-goal) | yes | wont | — | Excluded | Level-3 writing (confirmed non-goal) |
| F189 | Auxiliary conversion utilities | no | wont | — | Excluded | legacy CRISPEX converters (N/A) |

## Calibration & data quality

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F164 | Missing-data handling (NaN, -200/-199) | yes | must | — | Available today | IRIS rasters, SJIs and stacks load -200/-199 fill as NaN (#54; aligned AIA cutouts -200 only), so it draws transparent and stays out of limits and Mean profiles. Each dataset's '<label> mask' component is isnan(data) as uint8 (#59); +Inf saturation stays data. Docs: wp9-m0-user-guide-corrections, wp9-m0-mask-overlays. |
| F165 | Exposure-time normalisation (DN/s) | yes | should | M1 | `wp1-dn-per-s` (WP1, M1); `wp2-m2-input-quality` (WP2, M2) |  |
| F166 | SJI dust removal | yes | could | M3 | `wp2-irispy-calibration-actions` (WP2, M3) |  |
| F167 | Orbital/thermal wavelength drift correction | yes | could | M3 | `wp5-m3-rest-from-measurement` (WP5, M3) |  |
| F168 | Manual wavelength calibration against photospheric lines | yes | could | M3 | `wp5-m3-rest-from-measurement` (WP5, M3) |  |
| F169 | Radiometric calibration | yes | could | M3 | `wp2-irispy-calibration-actions` (WP2, M3) |  |
| F170 | Saturation check | yes | could | M2 | `wp2-m2-input-quality` (WP2, M2); `wp9-m3-saturation-recipe` (WP9, M3) |  |

## Data discovery & launch

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F001 | Local observation search by directory and time window | yes | could | M3 | `wp8-search-ui` (WP8, M3) |  |
| F002 | Recent time-windows history | yes | wont | M3 | `wp8-search-ui` (WP8, M3) |  |
| F003 | Filename glob search filter | yes | wont | M3 | `wp8-prescan-search` (WP8, M3) |  |
| F004 | Named search patterns with date-tree traversal | yes | could | M3 | `wp8-search-ui` (WP8, M3) |  |
| F005 | Start/Stop search with cancel | yes | should | M2 | `wp8-filter-stop` (WP8, M2) |  |
| F006 | Search directory field, picker and in-list navigation | yes | could | M3 | `wp8-browser-conveniences` (WP8, M3) |  |
| F007 | Persisted search settings | yes | could | M3 | `wp8-browser-conveniences` (WP8, M3) |  |
| F008 | Observation summary list | yes | must | — | Available today | Open 'IRIS: browse observations…'. Each observation is one row showing STARTOBS, OBSID, description (OBS_DESC, falling back to an ObsID decode), XCEN, YCEN and SAT_ROT (scan.py:54-68,101-107 and iris.py:228-239@236f0a8). No OBS_DEC fallback is needed: a header probe of all 130 FITS files in ~/DATA/IRIS (2013-2026, iris-plan env) found OBS_DESC in 129 and OBS_DEC in none; the one file without OBS_DESC is the derived rb_steps file. Docs item: wp9-m0-browsing-recipes. |
| F009 | Group all files of one observation | yes | must | — | Available today | The browser groups every SJI, raster, AIA cutout and archive by OBSID and STARTOBS; deconvolved SJIs list beside the plain ones (#62). |
| F010 | Find an observation's files by time (iris_find_file) | yes | could | M3 | `wp8-prescan-search` (WP8, M3) |  |
| F011 | Open files by double-click or 'Confirm selection' | yes | must | — | Available today | Tick rows or children in the browser and press 'Load selected' (iris.py:195,280-315@236f0a8), or use File→Open, which routes through the 'IRIS Level 2 FITS' data_factory (sources/iris.py:23-28). Non-FITS files are never listed (scan.py:145-150). An optional double-click shortcut is part of wp8-browser-conveniences. Docs item: wp9-m0-browsing-recipes. |
| F012 | Raster opens quicklook controller with matching SJIs | yes | must | M0 | `wp4-launch-entry` (WP4, M0) |  |
| F013 | Preview an SJI movie from the file list | yes | should | — | Available today | Tick an SJI in the browser and press 'Load selected'. The first SJI/AIA cube opens in an Image viewer (sources/iris.py:62-65) with transparent NaN padding (#53). Play it with the slice-widget playback buttons (released glue-qt 0.4.2 data_slice_widget.py:50-89,146) and adjust contrast with the stock stretches (glue/config.py:839-842@1.27.0). The missing gamma stretch belongs to the WP11 scaling item (F062), not here. Docs item: wp9-m0-browsing-recipes. |
| F014 | Print filename to console | yes | could | M3 | `wp8-browser-conveniences` (WP8, M3) |  |
| F015 | Quicklook mode launcher (iris_xcontrol) | yes | must | M0 | `wp4-launch-entry` (WP4, M0) |  |
| F016 | IRIS data search web page | yes | could | — | Excluded | online context and search (excluded by the user, 2026-09-30) |
| F017 | SSW remote query by time/OBSID | yes | could | — | Excluded | online context and search (excluded by the user, 2026-09-30) |
| F018 | Browsable quicklook movies before download | yes | wont | — | Excluded | online context and search (excluded by the user, 2026-09-30) |
| F019 | EIS data sources in iris_xfiles | no | wont | — | Excluded | EIS (confirmed non-goal) |

## Spectral analysis (moments, fits, diagnostics)

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F152 | No line fitting or moment maps in CRISPEX (verified absence) | yes | should | M1 | `wp5-m1-doppler-image` (WP5, M1) |  |
| F153 | Profile moment maps (intensity, velocity, width, errors, continuum) | yes | should | M2 | `wp2-m2-moment-maps` (WP2, M2); `wp2-m2-tests-docs` (WP2, M2); `wp2-m3-moments-extensions` (WP2, M3) |  |
| F154 | Define Line / moments prep tool (line and continuum windows) | yes | should | M2 | `wp2-m2-line-definition` (WP2, M2); `wp2-m3-moments-extensions` (WP2, M3) |  |
| F155 | Continuum-subtracted intensity map (iris_xmap) | yes | should | M2 | `wp2-m2-line-definition` (WP2, M2); `wp2-m2-tests-docs` (WP2, M2) |  |
| F156 | Moment/fit product selector and plot limits | yes | should | M2 | `wp2-m2-tests-docs` (WP2, M2) |  |
| F157 | Single-Gaussian fit maps | yes | could | M4 | `wp6-glue-fit-tool` (WP6, M4) | Fitting moved to glue's Fit tool, later (user, 2026-09-30). |
| F158 | Double-Gaussian fit with red-blue asymmetry | yes | could | M3 | `wp2-m3-red-blue` (WP2, M3); `wp6-glue-fit-tool` (WP6, M4) | The RB map is M3; the double-Gaussian fit is a model in the later fit tool. |
| F159 | Template multi-Gaussian fitting and fit viewer (iris_auto_fit, iris_fit_viewer) | yes | wont | M4 | `wp6-glue-fit-tool` (WP6, M4) |  |
| F160 | Window data with errors, calibration and binning (iris_getwindata) | yes | could | M3 | `wp2-m3-window-data` (WP2, M3) |  |
| F161 | Region-averaged spectrum with interactive fit | yes | should | M4 | `wp6-glue-fit-tool` (WP6, M4) | Today the stock Fit tab fits its own models to a Pixel-point or ROI-mean spectrum. |
| F162 | Mg II k/h feature extraction | yes | could | M3 | `wp2-m3-mg-features` (WP2, M3) |  |
| F163 | Density and temperature diagnostics | yes | wont | M3 | `wp2-m3-density-temperature` (WP2, M3) |  |

## Coordinates, WCS & co-alignment

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F049 | Cross-dataset pixel mapping via WCS | yes | must | M1 | `wp1-m4-autolink-matrix` (WP1, M4); `wp4-sji-click-to-raster` (WP4, M1) |  |
| F050 | Time-dependent SJI pointing and slit geometry | yes | must | M0 | `wp1-m0-link-hpc` (WP1, M0) |  |
| F051 | OFFSET_SJI arcsec offset | yes | could | M3 | `wp1-m3-pointing-offset` (WP1, M3) |  |
| F052 | Channel/SJI co-alignment check (fiducials, yshift) | yes | could | M3 | `wp1-m3-pointing-offset` (WP1, M3) |  |
| F053 | Raster scan direction (west-to-east scans) | yes | should | — | Available today | irispy 0.9.1 reverses STEPS_AV < 0 rasters with their mask and per-step metadata, and glue-solar keeps that orientation (longitude grows with step); a remote-data test on 3400109360 checks it (#65). |
| F054 | Roll-angle handling | yes | should | M3 | `wp11-north-up` (WP11, M3); `wp1-m4-autolink-matrix` (WP1, M4) | Rolled SJIs already carry their roll in the WCS that `link_hpc` and the readouts use |
| F055 | Multi-instrument co-registered browsing (IRIS + SST/AIA) | yes | could | M3 | `wp1-m3-multi-instrument` (WP1, M3) |  |

## Stokes/polarimetry

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F171 | Stokes component selection | no | wont | — | Excluded | Stokes (N/A to IRIS) |
| F172 | Multi-Stokes detailed spectra | no | wont | — | Excluded | Stokes (N/A) |
| F173 | Stokes continuum scaling and noise level (SCALE_STOKES) | no | wont | — | Excluded | Stokes (N/A) |
| F174 | Stokes cubes as main and reference data | no | wont | — | Excluded | Stokes (N/A) |

## Data input, formats & large-data performance

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F020 | CRISPEX entry-point keyword set | yes | could | M0 | `wp4-launch-entry` (WP4, M0) |  |
| F021 | Main image cube input (imcube) | yes | must | — | Available today | File→Open uses the IRIS Level 2 data_factory (sources/iris.py:23-28, priority 200 over glue's FITS reader), or Plugins → 'IRIS: browse observations…' (sources/iris.py:47-65). raster_data/image_data load single scans, per-scan datasets, a 4D stack or a sit-and-stare cube through irispy (loaders/iris.py:133-175@236f0a8), and `glue file.glu` restores a session in place of data. Reads are eager (memmap=False); lazy access is tracked in wp10-m2-lazy-loading and docs in wp9-m0-scripting-recipe. |
| F022 | Spectral (transposed) cube input (spcube) | yes | wont | — | Available today | spcube: IDL I/O workaround; Glue reads any axis pair (fast lambda-t access is F035). No transposed cube is needed: choose wavelength and exposure as the Image viewer axes; on irispy 0.9.1 that λ–t image equals `cube[:, y, :]` and takes 0.070 s per slit step on 4000255147 Si IV. |
| F023 | Data-cube ordering convention (folded third axis) | no | wont | — | Excluded | SST folded-cube storage (N/A) |
| F024 | FITS header parsing (axes, WCS, units, scaling, IRIS keywords) | yes | must | M1 | `wp1-m1-wrapper-coherence` (WP1, M1) |  |
| F025 | IRIS Level-3 im/sp FITS input and extensions | yes | wont | M3 | `wp8-m3-level3-input` (WP8, M3) |  |
| F026 | Select which spectral windows to load or process | yes | must | — | Available today | The browser shows one checkbox per spectral window and passes the ticked ones to raster_data(files, windows=...), i.e. irispy spectral_windows (loaders/iris.py:153-175); each window stays its own dataset with its own grid and scaling. File→Open loads every window. Documented in wp9-m0-scripting-recipe. |
| F027 | SOLARNET tabulated (-TAB) WCS support | no | wont | — | Excluded | SST SOLARNET -TAB loader (N/A; IRIS -TAB is WP3) |
| F028 | Legacy 'La Palma' CRISPEX binary cube format | no | wont | — | Excluded | SST La Palma format (N/A) |
| F029 | SINGLE_CUBE keyword | no | wont | — | Excluded | SST SINGLE_CUBE keyword (N/A) |
| F030 | Height-profile / simulation-cube mode | no | wont | — | Excluded | simulation height cubes (outside IRIS scope) |
| F031 | SPECTFILE normalised/average spectrum file | no | wont | M0 | `wp9-m0-user-guide-corrections` (WP9, M0) | SPECTFILE: the mean-spectrum reference is a full-dataset Profile with function Mean (glue's default is Maximum) |
| F032 | SCALE_CUBES multiplicative factor | no | wont | — | Available today | Data collection → 'Arithmetic attributes' (ArithmeticEditorWidget, glue_qt/app/application.py:423,487@0.4.2) defines a scaled derived component, e.g. `<window> * 2.5`. Documented in wp9-m0-browsing-recipes ('Arithmetic scaling'). |
| F033 | Programmatic access to the browsed cube | yes | should | M0 | `wp9-m0-scripting-recipe` (WP9, M0) |  |
| F034 | Memory-mapped lazy cube access | yes | should | M2 | `wp10-m2-lazy-loading` (WP10, M2) |  |
| F035 | Fast spectrum-vs-time access via sp cube; deferred updates without it | yes | must | — | Available today | On irispy 0.9.1 (no step index in the raster WCS) a spectrogram slider step takes 0.049-0.050 s at any exposure of the 1600-exposure 4000255147 Si IV raster, and a λ–t (wavelength × exposure) slit step 0.070 s, measured offscreen on main 0621253. |
| F036 | Sit-and-stare chunking | yes | could | M3 | `wp10-m3-sit-stare-chunks` (WP10, M3) |  |

## Main image display, scaling & colour

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F056 | Main image window (monochromatic raster image) | yes | must | M0 | `wp4-quicklook-preset` (WP4, M0) |  |
| F057 | Image-type toggle: X-Y (time-Y) vs lambda-Y | yes | must | M0 | `wp4-quicklook-preset` (WP4, M0) |  |
| F058 | Physical-unit axes (arcsec, Angstrom) vs pixel toggle | yes | must | M1 | `wp1-m1-wrapper-coherence` (WP1, M1) |  |
| F059 | Per-display colour tables incl. IRIS/AIA tables | yes | should | M1 | `wp11-raster-cmap` (WP11, M1) |  |
| F060 | Colour bars on image displays | yes | should | M2 | `wp11-colourbar` (WP11, M2) |  |
| F061 | Histogram-optimisation percentile clipping (IRIS_HISTO_OPT) | yes | must | M1 | `wp11-histo-opt-scaling` (WP11, M1) |  |
| F062 | Gamma (power-law) contrast | yes | should | M1 | `wp11-gamma-stretch` (WP11, M1) |  |
| F063 | Manual min/max limits, linear/log stretch, reset/auto | yes | must | — | Available today | The Image viewer's layer style editor has v_min/v_max, percentile presets, stretch (log among them, glue/config.py:839-842@1.27.0), flip, contrast/bias and reset, plus the image:contrast_bias drag tool. Documented by wp9-m0-viewer-tools-docs. |
| F064 | Scaling basis (first / current / per-time-step / key frame) | yes | should | M1 | `wp11-histo-opt-scaling` (WP11, M1) |  |
| F065 | Independent scaling per display and per spectral window | yes | must | M0 | `wp4-quicklook-preset` (WP4, M0) |  |
| F066 | IRIS_INTSCALE standard movie scaling | yes | could | M3 | `wp11-scaling-extras` (WP11, M3) |  |
| F067 | Slice scaling and interpolation preferences | yes | could | M3 | `wp11-scaling-extras` (WP11, M3) |  |

## Temporal navigation & playback

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F085 | Frame slider and playback controls | yes | must | — | Available today | Image-viewer slice sliders (Profile sliders arrive with Qt #70) have first/prev/back/stop/forward/next/last buttons driven by a QTimer (glue_qt/viewers/common/data_slice_widget.py:81-83,146-193 at glue-qt 0.4.2). The interval is round(500/\|n\|) ms, speeding up with repeated presses, and playback wraps. A focused slider steps with the arrow keys. Playback docs are in wp9-m0-browsing-recipes; the Tab/Backspace limits are in wp9-m0-viewer-tools-docs. CRISPEX-style frame shortcuts belong to the WP11 keyboard item (F197). |
| F086 | Playback modes: loop / cycle / temporal blink | yes | could | M3 | `wp4-playback-extras` (WP4, M3) |  |
| F087 | Animation speed and frame increment | yes | could | M3 | `wp4-playback-extras` (WP4, M3) |  |
| F088 | Temporal range restriction | yes | should | M1 | `wp4-time-controls` (WP4, M1) |  |
| F089 | DT and physical time-axis labelling | yes | should | M1 | `wp12-time-regrid` (WP12, M1) |  |
| F090 | Non-equidistant timing in spectrum-time display | yes | should | M1 | `wp12-time-regrid` (WP12, M1) |  |
| F091 | Jump to a given UTC time | yes | should | M1 | `wp4-time-controls` (WP4, M1) |  |
| F092 | Spectrogram animation ('Create Animation') | yes | should | — | Available today | Load a raster (default view wavelength × slit, the spectrogram) and press play on its step/exposure slider (data_slice_widget.py playback). Documented in wp9-m0-browsing-recipes (playback) and wp9-m0-workflow-recipes (spectrogram axes); movie export is the WP12 movie item (F178/F179). |
| F093 | Event-finding workflow (TR brightenings, flares) | yes | must | M0 | `wp4-tests` (WP4, M0) | The IRIS-9 tutorial and its acceptance run were dropped (user, 2026-09-30); the per-interaction matrix covers the clicks. |

## Sessions, state & preferences

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F175 | Session save / load (.cses) | yes | must | M1 | `wp3-app-session-acceptance` (WP3, M1) |  |
| F176 | Automatic last-session save and reload | yes | could | M3 | `wp3-last-session` (WP3, M3) |  |
| F177 | Preferences window | yes | could | — | Available today | The Preferences dialog (colours, theme, font) loads plugin panes from the preference_panes registry (glue_qt/config.py:218@0.4.2). IRIS display defaults are per dataset (wp11-raster-cmap). Browser search settings persist in QSettings beside iris/last_dir (wp8-search-ui, wp8-browser-conveniences, M3). No Preferences pane is planned. |

## Spectral navigation & spectrum panels

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F068 | Main spectral position slider and stepping across windows | yes | must | M1 | `wp4-m1-spectral-coupling` (WP4, M1) |  |
| F069 | Default starting wavelength | yes | should | M0 | `wp4-quicklook-preset` (WP4, M0) |  |
| F070 | Reference spectral position and lock to main | yes | could | — | Available today | Separate Image viewers of one raster keep independent wavelength sliders. For the lock, Profile Options → Navigate moves the wavelength slice of every open Image viewer showing that dataset together (glue_qt/viewers/profile/profile_tools.py:140-161 @ glue-qt 0.4.2, iris-plan env). Caveat: on 0.4.2, Navigate lands on the wrong slice when the display unit is not the native one ('slice 28, expected 20' in review_20260927/feas.json, spectral-marker entry). WP1's native Å or Qt #70 fixes this. Documented by wp9-m0-workflow-recipes. |
| F071 | Detailed spectrum window | yes | must | M0 | `wp4-quicklook-preset` (WP4, M0) |  |
| F072 | Multiple IRIS spectral windows shown side by side | yes | should | M1 | `wp4-m1-multi-window` (WP4, M1) |  |
| F073 | Diagnostics (spectral window) visibility selection | yes | should | M1 | `wp4-m1-multi-window` (WP4, M1) |  |
| F074 | Per-column wavelength-window menu (raster browser) | yes | could | M1 | `wp4-m1-multi-window` (WP4, M1) |  |
| F075 | Spectral/velocity range restriction (global or per window) | yes | should | M1 | `wp4-m1-spectral-coupling` (WP4, M1) |  |
| F076 | Spectral (two-wavelength) blink | yes | should | M1 | `wp5-m1-spectral-blink` (WP5, M1) |  |
| F077 | Spectrum plot y-range and plot styling | yes | could | — | Available today | Profile Options y_min/y_max (glue/viewers/matplotlib/state.py:127-128@1.27.0), per-layer linewidth (glue/viewers/profile/state.py:349) and the axes-editor label/tick sizes. The CRISPEX replay step 02 set ylim (-5, 50). Noted in wp9-m3-spectral-recipes. |
| F078 | Per-window spectral multiplier | yes | could | — | Available today | Each window gets its own Profile viewer, which autoscales on its own (wp4-m1-multi-window). Profile Normalize rescales each layer to [0,1] (glue/viewers/profile/state.py:50-51,411-412@1.27.0). The -200/-199 fill that set the normalised range (replay step 02 gave (-200, 7.25)) loads as NaN on main since #54. Noted in wp9-m3-spectral-recipes. |
| F079 | Compare detailed spectrum with the average spectrum | yes | could | M3 | `wp5-m3-mean-spectrum-compare` (WP5, M3) |  |
| F080 | Average-spectrum time range (MNSPEC) | yes | could | M3 | `wp9-m3-spectral-recipes` (WP9, M3) |  |
| F081 | Custom plot axis titles (XTITLE/YTITLE) | no | wont | — | Available today | Axis-label text fields in the Profile axes editor (glue_qt/viewers/matplotlib/axes_editor.ui:82,175). The Profile rewrites the x label when x_att changes (glue/viewers/profile/viewer.py:15-31@1.27.0). Priority 'wont', so no further work. Noted in wp9-m3-spectral-recipes. |
| F082 | Warping of non-equidistant sampling (NO_WARP) | yes | wont | M0 | `wp4-m0-time-wavelength-panels` (WP4, M0) | NO_WARP: IRIS wavelength equidistant; irregular time handled by WP4 time axes |
| F083 | Wavelength-pixel band averaging (raster browser) | yes | could | M3 | `wp11-band-average` (WP11, M3) |  |
| F084 | Photospheric context check (sunspot/pore) | yes | could | M3 | `wp9-m3-spectral-recipes` (WP9, M3) |  |

## Derived diagrams & light curves

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F134 | Spectrum-time (lambda-t) diagram at the cursor | yes | must | M0 | `wp4-m0-time-wavelength-panels` (WP4, M0) |  |
| F135 | Spectrum along a virtual slit (spectral phi-slice) | yes | should | M2 | `wp12-path-slicer` (WP12, M2) |  |
| F136 | Draw multi-point path with feedback | yes | should | — | Available today | The stock Slice tool's ClickRoiMode path: a click adds a vertex, dragging updates it, Enter finishes and Esc aborts (glue/viewers/matplotlib/toolbar_mode.py:188-230@1.27.0; used by glue_qt pv_slicer and core BasePathSlicerMode). Remove-last-vertex, a spline and rubber-band preview are accepted gaps. Saved paths are covered in wp12-path-overlays-slopes. Documented by wp9-m0-workflow-recipes. |
| F137 | Space-time (x-t) diagram along a path | yes | should | M2 | `wp12-path-slicer` (WP12, M2) |  |
| F138 | Nearest-neighbour vs interpolated slice sampling (EXTS) | yes | could | M3 | `wp12-path-batch` (WP12, M3) |  |
| F139 | Batch extraction from saved paths | yes | could | M3 | `wp12-path-batch` (WP12, M3) |  |
| F140 | Multi-wavelength light curves at the cursor pixel | yes | should | M2 | `wp12-point-light-curves` (WP12, M2) |  |
| F141 | Multi-cadence light-curve comparison (spectra + SJI) | yes | should | M2 | `wp12-point-light-curves` (WP12, M2) |  |
| F142 | Sit-and-stare slit-position vs time image | yes | must | M0 | `wp4-m0-time-wavelength-panels` (WP4, M0) |  |
| F143 | Whisker view (iris_xwhisker) | yes | should | M0 | `wp4-m0-time-wavelength-panels` (WP4, M0) |  |
| F144 | Per-position spectrogram panel grid (iris_xraster 'Spectroheliogram') | yes | wont | — | Available today | The default raster view is the wavelength × slit spectrogram, and the step slider (with playback) moves through each raster position's panel. A per-position panel grid falls under the plan's 'No IDL clone' non-goal; wp9-m0-workflow-recipes explains that iris_xraster's 'Spectroheliogram' is the per-position spectrogram. |
| F145 | Row/column cut plot (iris_xlineplot) | yes | could | M3 | `wp9-m3-spectral-recipes` (WP9, M3) |  |

## Cursor/position inspection, zoom & lock

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F094 | Live hover cursor synchronised across image windows | yes | should | M1 | `wp4-m1-hover-lock-tool` (WP4, M1) |  |
| F095 | Cursor lock/unlock and mouse bindings | yes | must | M1 | `wp4-m1-hover-lock-tool` (WP4, M1) |  |
| F096 | Numeric X/Y position sliders | yes | should | M0 | `wp4-m0-point-fixed-index` (WP4, M0) |  |
| F097 | Zoom controls (fit, true 1:1, factors, box zoom) | yes | should | M2 | `wp11-zoom-steps` (WP11, M2) |  |
| F098 | Pan / select mode and go-to-cursor | yes | could | M3 | `wp11-centre-on-point` (WP11, M3) |  |
| F099 | Parameter overview panel | yes | should | M1 | `wp11-selected-point-panel` (WP11, M1) |  |
| F100 | Per-dataset coordinate readout (pixel and arcsec) | yes | must | M1 | `wp11-cursor-readout` (WP11, M1) |  |
| F101 | Wavelength, Doppler, time and value readout | yes | must | M1 | `wp11-cursor-readout` (WP11, M1) |  |
| F102 | Raster browser linked image/spectrum panels with pixel selection | yes | must | M0 | `wp4-m0-point-fixed-index` (WP4, M0) |  |

## Layout, windows, help & shortcuts

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F190 | Launch with a coordinated default window layout | yes | must | M0 | `wp4-quicklook-preset` (WP4, M0) |  |
| F191 | Control panel with menus and tabs | yes | could | M1 | `wp11-selected-point-panel` (WP11, M1) | control-panel clone excluded; its useful part is the parameter overview F099 + preset |
| F192 | Displays tab window toggles | yes | could | M0 | `wp9-m0-viewer-tools-docs` (WP9, M0) |  |
| F193 | Window sizing (1:1, WINDOW_LARGE, aspect, nx=1 stretch) | yes | should | M1 | `wp11-physical-aspect` (WP11, M1) |  |
| F194 | Resizable plot windows | yes | should | — | Available today | Every viewer is a resizable QMdiSubWindow (glue-qt mdi_area.py). Documented by wp9-m0-viewer-tools-docs. |
| F195 | Gather windows / bring all to front | yes | could | — | Available today | Canvas > Gather Windows (Ctrl+G) tiles the subwindows (glue_qt/app/application.py:861-863@0.4.2). 'Bring to front' does not apply to a single MDI main window. Documented by wp9-m0-viewer-tools-docs. |
| F196 | Multiple simultaneous instances and window IDs | no | wont | — | Available today | Covered by equivalents: separate glue processes run side by side, tabs can be renamed (Canvas > Rename Tab), and comparing windows maps to the WP5 blink checkbox. IDL window IDs have no counterpart. |
| F197 | Keyboard shortcuts (menu accelerators only) | yes | should | M1 | `wp11-keyboard-shortcuts` (WP11, M1) |  |
| F198 | Shortcut overview window | yes | could | M3 | `wp9-m3-shortcuts-help` (WP9, M3) |  |
| F199 | Online / in-app help and issue reporting | yes | could | M3 | `wp9-m3-shortcuts-help` (WP9, M3) |  |
| F200 | About window and release notes | no | wont | — | Available today | Help > Version information lists every installed distribution, including glue-solar (application.py:817-822@0.4.2). Release notes come from the towncrier changelog, and auto-showing them is not needed. |
| F201 | Start-up progress window, precomputation and set-up warnings | yes | should | M1 | `wp10-nonblocking-load` (WP10, M1) |  |
| F202 | Developer menu (verbosity, interrupt, statistics, window IDs) | no | wont | — | Available today | `glue -v` for verbosity, `--faulthandler`, View > Console Log and Plugins > Plugin Manager (glue-qt main.py and application.py@0.4.2). |
| F203 | Raster-browser layout and legacy options (RETINA, YOFFSETS, NO_SJI) | yes | could | M4 | `wp0-qt68-macos-pass` (WP0, M4) |  |

## Observation metadata & external context

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F037 | FITS header viewer | yes | should | M0 | `wp9-m0-viewer-tools-docs` (WP9, M0) |  |
| F038 | Observation date and OBSID labels | yes | must | — | Available today | The browser shows STARTOBS and OBSID columns (loaders/iris_loader.ui:62-67@main), and every dataset label embeds OBSID-STARTOBS (loaders/iris.py _observation_label@main). DATE_OBS is available via Ctrl+I. |
| F039 | Spectral-window line list / observation info panel | yes | could | M3 | `wp8-browser-metadata` (WP8, M3) |  |
| F040 | Observation metadata summary (xcontrol labels, raster-browser Metadata tab) | yes | could | M3 | `wp8-browser-metadata` (WP8, M3) |  |
| F041 | HCR observation metadata | yes | could | — | Excluded | online context and search (excluded by the user, 2026-09-30) |
| F042 | OBS XML tables viewer | yes | wont | — | Excluded | OBS XML viewer (user kept as non-goal 2026-09-27) |
| F043 | Pipeline log-file viewer | yes | wont | — | Excluded | pipeline log viewer (user kept as non-goal 2026-09-27) |
| F044 | GOES light curve with selected-exposure marker | yes | could | — | Excluded | online context and search (excluded by the user, 2026-09-30) |
| F045 | SWPC flare list | yes | could | — | Excluded | online context and search (excluded by the user, 2026-09-30) |
| F046 | Full-disk AIA pointing context with IRIS FOV outline | yes | could | — | Excluded | online context and search (excluded by the user, 2026-09-30) |
| F047 | IRIS_getAIAdata co-aligned AIA request GUI | yes | could | — | Excluded | online context and search (excluded by the user, 2026-09-30) |
| F048 | Co-temporal Hinode/EIS observation list | no | wont | — | Excluded | EIS (confirmed non-goal) |

## Overlays, masks, detections & measurement

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F124 | Mask cube input and contour overlay | yes | could | — | Available today | IRIS masks load as a boolean '<label> mask' component (loaders/iris.py:86-87@d4f3cfd). An x-range selection in a Histogram viewer, or 'Create faceted subsets', gives a subset that is drawn as a filled overlay in every viewer of that dataset. A probe in the iris-plan env confirmed that a bool component has kind 'numerical' and that RangeSubsetState(0.5,1.5) selects exactly the masked pixels. An external integer FITS mask cube with the dataset's shape loads through the layer action 'Import subset mask(s)' (glue/io/formats/fits/subset_mask.py@1.27.0); masknt=1 cubes must be broadcast first. Contours are not built; a filled subset with alpha is the equivalent. Docs item: wp9-m0-mask-overlays. |
| F125 | Raster slit-position overlay (whole raster footprint) | yes | should | M1 | `wp4-raster-overlays` (WP4, M1) |  |
| F126 | Raster timing marker (current exposure) | yes | should | M1 | `wp4-raster-overlays` (WP4, M1) |  |
| F127 | Overlay saved paths and reopen their slices | yes | could | M3 | `wp12-path-overlays-slopes` (WP12, M3) |  |
| F128 | Overlay and marker styling | yes | could | — | Available today | Each viewer's layer style editor sets colour, alpha and linewidth per layer. Preferences sets foreground and background, the default data colour and alpha, and the font size (glue-qt app/preferences.py). Docs item: wp9-m0-browsing-recipes (style editor and Preferences bullet). |
| F129 | Space-time extraction from a detection file | no | wont | — | Excluded | SST detection files (N/A) |
| F130 | UV burst detection | yes | could | M3 | `wp2-burst-detection` (WP2, M3) |  |
| F131 | Spatial distance measurement | yes | should | M2 | `wp11-distance-measure` (WP11, M2) |  |
| F132 | TANAT speed/acceleration measurement on space-time diagrams | yes | could | M3 | `wp12-path-overlays-slopes` (WP12, M3) |  |
| F133 | Timestamp overlay on movie frames | yes | could | M3 | `wp12-export-annotations` (WP12, M3) |  |

## Doppler/velocity & line identification

| ID | Feature | IRIS | Priority | Milestone | Where | Note |
| --- | --- | --- | --- | --- | --- | --- |
| F146 | LINE_CENTER keyword | no | wont | M1 | `wp5-m1-rest-wavelength-policy` (WP5, M1) | LINE_CENTER: rest-wavelength override (WP5) |
| F147 | Doppler velocity axes and readouts per window (TWAVE) | yes | must | M1 | `wp5-m1-velocity-axis` (WP5, M1) |  |
| F148 | In-program Doppler (wing-difference) image | yes | should | M1 | `wp5-m1-doppler-image` (WP5, M1) |  |
| F149 | Dopplergram at +/-v with explicit rest wavelength and sign convention | yes | should | M1 | `wp5-m1-doppler-image` (WP5, M1) |  |
| F150 | Velocity axis referenced to the selected wavelength (raster browser) | yes | could | M3 | `wp5-m3-rest-from-measurement` (WP5, M3) |  |
| F151 | Line identification labels (CHIANTI line table) | yes | should | M1 | `wp5-m1-line-list` (WP5, M1) |  |

