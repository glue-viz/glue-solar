.. _glue_solar_users_guide_loading_iris_level_2_raster_and_sji_files:

======================================
Browsing and Loading IRIS Level 2 Data
======================================

Browsing a folder by observation
--------------------------------

``glue-solar`` adds an observation browser inspired by a subset of the IDL ``iris_xfiles`` tool;
it does not reproduce the IDL quicklook features.
Point it at any folder holding IRIS Level 2 files - the usual ``level2/yyyy/mm/dd/<obs>/`` tree,
a flat download folder, or a pooch cache - and it lists every observation it finds, grouped by
OBSID and start time, with the description, pointing and number of files:

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

Tick the entries you want (ticking the observation row ticks everything under it) and press
"Load selected". The data are added to the data collection and the first slit-jaw (or AIA) cube is
opened in an Image Viewer; use its ``Time (Utc)`` slider to step through time.
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
cube, and a raster file loads one dataset per spectral window.

Linking
-------

Glue does not currently autolink irispy's time-varying SJI gWCS and raster ``-TAB`` WCS. To
propagate spatial selections, open the Data Manager's link editor and manually pair
``Helioprojective Longitude`` and ``Helioprojective Latitude`` between datasets.
SJIs, aligned AIA cutouts and rasters all name their spatial axes this way.

Saving sessions
---------------

Saving a session that contains IRIS data can fail before any file is written. The irispy
metadata and WCS objects, including SJI gWCS and raster lookup tables, need dedicated serializers;
save derived products separately rather than relying on a Glue session as their only copy.
