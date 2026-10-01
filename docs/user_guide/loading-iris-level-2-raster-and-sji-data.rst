.. _glue_solar_users_guide_loading_iris_level_2_raster_and_sji_files:

======================================
Browsing and Loading IRIS Level 2 Data
======================================

Browsing a folder by observation
--------------------------------

``glue-solar`` adds an observation browser inspired by a subset of the IDL ``iris_xfiles`` tool;
it does not reproduce the IDL quicklook features.
Point it at any folder holding IRIS Level 2 files - the usual ``level2/yyyy/mm/dd/<obs>/`` tree,
a flat download folder, or a pooch cache - and it lists every observation it finds, one row per
OBSID and start time, with the columns STARTOBS, OBSID, Description, the pointing XCEN, YCEN and
SAT_ROT, and Files, the number of files:

.. image:: images/loading-iris-data-2.png
   :width: 800
   :alt: The IRIS observation browser listing the observations found in a folder

Open it from the "Plugins" menu with "IRIS: browse observations…". Subfolders are searched by
default; un-tick "Search subfolders" to look at one folder only. The last folder used is remembered.

Expand an observation to see what can be loaded:

- one entry per slit-jaw band (``SJI_1330``, ``SJI_1400``, ``SJI_2796``, ``SJI_2832``), and a
  separate one for each deconvolved slit-jaw file (``SJI_2796 (deconvolved)``),
- one entry per raster spectral window (for example ``Mg II k 2796 — 8 raster file(s)``): every
  raster scan of the observation is loaded for that window,
- one entry per co-aligned SDO/AIA cutout (``aia_l2_*.fits``), for example ``AIA 1700``. Cutouts
  are recognised by file name and header, so they need no ``_SDO`` directory.

An observation with only one entry shows it in its "Files" column (for example ``1 — AIA 1700``)
and has its tick box on its own row.

Tick the entries you want (ticking the observation row ticks everything under it); each slit-jaw
channel and AIA cutout you tick loads as a dataset of its own. Then press "Load selected": the data
are added to the data collection. With "Open quicklook" ticked, the default, each observation with a
raster or slit-jaw image opens in a quicklook (see `The quicklook`_). Otherwise the first slit-jaw
(or AIA) cube opens in an Image Viewer, where its ``Time (Utc)`` slider steps through time; nothing
opens for rasters alone.
Tick "Stack sequential raster scans" to place two or more raster scans of a window into a single
4D cube without resampling their detector values. The stack's values are floating point and are
kept in a temporary file (a NumPy memmap) rather than in memory. Its leading ``Scan`` coordinate
selects the original raster scan, and its ``Time`` component contains the exact acquisition time of
every pixel. Scan 0 supplies the stack's nominal helioprojective WCS; later scans remain aligned by
raster and detector index rather than carrying their distinct absolute pointings. Load scans
separately when those per-scan absolute coordinates are required. A selected window containing one
scan loads normally as a 3D dataset and also exposes its exact per-step ``Time`` values.

Every raster, stack, slit-jaw and AIA dataset has these components, in the order Glue lists them:
the data (named after the dataset), ``<label> mask``, ``Time`` and ``Exposure time`` (a stack lists
``Exposure time`` before ``Time``). ``Time`` is the UTC acquisition time as a datetime64, one value
per raster step, slit-jaw frame or AIA frame (per scan and step for stacks). ``Exposure time`` is in
seconds, one value per raster step or frame (per scan and step for stacks). The "Frame time" tool
in the Image Viewer toolbar shows the displayed frame's time and exposure in the status bar, as a
range when the image spans several frames; for a single slit-jaw frame its tooltip gives that
frame's pointing (PZT offset, field-of-view centre and slit position), which glue-solar keeps in
the dataset's metadata.

Slit-jaw and raster values are floating point. The IRIS fill values -200 and -199 become NaN; in
AIA cutouts only -200 does, and a cutout without fill keeps its integer values. glue-solar leaves
+Inf samples (the ITN 26 saturation code) unchanged and outside the mask; Level 2 files stored as
16-bit integers cannot hold +Inf, so their saturated samples keep the largest value the file can
store. ``<label> mask`` is a uint8 array that is 1 where the data are NaN and 0 elsewhere.

Rasters with a negative raster step (``STEPS_AV`` below -0.01) keep irispy's default orientation:
irispy reverses their raster-step axis, with the data, coordinates, times and per-step metadata
together, so the step axis runs opposite to the acquisition order and ``Time`` runs backwards
along it. The documented alternative is irispy's ``revert_v34=True`` option
(``irispy.io.spectrograph.read_spectrograph_lvl2``, also passed on by ``irispy.io.read_files``),
which keeps the file order; glue-solar does not use it.

Dragging a slice slider updates the image at most every 0.1 s and again when you let go, so large
cubes keep up with the mouse; the arrow keys, clicks on the slider and playback still step at once.

The point you select with the Pixel tool on a raster or stack is one slit position at one raster
step or exposure; on a stack it stays on the scan that was displayed when you clicked. If you then
swap the axes of a viewer of that dataset, for example turning the raster map into wavelength
against slit, the viewer's new step slider moves to the point. Wavelength sliders are never moved.
The "Coordinate" menu in the Image Viewer toolbar has "Time master", which records the displayed
dataset as the time reference of its observation (same OBSID and STARTOBS), and "Clear point".
The Pixel tool stays active after either entry.

Downloads that are still packed (``*_raster.tar.gz``, ``*_SDO.tar.gz``) show up under their observation
as an "Extract <archive> (<size> MB, next to the archive)" entry. Tick it and press "Load selected":
the archive is unpacked into a folder of the same name next to it (the layout irispy and pooch use),
the list refreshes, and you can then tick the spectral windows or cutouts it contained. Extraction
is completed in a temporary sibling directory, so a failure leaves the archive visible for retry.
Nothing is loaded in that step, and the archive is left in place.

Opening a single file
---------------------

"File -> Open Data Set" also understands IRIS Level 2 files directly: a slit-jaw file loads as one
cube, and a raster file loads one dataset per spectral window, labelled with the file's raster number
(``…-r00003``). Files opened this way, or given on the ``glue`` command line, load one by one with
every spectral window and cannot be stacked, so use the observation browser for large or multi-scan
observations.

Overlaying the missing-data mask
--------------------------------

To see where data are missing, turn ``<label> mask`` into a
`subset <http://docs.glueviz.org/en/stable/getting_started/index.html#defining-subsets>`__, which
every Image Viewer of the dataset draws over the data. A selection replaces the subset selected in
the data collection, which in a quicklook is ``Point``, so select the dataset itself first:

- Select the dataset in the data collection and choose "Create faceted subsets" in the
  "Data Manager" menu (or the data collection's right-click menu). Pick the ``<label> mask``
  attribute, set the range from 0 to 1 and the number of subsets to 2. The second subset,
  ``0.5<=<label> mask<=1.0``, holds every missing sample, and the first the others.
- Or select the dataset in the data collection, show ``<label> mask`` in a Histogram viewer and
  select an "X range" over the bar at 1. The Histogram viewer asks "Add large data set?" for
  datasets of 2e7 samples or more, with Cancel as the default button: a full slit-jaw cube, such as
  the 6.5e7 samples of OBSID 4000255147's SJI 1400, needs "OK".
- A mask of your own comes from a FITS file through "Import subset mask(s)" in the "Data Manager"
  menu, with the dataset selected. Each HDU of signed integers (BITPIX 16, 32 or 64) becomes a
  subset of the samples above 0, and must have the dataset's shape. glue skips unsigned HDUs, such
  as 8-bit images (BITPIX 8) and 16-bit ones stored with BZERO. "Export subset mask(s)" writes
  masks it can read back.

The first two leave the new subset selected, and "Pixel" would replace it, so select ``Point`` in
the data collection before moving a quicklook's point again.

Linking
-------

The observation browser links the ``Helioprojective Longitude`` and ``Helioprojective Latitude``
of every slit-jaw image, raster and aligned AIA cutout it loads, so selections carry over between
them. For data opened with "File -> Open Data Set", choose "IRIS: link helioprojective
coordinates" from the "Plugins" menu; it only adds links that are missing, so running it again
after loading more data is safe. Removing a dataset leaves the others linked.

- A region drawn on a raster map selects, in every slit-jaw frame, the pixels that lie inside it at
  that frame's own pointing. For a sit-and-stare raster the selection marks where the slit was on
  the Sun during the selected exposures: it lies on the slit in the slit-jaw frames taken then, and
  moves away from it in other frames as the pointing changes.
- A selection on longitude or latitude, for example from a scatter plot, carries over in both
  directions.
- A region drawn on a slit-jaw image does not carry over to a raster: which frame it belongs to
  would need the time, and time is never linked.

A region drawn on a raster map can be slow to show on a slit-jaw image: glue works out the selection
for every screen pixel of the slit-jaw viewer each time it draws a frame, and does not respond
meanwhile. At the default viewer size this takes under a second with a 64-step raster, but 10 to 20
seconds with a 1600-step sit-and-stare raster, for every frame you step to, and longer in a larger
viewer.

The quicklook
-------------

The quicklook is a CRISPEX-style set of viewers for one observation, in a new tab. Open it

- from the observation browser, with "Open quicklook" ticked (the default): each observation you
  load opens in its own quicklook, showing the raster window you ticked if you ticked one;
- for data already loaded, with "IRIS: quicklook…" in the "Plugins" menu, which asks which
  observation when several are loaded;
- from the command line, with ``glue --startup=iris_quicklook`` followed by the files. Files given
  this way load one by one, so each raster file keeps its raster number in its label
  (``…-r00003``) and the quicklook shows the first; to stack the scans, use the browser;
- from glue's Terminal, with ``glue_solar.quicklook.quicklook(application, datasets)``.

For those used to CRISPEX:

.. list-table::
   :header-rows: 1

   * - CRISPEX or iris_xcontrol
     - In glue-solar
   * - ``crispex, raster, sjicube=sji`` (one call per observation)
     - Tick the observation in the browser, or ``glue --startup=iris_quicklook raster.fits sji.fits``
   * - several ``sjicube`` files
     - Tick every slit-jaw channel; each gets its own viewer
   * - iris_xcontrol's raster, sit-and-stare and multi-raster modes
     - Chosen from the observation: map, slit against time, or a stack's map with its scan slider
   * - ``spcube`` (transposed cube)
     - Not needed: the wavelength panel shows wavelength against step, exposure or scan

It shows one spectral window: Mg II k 2796 when loaded, otherwise the first (pass
``window="Si IV 1403"`` to choose). The raster opens as three panels, plus one viewer per slit-jaw
channel and a spectrum panel:

- a raster: the map (step against slit), the spectrogram (wavelength against slit) and wavelength
  against step;
- a sit-and-stare raster: slit against time, the spectrogram and wavelength against time;
- a stack of raster scans: the map of the current scan, the spectrogram and wavelength against scan.

A sit-and-stare raster's exposure axis, in the quicklook or any Image viewer, is labelled
"Exposure (acquisition order)" with the UTC range of its exposures on a second line, and its ticks
are exposure numbers: it is an index axis, so exposures are evenly spaced whatever their cadence.
The other axis shows only its own coordinate. The label and ticks come back whenever glue resets
the axes, after an axis change or, on the wavelength panel, a slit move; a label typed in the
viewer's axes options is kept until that reset, as glue's own labels are.

In every Image viewer, each world coordinate's ticks are labelled with that coordinate's name.
WCSAxes can put a coordinate's ticks on another side than the axis it belongs to: latitude can run
along the bottom of a slit-jaw image rolled by more than 45°, and the step axis of a raster's
wavelength-against-step panel can show latitude on the left and longitude on the right when the
raster has a small roll. The label then stays with the ticks, and an x or y axis label typed in the
axes options names the coordinate of that axis, wherever its ticks are; glue-core 1.27.0 alone
labels the bottom and left ticks after the x and y axes, whichever coordinate they show.

The map shows the wavelength nearest the window's reference wavelength, and the panels use
99.5 % limits. A point, the edit subset "Point", starts at the centre of the map with the Pixel
tool active: drag it on the map, and the spectrum panel shows its spectrum. The point is a detector
pixel (a step or exposure, and a slit position) at every wavelength, and the other panels follow
it: the spectrogram moves to its step and the wavelength panel to its slit. Its crosshair shows
only on the map; the spectrogram and the wavelength panel highlight its row instead. Clicking the
spectrogram or the wavelength panel moves the point there and the map to the clicked wavelength;
no other wavelength slider moves. Moving a step, exposure or scan slider moves the point, so on a
stack the point stays on the map's scan. A Profile's collapse of an axis is left in place. After
"Clear point" the panels stop following each other until the next click, except in time: the
slit-jaw viewers keep following the exposure slider of a sit-and-stare raster and the scan slider of
a stack's map, on a scanning raster the time stays at the last point's raster step, and a slit-jaw
time master (see below) still moves the others. A point clicked on a slit-jaw image is
marked only there, and the spectrum panel is empty until the next raster click. The raster panels have no region selection tools, because a region drawn on a
raster map is recomputed on every slit-jaw viewer for each screen pixel at every frame (see
Linking). Each quicklook has its own point, shown only in its own panels, edited while its tab is
shown and moved only by that tab's sliders. Where a point does not show, it is not in the viewer's
layer list either, since glue would still redraw a hidden layer at every move: drag the subset onto
a viewer outside its quicklook to show it there. In its own quicklook, each move adds the point
back to the image panels of the dataset it is on and removes it from the others. Another Image viewer of the same data follows the point. When a slit-jaw channel is loaded both plain and deconvolved,
the plain one is shown and the status bar names the other. The spectrum panel does not ask "Add
large data set?", and the status bar gives the size of the data it shows.

The panels also follow one time. The raster is the time master: the slit-jaw viewers show the frame
nearest the time of the point's exposure or raster step (mid-raster before there is a point). Choose
"Time master" in the "Coordinate" menu of a slit-jaw viewer to make it the master instead; the
raster then moves to the exposure, or on a stack the scan, nearest each frame, keeping the slit and
the raster step. The master rules: moving the raster's exposure or scan slider by hand, or clicking
another exposure or scan, snaps the raster back to the one matching the master's frame, while a
slit-jaw follower moved by hand keeps its frame until the panels next follow the time, on a click, a
move of the point or of the master, or when its tab is shown again. A dataset with nothing within
half its own time step of the master's time (for a
scanning raster, one that does not cover it) keeps its frame and is greyed. The "Frame time" readout
says which dataset is the time master, how far each matched dataset's time is from the master's
(Δt) and "NO MATCH" with that offset for the others. Wavelength and slit sliders are never moved.

Each slit-jaw viewer is titled with its channel ("SJI 1400", "SJI 2796 (deconvolved)") and opens on
the raster's field of view with a margin. Every slit-jaw viewer, in a quicklook or not, draws the
displayed frame's slit as a dashed line (from the frame's slit position in the file) and the raster
point as a red cross, placed with that frame's own pointing. The cross is hidden, and the "Frame
time" readout says "outside SJI FOV", when the point is off the image; neither is drawn while the
viewer shows the frame axis. A slit-jaw frame taken a raster step earlier or later than the point
shows the slit a step away from the cross.

Viewer tools and windows
------------------------

glue's `getting started guide <http://docs.glueviz.org/en/stable/getting_started/index.html>`__
describes its viewers and tools; this section names those IRIS work uses most, as glue-qt 0.4.2
labels them. A toolbar button's tooltip gives the tool's single-key shortcut if it has one, for
example "Zoom to rectangle [shortcut: Z]".

Besides glue's "Home" (H), "Pan" (M), "Zoom" (Z) and region selection tools, the Image Viewer
toolbar has:

- "Pixel" ("Select a single pixel based on mouse location"): click or drag to select one pixel.
  On IRIS data this is the point the other viewers follow (see `The quicklook`_).
- "Contrast/Bias": drag on the image, left and right for the bias, up and down for the contrast.
  The "Reset" button next to the layer's contrast/bias sliders undoes it.
- "Slice Extraction" (P): draw a path and press Enter to see the data along it in a new window.
  It is offered for 3D data only, so not for stacks.
- "Cursor readout", from glue-solar: the world position and the value under the mouse, in the
  status bar. Press W over the image to switch between world and pixel positions; the button hides
  and shows the readout, and the mouse mode, such as Pixel, stays on.
- "Frame time" and the "Coordinate" menu, from glue-solar, described above; the "Frame time" button
  hides and shows its readout, and the mouse mode stays on.
- "Hide axes", from glue-solar: hides the viewer's axes (ticks, tick labels, axis labels and frame),
  and shows them again; the mouse mode, such as Pixel, stays on. Without them each slice step and
  redraw is faster, since no ticks are placed; the image, subsets, links, the slit and point of
  slit-jaw viewers and the readouts work as before, and the mouse-over position stays in world
  coordinates. A saved session keeps each viewer's choice. To open every new Image viewer,
  quicklook panels included, without axes, add ``solar_show_axes = false`` to the ``[main]`` section
  of glue's settings file, ``~/.glue/settings.cfg``, or type
  ``from glue.config import settings; settings.SOLAR_SHOW_AXES = False`` in glue's terminal for the
  rest of the session ("OK" in glue's Preferences then saves it to that file).
- A button with a spectrum icon and no tooltip, which opens a 1D Profile viewer of the image's data.
- The save menu, with "Save plot to file" and "Save Python script to reproduce plot", and the
  window menu, with "Move to another tab" and "Change viewer title".

Each viewer is a window in the current tab, with its own minimise, maximise and close buttons. The
"Canvas" menu has "New Data Viewer" (Ctrl+N), "New Tab" (Ctrl+T), "Gather Windows" (Ctrl+G), which
places the tab's viewers side by side, and "Rename Tab" (Ctrl+R); on macOS these use Cmd. Backspace
closes the active viewer after asking "Do you want to close this window?" if it is one of glue's own
Image, Scatter or Histogram viewers. It does nothing in a Profile or Table viewer, or in the
quicklook's map, spectrogram and wavelength panels. In the data collection, though, Backspace is
"Delete Layer": it removes the selected datasets and subsets at once, without asking and without
undo.

Glue has no gamma setting. A gamma below 1, which brightens faint emission, can be approximated with
the "Square Root" stretch, a gamma of 0.5 applied between the limits: in the Image Viewer's layer
options, type the lower and upper limits (the limits menu then reads "Custom") and choose
"Square Root" in the stretch menu.

Saving sessions
---------------

Saving a session that contains IRIS data can fail before any file is written. The irispy
metadata and WCS objects, including SJI gWCS and raster lookup tables, need dedicated serializers;
save derived products separately rather than relying on a Glue session as their only copy.
