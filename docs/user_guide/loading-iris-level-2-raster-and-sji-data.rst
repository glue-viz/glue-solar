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
A raster file that is not Level 2 (its ``DATA_LEV`` is not 2), such as a product derived from
rasters, is left out, and the progress bar says how many were, for example "Skipped 1 raster file(s)
that are not Level 2".

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
are added to the data collection. glue reads the files in the background, one at a time, and the
progress bar counts them; meanwhile the list and its boxes are locked and "Cancel" reads "Stop".
"Stop" ends the load once the file being read is done and loads the entries read in full, such as a
slit-jaw channel read before a raster window, or nothing if none was. Pressing Esc or closing the
browser drops the load: nothing is loaded. With "Open quicklook" ticked, the default, each
observation with a raster or slit-jaw image opens in a quicklook
(see :ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`). Otherwise the
first slit-jaw (or AIA) cube opens in an Image Viewer, where its ``Time (Utc)`` slider steps through
time; nothing opens for rasters alone. If an entry fails to load, the browser stays open and its progress bar names
the file and the error; for a raster window, the first raster file that fails to load on its own, or
how many raster files there are if each loads on its own but not together.
Tick "Stack sequential raster scans" to place two or more raster scans of a window into a single
4D cube without resampling their detector values. Each scan stays in its own file, as a single scan
does (see `Memory and open files`_); scans stored as floating point, such as irispy's test files,
are copied into a temporary file (a NumPy memmap) instead. Its leading ``Scan`` coordinate
selects the original raster scan, and its ``Time`` component contains the exact acquisition time of
every pixel. Scan 0 supplies the stack's nominal helioprojective WCS; later scans remain aligned by
raster and detector index rather than carrying their distinct absolute pointings. Load scans
separately when those per-scan absolute coordinates are required. A selected window containing one
scan loads normally as a 3D dataset and also exposes its exact per-step ``Time`` values.

Every raster, stack, slit-jaw and AIA dataset has these components: the data (named after the
dataset), ``Time`` and ``Exposure time`` (a stack lists ``Exposure time`` before ``Time``),
``<label> mask``, which Glue computes from the data as it reads them and so lists under "Derived
components" (files stored as floating point keep it in memory, listed second), and ``<label> DN/s``,
also derived. ``Time`` is the UTC acquisition time as a datetime64, one value per raster step,
slit-jaw frame or AIA frame (per scan and step for stacks). ``Exposure time`` is in seconds, one
value per raster step or frame (per scan and step for stacks). ``<label> DN/s`` is the data divided
by the exposure time, with the unit DN/s (the 1D Profile viewer's "y_unit" menu labels its axis
with it), and NaN where an exposure took 0 s, as step 157 of OBSID 3610108077's Si IV windows did.
The "Frame time" tool in the Image Viewer toolbar shows the displayed frame's time and exposure in
the status bar, as a range when the image spans several frames; for a single slit-jaw frame its
tooltip gives that
frame's pointing (PZT offset, field-of-view centre and slit position), which glue-solar keeps in
the dataset's metadata. The mouse-over readout (see "Cursor readout" in
:ref:`Viewer tools and windows <glue_solar_users_guide_viewer_tools_and_windows>`)
gives the time and exposure of the pixel under the mouse: on a raster map those of the step it is
on.

Slit-jaw, raster and AIA values are floating point. The IRIS fill values -200 and -199 become NaN,
in AIA cutouts too. glue-solar leaves
+Inf samples (the ITN 26 saturation code) unchanged and outside the mask; Level 2 files stored as
16-bit integers cannot hold +Inf, so their saturated samples keep the largest value the file can
store. ``<label> mask`` is a uint8 array that is 1 where the data are NaN and 0 elsewhere.

Slit-jaw images open in sunpy's IRIS colormap of their channel, raster windows and stacks in its
FUV or NUV colormap by their detector (``TDETn``), and AIA cutouts in sunpy's AIA colormap of their
wavelength. The FUV and NUV colormaps have the colours of the 1330 and 2796 ones, whose names the
colormap menu of an Image Viewer layer shows for them. That menu lists Glue's own colormaps and
these IRIS and AIA ones, plus the colormap of any file loaded as a sunpy Map; Glue draws every
colormap listed each time it opens a layer, so the other sunpy colormaps are left out. To list
another, add it with ``colormaps.add`` in a ``config.py``, as
`Glue's customization guide <https://docs.glueviz.org/en/stable/customizing_guide/customization.html>`__
describes.

Rasters with a negative raster step (``STEPS_AV`` below -0.01) keep irispy's default orientation:
irispy reverses their raster-step axis, with the data, coordinates, times and per-step metadata
together, so the step axis runs opposite to the acquisition order and ``Time`` runs backwards
along it. The documented alternative is irispy's ``revert_v34=True`` option
(``irispy.io.spectrograph.read_spectrograph_lvl2``, also passed on by ``irispy.io.read_files``),
which keeps the file order; glue-solar does not use it.

Dragging a slice slider shows its latest position each time the image has been redrawn, skipping
the positions passed in between, and again when you let go, so large cubes keep up with the mouse;
the arrow keys, clicks on the slider and playback still step at once.

The point you select with the Pixel tool on a raster or stack is one slit position at one raster
step or exposure; on a stack it stays on the scan that was displayed when you clicked. If you then
swap the axes of a viewer of that dataset, for example turning the raster map into wavelength
against slit, the viewer's new step slider moves to the point. Wavelength sliders are never moved.
The "Coordinate" menu in the Image Viewer toolbar has "Time master", which records the displayed
dataset as the time reference of its observation (same OBSID and STARTOBS), "Clear point", and
"Go to UTC…", which moves the time master, and "Loop…" for the frame, exposure, step or scan slider (see
:ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`). The Pixel tool stays active after
each entry.

Downloads that are still packed (``*_raster.tar.gz``, ``*_SDO.tar.gz``) show up under their observation
as an "Extract <archive> (<size> MB, next to the archive)" entry. Tick it and press "Load selected":
the archive is unpacked into a folder of the same name next to it (the layout irispy and pooch use),
the list refreshes, and you can then tick the spectral windows or cutouts it contained. Archives are
unpacked in the background too: "Stop" leaves those not yet started packed. Extraction
is completed in a hidden temporary sibling directory, which the list leaves out, so a failure leaves the
archive visible for retry.
Nothing is loaded in that step, and the archive is left in place.

.. _glue_solar_users_guide_iris_memory_and_open_files:

Memory and open files
---------------------

Level 2 files store their data as 16-bit integers with a scale and an offset. glue-solar leaves
those integers in the file and scales only what a viewer, readout or profile reads, with the fill
values as NaN, so even every spectral window of a large observation opens in little memory; a
``.fits.gz`` file is decompressed into memory, at two bytes a sample. A slit-jaw or AIA file is
still read in full as it opens, briefly taking about one and a half times its size. The first image
of a window takes its colour limits from a count of every stored value (of evenly spaced raster
steps or frames of a window over 512 MiB), which takes up to about half a second, and the "99.5%"
and other presets of the layer's style editor use the same count; "Per-frame limits" (see
:ref:`Viewer tools and windows <glue_solar_users_guide_viewer_tools_and_windows>`) count every value of the
displayed slice. ``<label> DN/s`` and other derived
attributes take theirs from 10,000 random samples, as glue does for data in memory, so they are
approximate. Memory still grows as you view a window, since the parts of the file read are kept, and
a Profile or Histogram of a whole cube, a
value-range subset, "Slice Extraction" and an export each read every value, as they did before.
Datasets merged with glue's "Merge datasets" take glue's own colour limits, sampled from a few
corners of the data, so set those by hand.

Each loaded file stays open, once for each time windows are loaded from it (the observation browser
loads the windows ticked in an observation at once), so glue-solar raises the number of files glue
may have open to 10240, or the system's hard limit if lower. A file must not be overwritten, cut
short or have its drive disconnected while it is loaded, which can crash glue; the observation
browser's archive extraction never overwrites a file.

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

.. _glue_solar_users_guide_iris_linking:

Linking
-------

The observation browser links the ``Helioprojective Longitude`` and ``Helioprojective Latitude``
of every slit-jaw image, raster and aligned AIA cutout it loads, so selections carry over between
them. It links any file loaded as a sunpy Map (see
:ref:`glue_solar_users_guide_loading_aia_and_hmi_files`) to them too, its degrees converted to
arcsec, while Glue's own WCS autolinking links maps to each other. For data opened with "File ->
Open Data Set", choose "IRIS: link helioprojective coordinates" from the "Plugins" menu; it only
adds links that are missing, so running it again after loading more data is safe. Removing a
dataset leaves the others linked. The links pair coordinates as they are: they do not allow for
the Sun's rotation between a map and the IRIS data, or for a map taken far from Earth. Once IRIS
data are linked, a selection on longitude or latitude values between two maps passes through them
too, so it ignores those differences between the maps; a region drawn on one map still reaches the
other through Glue's own link.

- A region drawn on a raster map or a sunpy Map selects, in every slit-jaw frame, the pixels that
  lie inside it at that frame's own pointing. For a sit-and-stare raster the selection marks where
  the slit was on the Sun during the selected exposures: it lies on the slit in the slit-jaw frames
  taken then, and moves away from it in other frames as the pointing changes.
- A region drawn on a raster map selects the pixels of a sunpy Map inside it, and the other way
  round.
- A selection on longitude or latitude, for example from a scatter plot, carries over in both
  directions. With a sunpy Map, one on longitude carries over only where Glue shows the map's
  longitude between -180° and 180°. Glue shows a map's longitudes as astropy gives them: from 0 to
  360° when the map's reference longitude is 0 or more, so that east of longitude 0 they are near
  360°, otherwise from -360° to 0.
- A region drawn on a slit-jaw image does not carry over to a raster or a sunpy Map: which frame it
  belongs to would need the time, and time is never linked. On a quicklook's slit-jaw image it does,
  as below.

A region drawn on the map of a quicklook (see :ref:`glue_solar_users_guide_iris_quicklook`) reaches
the other data by its outline in longitude and latitude, traced through the raster's own
coordinates with a corner at every raster step: on the raster it selects exactly the pixels inside
it, and elsewhere the pixels inside the outline, the same ones glue's own selection gives, but for a
few along the edge of a circle, whose outline is glue's 100-sided polygon of it. This
takes a fraction of a second per slit-jaw frame, for example 0.23 s for a full 1506 by 771 frame of
OBSID 4000005156's deconvolved SJI 2796 under a Si IV raster region, which glue takes 11 s over. It
reaches a sunpy Map whose longitudes run from 0 to 360° too. One drawn on a quicklook's slit-jaw
image reaches the raster and the other data by its outline too, placed at the pointing of the frame
shown as it was drawn: the raster pixels whose centres lie inside it in that frame, again but for a
few along the edge of a circle. This takes under 50 ms per raster panel, the longest for the 1600
exposures by 417 slit pixels of OBSID 4000255147's Si IV under a region on its SJI 1400.

A region drawn on a raster in any other Image Viewer is glue's own, and can be slow to show on a
slit-jaw image: glue works out the selection for every screen pixel of the slit-jaw viewer each
time it draws a frame, and does not respond meanwhile. At the default viewer size this takes under
a second with a 64-step raster, but 10 to 20 seconds with a 1600-step sit-and-stare raster, for
every frame you step to, and longer in a larger viewer. On a sunpy Map it takes about 4 seconds
with a 1600-step raster, each time the map's viewer draws.
