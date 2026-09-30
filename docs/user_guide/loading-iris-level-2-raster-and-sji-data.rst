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

Open it from the "Plugins" menu with "IRIS: browse observations...". Subfolders are searched by
default; un-tick "Search subfolders" to look at one folder only. The last folder used is remembered.

Expand an observation to see what can be loaded:

- one entry per slit-jaw band (``SJI_1330``, ``SJI_1400``, ``SJI_2796``, ``SJI_2832``), and a
  separate one for each deconvolved slit-jaw file (``SJI_2796 (deconvolved)``),
- one entry per raster spectral window (for example ``Mg II k 2796 - 8 raster file(s)``): every
  raster scan of the observation is loaded for that window,
- one entry per co-aligned SDO/AIA cutout when an ``_SDO`` folder is present.

Tick the entries you want (ticking the observation row ticks everything under it) and press
"Load selected". The data are added to the data collection and the first slit-jaw (or AIA) cube is
opened in an Image Viewer; use its slider to step through time.
Tick "Stack sequential raster scans" to place two or more raster scans of a window into a single
4D cube without resampling their detector values. Its leading ``Scan`` coordinate selects the
original raster scan, and its ``Time`` component contains the exact acquisition time of every
pixel. Scan 0 supplies the stack's nominal helioprojective WCS; later scans remain aligned by
raster and detector index rather than carrying their distinct absolute pointings. Load scans
separately when those per-scan absolute coordinates are required. A selected window containing one
scan loads normally as a 3D dataset and also exposes its exact per-step ``Time`` values.

Every raster, stack and slit-jaw dataset also has an ``Exposure time`` component in seconds, one
value per raster step or slit-jaw frame (per scan for stacks). The "Frame time" tool in the Image
Viewer toolbar shows the displayed frame's time and exposure in the status bar, as a range when the
image spans several frames; for a single slit-jaw frame its tooltip gives that frame's pointing (PZT
offset, field-of-view centre and slit position), which glue-solar keeps in the dataset's metadata.

Dragging a slice slider updates the image at most every 0.1 s and again when you let go, so large
cubes keep up with the mouse; the arrow keys, clicks on the slider and playback still step at once.

The point you select with the Pixel tool on a raster or stack is one slit position at one raster
step or exposure; on a stack it stays on the scan that was displayed when you clicked. If you then
swap the axes of a viewer of that dataset, for example turning the raster map into wavelength
against slit, the viewer's new step slider moves to the point. Wavelength sliders are never moved.
The "Coordinate" menu in the Image Viewer toolbar has "Clear point", and "Time master", which
records the displayed dataset as the time reference of its observation (same OBSID and STARTOBS).
The Pixel tool stays active after either entry.

Downloads that are still packed (``*_raster.tar.gz``, ``*_SDO.tar.gz``) show up under their observation
as an "Extract ..." entry. Tick it and press "Load selected": the archive is unpacked into a folder of
the same name next to it (the layout irispy and pooch use), the list refreshes, and you can then tick
the spectral windows or cutouts it contained. Extraction is completed in a temporary sibling
directory, so a failure leaves the archive visible for retry. Nothing is loaded in that step, and
the archive is left in place.

Opening a single file
---------------------

"File -> Open Data Set" also understands IRIS Level 2 files directly: a slit-jaw file loads as one
cube, and a raster file loads one dataset per spectral window.

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

Saving sessions
---------------

Glue sessions containing these IRIS datasets cannot currently be restored reliably. The irispy
metadata and WCS objects, including SJI gWCS and raster lookup tables, need dedicated serializers;
save derived products separately rather than relying on a Glue session as their only copy.
