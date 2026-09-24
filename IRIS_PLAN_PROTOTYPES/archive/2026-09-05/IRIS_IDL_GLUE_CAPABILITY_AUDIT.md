> Historical snapshot, archived 2026-09-05. Not an active checklist.
> Original location: `glue-solar/IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`. Body preserved verbatim; paths and status claims describe that original context and may be stale.
> Current instructions: [the central work plan](../../../IRIS_GLUE_GAP_PLAN.md).

# IRIS IDL and Glue Capability Audit

## Scope

This document audits the user-visible routines launched by the SolarSoft IDL
`iris_xfiles` workflow and compares them with the current `glue-solar` IRIS
observation browser.

The inventory follows the launch chain from `iris_xfiles` into the IRIS
quicklook controller and its viewers. It does not list internal widget event
handlers, plotting helpers, or implementation-only procedures.

The current plugin does not execute IDL or launch any of these SolarSoft
routines. It reads local files with `irispy`, converts the results to Glue
datasets, and relies on standard Glue viewers and manual coordinate linking.

Glue-side statements were re-verified on 2026-09-02 against glue-core 1.27.0,
glue-qt main (9780eaf9), irispy-lmsal 0.8.1, ndcube 2.4.1 and astropy 8.0.1.

A companion plan for closing the gaps identified below lives in
[`IRIS_GLUE_GAP_PLAN.md`](IRIS_GLUE_GAP_PLAN.md).
The 2026-09-05 cross-repository review and local fix status are in
[`IRIS_BRANCH_REVIEW.md`](IRIS_BRANCH_REVIEW.md). Prototype fixes are not
shipped capabilities; in particular, production IRIS sessions remain unsupported.

## SolarSoft launch hierarchy

```text
iris_xfiles
├── IRIS raster
│   └── iris_xcontrol
│       ├── iris_xdetector
│       ├── iris_raster_browser
│       │   └── iris_xwhisker
│       ├── iris_xraster
│       ├── iris_xwhisker
│       ├── iris_xmap
│       │   ├── iris_xlineplot
│       │   └── xmoment_moment
│       ├── iris_moment -> iris_xmap
│       ├── xsji_image -> SJI movie
│       ├── sdo_icon -> xpointing_image
│       └── iris_make_fits_level3
├── IRIS SJI
│   └── iris_sji -> ximovie / iris_ximovie
├── IRIS observing tables
│   └── IRISsim_showXML
├── EIS CCSDS or non-Level-2 FITS
│   └── xcontrol
├── EIS Level-2 FITS
│   └── xmap
└── EIS housekeeping
    └── hk_packet
```

## Routines launched directly by `iris_xfiles`

| Selection or action | Routine | What it does |
| --- | --- | --- |
| IRIS raster FITS | `iris_xcontrol` | Builds an IRIS data object from the raster and associated SJI files, then opens the main quicklook controller. |
| IRIS SJI FITS | `iris_sji` object `ximovie` method | Opens the slit-jaw sequence in the IRIS movie viewer when the file dimensions are valid. |
| Show OBS tables | `IRISsim_showXML` | Resolves observing-program XML dependencies and displays the selected OBS tables. |
| IRIS log file | Internal `iris_xfiles` log window | Shows the text contents of a selected log file. |
| EIS CCSDS | `xcontrol` | Opens the EIS quicklook controller with EIS data, header, and auxiliary objects. |
| EIS Level-2 FITS | `xmap` | Displays the Level-2 moment products for all EIS windows. |
| Other EIS FITS | `xcontrol` | Opens the EIS quicklook controller. |
| EIS housekeeping | `hk_packet` | Opens the housekeeping packet display. |

EIS support is part of `iris_xfiles`, but it is outside the stated IRIS scope
of the current Glue plugin and will not be added (decided 2026-08-29).

## IRIS quicklook routines launched by `iris_xcontrol`

| Routine | User-facing mode | What it does |
| --- | --- | --- |
| `iris_xdetector` | Detector | Displays selected spectral windows as wavelength versus slit position at a selected raster position or time. It provides raster/exposure selection, wavelength and slit units, scaling, color control, profiles, zooming, animation, and image export. |
| `iris_raster_browser` | Browser | Provides coordinated raster images and spectra. Mouse selections in one view update the other. It can show matching SJI data, GOES context, line identifications, wavelength or velocity coordinates, multiple rasters, and chunked sit-and-stare observations. |
| `iris_xraster` | Spectroheliogram | Displays wavelength-versus-slit panels for every raster position and selected spectral window. It supports scale changes, colors, animation, and PostScript/JPEG output. |
| `iris_xwhisker` | Whisker | Displays wavelength versus raster position, or wavelength versus time for sit-and-stare data, at a selected slit position. It provides slit selection, profiles, animation, colors, and export. |
| `iris_xmap` | Intensity map | Calculates or displays a zeroth-moment line-intensity map as solar-y versus solar-x, or solar-y versus time for sit-and-stare observations. It supports line selection, row/column profiles, scaling, colors, zooming, and export. |
| `iris_moment` followed by `iris_xmap` | Profile Moments | Calculates line-profile moments and displays the resulting maps. |
| `iris_moment` followed by `iris_xmap` | Single Gaussian Fit | Fits one Gaussian to selected lines and displays fit-result maps. |
| `iris_moment` followed by `iris_xmap` | Double Gaussian Fit | Fits two Gaussians to selected lines and displays fit-result maps. |
| `xsji_image` | SJI thumbnail/viewer | Displays a selected SJI channel and exposure, optionally overlays raster slit positions, switches logarithmic scaling, exports images, and launches the SJI movie viewer. |
| `sdo_icon` followed by `xpointing_image` | Pointing context | Retrieves a co-temporal SDO context image, rotates it to the observation time, and overlays the IRIS field of view. |
| `iris_make_fits_level3` | Generate Level 3 | Generates Level-3 FITS files for selected spectral lines, with options for SJI inclusion and replacement of existing products. |

### Secondary viewer launches

The quicklook viewers can open additional focused tools:

- `iris_xlineplot` plots selected detector, map-row, map-column, or spectral
  profiles.
- `iris_ximovie` provides forward/reverse/cyclic playback, frame-range and
  speed controls, blinking or mixing two streams, contrast controls, zooming,
  and snapshot or sequence export.
- `xmoment_moment` lets the user define or adjust a line before recalculating
  moment products.
- Zoom and color-table helpers provide interactive inspection shared by the
  quicklook viewers.

## What the current Glue plugin does

The implementation is split between
[`glue_solar/sources/iris.py`](glue_solar/sources/iris.py),
[`loaders/iris.py`](glue_solar/sources/loaders/iris.py), and
[`loaders/scan.py`](glue_solar/sources/loaders/scan.py).

### Observation discovery and selection

- Scans a selected local directory, recursively by default.
- Remembers the last selected directory.
- Groups files by OBSID and observation start time.
- Shows observation description, pointing, rotation, and file count.
- Lists SJI channels, raster spectral windows, and local aligned AIA cutouts.
- Recognizes pooch-prefixed filenames.
- Lists unexpanded raster or SDO archives and extracts them transactionally
  next to the archive.
- Allows an observation, channel, or spectral window to be selected with
  checkboxes.

### Data loading and representation

- Uses `irispy.io.read_files` for IRIS raster, SJI, and aligned AIA data.
- Creates one Glue dataset per SJI/AIA cube or raster scan and spectral window.
- Preserves the science array, bad-pixel mask, units, metadata, primary WCS,
  and exact raster exposure times.
- Names the wavelength and helioprojective world axes only where irispy leaves
  them unnamed: raster datasets expose `Helioprojective Longitude`,
  `Helioprojective Latitude` and `Wavelength`, while SJI datasets keep irispy's
  gWCS names `Longitude`, `Latitude` and `Time (UTC)`. Helioprojective
  coordinates are presented in arcseconds with longitude normalized to signed
  values; wavelength is exposed in metres today (Angstrom after WP1).
- Can optionally stack sequential raster scans without resampling as a 4-D
  dataset with a leading `Scan` coordinate and an exact per-pixel `Time`
  component.
- Registers an IRIS data factory for **File -> Open Data Set**.
- Adds browser selections through Glue's normal dataset path. Spatial links
  must currently be created manually: released glue-core (1.27.0) only offers
  `BaseHighLevelWCS` coordinates to `wcs_autolink`
  (`wcs_autolinking.py:321`), and the plugin's `_GlueWCS` is a low-level
  `BaseWCSWrapper`, so IRIS datasets are skipped (0 links; a direct
  `WCSLink(sji, raster)` raises `AttributeError: has_celestial`). The raw
  irispy gWCS and `-TAB` objects would crash `wcs_autolink` outright. The fork
  branch `glue:ape14-wcs-autolink` (draft PR glue-viz/glue#2595) fixes this and yields one SJI-raster
  helioprojective `WCSLink`, exact at the first exposure only (see the
  temporal-coordination row below).
- Opens the first selected SJI or AIA cube in Glue's Image Viewer.

The optional 4-D representation is a Glue visualization feature, not
functionality supplied by `irispy` or required to reproduce `iris_xfiles`.
It keeps each scan's raster indices, exact acquisition times and mask; the
stacked array is a float32 temp-file memmap in which masked pixels (-200 in
the files) are stored as NaN and the mask is rebuilt from `isfinite` (same
pixel count). Only unstacked per-scan datasets keep the raw detector values.
Scan 0 supplies the stack's nominal spatial WCS; later scans' distinct
absolute helioprojective pointings are available only when those scans are
loaded separately. A per-scan stack WCS needs no glue-core change: a `gwcs`
model built from `astropy.modeling.tabular.tabular_model(3)` over the stacked
`-TAB` lookup tables reproduces every scan's own coordinates exactly in the
forward direction; the missing piece is an inverse model
(`world_to_pixel_values` fails), which links and subsets require.

Glue sessions containing IRIS datasets cannot currently be saved: **File ->
Save Session** raises before anything is written. SJI datasets fail on the
unserializable `_GlueWCS`; rasters and stacks fail first on the two
`Quantity` values in irispy's `SGMeta` (`exposure time`, `observer radial
velocity`, `TypeError` from `numpy.save`), then on `_GlueWCS`; with coords
removed, the `Colormap` object in `preferred_cmap` raises a JSON `TypeError`.
The SJI metadata (148 keys) already round-trips, and glue-core silently drops
`Time`/`SkyCoord` meta values. glue's stock `@saver(WCS)` would save the
`-TAB` header without its table and fail on reload. No glue-core or
glue-astronomy saver is required: a `__gluestate__` on `_GlueWCS` (asdf for
the gWCS, a rebuild of the `-TAB` table from `Tabprm.coord`, a recursive
record for sliced/compound WCS) plus a version-2 `VisualAttributes` saver is
about 60 lines of glue-solar code and round-trips SJI, raster and stack; such
sessions need glue-solar (and its Qt import) importable when the session is
loaded. The `preferred_cmap` crash also breaks sessions for any sunpy Map
loaded through `glue_solar.sources.maps` (`maps.py:30`) on `main` today.
Browser-loaded datasets carry no `LoadLog`, so a session embeds the arrays
instead of referencing the files.

### Capabilities supplied by standard Glue

Once data are loaded, Glue can provide:

- multidimensional slicing in the Image Viewer;
- sliders for axes represented by the loaded dataset;
- 1-D profiles along a chosen axis, always as a collapse statistic (maximum,
  minimum, mean, median, sum) over the other axes in glue-core 1.27.0; a
  single-pixel spectrum needs a one-pixel subset, or the `'slice'` collapse
  function that exists only on the `glue:profile-wcs` fork branch (draft PR glue-viz/glue#2596);
- colormap and display-limit controls;
- subsets selected in image or profile views;
- propagation of selections between datasets when their coordinates are
  linked manually; and
- export of the current viewer frame through matplotlib's save tool (there is
  no movie or sequence export anywhere in glue-core or glue-qt).

These are generic data-viewing capabilities. They do not provide the
IRIS-specific calculations, line knowledge, coordinated quicklook layout, or
specialized movie behavior of the IDL routines.

## Capability comparison

| IDL capability | Current plugin or Glue equivalent | Coverage | Important difference |
| --- | --- | --- | --- |
| Search and group local observations | Recursive directory scan grouped by OBSID/start time | Partial | No time-range search, filename-pattern presets, recent search windows, search cancellation, or multiple IRIS/EIS data-source modes. |
| Read IRIS Level-2 raster and SJI data | `irispy.io.read_files` adapter | Covered | This is the strongest area of parity and uses the maintained Python reader. |
| Display observation metadata | Observation rows and Glue metadata | Partial | No OBS XML dependency resolution or `IRISsim_showXML` table viewer. `irispy.obsid.ObsID(<OBSID>)` decodes the OBS description, SJI filters, field of view, exposure, binning, cadence, compression and linelist offline (no XML) and is not surfaced by the browser yet. |
| Display log files | None | Missing | The browser ignores non-FITS files except supported archives. Public Level 2 downloads, irispy's test/sample data and pooch caches contain no `.log` files; they are level1to2 pipeline by-products (`iris_l2_<ts>_<obsid>[_raster|_sji].log`, also `.errorlog`) present only on local mirrors. `iris_xfiles` itself has no log search either: it only displays a picked non-FITS file whose name matches `.*log`. |
| SJI inspection | Glue Image Viewer with an axis slider | Partial | Playback (first/previous/back/stop/forward/next/last buttons; repeated back/forward presses change the speed) already exists in the Image Viewer slider. Missing: a raster-slit overlay (the SJI aux `SLTPX1IX`/`SLTPX2IX` columns are already exposed by irispy as the `slit x position`/`slit y position` extra coordinates; the slit sweeps across the frame during rasters, so the overlay must be per frame), exposure-aware matching, timed blink (mix exists through per-layer alpha and the "One color per layer" mode), and any movie or sequence export (none exists in glue-core or glue-qt; only the current frame can be saved). |
| Detector view | Generic 2-D slicing | Partial | No detector mosaic, selected-window layout, detector-aware scales, or linked row/column plots. irispy 0.8.1 `read_files` returns one cube per spectral window and has no full-detector reader, so this is a loader gap as well as a layout gap; no work is scheduled for it. |
| Coordinated raster browser | Glue Image and 1-D Profile viewers plus subsets | Partial | Views are not assembled into the synchronized raster/spectrum/SJI/GOES browser provided by IDL. On glue-core 1.27.0 the Profile viewer shows collapse statistics only; the per-pixel spectrum of `iris_raster_browser` needs the fork's `'slice'` function or a one-pixel subset. With manual lon/lat links a selection drawn on the raster viewer appears on the SJI viewer, but a selection drawn on the SJI viewer cannot be evaluated on the raster (`IncompatibleAttribute`), because the SJI pixel axes depend on time and the raster has no matching time component. |
| Multiple-raster navigation | Separate Glue datasets or an optional raw 4-D stack | Partial | The stack keeps exact per-pixel times and raster indices, stores masked pixels as NaN in a float32 memmap, and uses scan 0 as its nominal spatial WCS; `iris_raster_browser` retains every raster's own coordinates (feasible loader-side with a gwcs lookup-table model, see above; the inverse model is the open piece). |
| Sit-and-stare navigation | Loads today: a sit-and-stare raster file becomes a `(n_exposure, slit, wavelength)` dataset whose axis 0 is time, with a per-exposure `Time` component (irispy `sns` test data: shape (187, 40, 52), 2021-09-05 00:18 to 05:07); wavelength-versus-time is a 2-D slice choice and chunking is a slice range or subset | Partial | No dedicated time layout (the time axis is labelled `Helioprojective Longitude` because `Time` is a component, not a coordinate) and no chunk presets. |
| Spectroheliogram panels | The Image Viewer's default layout for a raster window (x = wavelength, y = slit, slider = raster position) | Partial | No automatic per-raster panel layout or IRIS-specific animation/export. |
| Whisker plot | A user can choose an appropriate 2-D slice | Partial | No dedicated slit selector, raster/time semantics, or linked profiles. |
| Zeroth-moment intensity map | glue-qt Profile viewer **Collapse** tab (no plugin code) | Partial | Drawing a wavelength range in the Profile viewer and choosing Sum makes the linked Image Viewer show the summed map over that range live (`AggregateSlice`); it is pixel-index based, with no rest wavelength, velocity or bad-pixel handling. `irispy.utils.moments.calculate_moments` (since irispy-lmsal 0.7.0; glue-solar pins >= 0.8.1) provides the full calculation; wrapping it as a right-click dataset action that adds the maps to the data collection is planned. |
| Profile moments | Profile viewer **Collapse** tab (Moment 1 / Moment 2, pixel units) | Partial | No plugin UI yet; `calculate_moments` returns `intensity`, `centroid`, `width` (0th/1st/2nd moments) plus `velocity` and `velocity_width` maps per spatial pixel, using `meta.rest_wavelength` (from `TWAVE`); 4-D stacks carry a plain dict meta and need an explicit rest wavelength. |
| Single/double Gaussian fitting | Single-spectrum fit only: `glue.core.fitters` and the glue-qt Profile viewer **Fit** tab fit one Gaussian or polynomial to the displayed profile in a background `Worker` | Partial | No per-pixel parameter maps, double-Gaussian model or diagnostics; `astropy.modeling.fitting.parallel_fit_dask` (astropy >= 7.0; `dask` is already a hard irispy-lmsal dependency) plus the irispy gallery recipes provide the batch fitting at about 1 ms per spectrum. Neither the bundled irispy rasters (line cores lie outside every window) nor the synthetic conftest rasters can drive a physical fit. |
| Wavelength/velocity and line IDs | Wavelength WCS only (metres today; Angstrom after WP1) | Partial | No velocity display unit or line-identification overlay. No rest-wavelength selection UI is needed for the default: irispy supplies `meta.rest_wavelength` from `TWAVE` for every per-scan window (stacks carry a dict meta; fall back to `TWAVE<n>`). Both are glue-solar work through glue-core's public `unit_converter` and `layer_artist_maker` registries. |
| SJI and raster temporal coordination | Manual lon/lat links propagate selections from the raster to the SJI only; SJI-drawn selections cannot be evaluated on the raster (the SJI pixel axes depend on time and the raster has no matching time component) | Partial | No automatic WCS link on released glue-core. The fork branch `glue:ape14-wcs-autolink` (draft PR glue-viz/glue#2595) autolinks SJI and raster, exact at the first exposure only: on the 4.8 h rotation-tracked `sns` test observation the pointing drifts 42 arcsec, so a time-aware link helper (gap plan Phase 1.4) stays necessary alongside it. No nearest-exposure selection and no synchronized slicing between viewers. |
| GOES context | None | Missing | No GOES query or flare/context plot. A plot needs `sunpy[timeseries]` (`h5netcdf`), which glue-solar does not declare (`pyproject.toml` has `sunpy[map,net]`); the target is the Scatter viewer (the Profile viewer raises on a datetime-first dataset); glue-core 1.27.0 labels datetime axes with the pre-matplotlib-3.3 epoch (`glue/utils/matplotlib.py:449`, no `set_epoch` anywhere), so date ticks read wrong with matplotlib 3.11. That last bug already affects any Scatter or Histogram plot of the raster `Time` component. |
| SDO pointing context | Loads pre-generated aligned AIA cutouts when present | Partial | No live SDO retrieval, limb/full-disk context, or IRIS field-of-view overlay ("rotation" is not a gap: the LMSAL cutouts are per-exposure time-matched). The FOV polygon can be a `PolygonalROI` subset on the AIA dataset in its own pixel coordinates, needing no link; glue-core's `RegionData` crashes on a WCS-bearing Data (`coordinate_helpers.py:42`). Cross-dataset linking must match `world_axis_physical_types`, never labels (SJI `Longitude`, raster `Helioprojective Longitude`, sunpy Map `Hpln`). |
| Level-3 FITS generation | None | Will not implement | The plugin is a reader and viewer adapter, not a product generator; Level-3 writing is a permanent non-goal (decided 2026-08-29). |
| EIS data and housekeeping | None | Will not implement | `iris_xfiles` also acts as an EIS front end; the Glue plugin is explicitly IRIS-only and EIS support is a permanent non-goal (decided 2026-08-29). |

## Recommended boundary

The current plugin is best described as an **`iris_xfiles`-inspired local
observation browser and Glue loader**, not a replacement for the SolarSoft
quicklook suite.

It should continue to delegate file interpretation to `irispy` and generic
visualization, slicing, manual linking, and subsets to Glue. Reimplementing every IDL
widget would duplicate a large, specialized analysis application.

An IRIS-specific analysis feature should be added only when there is a
demonstrated workflow that generic Glue and an existing Python library cannot
cover. Moment calculations, Gaussian fitting, and velocity products belong in
reusable scientific Python routines first — and largely already exist there
(`irispy.utils.moments.calculate_moments` since irispy-lmsal 0.7.0, and
`astropy.modeling.fitting.parallel_fit_dask` with worked irispy gallery
recipes). Glue should display their outputs rather than own separate
numerical implementations.

Two capabilities are permanent non-goals, not deferred work: Level-3 FITS
generation and EIS support (both decided 2026-08-29). The 4-D stack already
provides the in-memory equivalent of a Level-3 cube for visualization, and the
plugin remains IRIS-only.

## SolarSoft sources inspected

Source snapshot inspected 2026-08-29.

- [`iris_xfiles.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/iris_xfiles.pro)
- [`iris_xcontrol.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/iris_xcontrol.pro)
- [`iris_xdetector.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/iris_xdetector.pro)
- [`iris_xmap.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/iris_xmap.pro)
- [`iris_xraster.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/iris_xraster.pro)
- [`iris_xwhisker.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/iris_xwhisker.pro)
- [`iris_sji__define.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/objects/iris_sji__define.pro)
- [`iris_moment__moment.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/objects/iris_moment__moment.pro)
- [`iris_moment__gaussian.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/objects/iris_moment__gaussian.pro)
- [`iris_moment__dgf.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/objects/iris_moment__dgf.pro)
- [`sdo_icon__define.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/objects/sdo_icon__define.pro)
- [`xsji_image.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/xsji_image.pro)
- [`xpointing_image.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/xpointing_image.pro)
- [`xmoment_moment.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/ql/xmoment_moment.pro)
- [`iris_ximovie.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/utils/iris_ximovie.pro)
- [`iris_xlineplot.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/utils/iris_xlineplot.pro)
- [`irissim_showxml.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/iris_simulator/irissim_showxml.pro)
- [`iris_make_fits_level3.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/uio/fits/iris_make_fits_level3.pro)
- [`iris_raster_browser.pro`](https://hesperia.gsfc.nasa.gov/ssw/iris/idl/nrl/iris_raster_browser.pro)
