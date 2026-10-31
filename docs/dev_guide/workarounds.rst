.. _glue_solar_dev_docs_workarounds:

===================
Workaround register
===================

glue-solar patches or overrides glue-core, glue-qt, echo, astropy, WCSLIB, dkist and mpl-scatter-density where IRIS,
SST or DKIST data hit a fault, or need what those packages lack. Each entry names what is patched (with its PR),
the switch that turns it on, and the upstream change that retires it. A switch is a ``needs_*`` probe in
``glue_solar/glue_patches.py`` that finds the fault at import; "always on" means no probe is safe. A PR that adds or
retires a patch edits this page in the same change. ``UPSTREAM_REVIEW.md`` on the ``plan`` branch re-verifies each
entry against the latest releases and mains, and names its fork branch, draft or report.

Routes: a *fork branch* is a branch on the user's fork with the fix, no PR yet; a *report candidate* is an issue to
open; the *upstream list* is the plan's ``wp0-upstream`` item; *glue-solar feature* and *kept by decision* (a D-number
in the plan) stay.

Rules for new code: raw-WCS readers hold ``WCS_LOCK`` or use a deep copy, and never fake an all-ones
``axis_correlation_matrix``.

glue-core
---------

- **Correlated-axis** ``world2pixel_single_axis`` (#71). Switch ``needs_inverse_workaround()``. Retired by glue
  #2598.
- **Date epoch** in ``datetime64_to_mpl`` and ``mpl_to_datetime64`` (#128). Switch ``needs_date_epoch_workaround()``.
  Retired by glue #2599.
- **An empty** ``AggregateSlice`` **range** drawn as its first sample (#132). Switch
  ``needs_empty_collapse_workaround()``. Retired by a glue fix, not yet reported.
- ``_GlueWCS.has_celestial = False`` (#66). Always on. Retired by glue #2595.
- **Pixel point off a linked dataset**, or whose fixed axes reach no pixel axis of it (the SST quicklook's scan and
  Stokes), placed at its own slices (``PixelSubsetState._to_linked_pixel_coords``, #76, #85, #246). Switch
  ``needs_pixel_point_workaround()`` (either probe). Retired by the upstream list for the NaN, and glue's round-trip
  check accepting a subset of the fixed axes (report candidate).
- **A Pixel click or drag off the image skipped**, after glue's own button check, and a click on another tile of a
  DKIST mosaic's imager panel moving the point to that tile's pixel (``PixelSelectionTool._select_pixel``,
  ``QuicklookImageViewer.tile_at``, #331, #366, #392, D109). Switch ``needs_pixel_off_image_workaround()``. Retired by
  glue's Pixel tool ignoring positions off the image (report candidate); the tile click then needs its own hook.
- **FITS export of lazy data and of uint8 components in a subset** (``export_fits``, #96). Switch
  ``needs_fits_export_dask_workaround()``. Retired by glue's exporter writing dask arrays and uint8 subsets (report
  candidate).
- **No (0, 0) Pixel crosshair** (``ImageSubsetLayerArtist._update_visual_attributes``, #87). Switch
  ``needs_crosshair_workaround()``. Retired by the upstream list.
- **A linked layer's Pixel crosshair placed from the reference data** (``ImageSubsetLayerArtist._update_data``, #107).
  Switch ``needs_reference_crosshair_workaround()``. Retired by the upstream list.
- **Per-frame limits skipped while a viewer has no reference data** as its data are removed, where glue raises
  TypeError and stops the removal partway (``ImageLayerState._update_slice_subset``, #364). Switch
  ``needs_slice_subset_workaround()``. Retired by ``_update_slice_subset`` returning while
  ``numpy_slice_aggregation_transpose`` is None, or glue removing a removed layer's ``slices`` callback (report
  candidate).
- **Axis labels set on the WCSAxes coordinate of glue's world axis**, ``world_n_dim - 1 - axis``, without placing
  ticks (``ImageViewer.update_x_axislabel``, ``update_y_axislabel``, #90, #371, D102). Switch
  ``needs_axis_label_workaround()``. Retired by glue's ``_set_wcs`` label fix (fork branch ``perf-g1a-wcs-labels``).
- **Redo of a subset change puts back the subset states its first run made** (``ApplySubsetState.do``, #182). Switch
  ``needs_redo_workaround()``. Retired by glue's ``ApplySubsetState`` keeping its states (upstream list).
- **Undo of a subset change, and the Redo put-back, under** ``Coordinator.restoring``: the Pixel points glue puts
  back are neither followed nor linked again, the shown tab's point stays followed, and Undo deletes only the groups
  the command made, keeping subsets made since (``ApplySubsetState.undo``, ``undo_subset_state``, #368, #377, D39,
  D52, D97). Always on (the kept subsets only while ``needs_redo_workaround()``). glue-solar feature; for the kept
  subsets, glue's ``ApplySubsetState.undo`` deleting only what its ``do`` made (report candidate).
- ``u.Quantity`` **saver and loader for sessions** (``save_quantity``, #186, D13). Switch: only while glue has no
  Quantity saver. Retired by the upstream list.
- ``LinkSameWithUnits`` **saved by its two components** (#205). Switch ``needs_link_restore_workaround()``. Retired
  by glue's saver (upstream list).
- **Link editor names**: ``LinkSameWithUnits`` ends named ``x`` and ``y``, taking ``cids1`` and ``cids2``;
  ``PathRelativeLink`` ends ``k_from`` and ``k_to`` with one-argument conversions (#245). Switch
  ``needs_link_editor_workaround()`` (two OK rounds). Retired by glue naming both classes' ends apart,
  ``LinkSameWithUnits`` accepting ``cids1`` and ``cids2``, and the editor's ``link`` keeping a ``ComponentLink``'s
  names (report candidate).
- **A time linked from another dataset kept a datetime** (``DerivedComponent.datetime``, #208). Switch
  ``needs_derived_datetime_workaround()``. Retired by glue reading a derived component's datetime kind (report
  candidate).
- **Profile display units restored after** ``x_att`` (``ProfileViewerState._update_priority``, #197). Switch
  ``needs_profile_restore_workaround()``. Retired by glue ranking the display units after ``x_att`` (upstream list).
- **The IRIS fitter's** ``set_constraint`` **replacing a parameter's entry**, so a value or bound cleared in Settings
  clears (#259). Always on. Retired by glue-core's ``BaseFitter1D.set_constraint`` taking None as a clear (report
  candidate).
- **A line's width keeps its positive lower bound when Settings gives an upper bound alone**, where glue-core's
  ``_get_model_fitter`` sets ``(None, upper)`` and drops the floor; glue's own Gaussian fitter loses astropy's
  ``stddev`` floor the same way (``GaussianConstantFitter.fit``, #367). Always on. Retired by ``_get_model_fitter``
  leaving a None limit to the model's own bound (report candidate).
- **Lazy data's sampled statistics**: raw-code counts (D33) and random samples of derived attributes
  (``LazyData.compute_statistic``, ``loaders/lazy.py``). Always on. Retired by glue sampling dask arrays at random,
  not at chunk corners (upstream list).
- **DKIST datasets' coordinates in glue's order** (``GlueWCS``, ``sources/dkist.py``, #371, #373, #375, #378, #389,
  D102): a gWCS's world axes reordered to one per pixel axis as glue maps them, those of no pixel axis first,
  longitude and latitude wrapped to ±180°; IRIS data reach a raster through ``link_hpc``'s links to its step and slit
  pixel (``_SlitAt``, a slit table per repeat or measurement at the raster frame nearest the IRIS frame's time) and
  from its pixels to the angle glue gives none of its axes (``_SlitPlace``); the inverse is evaluated at finite world
  values only. Always on (DKIST datasets). Retired by glue mapping world axes to pixel axes by
  ``axis_correlation_matrix`` (a comment on glue #2574, drafted).
- **DKIST datasets' sampled statistics**: 10,000 values at random from up to 16 evenly spaced whole frames whose files
  are present, one sample for a VBI mosaic's tiles (``DKISTData.compute_statistic``, #371, D102). Always on. Retired
  by glue sampling dask arrays at random (upstream list).
- **glue's WCS link by APE 14 alone** where glue's needs an astropy WCS or either side has no ``has_celestial``: the
  physical types both share, through the pixel axes along which only those vary, tried as a round trip from either
  side's middle, first and last pixel, with as many values as each takes (``wcs_link_init``, #373, #378, #379, #385,
  D102, D103). Switch ``needs_wcs_link_workaround()``. Retired by glue's general case by ``axis_correlation_matrix``
  for APE 14 WCSes and ``get_cids_and_functions`` trying each side with its own axis count (fork branch
  ``ape14-wcs-link``, 67f47e4, overlapping glue #2595), and glue testing pixel 0 only (report candidate).
- **A DKIST mosaic's tiles suggested linked to its center tile only**, and other data to that tile, where glue
  suggests every pair (5778 for 108 tiles); the first tile left becomes the center once it is removed, saved in
  sessions (``sources/dkist.py``'s ``wcs_autolink`` in place of 'Astronomy WCS', ``_Recenter``, #373, #378, D102).
  Always on. Retired by glue's autolinker suggesting a spanning set rather than every pair (report candidate).
- **An Image buffer of a DKIST dataset reads only the pixels glue samples**, where glue reads a DaskComponent's
  bounding box, 500 files of a ViSP map whose view samples 34 (``DKISTData.compute_fixed_resolution_buffer`` setting
  ``_EXACT``; ``_BoxRead`` in place of glue's ``fixed_resolution_buffer.DaskComponent``, #383, D103). Always on
  (DKIST values, no subset). Retired by glue reading a DaskComponent's sampled pixels through the data's ``get_data``
  or dask's ``vindex`` (report candidate).
- **A restored Image layer's bad color given to its image** (``ImageLayerArtist.__init__``,
  ``glue_patches.image_layer_init``, #386, D103): glue sets ``cmap_bad`` only as the layer state changes, so restored
  IRIS and DKIST layers drew NaN opaque. Switch ``needs_cmap_bad_restore_workaround()``. Retired by glue applying a
  layer state's ``cmap_bad`` at construction (fork branch, the restored ``cmap_bad``).
- **A DKIST mosaic image's tiles given their frame or repeat index at each pixel** beside their time
  (``_mosaic_links``, ``_At``, #391, D108): glue derives a component through the first of equally short link paths,
  so a tile's frame came from another tile. Always on (mosaic images). Retired by glue preferring a dataset's own
  coordinate links among equally short paths (report candidate).
- **A DKIST frame quality's Time added after its header columns** (``_frame_quality``, #395, D110): glue's Profile
  viewer gives a layer its data's first numeric component, a datetime too. Always on. Retired by glue's Profile
  layers leaving datetime components out of their attributes (report candidate).
- **SST cubes' color-limit sample**: 16 planes of 25 evenly spaced rows and columns, plane k at the k-th of 16 even
  tunings, Stokes k modulo their number and the (7k mod 16)-th of 16 even scans; all planes of a cube of 16 or fewer
  (``_Cube.compute_statistic``, #230, #248, D70). Always on. Retired by glue sampling cheaply (upstream list, R32).
- **An SST cube's reads hinted to the kernel before glue makes them**: MADV_WILLNEED on the memory-mapped file's pages
  for index-array views and slice subsets, up to 100,000 rows or values in 128 KB calls, nothing where mmap has no
  madvise (``_Cube.get_data``, ``_Cube._will_need``, #362). Always on (Linux and macOS). Retired by glue's
  ``compute_fixed_resolution_buffer`` and ``Data.get_data`` reading memory maps cheaply cold (report candidate).
- ``_TabularWCS.__gluestate__`` **and** ``__setgluestate__`` in place of glue's ``_save_wcs`` and ``_load_wcs``, which
  raise 'HDUList is required to retrieve -TAB coordinates' (``sst.py``, #227, SST5). Always on (SST cubes). Retired
  by glue saving a -TAB WCS with its tables (report candidate).
- **Axis labels glue-solar sets in viewer state after glue's own resets**: a Profile x label with its display unit
  (in km / s 'Velocity from <rest> Å'), a quicklook Image panel's world labels with their units, a path diagram's
  labels on any Image viewer, the light curves' 'Value' as their units, the Profile y label from the y display unit
  (``VelocityTool._label_x``, ``FrameTimeTool._label_exposures``, ``_diagram_label``, ``_point_curves``,
  ``VelocityTool._unit_y``, #339, #367, D90). Always on. Retired by glue's viewers labelling axes with their units
  (report candidate); for 'World N', glue's ``axis_label`` returning the name it checks.
- **Path diagram overrides of core's path slicer and their session savers** (``PathTool``, ``PathData``, #151,
  #191): each sample at the nearest pixel where core truncates (D90), coordinates without the helioprojective angles
  of a moving pointing (``_DiagramCoordinates``), a plain ``DaskComponent`` read through ``vindex`` (#356), diagrams
  closed with ``close(warn=False)`` (``_close_slice_viewers``, #243), the crosshair rounded and clamped
  (``PathCrosshairTool._on_move``, #262), and the path ROI's ``_background_cache`` cleared (``_finish_roi``). Always
  on. Retired by core's path slicer fixes (upstream list; report candidates for ``_close_slice_viewers`` calling
  ``close(warn=False)``, ``drive_parent_slice`` rounding and clamping, ``PathSlicedCoordinates`` leaving out world
  axes on the sliced pixel axes, index arrays through ``vindex``, and ``MplPathROI.finalize_selection`` resetting
  its background).
- **An SSTRED Stokes cube's unnamed Stokes axis named 'Stokes'** where its y axis is named (``sst_data``, #356), as
  glue's ``axis_label`` checks ``world_axis_names[axis]`` but returns ``world_axis_names[world_n_dim - 1 - axis]``.
  Always on. Retired by ``axis_label`` checking the name it returns (report candidate, upstream list).
- **Sunpy colormaps a session names listed before glue restores them**, and registered in matplotlib under their own
  names (``_add_session_colormaps``, ``maps._add_colormap``, #98, #129). Always on. Retired by glue restoring sunpy
  colormaps by name (upstream list).
- **Raster windows of one restore read together** (``_read_logged_windows_together``, ``raster_files_data``'s
  ``_RESTORING``, #234). Always on. Retired by glue's LoadLog restoring one file's logs in one load (upstream list).
- **A dataset's style saved with its preferred colormap** (``maps._Style``, #189). Always on. Retired by glue-core
  saving and restoring ``preferred_cmap`` (upstream list).
- **A Profile viewer adds a quicklook spectrum panel's raster**, and any cube of ``large_data_size`` values or more not
  from the IRIS reader, with its data layer hidden, a status-bar note and the range fitted once to the first computed
  subset profile (``hidden_cube_profile``, ``_FitOnceComputed``, #95, #233, S13, SST4). Switch: the viewer's
  ``large_data_size`` and the data's ``_role``; the quicklook's ``_solar_hidden``. Retired by glue's
  ``_reset_y_limits`` using cached profiles only (R14) and ``compute_statistic`` without the float64 copy (R21), or
  glue-qt adding large data hidden (upstream list).
- **A quicklook spectrum or curve panel's profile limits set on the GUI thread after each move of its subset**, so
  glue's ``update_limits`` finds them unchanged and does not queue the worker again (``_Refit._limits``, #363).
  Always on. Retired by glue's ``ProfileLayerArtist._update_profile`` recomputing on ``v_min`` and ``v_max`` only
  while ``normalize`` is on, or glue-qt's ``_calculate_profile`` drawing a cached profile without the worker (fork
  branches ``perf-g7``, ``perf-q1``, ``perf-q2``).

glue-qt
-------

- **Generic** ``solar:cursor_readout``. Switch ``not hasattr(ImageViewer, 'cursor_status')``. Retired by glue-qt #74.
- **Slice-slider drag throttle** (#68). Always on. Retired by glue-qt slider coalescing (upstream list).
- **Slice playback stopped when its viewer closes** (``ImageViewer.closeEvent``, #115). Per close: a slider still
  playing after glue-qt's own close. Retired by glue-qt stopping play timers on close (report candidate).
- **Loop… replaces a slice slider's** ``_browse_slice``, which the play timer calls through ``_play_slice``, and
  reverses the private ``_play_speed`` for Bounce; the step buttons keep glue-qt's (``tools._loop``, ``_LoopEntry``,
  #115). Per slider, after Loop…, until glue-qt rebuilds the slider. Retired by glue-qt slider playback taking a
  range, step and bounce (kept by decision, D90; upstream list).
- **Quicklook panels out of sight draw once in sight**: ``_arrange`` sets each panel canvas's ``_draw_idle`` to
  ``_draw_in_sight``, leaving the draw due while the panel has no visible region (``quicklook.py``, #235, #254).
  Always on for panels ``_arrange`` lays out; a panel hidden itself draws at once. Retired by matplotlib's Qt canvas
  or glue-qt's ``MplCanvas`` leaving a queued draw out of sight to its paint (report candidate).
- **Quicklook Image panels take Pixel as their window becomes active** (``QuicklookImageViewer.set_focus``, #244),
  since glue-qt turns the last viewer's mouse mode off and a click then empties the edit subset. Always on (panels with
  no mouse mode on). Retired by glue-qt keeping a viewer's mouse mode across focus changes, or its default mode leaving
  the edit subset alone (report candidate).
- **Image viewer keys, Tab and Backspace included, copied to** ``QuicklookImageViewer`` (``_add_keys`` in ``setup``,
  #120). Always on (adds only keys the class lacks). Retired by glue-qt dispatching keys by ``isinstance`` (report
  candidate).
- **matplotlib's full-screen, save, grid, log-scale, pan and zoom keys dropped from glue-qt's canvases**, g and G kept
  on Profile viewers (``MplCanvas.__init__``, ``canvas_init``, ``_DROPPED_KEYMAPS``, ``_PROFILE_KEYMAPS``, #120,
  #222, #257). Per canvas: a figure manager connecting matplotlib's key handler. Retired by glue-qt dropping
  matplotlib's key bindings (report candidate).
- **Toolbar menu tooltips on the button and its entries** (``BasicToolbar.add_tool``, #222). Per button: no tooltip,
  or menu tooltips hidden. Retired by a glue-qt fix (report candidate).
- **One fitter per Profile viewer and fitter class** for Fit Settings and fits (``glue_patches._get_fitter``,
  ``_on_settings``, ``_fit``, #287). Switch: while ``ProfileTools`` has no ``_get_fitter`` (``_on_settings`` also
  while ``needs_fitter_settings_workaround()``). Retired by glue-qt's ``ProfileTools._get_fitter`` (fork branch
  ``fitter-settings``).
- ``ProfileTools._fit`` **replaced, for the IRIS fitter, by its own loop over the layers**: each layer's saturated
  samples left out (D87), the model given the layer's rest wavelength, attribute, x unit, function, range and
  saturated counts for ``summarize`` and 'Fit every spectrum' (``fitters._fit``, #291, #313); with glue-qt's own
  ``_get_fitter`` it fits with the fitter glue-qt passes. Always on. Retired by glue-qt passing the layer to a
  fitter's ``fit`` and ``summarize`` (upstream list).
- **A quicklook panel makes its Point the edit subset** at a Pixel or Follow/lock press or move while a dataset is
  selected (``QuicklookImageViewer._edit_point``, ``FollowLockTool._follow``, #288, #361). Always on. Retired by
  glue-qt's data collection leaving the edit subset alone when a dataset is selected (upstream list).
- **The edit subset kept through a data-tree rebuild** (``quicklook._Application.__setgluestate__``, ``_new_group``,
  the light curves), where glue-qt's rebuild empties it. Always on. Retired by glue-qt keeping the edit subset through
  a tree rebuild (two parts, about 10 lines; UPSTREAM_REVIEW glue-qt row 46).
- **Quicklook panels marked** ``_closed`` **as their window's close box closes them** (``window_closed`` connected in
  ``quicklook._fill``'s ``add``, #360), as glue-qt's ``closeEvent`` leaves ``_closed`` unset. Always on (quicklook
  panels). Retired by glue-qt's ``closeEvent`` setting ``_closed`` (report candidate).
- **Analysis result viewers open with glue-qt's default mouse mode off** (``moments._view``, #300). Always on. Retired
  by glue-qt's data collection leaving the edit subset alone (upstream list).
- **Settings on the Fit tab opens a fitter's own** ``settings_widget``, the IRIS fitter's component list
  (``glue_patches._on_settings``, ``fitters._Settings``, #314, D86). Switch ``needs_fitter_settings_workaround()``,
  or while ``ProfileTools`` has no ``_get_fitter``. Retired by glue-qt's ``_on_settings`` using
  ``fitter.settings_widget`` (fork branch ``fitter-settings-widget``, dba71453).
- **The Fit tab keeps every artist a fitter's** ``plot`` **returns**, so Clear removes each IRIS line's dashed curve
  (``glue_patches._plot_fit``, #314). Switch ``needs_fit_artists_workaround()``. Retired by glue-qt's ``_plot_fit``
  keeping every artist (fork branch ``fit-artists``, d6655bc5).
- **'Fit every spectrum' beside Fit on the Fit tab**, enabled after each fit's report for the viewer's last IRIS fit
  of a raster window or stack, its tooltip saying why when not (``fit_maps._enable`` wrapping ``ProfileTools.enable``,
  ``_report_fit``, ``_refresh``, D88). Always on. Retired by a glue-qt hook for a fitter's own Fit-tab actions (report
  candidate; none on glue-qt or glue-core main).
- **Colormap icons drawn once per colormap and width** (``QColormapCombo._update_icons``, #177). Switch
  ``needs_icon_cache_workaround()``, at the first combo. Retired by glue-qt caching icons (fork branch
  ``perf-q3-cmap-icon-cache``).
- **Layer actions hidden where** ``applies(data)`` **refuses with a ValueError**, shown when the check raises anything
  else (``UserAction._can_trigger``, #223, #257). Switch ``needs_layer_action_applies_workaround()``. Retired by
  glue-qt's layer actions taking ``applies`` (fork branch ``layer-action-applies``).
- **glue-qt's slice sliders**: the sliders a rebuild replaces hidden, as glue-qt only closes them and Qt's queued show
  put one back over an Image viewer's options; each new slider showing the values and unit of glue's world axis
  ``world_n_dim - 1 - axis``, where glue-qt reads ``ndim - 1 - axis`` (``sync_sliders_from_state``, #380, D103).
  Always on (world values only for data of more world axes than array axes); UPSTREAM_REVIEW asks for a probe gate.
  Retired by glue-qt's ``MultiSliceWidgetHelper`` hiding replaced sliders and reading glue's world axis (report
  candidate).
- ``GlueApplication.__init__`` **wrapped to put glue-solar's icon**, the macOS app's, on the application and its
  window after glue's own; quicklook panels' and strip windows' title bars get it too (``__init__.py``,
  ``quicklook._fill``, D90 P8). Always on. Retired by a glue-qt hook for the application icon (report candidate).
- **Viewers closed but not yet deleted left out of a saved session**, as when a script removes their data and saves in
  the same turn, where glue-qt lists them and glue cannot restore such an Image viewer (``GlueApplication.__gluestate__``,
  ``glue_patches.application_gluestate``, #364). Always on. Retired by glue-qt's ``GlueApplication.viewers`` or
  ``__gluestate__`` leaving closed viewers out (report candidate).
- **The Slope table's Table viewers reset after new rows** (``SlopeTool``, ``tools.py``, #175). Always on. Retired by
  glue-qt's Table viewer showing and sorting rows added to its dataset (report candidate).
- **A Table viewer of data with a time searches each value as the text the table shows**
  (``glue_patches.get_filter_mask``, #260). Switch ``needs_table_time_workaround()``. Retired by glue-qt's Table
  search matching ``str(x)`` (report candidate).
- **A tooltip for glue-qt's Profile viewer button** (``ProfileViewerTool.tool_tip``, ``setup``, #222). Switch
  ``ProfileViewerTool.tool_tip is None``. Retired by glue-qt giving the button a tooltip (upstream list).
- **glue-qt's Slice Extraction left off Image viewers**: its ``pv_slicer`` plugin ``setup`` made a no-op and the tool
  filtered from ``ImageViewer.tools``, so Path diagram is the one path tool (``setup``, D90). Always on. Kept by
  decision (D90).

astropy, WCSLIB, echo and mpl-scatter-density
--------------------------------------------------

- ``_GlueWCS`` ``WCS_LOCK`` (#60). Always on (not safely probeable). Retired by astropy #19174's fix, once 8 unlocked
  threads give 0 wrong -TAB values: it corrupts silently, without crashing, 1187 to 1267 of 2400 calls on 8.0.2
  (comment drafted, ``updrafts/reports/astropy-19174-comment.md`` in the session archive).
- ``_LockedWCS``: each plain WCS beneath a ``_GlueWCS`` becomes one in place at construction (``_lock_wcslib``: a
  raster's, a stack's scans' and scan axis's, a rebinned or restored window's, AIA and SOT cubes'), so the analyses
  hold ``WCS_LOCK`` per wcslib call, never across irispy's calls; each plain WCS ``link_hpc`` links on request, or a
  restored session holds linked (``_LinkedCollection``, #358), becomes a ``_HeldWCS``, its transforms, copies and
  struct properties holding ``WCS_LOCK``; an SST cube's ``_LockedTabularWCS`` holds the cube's own ``RLock`` instead
  (#240); lock-only wrappers of glue's ``world2pixel_single_axis`` and ``PixelSubsetState._to_linked_pixel_coords``
  (``_hold_wcs_lock``) run glue's function, or the probe-gated fix, inside ``WCS_LOCK`` (#232);
  ``WCSAxes.reset_wcs`` holds the WCS's ``_held()`` lock; a cube's lock comes after ``WCS_LOCK`` (#226, #251, D73).
  Names pinned by ``test_the_link_patches_hold_the_wcs_lock`` and
  ``test_the_analyses_hold_the_wcs_lock_in_each_wcslib_call_not_across_irispy``. Always on. Retired by astropy
  #19174's fix with the ``_GlueWCS`` lock; for the SST cube's lock, also WCSLIB's -TAB transforms no longer writing
  the shared tabprm's scratch fields (``tabx2s``), which astropy #19819 does not change.
- **'Fit every spectrum' asks** ``parallel_fit_dask`` **for** ``("param_cov", "success", "active_mask")`` **only** and
  makes each ``FitInfoSubset`` a plain dict, as all of the fit info took a C II window's main process to 5.9 GB
  (``fit_maps._fit_maps``, #314, #328). Always on. Retired by astropy's ``FitInfoSubset.__getattr__`` raising
  AttributeError, not KeyError, which ``FitInfoArrayContainer.__getitem__`` and irispy's ``maps_from_fit`` trip over
  (report candidate); irispy #320 is a second route.
- **Tied IRIS fits use an estimated Jacobian, step 1e-12** (``fitters._jacobian``, #291; astropy #20462 for the
  step), and ``model_cls`` ties each line of a chain to the chain's root (#314). Switch ``model.has_tied``; the ties
  always on. Retired by astropy's ``_wrap_deriv`` including a tied parameter's part (report candidate) and
  ``fitter_to_model_params_array`` setting each tie before the next.
- **An Image view along a raveled DKIST axis** (a raster's steps with repeats, a Cryo-NIRSP step's measurements)
  never drew: off either end dkist's ``Ravel`` gives a NaN time, on which WCSAxes raises for a range all NaN
  (``formatter_locator.py:159``); taken at the nearest end, of that end's time and no longitude or latitude
  (``GlueWCS.pixel_to_world_values``, #379, #385, D103). Always on (DKIST datasets with a ``Ravel``). Retired by a
  WCSAxes fix for an all-NaN world range (report candidate).
- ``_TabularWCS.has_celestial = False`` **against wcslib's SIGSEGV in glue's autolinker** (#227); astropy then gives
  the angles as quantities, which ``tools._sky`` puts in a SkyCoord by physical type for paths, profiles and Slope
  (#359). Always on. Retired by WCSLIB cutting a -TAB table's celestial axes safely (report candidate).
- **SPECSYS 'TOPOCENT' on ground-based files without one** (``sst.py``, #227, SST2). Switch: files with no SPECSYS.
  Retired by astropy treating a missing SPECSYS as no spectral observer (report candidate).
- ``_TabularWCS.axis_correlation_matrix`` **from the tables**, where astropy's says each -TAB world axis depends on
  its own pixel axis only (``sst.py``, #227). Always on (SST cubes). Retired by astropy computing a -TAB WCS's matrix
  from its tables (report candidate).
- **The SST cube's own inverse**, ``_TabularWCS.world_to_pixel_values``, falling back to wcslib's (``sst.py``, #227,
  D67). Always on (SST cubes). Kept by decision (D67; ``wp0-wcslib-tab-inverse``).
- **The mouse-over readout places WCSAxes ticks before formatting** (``_readout``, ``tools.py``, #90). Always on.
  Retired by WCSAxes ``format_coord`` without a tick placement (report candidate).
- **A colormap matched to its own combo entry** (echo's ``_find_combo_data``, #194). Switch
  ``needs_combo_match_workaround()``. Retired by echo matching the entry that is the value first (upstream list).
- **mpl-scatter-density's 0.5 s hold after a canvas resize, ended before each saved frame**: ``SaveSequenceTool``
  calls ``on_release()`` on each ``BaseImageArtist`` in the viewer's axes (#270). Always on. Retired by
  mpl-scatter-density ignoring the hold while matplotlib saves (``canvas._is_saving``; report candidate).

dkist
-----

- **A world-to-pixel through a slit-jaw image's gWCS at a time off its frames gives NaN pixels**: inverted at a time
  where dkist raises (x86-64), and each pixel inverted with a NaN frame made NaN (ARM) (``_GlueWCS.world_to_pixel_values``,
  ``_off_frames``, ``_frames``, #342, #353). Switch: dkist raising NotImplementedError (``_off_frames``); always on
  for the NaN x and y. Retired by dkist #765 (on dkist main since 2026-10-14, after 1.18.1), retiring ``_off_frames``
  with the release that ships it; dkist's ``sanitize_index`` handling a NaN index (x86-64 casts it to the least
  int64, ARM to 0; report candidate) retires the NaN x and y.
- **dkist's inverse given raveled 1-D values** (``GlueWCS.world_to_pixel_values``, #378): its ``Unravel`` inverse,
  which a Cryo-NIRSP context image of repeated measurements uses, raises TypeError on arrays of more than one
  dimension, on 1.18.1 and main alike. Always on (DKIST datasets). Retired by ``Unravel.evaluate`` taking N-d input
  (report candidate).
- **A point or image of DKIST data at a time outside another DKIST dataset's frames** raised NotImplementedError
  (dkist's inverse there is ``Const1D & Const1D``, of no inverse) and, for a raveled dataset, ValueError (``Unravel``
  calling ``int()`` on a NaN time); ``GlueWCS.world_to_pixel_values`` gives NaN pixels there by ``_off_frames``,
  except while the WCS link tests its transforms (``STRICT_INVERSE``), where it also refuses a NaN world value, so
  data of other times stay unlinked (#379, #385, D103). Switch: dkist raising NotImplementedError or ValueError.
  Retired by dkist #765 for the NotImplementedError half, the link test then refusing a NaN pixel in its place;
  ``Unravel`` giving NaN for a NaN index (report candidate).
- **DKIST values read by glue-solar, not dkist's dask array** (``DKISTData.get_data``, ``_Files``, ``_section``,
  ``_Open``, #383, #385, D103): only the tiles of each file a view touches decompressed (astropy's ``section``), up
  to 4096 files kept open (``_open_files``: half the open-file soft limit, raised toward its hard limit), closed as
  their dataset leaves glue or its window closes, and once read by a profile still computing after that; 8 threads, a
  lock per file, a missing file NaN; dask's reads where a dataset is cut within its files' frames or dkist gives no
  HDU of its files; ``GlueWCS.pixel_to_world_values`` keeps its last 64 distinct inputs of up to 10,000 values, as
  WCSAxes asks the same at each draw. Always on (DKIST datasets). Retired by dkist's dask array passing each view to
  its loaders' ``hdu.section`` (dkist #226) and ``VaryingCelestialTransform`` evaluating all raster steps at once
  (dkist #246, #256).
- **dkist's** ``VaryingCelestialTransform`` **sets the parameters of its one celestial model at each pointing index,
  then evaluates it**, so glue-qt's profile worker beside the GUI thread gave the map another step's pointing
  (143.6" off on AIOMGG); a lock around dkist's forward and inverse and ``_off_frames`` (``GlueWCS._lock``, #385,
  D103). Always on (DKIST datasets). Retired by dkist evaluating it without changing its shared model (report
  candidate).
- **dkist's private** ``_striped_external_array.target`` **read**, the HDU each file's array is in, as the loader
  sets up a dataset's ``_Files`` (``sources/dkist.py``). Always on (DKIST datasets). Retired by ``target`` proxied on
  ``DKISTFileManager`` (1 line; UPSTREAM_REVIEW dkist row 8).
- **The ASDF path made absolute before** ``dkist.load_dataset`` (``sources/dkist.py``), as a relative
  ``files.basepath`` breaks dkist's reads from another working directory. Always on. Retired by dkist resolving
  ``files.basepath`` (1 line, on dkist #366; UPSTREAM_REVIEW dkist row 10).
- **'Download these frames…' sends a DKIST dataset's chosen FITS files alone** through dkist's private
  ``_orchestrate_transfer_task``, their list built as ``FileManager.download`` builds it from the refreshed inventory,
  since ``FileManager.download`` adds the ASDF file, browse movie and quality report to every transfer (``_transfer``,
  ``sources/dkist.py``, #396, D110). Always on (a DKIST download); the fallback, ``FileManager.download`` of each
  sliced dataset, on ImportError, AttributeError or arguments that no longer bind. Retired by ``FileManager.download``
  sending the FITS files alone (draft ``dkist-fits-only.md`` in the session archive).
- **'Download these frames…' follows its transfer by the files in the folder**, a file whole once its size and mtime
  are unchanged over one 5 s look, read as missing until then (``_ARRIVING`` in ``_section``, ``_watch_download``,
  ``sources/iris.py``, #396, D110), as neither ``FileManager.download(wait=False)`` nor
  ``_orchestrate_transfer_task`` returns a Globus task to follow. Always on (a DKIST download). Retired by dkist
  returning the Globus task ID of a transfer that does not wait (dkist #516).

glue-solar's own
----------------

Features and decisions with no upstream route; listed so the overrides are known.

- **Physical aspect** replaces glue's ``ImageViewerState._set_axes_aspect_ratio`` on each Image viewer's state,
  scaling its ratio by the arcsec ratio while on and by 1 while off, and refits the limits through glue's private
  ``_axes_aspect_ratio`` and ``_adjust_limits_aspect`` (``PhysicalAspectTool``, #103). Always on. glue-solar feature
  (an upstream candidate in UPSTREAM_REVIEW).
- **A quicklook saved as a recipe on its first panel's record** and rebuilt by ``_reopen`` (``quicklook._recipe``,
  ``_reopen_quicklooks`` session patch, #301). Always on. glue-solar feature.
- ``GlueApplication.closeEvent`` **wrapped to keep the last session on quit**, telling a replaced window by glue-qt's
  private ``_new_application`` (``__init__.py``, #206, #297). Always on. glue-solar feature.
- **glue's unit converter default set to** ``lines.DopplerConverter`` (``__init__.py``). Always on. glue-solar
  feature.
- **Quicklook Image panels leave each mouse mode's hint** (its ``status_tip``) out of their status line, where a
  narrow panel's frame time clipped it (``QuicklookImageViewer.set_status``, D90). Always on. Kept by decision (D90).
- **A sit-and-stare raster's slit axis rolled past 45° labeled as its longitude**, in viewer state and on that
  WCSAxes coordinate, which glue labels by spine with the exposure axis' label (``FrameTimeTool._label_exposures``,
  ``_beside_exposures``, #359, D30). Switch: sit-and-stare rasters rolled past 45°. glue-solar feature.
- **A gzipped raster file opened once in memory** for its window headers and irispy's read, where a plain
  ``fits.open`` of the headers and irispy's own read would inflate it twice (``_raster_windows_data``,
  ``_window_scaling(opened=)``, #345, #352; irispy #275's open-file seam). Switch: gzipped raster files, ``LAZY`` on.
  Kept (UPSTREAM_REVIEW others row 43: a later header of a gzip stream needs the stream inflated up to it).
