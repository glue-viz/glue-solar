.. _glue_solar_dev_docs_workarounds:

===================
Workaround register
===================

glue-solar patches or overrides glue-core, glue-qt, echo, astropy, WCSLIB, matplotlib, dkist, irispy and
mpl-scatter-density where IRIS, SST or DKIST data hit a fault, or need what those packages lack. Each entry names what
is patched (with its PR), the switch that turns it on, and the upstream change that retires it. A switch is a
``needs_*`` probe in ``glue_solar/glue_patches.py`` that finds the fault, at import unless its entry says when;
"always on" means the patch has none. A probe switches only the fix of the fault it tests: where a patch also carries
other behaviour, the patch is installed always and the probe switches that part alone. A PR that adds or retires a
patch edits this page in the same change, and ``test_the_register_and_glue_patches_name_the_same_probes`` fails while a
probe has no entry here, or an entry names a probe that is gone. ``UPSTREAM_REVIEW.md`` on the ``plan`` branch
re-verifies each entry against the latest releases and mains, and names its fork branch, draft or report.

Routes: a *fork branch* is a branch on the user's fork with the fix, no PR yet; a *report candidate* is an issue to
open; the *upstream list* is the list of fixes to propose upstream, in the same file; *glue-solar feature* and
*kept by decision* stay.

Rules for new code: raw-WCS readers hold ``WCS_LOCK`` or use a deep copy, and never fake an all-ones
``axis_correlation_matrix``.

glue-core
---------

- **Correlated-axis** ``world2pixel_single_axis`` (#71). Switch ``needs_inverse_workaround()``. Retired by glue
  #2598.
- **Date epoch** in ``datetime64_to_mpl`` and ``mpl_to_datetime64`` (#128). Switch ``needs_date_epoch_workaround()``.
  Retired by glue #2599.
- **An empty** ``AggregateSlice`` **range** drawn as its first sample (#132). Switch
  ``needs_empty_collapse_workaround()``, which gives glue-core's image buffer a range of no samples. Retired by
  glue-core's buffer taking such a range, which the probe sees, or by glue-qt's ``ProfileTools._on_collapse`` no longer
  making one, the natural place for the fix, which the probe does not see: the patch is then removed by hand (report
  candidate).
- ``_GlueWCS.has_celestial = False`` (#66). Always on. Retired by glue #2595.
- **Pixel point off a linked dataset**, or whose fixed axes reach no pixel axis of it (the SST quicklook's scan and
  Stokes), placed at its own slices (``PixelSubsetState._to_linked_pixel_coords``, #76, #85, #246). Switch
  ``needs_pixel_point_workaround()`` (either probe). Retired by the upstream list for the NaN, and glue's round-trip
  check accepting a subset of the fixed axes (report candidate).
- **A Pixel click or drag off the image, or in a viewer of no data, skipped**, and a click on another tile of a DKIST
  mosaic moving the point to it (``PixelSelectionTool._select_pixel``, ``QuicklookImageViewer.tile_at``, #331, #366,
  #392). Installed always, for the tile click and the viewer of no data; switch ``needs_pixel_off_image_workaround()``
  for the skip off the image alone. Retired by glue's Pixel tool ignoring positions off the image, for the skip, and
  presses in an empty viewer, which no probe tests (report candidate); the tile click is a glue-solar feature.
- **FITS export of lazy data and of uint8 components in a subset** (``export_fits``, #96). Switch
  ``needs_fits_export_dask_workaround()``. Retired by glue's exporter writing dask arrays and uint8 subsets (report
  candidate).
- **No (0, 0) Pixel crosshair** (``ImageSubsetLayerArtist._update_visual_attributes``, #87). Switch
  ``needs_crosshair_workaround()``. Retired by the upstream list.
- **A linked layer's Pixel crosshair placed from the reference data** (``ImageSubsetLayerArtist._update_data``, #107).
  Switch ``needs_reference_crosshair_workaround()``. Retired by the upstream list.
- **Per-frame limits skipped while a viewer has no reference data**, where glue raises TypeError as its data are removed
  (``ImageLayerState._update_slice_subset``, #364). Switch ``needs_slice_subset_workaround()``. Retired by
  ``_update_slice_subset`` returning while ``numpy_slice_aggregation_transpose`` is None, which the probe sees, or by
  glue removing a removed layer's ``slices`` callback, which it does not see: the patch is then removed by hand (report
  candidate).
- **Axis labels set on the WCSAxes coordinate of glue's world axis**, ``world_n_dim - 1 - axis``, without placing ticks
  (``ImageViewer.update_x_axislabel``, ``update_y_axislabel``, #90, #371). Switch ``needs_axis_label_workaround()``,
  which the fork branch ``perf-g1a-wcs-labels`` leaves true. Retired by glue's label updates labelling that WCSAxes
  coordinate, which places no ticks (report candidate). One labelling the coordinate of ``ndim - 1 - axis`` also turns
  the probe false: the world axis of data of more world axes than pixel axes, as DKIST's, must then be installed apart
  from the probe, as the Redo patch's record is.
- **Redo of a subset change puts back the subset states its first run made, and Undo deletes only the groups the command
  made**, both under ``Coordinator.restoring`` (``ApplySubsetState.do`` and ``undo``, ``apply_subset_state``,
  ``undo_subset_state``, #182, #368, #377). Installed always, as Undo reads what each run records; switch
  ``needs_redo_workaround()`` for the Redo put-back alone. Retired by glue's ``ApplySubsetState`` keeping its states
  (upstream list) and its ``undo`` deleting only what its ``do`` made (report candidate); ``restoring``, under which no
  point follows one put back, is a glue-solar feature.
- ``u.Quantity`` **saver and loader for sessions** (``save_quantity``, #186). Switch: only while glue has no
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
- **A line's width keeps its positive lower bound when Settings gives an upper bound alone**, where glue-core's
  ``_get_model_fitter`` sets ``(None, upper)`` and drops the floor; glue's own Gaussian fitter loses astropy's
  ``stddev`` floor the same way (``GaussianConstantFitter.fit``, #367). Always on. Retired by ``_get_model_fitter``
  leaving a None limit to the model's own bound (report candidate).
- **Sampled statistics, the color limits among them, from glue-solar's own samples**: the raw-code counts of IRIS lazy
  data (``LazyData.compute_statistic``, ``sources/loaders/lazy.py``), whole frames of a DKIST dataset whose files are
  present (``DKISTData.compute_statistic``, #371) and evenly spaced rows and columns of 16 planes of an SST cube
  (``_Cube.compute_statistic``, ``_Cube._sample``, #230, #248). Always on. Retired by glue sampling dask arrays at
  random, not at chunk corners, and, for the SST cube, sampling cheaply (upstream list).
- **DKIST datasets' coordinates in glue's order**: a gWCS's world axes reordered to one per pixel axis as glue maps
  them, and IRIS data linked to a raster's step and slit pixel (``DKISTWCS``, ``_glue_order``, ``sources/dkist.py``;
  ``_SlitAt`` and ``_SlitPlace`` in ``link_hpc``'s links; #371, #373, #375, #378, #389). Always on (DKIST datasets).
  Retired by glue mapping world axes to pixel axes by ``axis_correlation_matrix`` (a comment on glue #2574, drafted).
- **glue's WCS link by APE 14 alone** where glue's needs an astropy WCS or either side has no ``has_celestial``, tested
  by a round trip from either side (``wcs_link_init``, #373, #378, #379, #385). Switch ``needs_wcs_link_workaround()``,
  which sees glue's AttributeError alone. Retired by the two commits of the fork branch ``ape14-wcs-link`` together:
  67f47e4 (overlapping glue #2595) gives glue's general case by ``axis_correlation_matrix`` for APE 14 WCSes, which
  turns the probe false, and 5ce2543 the round trip. A glue with the first and not the second also turns the probe
  false, and loses the round trip.
- **A DKIST mosaic's tiles suggested linked to its center tile only**, and other data to that tile, where glue
  suggests every pair (5778 for 108 tiles); the first tile left becomes the center once it is removed, saved in
  sessions (``sources/dkist.py``'s ``wcs_autolink`` in place of 'Astronomy WCS', ``_Recenter``, #373, #378).
  Always on. Retired by glue's autolinker suggesting a spanning set rather than every pair (report candidate).
- **An Image buffer of a DKIST dataset reads only the pixels glue samples**, where glue reads a DaskComponent's
  bounding box, 500 files of a ViSP map whose view samples 34 (``DKISTData.compute_fixed_resolution_buffer`` setting
  ``_EXACT``; ``_BoxRead`` in place of glue's ``fixed_resolution_buffer.DaskComponent``, #383). Always on
  (DKIST values, no subset). Retired by glue reading a DaskComponent's sampled pixels through the data's ``get_data``
  or dask's ``vindex`` (report candidate).
- **A restored Image layer's bad color given to its image** (``ImageLayerArtist.__init__``,
  ``glue_patches.image_layer_init``, #386): glue sets ``cmap_bad`` only as the layer state changes, so restored
  IRIS and DKIST layers drew NaN opaque. Switch ``needs_cmap_bad_restore_workaround()``. Retired by glue applying a
  layer state's ``cmap_bad`` at construction (fork branch, the restored ``cmap_bad``).
- **A DKIST mosaic image's tiles given their frame or repeat index at each pixel** beside their time
  (``_mosaic_links``, ``_At``, #391): glue derives a component through the first of equally short link paths,
  so a tile's frame came from another tile. Always on (mosaic images). Retired by glue preferring a dataset's own
  coordinate links among equally short paths (report candidate).
- **A DKIST frame quality's Time added after its header columns** (``_frame_quality``, #395): glue's Profile
  viewer gives a layer its data's first numeric component, a datetime too. Always on. Retired by glue's Profile
  layers leaving datetime components out of their attributes (report candidate).
- **An SST cube's reads hinted to the kernel before glue makes them** (MADV_WILLNEED), **and a dense view read as one
  plain read of the rows' band per plane** (``_Cube.get_data``, ``_Cube._hint``, ``_Cube._band``, #362). Always on
  (Linux and macOS). Retired by glue's ``compute_fixed_resolution_buffer`` and ``Data.get_data`` reading memory maps
  cheaply cold (report candidate).
- ``_TabularWCS.__gluestate__`` **and** ``__setgluestate__`` in place of glue's ``_save_wcs`` and ``_load_wcs``, which
  raise 'HDUList is required to retrieve -TAB coordinates' (``sources/sst.py``, #227). Always on (SST cubes). Retired
  by glue saving a -TAB WCS with its tables (report candidate).
- **Axis labels glue-solar sets in viewer state after glue's own resets**, with their units: a Profile's x and y, a
  quicklook Image panel's, a path diagram's and the light curves' (``VelocityTool._label_x``, ``VelocityTool._unit_y``,
  ``FrameTimeTool._label_exposures``, ``_diagram_label``, ``_point_curves``, #339, #367). Always on. Retired by glue's
  viewers labelling axes with their units (report candidate); for 'World N', glue's ``axis_label`` returning the name it
  checks.
- **Path diagram overrides of core's path slicer and their session savers** (``PathTool``, ``PathData``,
  ``_DiagramCoordinates``, ``_close_slice_viewers``, ``PathCrosshairTool._on_move``, ``_finish_roi``, #151, #191, #243,
  #262, #356). Always on. Retired by core's path slicer fixes (upstream list; report candidates for
  ``_close_slice_viewers`` calling ``close(warn=False)``, ``drive_parent_slice`` rounding and clamping,
  ``PathSlicedCoordinates`` leaving out world axes on the sliced pixel axes, index arrays through ``vindex``, and
  ``MplPathROI.finalize_selection`` resetting its background).
- **An SSTRED Stokes cube's unnamed Stokes axis named 'Stokes'** where its y axis is named (``sst_data``, #356), as
  glue's ``axis_label`` checks ``world_axis_names[axis]`` but returns ``world_axis_names[world_n_dim - 1 - axis]``.
  Always on. Retired by ``axis_label`` checking the name it returns (report candidate, upstream list).
- **Sunpy colormaps registered in matplotlib under their own names**, as glue saves a colormap's name and restores
  it from matplotlib's, where sunpy lists most under their key alone (``maps._add_colormap``, for each as the plugin
  loads, #98, #129). Always on. Retired by glue restoring sunpy colormaps by name (upstream list).
- **Raster windows of one restore read together** (``_read_logged_windows_together``, ``raster_files_data``'s
  ``_RESTORING``, #234). Always on. Retired by glue's LoadLog restoring one file's logs in one load (upstream list).
- **A dataset's style saved with its preferred colormap** (``maps._Style``, #189). Always on. Retired by glue-core
  saving and restoring ``preferred_cmap`` (upstream list).
- **A Profile viewer adds a quicklook Profile panel's dataset, and any cube of** ``large_data_size`` **values or more
  not from the IRIS reader, with its data layer hidden** (``hidden_cube_profile``, ``_FitOnceComputed``, #95, #233).
  Switch: the viewer's ``large_data_size`` and the data's ``describe.role``; the quicklook's ``_solar_hidden``. Retired
  by glue's ``_reset_y_limits`` using cached profiles only and ``compute_statistic`` without the float64 copy, or
  glue-qt adding large data hidden (upstream list).
- **A quicklook spectrum or curve panel's profile limits set on the GUI thread after each move of its subset**, so
  glue's ``update_limits`` finds them unchanged and does not queue the worker again (``_Refit._limits``, #363).
  Always on. Retired by glue's ``ProfileLayerArtist._update_profile`` recomputing on ``v_min`` and ``v_max`` only
  while ``normalize`` is on, or glue-qt's ``_calculate_profile`` drawing a cached profile without the worker (fork
  branches ``perf-g7``, ``perf-q1``, ``perf-q2``).
- **Per-frame limits left to the reference data's layers** as an Image viewer's reference data change
  (``PerFrameLimitsTool._whole_cube_again``, ``tools.py``, #102), as glue takes a per-frame layer's limits at the
  reference data's slice indices, an IndexError for data of another shape. Always on (Image viewers). Retired by glue
  taking a per-frame layer's limits at its own data's slice (report candidate).
- **A broadcast component saved as its values before the broadcast**, where glue writes the broadcast in full
  (``_BroadcastComponent``, ``_BroadcastTimes``, ``sources/loaders/iris.py``, #309). Always on (those components).
  Retired by glue's ``Component`` saver writing a broadcast array as its values and shape (report candidate).
- **A Profile viewer told that its x unit's conversion changed**, as 'Set rest wavelength…' sets or clears the rest
  wavelength its km / s is from, through glue's private ``ProfileViewerState._update_x_display_unit_choices``,
  ``_previous_x_att`` and ``_reset_x_limits`` (``VelocityTool._rest_changed``, ``lines.py``, #187). Always on. Retired
  by a public way to tell a Profile viewer's state that its x unit's conversion changed (report candidate).
- **glue's 'Save Python script to reproduce plot' listed once, before glue-solar's Save entries**: ``setup`` imports
  ``glue.plugins.tools.python_export`` and puts ``save:python`` in the Image and Profile viewers' ``subtools['save']``
  ahead of its own entries (``__init__.py``, #222), as glue's plugin adds it after them where it loads later. Always on.
  Retired by glue listing ``save:python`` before other plugins load (report candidate).

glue-qt
-------

- **Generic** ``solar:cursor_readout``. Switch ``not hasattr(ImageViewer, 'cursor_status')``. Retired by glue-qt #74.
- **Slice-slider drag throttle** (#68). Always on. Retired by glue-qt slider coalescing (upstream list).
- **Slice playback stopped when its viewer closes** (``ImageViewer.closeEvent``, #115). Per close: a slider still
  playing after glue-qt's own close. Retired by glue-qt stopping play timers on close (report candidate).
- **Loop… replaces a slice slider's** ``_browse_slice``, which the play timer calls through ``_play_slice``, and
  reverses the private ``_play_speed`` for Bounce; the step buttons keep glue-qt's (``tools._loop``, ``_LoopEntry``,
  #115, #166). Per slider, after Loop…, until glue-qt rebuilds the slider. Retired by glue-qt slider playback taking a
  range, step and bounce (kept by decision; upstream list).
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
- **One fitter per Profile viewer and fitter class for Fit Settings and fits, and Settings opening a fitter's own**
  ``settings_widget``, the IRIS fitter's component list (``glue_patches._get_fitter``, ``_on_settings``, ``_fit``,
  ``fitters._Settings``, #287, #314). Switch: while ``ProfileTools`` has no ``_get_fitter``; ``_on_settings`` also while
  ``needs_fitter_settings_workaround()``. Retired by glue-qt's ``ProfileTools._get_fitter`` (fork branch
  ``fitter-settings``) and its ``_on_settings`` using ``fitter.settings_widget`` (fork branch
  ``fitter-settings-widget``, dba71453).
- ``ProfileTools._fit`` **replaced, for the IRIS fitter, by its own loop over the layers**, which leaves out each
  layer's saturated samples and gives the model what ``summarize`` and 'Fit every spectrum' take of the layer
  (``fitters._fit``, #291, #313); with glue-qt's own ``_get_fitter`` it fits with the fitter glue-qt passes. Always on.
  Retired by glue-qt passing the layer to a fitter's ``fit`` and ``summarize`` (upstream list).
- **A quicklook panel makes its Point the edit subset** at a Pixel or Follow/lock press or move while a dataset is
  selected (``QuicklookImageViewer._edit_point``, ``FollowLockTool._follow``, #288, #361). Always on. Retired by
  glue-qt's data collection leaving the edit subset alone when a dataset is selected (upstream list).
- **The edit subset kept through a data-tree rebuild** (``quicklook._Application.__setgluestate__``, ``_new_group``,
  the light curves), where glue-qt's rebuild empties it. Always on. Retired by glue-qt keeping the edit subset through
  a tree rebuild (two parts, about 10 lines).
- **Quicklook panels marked** ``_closed`` **as their window's close box closes them** (``window_closed`` connected in
  ``quicklook._fill``'s ``add``, #360), as glue-qt's ``closeEvent`` leaves ``_closed`` unset. Always on (quicklook
  panels). Retired by glue-qt's ``closeEvent`` setting ``_closed`` (report candidate).
- **Analysis result viewers open with glue-qt's default mouse mode off** (``analysis.view``, #300). Always on. Retired
  by glue-qt's data collection leaving the edit subset alone (upstream list).
- **The Fit tab keeps every artist a fitter's** ``plot`` **returns**, so Clear removes each IRIS line's dashed curve
  (``glue_patches._plot_fit``, #314). Switch ``needs_fit_artists_workaround()``. Retired by glue-qt's ``_plot_fit``
  keeping every artist (fork branch ``fit-artists``, d6655bc5).
- **'Fit every spectrum' beside Fit on the Fit tab**, enabled after each fit's report for the viewer's last IRIS fit
  of a raster window or stack, its tooltip saying why when not (``fit_maps._enable`` wrapping ``ProfileTools.enable``,
  ``_report_fit``, ``_refresh``). Always on. Retired by a glue-qt hook for a fitter's own Fit-tab actions (report
  candidate; none on glue-qt or glue-core main).
- **Colormap icons drawn once per colormap and width** (``QColormapCombo._update_icons``, #177). Switch
  ``needs_icon_cache_workaround()``, at the first combo. Retired by glue-qt caching icons (fork branch
  ``perf-q3-cmap-icon-cache``).
- **Layer actions hidden where** ``applies(data)`` **refuses with a ValueError**, shown when the check raises anything
  else (``UserAction._can_trigger``, #223, #257). Switch ``needs_layer_action_applies_workaround()``. Retired by
  glue-qt's layer actions taking ``applies`` (fork branch ``layer-action-applies``).
- **glue-qt's slice sliders**: the sliders a rebuild replaces hidden, and each new slider showing the values and unit of
  glue's world axis ``world_n_dim - 1 - axis``, where glue-qt reads ``ndim - 1 - axis`` (``sync_sliders_from_state``,
  #380). Switch ``needs_slider_world_workaround()``, asked at the first call, for the world values; the hide of replaced
  sliders is always on. Retired by glue-qt's ``MultiSliceWidgetHelper`` hiding replaced sliders and reading glue's world
  axis (report candidate).
- ``GlueApplication.__init__`` **wrapped to put glue-solar's icon**, the macOS app's, on the application and its
  window after glue's own; quicklook panels' and strip windows' title bars get it too (``__init__.py``,
  ``quicklook._fill``). Always on. Retired by a glue-qt hook for the application icon (report candidate).
- **Viewers closed but not yet deleted left out of a saved session**, as when a script removes their data and saves in
  the same turn, where glue-qt lists them and glue cannot restore such an Image viewer
  (``GlueApplication.__gluestate__``, ``glue_patches.application_gluestate``, #364). Always on. Retired by glue-qt's
  ``GlueApplication.viewers`` or ``__gluestate__`` leaving closed viewers out (report candidate).
- **A write to glue's console log from another thread made on the GUI thread** (``GlueLogger.write``,
  ``glue_patches.logger_write``): the log is ``sys.stderr`` and edits its QTextEdit on the thread that writes, as
  irispy's warnings do while the observation browser reads files on a worker thread, which Qt allows on the GUI
  thread only. Always on. Retired by glue-qt's ``GlueLogger.write`` handing a write off the GUI thread to it (report
  candidate).
- **The Slope table's Table viewers reset after new rows** (``SlopeTool``, ``tools.py``, #175). Always on. Retired by
  glue-qt's Table viewer showing and sorting rows added to its dataset (report candidate).
- **A Table viewer of data with a time searches each value as the text the table shows**
  (``glue_patches.get_filter_mask``, #260). Switch ``needs_table_time_workaround()``. Retired by glue-qt's Table
  search matching ``str(x)`` (report candidate).
- **A tooltip for glue-qt's Profile viewer button** (``ProfileViewerTool.tool_tip``, ``setup``, #222). Switch
  ``ProfileViewerTool.tool_tip is None``. Retired by glue-qt giving the button a tooltip (upstream list).
- **glue-qt's Slice Extraction left off Image viewers**: its ``pv_slicer`` plugin ``setup`` made a no-op and the tool
  filtered from ``ImageViewer.tools``, so Path diagram is the one path tool (``setup``). Always on. Kept by
  decision.
- **A tool menu's entries treated as buttons are**, shown while ``enabled``, check-marked and keyed, **and the viewer's
  mouse mode, such as Pixel, left on as a plain entry runs, or turned back on after 'Save frames or movie…'** of
  glue-qt's Save menu (``tools._ToolMenu``, ``tools._keep_mouse_mode``, #92, #156, #222). Always on (``CoordinateTool``,
  ``ModesTool``, ``ViewTool``; the Save entry). Retired by glue-qt #72 for the entries shown while ``enabled``; for the
  rest by glue-qt's toolbar listing subtools in ``tools`` and ``actions``, with check marks and keys of the toolbar's,
  and leaving the active mouse mode on as a plain tool runs (report candidate).
- **A wavelength band kept as its slider moves**, by a validator of an Image viewer state's ``slices``
  (``tools.BandTool._band``, #169), as glue-qt's slider sets a plain index at any move. Per viewer: while a band is on.
  Retired by glue-qt's slice slider moving an ``AggregateSlice``'s center and keeping its range (upstream list).
- **The right-click entries shown or hidden for the selection again as a glue-solar data action returns, and as its
  worker ends** (``glue_patches.refresh_layer_actions``, called by ``layer_action``'s wrapper and ``analysis.start``,
  #255): glue-qt's ``LayerAction.update_enabled`` runs as the selection changes only, so an action that changes its
  own guard, as 'IRIS: radiometric calibration', stayed offered. Always on. Retired by glue-qt updating its layer
  actions after one runs (report candidate).
- **A Profile viewer's Fit and Collapse range read from glue-qt's private** ``_profile_tools.rng_mode`` of its
  ``profile-analysis`` tool: the range 'Lines in this range…' lists, and the one 'IRIS: line maps…' starts from
  (``lines.LinesInRangeTool.activate``, ``moments._profile_range``, #180, #332). Always on. Retired by glue-qt giving
  the range a public name (report candidate).
- **glue-solar's right-click entries listed by data kind**: ``layer_action.members``, glue-qt's registry list, sorted
  in place by ``_DATA_ACTIONS`` at import, other packages' entries first and as they were (``__init__.py``, #223), as
  glue-qt lists layer actions as they register, in import order. Always on. Retired by glue-qt's layer actions taking
  an order (report candidate).

astropy, WCSLIB, echo, matplotlib and mpl-scatter-density
---------------------------------------------------------

- ``_GlueWCS`` ``WCS_LOCK`` (#60), which also guards the one celestial model a slit-jaw image's gWCS sets and then
  evaluates at each frame (the dkist entry below; ``sji_bursts`` gives irispy a deep copy). Always on (not safely
  probeable). Retired by astropy #19174's fix, once 8 unlocked threads give 0 wrong -TAB values, where 8.0.2 gives 1187
  to 1267 in 2400 calls without crashing (comment drafted), together with dkist's ``VaryingCelestialTransform`` safe
  across threads.
- ``_LockedWCS``: each plain WCS beneath a ``_GlueWCS``, and each that ``link_hpc`` links or a restored session holds
  linked, made to hold ``WCS_LOCK`` in its transforms, copies and struct properties (``_lock_wcslib``, ``_HeldWCS``,
  ``_LinkedCollection``, #358); an SST cube's ``_LockedTabularWCS`` holds the cube's own ``RLock`` instead, taken after
  ``WCS_LOCK`` (#240); glue's ``world2pixel_single_axis`` and ``PixelSubsetState._to_linked_pixel_coords``, or their
  probe-gated fixes, run inside ``WCS_LOCK`` (``_hold_wcs_lock``, #232), and ``WCSAxes.reset_wcs`` inside the WCS's
  ``_held()`` lock (#226, #251). Names pinned by ``test_the_link_patches_hold_the_wcs_lock`` and
  ``test_the_analyses_hold_the_wcs_lock_in_each_wcslib_call_not_across_irispy``. Always on. Retired by astropy #19174's
  fix with the ``_GlueWCS`` lock; for the SST cube's lock, also WCSLIB's -TAB transforms no longer writing the shared
  tabprm's scratch fields (``tabx2s``), which astropy #19819 does not change.
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
  **drawn**: off either end dkist's ``Ravel`` gives a NaN time, on which WCSAxes raises for a range all NaN
  (``formatter_locator.py:159``), so a pixel past an end is given that end's time (``DKISTWCS.pixel_to_world_values``,
  #379, #385). Always on (DKIST datasets with a ``Ravel``). Retired by a WCSAxes fix for an all-NaN world range (report
  candidate).
- ``_TabularWCS.has_celestial = False`` **against wcslib's SIGSEGV in glue's autolinker** (#227); astropy then gives
  the angles as quantities, which ``tools._sky`` puts in a SkyCoord by physical type for paths, profiles and Slope
  (#359). Always on. Retired by WCSLIB cutting a -TAB table's celestial axes safely (report candidate).
- **SPECSYS 'TOPOCENT' on ground-based files without one** (``sources/sst.py``, #227). Switch: files with no SPECSYS.
  Retired by astropy treating a missing SPECSYS as no spectral observer (report candidate).
- ``_TabularWCS.axis_correlation_matrix`` **from the tables**, where astropy's says each -TAB world axis depends on
  its own pixel axis only (``sources/sst.py``, #227). Always on (SST cubes). Retired by astropy computing a -TAB WCS's
  matrix from its tables (report candidate).
- **The SST cube's own inverse**, ``_TabularWCS.world_to_pixel_values``, falling back to wcslib's (``sources/sst.py``,
  #227). Always on (SST cubes). Kept by decision.
- **A slit-jaw click finds a scanning raster's step and slit row from each step's slit as a line** (``sji_to_raster``,
  by ``_SlitAt`` as a DKIST raster's), not from the raster's world-to-pixel: WCSLIB's -TAB inverse does not extrapolate
  a 2-D table (``tab.c``: "Extrapolation for M > 1 is TBD"), so it has no pixel past the center of a first or last step.
  Always on. glue's links still invert the table, so a region or a linked layer ends at those centers. Retired by WCSLIB
  extrapolating a 2-D table by half a cell (report candidate).
- **The mouse-over readout places WCSAxes ticks before formatting** (``_readout``, ``tools.py``, #90). Always on.
  Retired by WCSAxes ``format_coord`` without a tick placement (report candidate).
- **A colormap matched to its own combo entry** (echo's ``_find_combo_data``, #194). Switch
  ``needs_combo_match_workaround()``. Retired by echo matching the entry that is the value first (upstream list).
- **mpl-scatter-density's 0.5 s hold after a canvas resize, ended before each saved frame**: ``SaveSequenceTool``
  calls ``on_release()`` on each ``BaseImageArtist`` in the viewer's axes (#270). Always on. Retired by
  mpl-scatter-density ignoring the hold while matplotlib saves (``canvas._is_saving``; report candidate).
- **No figure manager on the canvas while 'Save frames or movie…' saves** (``SaveSequenceTool``, ``tools.py``, #145), as
  matplotlib's ``FFMpegWriter`` evens out an odd frame size with ``set_size_inches(forward=True)``, which resizes the
  canvas through its manager, and glue then zooms to the new size. Per run. Retired by matplotlib's movie writers sizing
  the figure without resizing its window (report candidate).
- **An IRIS dataset's pixel-to-world values kept by their exact inputs** (``_GlueWCS.pixel_to_world_values``,
  ``_MEMO_ENTRIES``, ``_MEMO_SAMPLES``, ``sources/loaders/iris.py``, #90), as WCSAxes converts the same pixels about
  twice in each draw and all of them again at every redraw; ``DKISTWCS`` keeps its own (under dkist). Always on. Retired
  by WCSAxes keeping its own conversions through each tick placement (upstream list).

dkist
-----

- **A world-to-pixel through a slit-jaw image's gWCS at a time off its frames gives NaN pixels on ARM too**: dkist casts
  the NaN frame index to an int, on x86-64 the least int64, off its table, which it leaves NaN, and on ARM 0, frame 0's
  x and y (``_GlueWCS.world_to_pixel_values``, ``_frames``, #342, #353). Always on. Retired by dkist's
  ``sanitize_index`` handling a NaN index (report candidate).
- **dkist's** ``Unravel`` **inverse, of a raveled dataset, given 1-D values, and NaN pixels at a time off the dataset's
  frames** (``DKISTWCS.world_to_pixel_values``, ``_off_frames``, #378, #379, #385): it raises TypeError on arrays of
  more than one dimension, and ValueError, calling ``int()`` on a NaN time. Always on (DKIST datasets) for the 1-D
  values; switch for the NaN pixels: dkist raising ValueError, outside the WCS link's test of its transforms
  (``STRICT_INVERSE``), which leaves data of other times unlinked. Retired by ``Unravel.evaluate`` taking N-d input, and
  ``Unravel`` giving NaN for a NaN index (report candidates).
- **DKIST values read by glue-solar, not dkist's dask array**, which decompresses each file whole
  (``DKISTData.get_data``, ``_Files``, ``_section``, ``_Open``, ``KEPT_OPEN``, #383, #385), the open-file limit raised
  by ``lazy.allow_open_files``; dask's reads where a dataset is cut within its files' frames or dkist gives no HDU of
  its files; ``DKISTWCS.pixel_to_world_values`` keeps its last inputs, as the IRIS memo above. Always on (DKIST
  datasets). Retired by dkist's dask array passing each view to its loaders' ``hdu.section`` (dkist #226) and
  ``VaryingCelestialTransform`` evaluating all raster steps at once (dkist #246, #256).
- **dkist's** ``VaryingCelestialTransform`` **sets the parameters of its one celestial model at each pointing index,
  then evaluates it**, so glue-qt's profile worker beside the GUI thread gave the map another step's pointing
  (143.6" off on AIOMGG); a lock around dkist's forward and inverse and ``_off_frames`` (``DKISTWCS._lock``, #385).
  Always on (DKIST datasets). Retired by dkist evaluating it without changing its shared model (report candidate).
- **dkist's private** ``_striped_external_array.target`` **read**, the HDU each file's array is in, as the loader
  sets up a dataset's ``_Files`` (``sources/dkist.py``). Always on (DKIST datasets). Retired by ``target`` proxied on
  ``DKISTFileManager`` (1 line).
- **The ASDF path made absolute before** ``dkist.load_dataset`` (``sources/dkist.py``), as a relative
  ``files.basepath`` breaks dkist's reads from another working directory. Always on. Retired by dkist resolving
  ``files.basepath`` (1 line, on dkist #366).
- **'Download these frames…' sends a DKIST dataset's chosen FITS files alone** through dkist's private
  ``_orchestrate_transfer_task``, since ``FileManager.download`` adds the ASDF file, browse movie and quality report to
  every transfer (``_transfer``, ``sources/dkist.py``, #396). Always on (a DKIST download); ``FileManager.download`` of
  each sliced dataset where the private name is gone or its arguments changed. Retired by ``FileManager.download``
  sending the FITS files alone (drafted).
- **'Download these frames…' follows its transfer by the files in the folder** (``_watch_download``,
  ``DOWNLOAD_STALLED``, ``sources/dkist_actions.py``; ``_ARRIVING`` in ``_section``; #396), as neither
  ``FileManager.download(wait=False)`` nor ``_orchestrate_transfer_task`` returns a Globus task to follow. Always on (a
  DKIST download). Retired by dkist returning the Globus task ID of a transfer that does not wait (dkist #516).

irispy
------

- **irispy's private** ``irispy.utils.bursts._SI_IV`` **and** ``irispy.utils.mg_features._REST_WAVELENGTH`` **read**,
  the rest wavelengths its burst search and Mg II features measure from, to cut a raster window to the wavelength pixels
  irispy takes and, for Mg II, to check and apply a rest wavelength set on the window (``bursts._crop``,
  ``sources/bursts.py``, #172; ``mg_features._crop``, ``_rest``, ``sources/mg_features.py``, #153, #237). Always on
  ('IRIS: detect UV bursts…', 'IRIS: Mg II features…'). Retired by irispy giving the wavelengths public names (report
  candidate).

glue-solar's own
----------------

Features and decisions with no upstream route; listed so the overrides are known.

- **Physical aspect** replaces glue's ``ImageViewerState._set_axes_aspect_ratio`` on each Image viewer's state,
  scaling its ratio by the arcsec ratio while on and by 1 while off, and refits the limits through glue's private
  ``_axes_aspect_ratio`` and ``_adjust_limits_aspect`` (``PhysicalAspectTool``, #103). Always on. glue-solar feature
  (an upstream candidate in UPSTREAM_REVIEW).
- ``GlueApplication.closeEvent`` **wrapped to keep the last session on quit**, telling a replaced window by glue-qt's
  private ``_new_application`` (``__init__.py``, #206, #297). Always on. glue-solar feature.
- **Quicklook Image panels leave each mouse mode's hint** (its ``status_tip``) out of their status line, where a
  narrow panel's frame time clipped it (``QuicklookImageViewer.set_status``). Always on. Kept by decision.
- **A sit-and-stare raster's slit axis rolled past 45° labeled as its longitude**, in viewer state and on that
  WCSAxes coordinate, which glue labels by spine with the exposure axis' label (``FrameTimeTool._label_exposures``,
  ``_beside_exposures``, #359). Switch: sit-and-stare rasters rolled past 45°. glue-solar feature.
