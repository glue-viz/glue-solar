# Plan: closing the IRIS capability gaps

Companion to [`IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`](IRIS_IDL_GLUE_CAPABILITY_AUDIT.md)
(audit dated 2026-08-29). For every **Partial**/**Missing** row of the audit's
capability comparison, this plan names the repository where the fix belongs —
`glue-solar`, `glue-core`, `glue-qt`, or an upstream science library — and what
would need to be built. Phases are ordered by value per unit of work, not by
audit order.

**Current status (2026-08-29):** the observation browser (glue-solar PR #44)
is in review with CI green. While it lands, active work is the glue-core
items — starting with Phase 3.1 (APE-14 autolink), which is independent of
#44. The first glue-solar work after #44 merges is the moments-only PR
(Phase 2.1, decided). Detailed working TODOs for the glue-side efforts live
in the glue fork: `~/Git/glue/APE14_AUTOLINK_TODO.md` and
`~/Git/glue/PROFILE_WCS_RESTART_TODO.md`; macOS desktop-integration fixes
are scoped in `~/Git/glue-qt/MACOS_INTEGRATION_TODO.md`.

## Guiding principles (from the audit's "Recommended boundary")

1. `glue-solar` stays a browser + loader + thin glue between Glue and irispy.
2. Numerical products (moments, fits) are implemented in reusable science
   libraries (`irispy-lmsal`, `sunpy`, `ndcube`/astropy) and only *invoked
   and displayed* from Glue.
3. Viewer behavior that any astronomy user would want (synchronized slicing,
   blinking, line lists) belongs in `glue-qt`/`glue-core`, not in this plugin.
4. Anything below is added only when a demonstrated workflow needs it; the
   audit explicitly warns against reimplementing the IDL widget suite.

## Where each gap lands

| Audit row | Coverage today | Home | What to add |
| --- | --- | --- | --- |
| Search and group local observations | Partial | glue-solar | Date-range + text filters, background scan with cancel |
| Display observation metadata (OBS XML) | Partial | — | Non-goal (SolarSoft-specific XML resolution) |
| Display log files | Missing | glue-solar | List `*.log` per observation, plain-text dialog (trivial) |
| SJI inspection (movie, slit overlay, blink) | Partial | glue-solar + glue-qt | Slit-overlay dataset in glue-solar; blink/mix in glue-qt |
| Detector view (mosaic) | Partial | glue-solar | Optional full-detector loader variant |
| Coordinated raster browser | Partial | glue-solar + glue-core | Quicklook layout helper now; synchronized slicing upstream |
| Multiple-raster navigation (per-scan WCS) | Partial | glue-core (long-term) | Accepted limitation; needs slice-dependent WCS support |
| Sit-and-stare navigation (chunking) | Partial | glue-solar | Defer until a real long observation demands it |
| Spectroheliogram panels | Partial | glue-solar | One-click viewer-preset action |
| Whisker plot | Partial | glue-solar | One-click viewer-preset action |
| Zeroth-moment intensity map | Missing | glue-solar (wraps irispy) | `irispy.utils.moments.calculate_moments` already released in 0.8.1 |
| Profile moments | Missing | glue-solar (wraps irispy) | Same function: 0th/1st/2nd moments per spatial pixel |
| Single/double Gaussian fitting | Missing | glue-solar (wraps astropy) | `astropy.modeling.fitting.parallel_fit_dask` + irispy gallery recipes |
| Wavelength/velocity + line IDs | Partial | glue-core + glue-qt | Velocity display units in core; line-list overlay in qt |
| SJI/raster temporal coordination, autolink | Partial | glue-core | APE-14-capable `WCSLink`/autolinker; time-nearest join |
| GOES context | Missing | glue-solar (via sunpy) | Load GOES XRS light curve for the observation interval |
| SDO pointing context | Partial | glue-solar (via sunpy) | Live AIA fetch, rotate, FOV overlay |
| Level-3 FITS generation | Missing | — | Non-goal: will not be implemented (see below) |
| Session round trips (audit §"unsupported") | Missing | glue-core + glue-solar | APE-14/gWCS/`-TAB` serializers, done completely or not at all |
| EIS data and housekeeping | Out of scope | — | Non-goal: will not be implemented (see below) |

---

## Phase 1 — glue-solar only, no upstream dependencies

Everything here ships in this repository with what glue-core/glue-qt already
provide.

1. **Browser search filters.** Add a start/end date filter and a free-text
   filter (description/OBSID) above the observation tree, and run
   `scan_directory` in a `QThread` with a cancel button so large trees do not
   block the dialog. Closes the "no time-range search / no cancellation" half
   of the search row; filename-pattern presets stay a non-goal.
2. **Viewer presets.** Menu or per-dataset actions that open a correctly
   configured Image Viewer: *Whisker* (wavelength × raster/time at a chosen
   slit position) and *Spectroheliogram* (wavelength × slit, stepping over
   raster position). These are a few lines each — create the viewer, set the
   `x_att`/`y_att`/slice state — and close the "user must know which axes to
   pick" caveat on both rows.
3. **Quicklook layout helper.** One action that, for a selected observation,
   loads raster + SJI, creates the manual HPC links, and opens the standard
   trio: SJI Image Viewer, raster map Image Viewer, 1D Profile viewer. This is
   the honest subset of `iris_raster_browser` that Glue's linking already
   supports; true cursor-coupled browsing waits for Phase 3.
4. **Explicit link helper.** A "Link IRIS datasets" action that creates the
   HPC longitude/latitude links programmatically (the audit verified autolink
   cannot do it). Removes the most error-prone manual step and is deleted once
   Phase 3's autolink work lands upstream.
5. **GOES context.** An action that queries GOES XRS via `sunpy.net.Fido` for
   the observation interval and adds it as a 1D dataset (time, flux) shown in
   a Profile/Scatter viewer. Network access must be explicit (button, not
   automatic) and failure non-fatal.
6. **Slit overlay on SJI.** Build a small scatter dataset of the raster slit
   positions (already available from the `-TAB` WCS) and add it as a layer on
   the SJI viewer, linked through the HPC components. No glue-qt change
   needed.
7. **Log files (trivial).** Show `*.log` files under an observation and open
   them read-only in a text dialog.

## Phase 2 — science-feature wrappers (the math already exists upstream)

Per the boundary, none of the math lives in glue-solar — and none needs to be
written: irispy-lmsal and astropy already provide it.

1. **Moment maps** (`iris_moment`/`iris_xmap` equivalents):
   `irispy.utils.moments.calculate_moments` (released in irispy-lmsal 0.8.1,
   glue-solar's declared minimum) computes 0th/1st/2nd moments per spatial
   pixel with `rest_wavelength`, `wings` (spectral window), `min_intensity`
   and `saturation_limit` arguments. The rest wavelength auto-resolves from
   the window's `TWAVE` header card via `cube.meta.rest_wavelength`, and when
   known the function also returns `velocity` and `velocity_width` maps in
   km/s. It returns a `RasterCollection` of 2D `SpectrogramCube`s with the
   spatial WCS preserved, so the plugin's existing cube→`Data` conversion
   path ingests the outputs unchanged. glue-solar adds only a dialog — pick
   dataset, enter wings numerically, run, add the maps as datasets linked to
   the source. No new dependencies, no upstream work.
   **Decided 2026-08-29: this is the first science PR, moments only, with
   numeric-only wings fields.** Prefilling wings from a Profile-viewer
   wavelength subset is a follow-up, not part of v1.
   *Prerequisite:* the loader must keep a handle back to the source
   `SpectrogramCube` (or the file path + window) on the `Data` it creates,
   so analysis actions can recover the cube without re-reading files.
2. **Gaussian fit maps** (single and double):
   `astropy.modeling.fitting.parallel_fit_dask` does per-pixel batch fitting
   over a cube, and the irispy gallery has complete worked recipes —
   `examples/analysis/01_spectral_fitting.py` (single Gaussian, with
   percentile background seeding and an averaged-spectrum prefit) and
   `07_mg_ii_two_gaussian_fitting.py` (double Gaussian, Mg II k). glue-solar
   wraps the recipe: same dialog as moments plus model choice, run in a
   background thread, add amplitude/centroid/width/background and residual
   maps as datasets. Requires `dask` — add as an optional `fitting` extra.
   Ship single Gaussian first; double follows the same path once single is
   proven.
3. **Free extensions of the same pattern.** irispy-lmsal also ships
   `calculate_red_blue_asymmetry` and `density_diagnostic` (O IV), both
   cube-in/cube-out like `calculate_moments`. Once the moments dialog and the
   cube-handle prerequisite exist, exposing these is one entry each in the
   same action list — beyond IDL `iris_xfiles` parity, at near-zero cost.
4. **SDO pointing context**: use `sunpy` (Fido AIA/HMI fetch +
   `propagate_with_solar_surface`) to retrieve a co-temporal context image and
   overlay the IRIS FOV polygon. Implement the retrieval as a plain sunpy
   recipe first; glue-solar only wraps it.

## Phase 3 — glue-core / glue-qt infrastructure

These are proper upstream contributions; each also benefits non-solar users.

1. **APE-14 `WCSLink` and autolinker (glue-core).** Today
   `wcs_autolink` only considers `BaseHighLevelWCS` and `WCSLink` requires
   astropy-`WCS` attributes (`has_celestial`, `.celestial`), so irispy's SJI
   gWCS and the raster `-TAB` WCS are skipped (audit §4a). Generalize link
   discovery to match on `world_axis_physical_types` and transform through
   `pixel_to_world_values`/`world_to_pixel_values` only. This single change
   makes IRIS autolinking work and removes Phase 1 item 4.
2. **Synchronized slicing (glue-core state + glue-qt UI).** Allow slice
   sliders in different viewers to be joined through the data links, so
   stepping the raster scan updates the SJI frame (nearest exposure) and vice
   versa. Combine with a time-nearest join primitive (extension of
   `Data.join_on_key` to nearest-value matching on a Time component). This is
   the load-bearing feature behind "coordinated raster browser" and "temporal
   coordination".
3. **Velocity display units (glue-core).** Register a spectral unit converter
   (wavelength ⇄ velocity given a user-set rest wavelength) with glue's
   display-unit machinery so profile and image axes can show km/s. glue-solar
   contributes only the rest-wavelength UI affordance.
4. **Line-list overlay (glue-qt).** Vertical line annotations with labels in
   the Profile viewer, fed from a simple table. glue-solar then ships an IRIS
   line list as data, not code.
5. **Blink/mix (glue-qt).** Alternate or blend two image layers with adjustable
   rate/ratio — the one `iris_ximovie` behavior generic Glue lacks. Playback,
   speed and export of the current slice already exist.
6. **Session serialization (glue-core + glue-solar).** Only as a complete
   unit, per the audit's warning: gWCS and APE-14 low-level WCS savers in
   glue-core (or glue-astronomy), a `-TAB` saver that persists the lookup
   table (not just the header), a compound-WCS saver, plus metadata and
   preferred-colormap sanitizers in glue-solar — with
   serialize → deserialize *coordinate* tests for a real SJI, raster and
   stack. Until all of that exists, keep documenting sessions as unsupported.

## Explicit non-goals

- **Level-3 FITS generation.** Decided 2026-08-29: this will not be
  implemented, in glue-solar or upstream on our initiative. The 4-D stack
  loader already gives the in-memory equivalent for visualization; anyone
  needing Level-3 files on disk should request the writer from irispy-lmsal
  directly.
- **EIS support.** Decided 2026-08-29: the EIS front-end behavior of
  `iris_xfiles` (quicklook, Level-2 maps, housekeeping, CCSDS) will not be
  implemented. The plugin is and stays IRIS-only.
- OBS XML dependency resolution / `IRISsim_showXML`.
- Reimplementing the IDL widget layouts (detector mosaic chrome, per-raster
  panel grids, PostScript export paths).
- Per-scan absolute WCS inside the 4-D stack: stays a documented limitation
  until glue-core can represent slice-dependent WCS; loading scans separately
  remains the supported way to get exact per-scan pointing.

## Suggested order of attack

| Step | Items | Why first |
| --- | --- | --- |
| 1 | Phase 1.1–1.4 | Pure glue-solar, no new deps, directly removes daily friction |
| 2 | Phase 3.1 (APE-14 autolink) | Small, well-scoped glue-core PR; deletes Phase 1.4 |
| 3 | Phase 1.5–1.7 | Independent nice-to-haves |
| 4 | Phase 2.1 (moments-only PR, decided) then 2.2 (Gaussian fits) | Unlocks the three Missing science rows; math already exists |
| 5 | Phase 3.2 (synchronized slicing) | Biggest UX win, largest upstream effort |
| 6 | Remainder (2.3–2.4, 3.3–3.6) | On demonstrated demand |
