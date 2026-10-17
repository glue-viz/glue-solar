.. _glue_solar_users_guide_saving:

======
Saving
======

.. _glue_solar_users_guide_saving_sessions:

Saving sessions
---------------

A session refers to the files of the IRIS data loaded with the observation browser, File → Open Data Set,
or ``raster_data`` and ``image_data`` in glue's terminal, and of SST cubes (see
:ref:`glue_solar_users_guide_loading_sst_cubes`), and reads them again as it opens, rather than holding
their values. Save it as "Glue Session with relative paths to data", the type glue's
Export Session dialog starts with, to move it and the files together: it opens wherever the files
keep their place relative to it. "Glue Session including data" holds the values instead, and fails
on data read from their files as they are viewed. A session keeps the coordinates of every IRIS
dataset and of those made from them, with any pointing offset set with "IRIS: shift pointing…", the
colormap each opens in, their metadata, and the helioprojective links of the observation browser
and "IRIS: link helioprojective coordinates", a stack's scans and sunpy maps included. Data read
from their files as they are viewed take their coordinates and metadata from the files again, so
the session holds little more than their offset; the others lose the time and field-of-view center
irispy gives each raster step (``auxiliary times`` and ``exposure FOV center``), which neither UV
bursts nor the radiometric calibration need. Each viewer opens again with its slices, a wavelength
band included, and its colormaps, and a Profile viewer, such as a quicklook's spectrum panel, with
its x axis, "x unit" (km / s too) and range. Each quicklook adds its viewers and the recipe it opens
again from (see :ref:`the IRIS quicklook <glue_solar_users_guide_iris_quicklook>`): one of
4000255147's Si IV 1403 window and slit-jaw image, read as they are viewed, saves a 45 kB session
(199 kB with all nine windows shown) in under 0.1 s, and with a stack of the eight scans of
3400109360's Si IV 1403 window in a second quicklook, 105 kB, which opens in about 2.5 s and, saved
and opened again, gives the same quicklooks. A session reads each raster file once per copy of
the windows it holds of it (twice for an observation opened twice), as the observation browser
does: a quicklook of the seven windows of 3602506433's 99 scans, stacked, opens in about 7 s.
Datasets made from IRIS data, such as line moments or rebinned and north-up data, are saved with
their values, which can make a session large (36 MB with line moments of that Si IV 1403 window):
save derived products separately rather than relying on a Glue session as their only copy.

As glue quits with data loaded, glue-solar keeps the session as a "Glue Session with absolute paths
to data" in glue's settings folder (``~/.glue/glue-solar-last-session.glu``), and Plugins → "IRIS:
restore last session" opens it as File → Open Session does. Open Session, Reset Session and the
restore itself keep nothing, so restoring twice gives the same session. The 4000255147 quicklook
above is kept in about 0.03 s and restored from the menu in about 2 s; if its files have moved,
glue says which it cannot find. A session glue cannot save, or of over 1 MB, such as one with those
line moments, is not kept: the one kept before stays, and a message says why as glue quits ("Could
not keep this session for 'IRIS: restore last session'", "its data hold 26.7 MB of values, over 1
MB"), the values being counted before glue saves them.

Not saved yet:

- A quicklook's raster overlays and its panels' moves and resizes (see :ref:`the IRIS quicklook
  <glue_solar_users_guide_iris_quicklook>`), a blink and its partner, and each viewer's mouse mode:
  choose the Pixel tool again, which a quicklook's image panels take as their window becomes active.
- Data regridded on time from data read as they are viewed: a session holding them does not save
  ("Don't know how to serialize dask.array").
- "Per-frame limits", with glue-core 1.27.0: a session saved while an Image viewer has them on,
  whatever its data, does not open, and glue reports "'NoneType' object has no attribute
  'add_callback'". Turn them off before saving.

.. _glue_solar_users_guide_iris_save_frames:

Saving frames or a movie
------------------------

"IRIS: save frames or movie…", in an Image viewer's save menu, saves the image at each index of a slider, from a first to a
last, as "Save plot to file" would save it there: as PNG files named after the file chosen with
the index added (``sji.png`` gives ``sji_0000.png``, ``sji_0001.png``, …), or as a movie at 10
frames per second, an MP4 where ffmpeg is installed or else a GIF. A GIF is kept in memory until
it is written, about 1.4 MB a frame of 800 × 600 pixels, so save long sequences as an MP4 or as
PNG files. Of several sliders it asks which, offering first that of the data's first axis (a
slit-jaw image's frames, a sit-and-stare raster's exposures, a scanning raster's steps or a
stack's scans), then for the first and last index, or ±N around the current one, as "Loop…" does,
starting from the slider's loop or else its whole range, and saves every index between them.
Playback of the slider, or of the time master, stops; the slider moves as when it plays, so the
other viewers follow, and the slit, the point and the raster overlays are drawn as they then show.
glue stays usable while it saves: a frame is saved at each turn of glue's event loop, ffmpeg
encodes an MP4 as they come, and a GIF is encoded in the background once they are all saved,
while the status bar says ``Saving sji.gif…``. The viewer, its options and its layers are grayed,
and its window can be neither moved nor resized by dragging, until the last frame is saved; the
other viewers and tabs stay usable, and what they change in the viewer,
such as the point or the time master's time, shows in the frames saved after. One viewer saves
at a time.
Every frame has the same color limits:
with "Per-frame limits" on, the whole cube's. Ticking "UTC time on each frame", under the indices,
draws each frame's time at the lower left of the plot, in white edged in black, the "Frame time"
readout's time, to 0.01 s (``2013-09-02T16:39:39.66 UTC``): a raster step's or
exposure's, or the first and last of a frame showing several, such as a stack's scan. Ticking
"Frame numbers" draws the slider's index and its last index at the upper left (``frame 7/399``),
and "Scale bar" a white bar edged in black at the lower right, its length above it: the largest
of 1, 2, 5, 10, 20, 50, 100, 200, 500 and 1000" that fits in the right quarter of the plot, at
the angle a pixel along x spans on the sky at each frame, averaged across the image through the
middle of the view, so it keeps its length on a rolled or stretched image; on a raster map, whose
steps differ by up to 15 %, it is the mean step's. Where the axes are not a longitude and a
latitude, as on a spectrogram, the main window's status bar says there is no scale bar. These
are drawn only while saving, so "Save plot to file" and the viewer stay without them. The file
dialog offers a name made of the dataset's label and the first and last index
(``SJI_1400-4000255147-2013-09-02T16_39_35_0-399``), the file type chosen adding its suffix.
"Cancel" in its progress dialog, closing the viewer's tab, or resizing the viewer from outside its
window, with "Gather Windows" or by resizing the main window with the viewer maximized, keeps the
frames saved so far, a movie of them too, and the viewer goes back to its slice and limits.

.. _glue_solar_users_guide_iris_save_profiles:

Saving the profiles
-------------------

"IRIS: save profiles as ECSV…" in the Profile viewer's save menu writes the
profiles of its visible layers, as the viewer draws them, to one ECSV table, which
``astropy.table.Table.read`` reads back. Its file dialog opens where the last plot or frames were
saved and suggests ``<OBSID> <function> profiles.ecsv``, such as ``4000255147 mean profiles.ecsv``,
with the dataset's label, its spaces and punctuation made ``_``, for data without an OBSID, such as
an SST cube. Each layer saved, up the layer list (the order the layers are drawn, bottom first),
gives columns named after its label as glue's terminal names a variable: each character other than
an ASCII letter, digit or ``_`` becomes ``_``, and a label starting with a digit gets ``_`` before
it, so ``Si IV 1403`` gives ``Si_IV_1403``. A label met again once so named, such as a subset named as its
dataset or one subset group shown on two datasets, gets ``_01``, ``_02``, … as glue makes names
unique. The columns are ``<label>_x``, in the "x unit", ``km / s`` included, ``<label>_y``, the
viewer's function ("Maximum", "Mean", …) of its attribute in the "y unit", and, with "normalize"
ticked, ``<label>_y_normalized``, from 0 to 1 as drawn. ``<label>_x`` is described by the x axis's
name, ``<label>_y`` by the layer's label, and the meta of ``<label>_y`` give its attribute and, for
a "Pixel" subset, the pixel it selects along each axis it fixes. With the exposures of a
sit-and-stare raster, the scans of a stack or the frames of a slit-jaw image as the x axis,
``<label>_time`` gives the UTC time of each sample from the ``Time`` component, read back as an
``astropy.time.Time`` column: at the pixel of a "Pixel" subset or of "Light curve of this window",
else at the first raster step and slit pixel. A "Pixel" subset or light curve also gives
``<label>_lon`` and ``<label>_lat``, the helioprojective position of each sample there, in arcsec:
along the exposures, each exposure's pointing, which follows the Sun's rotation (on OBSID 4000255147
slit pixel 200 of Si IV 1403 is at 99.18" at exposure 0 and 105.66" at exposure 800), and along the
wavelength the same in every row. The whole dataset and other subsets cover no one place and get
none. The table's meta give the function and the data's ``OBSID`` and ``STARTOBS``. A shorter
profile is padded with empty values. Hidden layers are left out, as are layers without a profile,
such as one still being computed, or a subset one sample wide along x, which glue does not draw, and
the main window's status bar names both ("Left out, hidden: …; without a profile: …"), except the
layers glue-solar hides itself, even once ticked and unticked: a quicklook spectrum panel's raster
and the other subsets there, and a large cube. On the full Si IV 1403
window of OBSID 4000255147, 1600 exposures of 417 slit pixels and 262 wavelengths, the window's mean
and a pixel's light curve over the exposures, with their times and positions, save in under 0.1 s.
In Python, for a "Point" subset::

    from astropy.table import Table

    profiles = Table.read("4000255147 mean profiles.ecsv")
    profiles["Point_time"]  # an astropy Time, UTC
    profiles["Point_lon"]  # arcsec, at each exposure
    profiles["Point_y"]  # in the y unit
    profiles["Point_y_normalized"]  # from 0 to 1, saved with "normalize" ticked

.. _glue_solar_users_guide_exporting_derived_data:

Exporting derived data
----------------------

To save a map with its coordinates, such as the line moments, a line ratio, a red-blue asymmetry or
the Mg II features, choose "Export Data/Subsets" in glue's toolbar, or "Export data values" from the
map's right-click menu, and "IRIS FITS (coordinates and Time)". As with glue's "FITS (1
component/HDU)", each attribute is an image named after it, with its unit in ``BUNIT``, and here
also the observation's ``OBSID`` and ``STARTOBS`` and the map's coordinates as a FITS-TAB WCS: the
helioprojective longitude and latitude of every pixel as glue gives them, shifted pointing included,
in degrees, in the ``WCS-TABLE`` extension, with the observer and time of their frame. A ``Time``
attribute is the ``TIME`` image, seconds since its ``DATEREF``, UTC. astropy reads them back, and
with sunpy imported gives positions in the observer's helioprojective frame::

    import astropy.units as u
    import sunpy.coordinates  # noqa: F401
    from astropy.io import fits
    from astropy.time import Time
    from astropy.wcs import WCS

    with fits.open("moments.fits") as hdus:
        wcs = WCS(hdus["INTENSITY"].header, fobj=hdus)
        position = wcs.pixel_to_world(slit, step)  # FITS order: the fastest axis first
        # for a map with a Time attribute
        times = Time(hdus["TIME"].header["DATEREF"], scale="utc") + hdus["TIME"].data * u.s

``glue_solar.sources.iris.export_iris_fits(filename, data)`` writes the file in glue's terminal too.
Only 2-D maps on helioprojective coordinates export so: glue says why for a raster window, a
slit-jaw image or other data, which glue's "FITS (1 component/HDU)" writes without their IRIS
coordinates.

1-D data, such as the light curves at a point (see :ref:`The quicklook
<glue_solar_users_guide_iris_quicklook>`), export with "ECSV (with Time)" as an ECSV table: a
column for each attribute, as glue's "Comma-separated table" writes them, with its unit, a time
such as ``Time`` as UTC times to the nanosecond, which astropy reads back as a
`~astropy.time.Time` (glue's "Comma-separated table" writes nanoseconds since 1970), and the
observation's ``OBSID`` and ``STARTOBS`` in its header::

    from astropy.table import Table

    curve = Table.read("curve.ecsv")
    curve["Time"]  # an astropy Time, UTC
    curve["Value"]  # in the data's unit

``glue_solar.sources.iris.export_ecsv(filename, data)`` writes the file in glue's terminal too, and
glue says why for data that are not 1-D.

The profiles a Profile viewer draws, such as a quicklook's spectrum panel, save with "IRIS: save
profiles as ECSV…" in its save menu, a column for each layer's x, y, time and position, named after
the layer (see :ref:`Saving the profiles <glue_solar_users_guide_iris_save_profiles>`).
