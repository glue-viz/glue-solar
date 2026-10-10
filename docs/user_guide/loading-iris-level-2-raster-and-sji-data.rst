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
To search another folder, type it in "Folder" and press Return (or leave the field), or pick one with
"Change…"; a folder that does not exist is not searched, and the progress bar says so. The browser
opens with its tick boxes, "Search subfolders", "Stack sequential raster scans" and "Open quicklook",
as you last left them.
glue reads the folder's headers in the background, and the progress bar counts the files; meanwhile
"Cancel" reads "Stop". "Stop" ends the search once the file being read is done and lists what it
found so far, so observations may be missing or show only some of their files, which the progress
bar says; pressing Esc or closing the browser drops the search. A raster file that is not Level 2
(its ``DATA_LEV`` is not 2), such as a product derived from rasters, is left out, and the progress
bar says how many were, for example "Skipped 1 raster file(s) that are not Level 2".

Expand an observation to see what can be loaded:

- one entry per slit-jaw band (``SJI_1330``, ``SJI_1400``, ``SJI_2796``, ``SJI_2832``), and a
  separate one for each deconvolved slit-jaw file (``SJI_2796 (deconvolved)``),
- one entry per raster spectral window (for example ``Mg II k 2796 — 8 raster file(s)``): every
  raster scan of the observation is loaded for that window, and its tooltip gives the window's detector and
  wavelength range (``NUV, 2790.5–2806.6 Å``),
- one entry per co-aligned SDO/AIA cutout (``aia_l2_*.fits``), for example ``AIA 1700``. Cutouts
  are recognised by file name and header, so they need no ``_SDO`` directory.
- one entry per co-aligned Hinode/SOT cube (``sot_l2_*.fits`` and ``sotsp_l2_*.fits``, from the
  ``_SOTFG`` and ``_SOTSP`` archives; `IRIS Technical Note 32 <https://iris.lmsal.com/itn32/>`__),
  recognised by file name and header too, for example ``SOT G band 4305``, ``SOT TF Na I 5896`` or
  ``SOT 6302A B_LOS``. SP maps, all ``6302A``, are named by what they measure (``BTYPE``), and a
  second file of the same name has its file name added, as ``irispy.io.read_files`` keys them; each
  map's dataset is labelled with its file's time too (``6302A B_LOS 08:06:09-3603259402-…``).

An observation with only one entry shows it in its "Files" column (for example ``1 — AIA 1700``)
and has its tick box on its own row.

Type in "Filter" to list only the observations whose row or entries contain the text, in any case:
a line such as ``mg ii`` or ``Si IV 1403``, a start date as STARTOBS shows it (``2013-09-02``), or
an OBSID. An observation it lists shows all its entries, and the filter stays as the folder is
searched again. Ticks stay as the filter changes, and "Load selected" loads every tick, listed or
not.

Type a UTC time in "Start" or "End", such as ``2013-09-02T16:00``, ``2013-09-02`` or ``2013-09``,
and press Return to search the folder again for the observations that run at some time between
them; leave one empty for no limit. An "End" that names no second runs to the end of the minute,
hour, day, month or year it names, so a "Start" and "End" of ``2013-09-02`` list every observation
running that day. Only the headers of the files whose names are stamped from a day before "Start"
to "End", or hold no time, are read, so an observation that began more than a day before "Start"
is not listed. "Recent" lists the last 10 searches, each a folder with its "Start" and "End": pick
one to search it again. "Add current folder…" saves the folder under a name you give, which
"Saved" lists: pick it to search that folder, or press "Remove" to forget the one shown. The
browser keeps them for next time, and opens with the latest search's "Start" and "End".

Tick the entries you want (ticking the observation row ticks everything under it); each slit-jaw
channel, AIA cutout and SOT cube you tick loads as a dataset of its own. Then press "Load
selected", or Return anywhere but in a text field: the data are added to the data collection.
Double-click an entry to load it alone, whatever is ticked (a double-click on its tick box only
ticks and un-ticks it); a double-click on an observation of several entries expands or collapses it
instead. glue reads the files in the background, one at a time, and
the progress bar counts them; meanwhile the list and its boxes are locked and "Cancel" reads "Stop".
"Stop" ends the load once the file being read is done and loads the entries read in full, such as a
slit-jaw channel read before a raster window, or nothing if none was. Pressing Esc or closing the
browser drops the load: nothing is loaded. With "Open quicklook" ticked, the default, each
observation with a raster or slit-jaw image opens in a quicklook of the raster windows ticked,
with the map, spectrogram and wavelength panels of the one chosen in "Main window" where it is
ticked (see :ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`). "Main window" lists the
ticked raster windows and shows Mg II k 2796 when ticked, else the first, until you choose one.
Otherwise the first slit-jaw (or AIA) cube opens in an Image Viewer, where its ``Time (Utc)`` slider
steps through time; nothing opens for rasters alone. If an entry fails to load, the browser stays open and its progress bar names
the file and the error; for a raster window, the first raster file that fails to load on its own, or
how many raster files there are if each loads on its own but not together.
Tick "Stack sequential raster scans" to place two or more raster scans of a window into a single
4D cube without resampling their detector values. Each scan stays in its own file, as a single scan
does (see `Memory and open files`_); scans stored as floating point, such as irispy's test files,
are copied into a temporary file (a NumPy memmap) instead. Its leading ``Scan`` coordinate
selects the original raster scan, and its ``Time`` component contains the exact acquisition time of
every pixel. Each scan keeps its own coordinates, so a pixel's helioprojective longitude and
latitude are those its scan gives it, and placing a stack on other data takes a scan as well: the
links (see `Linking`_) place it on each slit-jaw image, AIA cutout and raster, not on another stack,
with the scan nearest the time of each frame, exposure or step, each scan timed by its middle raster
step, however far; a frame without a time, such as a gap of data regridded on time, gets none. A
selected window containing one scan loads normally as a 3D dataset and also exposes its exact
per-step ``Time`` values.

Every raster, stack, slit-jaw and AIA dataset has these components: the data (named after the
dataset), ``Time`` and ``Exposure time`` (a stack lists ``Exposure time`` before ``Time``),
``<label> mask``, which Glue computes from the data as it reads them and so lists under "Derived
components" (files stored as floating point keep it in memory, listed second), and ``<label> DN/s``,
also derived. ``Time`` is the UTC acquisition time as a datetime64, one value per raster step,
slit-jaw, AIA or SOT frame (per scan and step for stacks). ``Exposure time`` is in seconds, one
value per raster step or frame (per scan and step for stacks). ``<label> DN/s`` is the data divided
by the exposure time, with the unit DN/s (the 1D Profile viewer's "y_unit" menu labels its axis
with it), and NaN where an exposure took 0 s, as step 157 of OBSID 3610108077's Si IV windows did.
The "Frame time" tool, in the Image Viewer toolbar's View menu, shows the displayed frame's time
and exposure in the status bar, as a range when the image spans several frames; for a single
slit-jaw frame its tooltip gives that frame's pointing (PZT offset, field-of-view centre and slit
position), which glue-solar keeps in the dataset's metadata. The mouse-over readout (see "Cursor readout" in
:ref:`Viewer tools and windows <glue_solar_users_guide_viewer_tools_and_windows>`)
gives the time and exposure of the pixel under the mouse: on a raster map those of the step it is
on.

Slit-jaw, raster and AIA values are floating point. The IRIS fill values -200 and -199 become NaN,
in AIA cutouts too. Level 2 files, stored as 16-bit integers, cannot hold +Inf, the ITN 26
saturation code, so they clip saturated samples to 16182 DN; glue-solar reads the samples of
raster windows and slit-jaw images at that ceiling as +Inf again, as irispy does, but not those of
AIA cutouts, and leaves +Inf outside the mask (see `Was it saturated?`_). An Image viewer draws
+Inf in its colormap's top colour, as it draws values above its upper colour limit, and leaves it
out of its colour limits; the cursor readout shows ``inf``; and a Profile leaves it out: a gap in
a pixel's spectrum. ``<label> mask`` is a uint8 array that is 1 where the data are NaN and 0
elsewhere.

Hinode/SOT cubes load as AIA cutouts do, each frame with its own time and pointing, in the unit
irispy reads from their ``BUNIT``: DN for filtergrams and the SP continuum, dimensionless for
narrowband magnetograms (Stokes V/I × 4096), and G, km/s, degrees or dimensionless for the other SP
maps, which have no ``<label> DN/s``. Their values are float32, NaN where missing, and no other
value is fill, as negative fields are data. The quicklook gives them no panel; an Image viewer of
one follows its observation's time and can be its master, as one of an AIA cutout does (see
:ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`).

Slit-jaw images open in sunpy's IRIS colormap of their channel, raster windows and stacks in its
FUV or NUV colormap by their detector (``TDETn``), AIA cutouts in sunpy's AIA colormap of their
wavelength, and SOT cubes in DN in sunpy's Hinode SOT intensity colormap, other SOT cubes in gray.
The colormap menu of an Image Viewer layer lists Glue's own colormaps and every sunpy
colormap, under sunpy's names for them, such as ``SDO AIA 171.0 Angstrom``, and shows the layer's
own colormap even where another has the same colours (the FUV and NUV ones have those of 1330 and
2796, AIA 171 those of SUVI 171). To list another, add it with ``colormaps.add`` in a
``config.py``, as
`Glue's customization guide <https://docs.glueviz.org/en/stable/customizing_guide/customization.html>`__
describes.

Rasters with a negative raster step (``STEPS_AV`` below -0.01) keep irispy's default orientation:
irispy reverses their raster-step axis, with the data, coordinates, times and per-step metadata
together, so the step axis runs opposite to the acquisition order and ``Time`` runs backwards
along it. The documented alternative is irispy's ``revert_v34=True`` option
(``irispy.io.spectrograph.read_spectrograph_lvl2``, also passed on by ``irispy.io.read_files``),
which keeps the file order; glue-solar does not use it.

A raster that takes several exposures at each of its positions (``NEXP_PRP`` and ``NRASTERP`` above 1) has each
position on as many raster steps. A place on the Sun, such as a click on a quicklook's slit-jaw image, then lands on
one of the exposures at its position, so glue-solar warns once per observation as such a raster loads: glue's "Error
Console" button turns red and shows the warning. A sit-and-stare raster, which takes every exposure at its one
position (``NRASTERP`` 1), steps through time instead and gives no warning.

Dragging a slice slider shows its latest position each time the image has been redrawn, skipping
the positions passed in between, and again when you let go, so large cubes keep up with the mouse;
the arrow keys, clicks on the slider and playback still step at once.

The point you select with the Pixel tool on a raster or stack is one slit position at one raster
step or exposure; on a stack it stays on the scan that was displayed when you clicked. If you then
swap the axes of a viewer of that dataset, for example turning the raster map into wavelength
against slit, the viewer's new step slider moves to the point. Wavelength sliders are never moved.
The "Coordinate" menu (the link icon) in the Image Viewer toolbar has "Time master", which records
the displayed dataset as the time reference of its observation (same OBSID and STARTOBS), "Go to
UTC…", which moves the time master, "Loop…" for the frame, exposure, step or scan slider, and
"Raster overlays", which shows or hides the raster's steps on every viewer of the observation. Its
"Point" submenu has "Clear point", "Light curve of this window", which opens the point's light curve
over the map's wavelength or band, "Light curves of every window and SJI…", which plots each
raster window and slit-jaw image at the point against time, and "Row at the point" and "Column at
the point", which open the map's row and column through the point; its "Blink" submenu has "Set blink
partner here", "Blink" and "Blink interval", which alternate the viewer between two positions at the
interval chosen (see :ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`). The menu shows
only the entries that can act on the viewer's data (see :ref:`Viewer tools and windows
<glue_solar_users_guide_viewer_tools_and_windows>`), and the Pixel tool stays active after each
entry.

Downloads that are still packed (``*_raster.tar.gz``, ``*_SDO.tar.gz``, ``*_SOTFG.tar.gz``,
``*_SOTSP.tar.gz``) show up under their observation as an "Extract <archive> (<size> MB, next to
the archive)" entry. Tick it and press "Load selected":
the archive is unpacked into a folder of the same name next to it (the layout irispy and pooch use),
the list refreshes, and you can then tick the spectral windows, cutouts or SOT cubes it contained.
Archives are unpacked in the background too: "Stop" leaves those not yet started packed. Extraction
is completed in a hidden temporary sibling directory, which the list leaves out, so a failure leaves the
archive visible for retry.
Nothing is loaded in that step, and the archive is left in place.

.. _glue_solar_users_guide_iris_memory_and_open_files:

Memory and open files
---------------------

Level 2 files store their data as 16-bit integers with a scale and an offset. glue-solar leaves
those integers in the file and scales only what a viewer, readout or profile reads, with the fill
values as NaN, so even every spectral window of a large observation opens in little memory; a
``.fits.gz`` file is decompressed into memory once, at two bytes a sample, briefly twice that as it
opens. The first image
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

On OBSID 4000005156's first raster file (64 steps, nine windows, 119 million values in 0.24 GB) and
its deconvolved SJI 2796 (37 million values), opened with "File → Open Data Set", glue grows from
0.38 to 0.84 GB as they load and the quicklook of Mg II k 2796 opens, and to 1.01 GB once the map
has been stepped through every wavelength, the spectrogram through every step, the λ–step panel
through every slit row and the slit-jaw image through every frame: about 4 bytes a value. Of that,
only 55 MB are the raster file's pages, the Mg II k 2796 window read for its colour limits as the
quicklook opens. The memory the system reports for glue ("resident" memory) counts such pages;
most of the rest that Activity Monitor's "Memory" column leaves out (it reads 0.56 GB) is the code
of glue's libraries and memory glue has freed but the system has not yet taken back, which it
reclaims, like the file's pages, when memory runs short. With astropy 8.0, whose WCSLIB 8.6 never
frees the error message of a point it cannot convert, each new slit row shown on the λ–step panel
(its slider, or a click on the map) adds about 0.1 MB, as WCSAxes places that panel's tick marks
past the raster's first and last steps; astropy's development version, with WCSLIB 8.9, frees them.

A sit-and-stare raster loads every exposure this way. On OBSID 4000255147 (1600 exposures, a 2.1 GB
file) and 3660259102 (1020 exposures, 1.5 GB), every window opened with "File → Open Data Set"
opens in about 0.6 s with under 0.1 GB more memory, and the quicklook of Mg II k 2796, stepped with
F through every exposure and then through every slit row of its wavelength panel, keeps glue under
1.8 GB, each step redrawing the images in 0.06 to 0.12 s and the spectrum in 0.18 s. Every window
and the slit-jaw image ticked in the observation browser, with "Open quicklook", take about 4 s, as
the colour limits of each are counted first, and peak at about 3 GB on 4000255147, most of it the
file's pages read for those counts.

Each loaded file stays open, once for each time windows are loaded from it (the observation browser
loads the windows ticked in an observation at once), so glue-solar raises the number of files glue
may have open to 10240, or the system's hard limit if lower. A file must not be overwritten, cut
short or have its drive disconnected while it is loaded, which can crash glue; the observation
browser's archive extraction never overwrites a file.

Opening a single file
---------------------

"File → Open Data Set" also understands IRIS Level 2 files directly, as the file type "IRIS Level 2
FITS", which its default type, "Auto", chooses for them: a slit-jaw file, an aligned AIA cutout
(``aia_l2_*.fits``) or a Hinode/SOT cube (``sot_l2_*.fits``, ``sotsp_l2_*.fits``) loads as one cube,
as the observation browser loads it, and a raster file loads one dataset per spectral window,
labelled with the file's raster number (``…-r00003``). Other AIA and HMI files need "sunpy Map"
picked instead (see :ref:`glue_solar_users_guide_loading_aia_and_hmi_files`).
Files opened this way, or given on the ``glue`` command line, load one by one with every spectral
window and cannot be stacked, so use the observation browser for large or multi-scan observations.

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

.. _glue_solar_users_guide_iris_saturation:

Was it saturated?
-----------------

Level 2 files flag no saturated sample: the Level 2 pipeline clips every sample to -199 to 16182
DN, so a sample saturated in Level 1, at or above 16000 DN, is stored as 16182 DN, and so is any
other sample calibrated past it. glue-solar, as irispy, reads the samples of raster windows and
slit-jaw images at that ceiling as +Inf. ``NSATPIX`` and ``TSATPXn`` are 0 in every Level 2 file;
ignore them.

- The header's ``HISTORY`` line from iris_prep, ``Set N saturated pixels to Inf``, says the
  observation saturated somewhere. "View metadata/header" (Ctrl+I) in the data collection's
  right-click menu lists only the last ``HISTORY`` line, so type
  ``[line for line in raster.meta.fits_header["HISTORY"] if "saturated" in line]`` in glue's
  terminal, with ``raster`` a scan's dataset, such as ``data_collection[0]`` (a stack's ``meta``
  keeps no header). N counts a batch of up to 100 Level 1 files, often the whole observation, and
  the line is left out when the first batch had none, so its absence says nothing.
- A subset shows the +Inf samples: select the dataset in the data collection, choose "Add/edit
  arithmetic attributes" in the "Data Manager" menu and add an attribute named ``saturated``,
  ``np.isinf({<label>}) * 1``, with the data's own attribute, named after the dataset, inserted
  from the list (glue's faceted subsets take neither infinite limits nor a true-or-false
  attribute); then choose "Create faceted subsets", pick ``saturated``, and set the range from 1 to
  1 and the number of subsets to 1. Every Image viewer of the dataset draws the subset,
  ``1.0<=saturated<=1.0``: a spectrogram at the line core of the slit positions that saturated, a
  map at the wavelength shown (A and S step through them). As with the mask, select ``Point``
  before moving a quicklook's point again. In glue's terminal::

      from irispy.utils.constants import SATURATION_LIMIT

      cid = raster.main_components[0]
      data_collection.new_subset_group("saturated", raster.id[cid] >= SATURATION_LIMIT.value)

A sample at the ceiling is saturated or merely bright, as Level 2 cannot tell them apart, although
in two saturated flares checked against their Level 1 frames 99.88 % of them lay within a pixel of
a saturated sample. :ref:`Line moments <glue_solar_users_guide_iris_line_moments>` are NaN where a
sample within the velocity range is +Inf, a background subtracted or not,
:ref:`Mg II features <glue_solar_users_guide_iris_mg_features>` where one within the velocities
searched for their line is, :ref:`red-blue asymmetry <glue_solar_users_guide_iris_red_blue>` where
one taken is, and :ref:`Doppler images <glue_solar_users_guide_iris_doppler>` where one
interpolated is. On OBSID 3860258481's raster r00173, of the X1 flare of 2014-03-29, whose header
has no such ``HISTORY`` line, the Si IV 1403 subset holds 13,760 samples: plateaus about the line
core at 1402.8 Å in 428 pixels, 28 to 82 at each raster step, a few across most of the window.

.. _glue_solar_users_guide_iris_linking:

Linking
-------

The observation browser links the ``Helioprojective Longitude`` and ``Helioprojective Latitude``
of every slit-jaw image, raster, aligned AIA cutout and SOT cube it loads, so selections carry
over between them, and a quicklook and the analyses link the IRIS data they open or make. Data from
outside the IRIS observations, such as a file loaded as a sunpy Map (see
:ref:`glue_solar_users_guide_loading_aia_and_hmi_files`), an SST cube or any other FITS file, are
linked to IRIS data only on request: choose "IRIS: link helioprojective coordinates" from the
"Plugins" menu, which links every loaded dataset with helioprojective coordinates, a map's degrees
converted to arcsec, as well as IRIS data opened with "File → Open Data Set". Glue's own WCS
autolinking links maps to each other. Once a map is linked, every quicklook panel and spectrum works
through its coordinates too. A linked SST cube's viewer shows the IRIS data's regions and crosshair,
and a region drawn on the cube selects the IRIS pixels at its place in the cube's scan nearest each
frame's time (see :ref:`glue_solar_users_guide_loading_sst_cubes`). Every quicklook panel and spectrum
then works through the cube's coordinates as well: beside a linked SST cube, a quicklook of the nine
windows of 4000255147 took about 9 s to open rather than 6 s (14 s where a region on a co-pointed cube
selected IRIS pixels), an exposure step about 0.63 s rather than 0.55 s, and a slit-jaw frame step
0.1 s rather than 0.03 s. The menu entry only adds
links that are missing, so running it again after loading more data is safe. Removing a dataset
leaves the others linked, those linked on request included. A reopened session restores those links,
but choose the menu entry again after reopening it: until then, removing a dataset drops a map's
links, and a map's viewer and Glue's spectrum threads can reach its coordinates at once, which can
crash Glue. The links pair coordinates as they are:
they do not allow for the Sun's rotation between a map and the IRIS data, or for a map taken far
from Earth; an IRIS dataset's own pointing can be corrected with "IRIS: shift pointing…" (see
:ref:`glue_solar_users_guide_iris_pointing`). Once IRIS data are linked, a selection on longitude
or latitude values between two maps passes through them too, so it ignores those differences
between the maps; a region drawn on one map still reaches the other through Glue's own link.

- A region drawn on a raster map or a sunpy Map selects, in every slit-jaw frame, the pixels that
  lie inside it at that frame's own pointing. For a sit-and-stare raster the selection marks where
  the slit was on the Sun during the selected exposures: it lies on the slit in the slit-jaw frames
  taken then, and moves away from it in other frames as the pointing changes. On a stack's map, its
  steps and slit rows lie where the scan nearest the frame's time places them, at that scan's own
  pointing.
- A region drawn on a raster map selects the pixels of a sunpy Map inside it, and the other way
  round.
- A selection on longitude or latitude, for example from a scatter plot, carries over in both
  directions. With a sunpy Map, one on longitude carries over only where Glue shows the map's
  longitude between -180° and 180°. Glue shows a map's longitudes as astropy gives them: from 0 to
  360° when the map's reference longitude is 0 or more, so that east of longitude 0 they are near
  360°, otherwise from -360° to 0.
- A region drawn on a slit-jaw image does not carry over to a raster or a sunpy Map: which frame it
  belongs to would need the time, and nothing links to a slit-jaw image's time. On a quicklook's
  slit-jaw image it does, as below.

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
few along the edge of a circle. On a sit-and-stare raster these are the exposures whose slit lay
inside it at that frame's pointing: as the pointing changes, the slit moves out of it in exposures
taken long before or after, although it stays on the same slit-jaw pixels. A box 47 pixels wide
around the slit on frame 200 of OBSID 4000255147's SJI 1400 selects 952 of its 1600 exposures. This
takes under 50 ms per raster panel, the longest for the 1600 exposures by 417 slit pixels of OBSID
4000255147's Si IV under a region on its SJI 1400, and under a second for its mean spectrum.

A region drawn on a raster in any other Image Viewer is glue's own, and can be slow to show on a
slit-jaw image: glue works out the selection for every screen pixel of the slit-jaw viewer each
time it draws a frame, and does not respond meanwhile. At the default viewer size this takes under
a second with a 64-step raster, but 10 to 20 seconds with a 1600-step sit-and-stare raster, for
every frame you step to, and longer in a larger viewer. On a sunpy Map it takes about 4 seconds
with a 1600-step raster, each time the map's viewer draws.
