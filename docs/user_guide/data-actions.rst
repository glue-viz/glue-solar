.. _glue_solar_users_guide_data_actions:

============
Data actions
============

These actions are in a dataset's right-click menu in the data collection.

.. _glue_solar_users_guide_iris_regrid:

Regridding on time
------------------

Every axis of glue's viewers is an index axis, so a sit-and-stare raster's exposures, the frames of
a slit-jaw image, aligned AIA cutout or Hinode/SOT cube and a stack's scans show evenly spaced
whatever their timing: the cadence of OBSID 4000255147's Si IV varies from 2.71 to 3.29 s, and an
observation can have gaps. To see them in time, select one such dataset in the data collection and
choose "IRIS: regrid on time (sit-and-stare, stack, SJI, AIA, SOT)" from its right-click menu. This
adds ``<label> regridded``, resampled at the median step
between their times:
each pixel along that axis is one step after the previous one, from the first time up to the first
pixel at or past the last, and holds the exposure, frame or scan nearest its time within 0.75 steps
(the earlier of two as near), so one exposure can fill two pixels. A pixel with none, in a gap, is
NaN, with ``Time`` NaT, ``Exposure time`` NaN and the missing-data mask 1. The 1600 exposures of
4000255147's Si IV, 4750 s at a median step of 2.89 s, give 1645 pixels, none of them empty.

- A stack is regridded scan by scan, each scan timed by its middle raster step: its steps are
  places on the Sun, so each pixel keeps a whole scan, and the scan slider stays its time, as in
  the quicklook.
- A scanning raster is not offered it: its steps are places on the Sun, not times. Stack its scans
  in the observation browser and regrid the stack instead.
- The new dataset has the original's other axes, units, colormap, ``<label> DN / s`` and metadata,
  ``meta['time_step']`` adding the step in seconds, and its coordinates: along the regridded axis,
  those at each pixel's time, so that a slit-jaw image's time coordinate is regular, and those of
  the last time for a last pixel past it. Its helioprojective coordinates are linked with the other
  IRIS datasets (an AIA cutout's or SOT cube's only on request, as its original's), no viewer opens,
  and data read from their files as they are viewed (see
  :ref:`Memory and open files <glue_solar_users_guide_iris_memory_and_open_files>`) stay there.
- In an Image viewer, a regridded sit-and-stare raster's time axis is labeled "Time (2.89 s per
  pixel)", with the UTC range of its exposures on a second line, and its ticks are pixel numbers. It
  follows and leads the time sync as its original does (see :ref:`Quicklook <glue_solar_users_guide_iris_quicklook>`): a pixel in a gap has
  no time, so its "Frame time" readout is empty, the other datasets keep their frames and show "NO
  MATCH", and a slit-jaw time master never moves it into a gap. "Quicklook…" shows the
  original; for a quicklook of the regridded raster, type
  ``from glue_solar.quicklook import quicklook`` in glue's terminal, then
  ``quicklook(application, [dc["<raster label> regridded"], dc["<slit-jaw label>"]])`` with the
  labels the data collection shows. ``glue_solar.regrid.regrid_on_time(data)`` regrids a dataset
  there too.

.. _glue_solar_users_guide_iris_rebinning:

Rebinning
---------

To trade resolution for signal, select a raster window, stack, slit-jaw image or AIA cutout in the
data collection and choose "IRIS: rebin…" from its right-click menu. Type the pixels in a bin along each
axis, named as glue names its coordinates: 2 by 2 pixels of the map or image at first, raster steps
or exposures and slit pixels, or y and x, and 1 along wavelength, frames and scans. This adds
``<label> rebinned <bins>``, such as ``… rebinned 2x2x1``, while glue's status bar says "Rebinning
<label>…". Each pixel is the mean of the values in its bin, by ndcube's ``NDCube.rebin``, missing
samples left out, and NaN where every one is missing; pixels past the last whole bin along an axis
are left out. Its coordinates are at each bin's center, its ``Time`` is the mean of the bin's times,
and its ``Exposure time`` the mean of the bin's exposure times, NaN where one is 0 s, over which
``<label> DN / s`` is its mean DN. It has the original's units, colormap, pointing offset and
metadata, ``meta['rebinned']`` adding the bins, but not a slit-jaw image's per-frame pointing, so a
quicklook draws no slit on it and its "Frame time" tooltip gives none; a dataset regridded on time
has its ``meta['time_step']``, the seconds per pixel of its axis label, multiplied by the bin along
time. Its helioprojective coordinates are linked with the other IRIS datasets (an AIA cutout's or
SOT cube's only on request, as its original's), it follows and leads the time sync as its original
does, and no viewer opens. Its values are held in memory, in float32, and read from the original a
slab at a time, a stack's a bin of scans at a time: a 2 by 2 rebin of 3610108077's full Si IV 1403
window, 320 steps by 548 slit pixels by 337 wavelengths, takes 0.3 to 0.5 s.

- A rebinned raster window's line moments are those of each bin's mean: a bin with a saturated
  sample is +Inf, saturated, and error maps are refused, as irispy would give each bin the noise of
  one sample.
- A bin with missing samples counts as much as a full one, so the rebinned data's mean can differ
  from the original's: by 0.2 % on 3610108077's Si IV 1403, whose 1 % of bins partly missing lie at
  the edges of the missing data. Weighted by their samples, the bins' means give the original's.
- ``glue_solar.regrid.rebin(data, bins)`` rebins a dataset in glue's terminal too, ``bins`` one
  whole number per axis, in numpy's order.

.. _glue_solar_users_guide_iris_pointing:

Shifting the pointing
---------------------

IRIS pointing can be off by an arcsecond or two between a slit-jaw image and its raster, or against
AIA. To correct it, select the dataset in the data collection and choose "IRIS: shift pointing…" from
its right-click menu. Type Δx and Δy in arcsec, which are added to its helioprojective longitude and
latitude, a shift in the plane of the sky; the dialog shows the current offset, and 0, 0 takes it
away. A raster window shifts with the other windows of its raster file, which share its slit. The
mouse-over readout, the Point window, the links to the other data and every viewer follow at once:
a map shown over the image moves across it, and on a quicklook's slit-jaw image the raster point's
red cross and the raster overlays move, while a click there reaches the raster pixel at its new
position. On OBSID 4000005156's deconvolved SJI 2796, (+2, −1) turns the readout at one pixel from
``67.10" 65.43"`` to ``69.10" 64.43"``, and a click there that reached the Mg II k raster's step
10, slit 300 reaches step 11, slit 294.

- Only IRIS data can be shifted: a sunpy Map is not offered it, so shift the IRIS data against it
  instead.
- Data made from it, by "IRIS: regrid on time", "IRIS: rebin…", "IRIS: remove dust (SJI)", line
  moments, red-blue asymmetry, Doppler images, Mg II features or UV bursts, take its offset and
  follow every later shift of it, as do data made from those in turn, such as a rebinned window's
  line moments, and a burst events table's ``coordinate.Tx`` and ``coordinate.Ty``; a saved
  session keeps them following. Chosen on data made from another dataset, "IRIS: shift pointing…"
  shifts the furthest dataset they were made from still in the data collection, which the dialog
  names, so its raster file's windows and everything made from them move together: on OBSID
  4000255147, a (+3, −2) shift chosen on the line moments of a 2×2×1 rebinned copy of the Si IV
  1403 window moves that window, the file's eight other windows, the copy and the moments by
  exactly +3″ and −2″. Once removed, a dataset moves the data made from it no more; they keep
  their offset, and once none of the datasets they were made from is left, they shift on their
  own, with the data made from them. A line ratio shares its numerator's coordinates and shifts
  with it; a north-up grid stays where it was made, and the slit-jaw image moves across it.
- A region drawn on a quicklook's map or slit-jaw image keeps the outline it had in longitude and
  latitude, so draw it again after shifting the dataset it was drawn on.
- The "Frame time" tooltip keeps the file's pointing. A saved session keeps the offset (see :ref:`glue_solar_users_guide_saving_sessions`).

To co-align a slit-jaw image with its raster, click a small, distinct feature on the raster map: the
red cross marks where the raster places it on the slit-jaw image. Read the feature's position in
both with the mouse-over readout, and shift the slit-jaw image by the raster's position less its
own. Against AIA, show the AIA cutout or map in a viewer beside it, or drag the map onto the
slit-jaw viewer and lower its opacity in its layer options or blink the two ("Set blink partner
here" and "Blink" in the "Coordinate" menu's "Blink" submenu), and read the feature's position in
each the same way. A "Measure" line from the feature in one to the feature in the other then
checks the shift: it should be under a pixel long.

North up
--------

A slit-jaw image or aligned AIA cutout of a rolled observation shows solar north at the roll angle:
45.6° from the top for OBSID 3860608353, whose ``SAT_ROT`` is 45. To see one north up, select it in
the data collection and choose "IRIS: north up (SJI, AIA, SOT)" from its right-click menu, which
offers it for a slit-jaw image, an aligned AIA cutout or a Hinode/SOT cube. This adds ``<label> north
up``, a grid with no values of its own (its ``empty`` component is NaN): square pixels as wide as
the image's (``CDELT1``) on a gnomonic projection, helioprojective latitude up and longitude along
x, covering every frame where its pointing places it, with the image's frames and ``Time``. An
Image viewer of the grid opens showing the image, which glue resamples onto it as it draws, through
its links, as it shows any dataset on another's axes: each screen pixel takes the nearest sample of
the frame shown, placed with that frame's own pointing, and no copy is made. The grid's own layer is
hidden.

- The slider steps through the image's frames, as D, F and Space do, and "Frame time" gives each
  frame's time, without its exposure. The grid is fixed on the sky, so the image moves across it as
  IRIS follows the solar rotation: 12″ west over the 65 frames of 3860608353's SJI 2832, whose grid
  is 570 by 533 pixels for its 364 by 387.
- A frame step costs about twice a native one, as glue places the frame through its coordinates
  at each step: 0.13 s against 0.06 s for that SJI 2832 in a viewer 800 pixels square.
- The grid's helioprojective coordinates are linked with the other IRIS datasets (see
  :ref:`Linking <glue_solar_users_guide_iris_linking>`), and so are an AIA cutout's or SOT cube's,
  which glue shows on the grid through them, as "IRIS: link helioprojective coordinates" links them;
  its time and frames are linked with the image's only, which glue needs to place each frame.
- The grid belongs to no observation, so time sync, the point and the raster overlays leave its
  viewer alone. "Per-frame limits" and "Color bar", which take the viewer's reference data, act on
  the hidden grid rather than the image, and "Cursor readout" gives no value: set the image's
  limits in its layer's style editor.
- In glue's terminal, ``glue_solar.regrid.north_up_iris(data, dc)`` does the same, and
  ``glue_solar.regrid.north_up(data)`` gives the grid alone.
