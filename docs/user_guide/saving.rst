.. _glue_solar_users_guide_saving:

======
Saving
======

.. _glue_solar_users_guide_saving_sessions:

Sessions
--------

Save a session with File → Export Session as "Glue Session with relative paths to data", the type the
dialog starts with (see glue's `guide
<http://docs.glueviz.org/en/stable/getting_started/index.html#saving-your-work>`__). It refers to the
IRIS, SST and DKIST files rather than holding their values, and opens wherever the files keep their
place relative to it. A DKIST dataset's coordinates, too, are read again from its ASDF file, which
must still be where the session found it. Datasets made from them, such as line maps, are saved
with their values: export a copy of each (see `Exporting derived data`_).

A session keeps the datasets' coordinates, pointing shifts, colormaps, metadata and links, and the
viewers' slices, colormaps and Profile axes. Each quicklook opens again with its point, the dataset
leading the time, panel settings and panels turned off. A quicklook's raster overlays, panels moved by hand, a blink and
the viewers' mouse modes are not saved, and glue opens each Image viewer zoomed to fit its reference dataset, such as a
VBI mosaic's center tile. A light curve, row or column at the point opens where it was, no longer following the point.
For sessions that fail to save or open, see :ref:`Known issues
<glue_solar_users_guide_known_issues>`.

Restoring the last session
--------------------------

As glue quits with data loaded, glue-solar keeps the session, with absolute paths to the files, in
``~/.glue/glue-solar-last-session.glu``. "Restore last session" in the "Plugins" menu opens it
as File → Open Session does.

A session over 1 MB, such as one holding line maps, or one glue cannot save, is not kept: a message
says why as glue quits, and the session kept before stays.

.. _glue_solar_users_guide_iris_save_frames:

Frames and movies
-----------------

1. In an Image viewer, choose "Save frames or movie…" in the save menu, the disk icon.
2. With several sliders, pick one: the data's first axis, such as a slit-jaw image's frames, comes
   first.
3. Type the first and last index, such as ``100 120``, or ``±10`` around the current one.
4. Tick what to draw on each frame: "UTC time on each frame", "Frame numbers" or "Scale bar".
5. Pick a file name and type: PNG, MP4 where ffmpeg is installed, or GIF.

PNG files take the index after the name: ``sji.png`` gives ``sji_0000.png``, ``sji_0001.png``, ….
Movies play at 10 frames per second. A GIF is held in memory until written: save long sequences as
MP4 or PNG.

Each frame is what "Save plot to file" saves at that index, and the other viewers follow, as when the
slider plays. Every frame has the same color limits, the whole cube's with "Per-frame limits" on.
glue stays usable while the viewer saves, grayed. "Cancel", closing the viewer or resizing it keeps
the frames saved so far.

.. _glue_solar_users_guide_iris_save_profiles:

Profiles
--------

"Save profiles as ECSV…", in a Profile viewer's save menu, writes the profiles of its visible
layers, as drawn, to one ECSV table. Each layer gives columns named after its label, made a Python
name: ``Si IV 1403`` gives ``Si_IV_1403``.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Column
     - Holds
   * - ``<label>_x``
     - The x axis, in the "x unit", ``km / s`` included.
   * - ``<label>_y``
     - The viewer's function, such as Mean, of the layer's attribute, in the "y unit".
   * - ``<label>_y_normalized``
     - The profile from 0 to 1, with "normalize" ticked.
   * - ``<label>_time``
     - The UTC time of each sample, when x is a sit-and-stare raster's exposures, a stack's scans or a
       slit-jaw image's frames.
   * - ``<label>_lon``, ``<label>_lat``
     - The helioprojective position of each sample, in arcsec, for the point or a cut through it.

The table's meta hold the function and the observation's ``OBSID`` and ``STARTOBS``. A shorter
profile is padded with empty values. Hidden layers are left out, and the status bar names them.
``astropy.table.Table.read`` reads the table back, ``<label>_time`` as an astropy ``Time``.

.. _glue_solar_users_guide_exporting_derived_data:

Exporting derived data
----------------------

Select a dataset and choose "Export Data/Subsets" in glue's toolbar, or "Export data values" in its
right-click menu, then the file type:

- **"IRIS FITS (coordinates and Time)"**, for a 2-D map on helioprojective coordinates, such as line
  moments, a line ratio, a red-blue asymmetry or the Mg II features. Each attribute is an image named
  after it, with its unit in ``BUNIT``. The coordinates, pointing shift included, are a FITS-TAB WCS,
  and a ``Time`` attribute is the ``TIME`` image, in s since its ``DATEREF``. A stack's maps, of
  (scan, step, slit), export with glue's "FITS (1 component/HDU)", without their coordinates.
- **"ECSV (with Time)"**, for 1-D data such as the light curves at the point: a column per
  attribute, with its unit, and times in UTC.

Both hold the observation's ``OBSID`` and ``STARTOBS``. Raster windows and slit-jaw images export
with glue's own types, without their IRIS coordinates. astropy reads the files back; for positions in
the helioprojective frame, import sunpy too::

    import sunpy.coordinates  # noqa: F401
    from astropy.io import fits
    from astropy.wcs import WCS

    with fits.open("moments.fits") as hdus:
        wcs = WCS(hdus["INTENSITY"].header, fobj=hdus)
        position = wcs.pixel_to_world(slit, step)  # FITS order: the fastest axis first

In glue's terminal, ``glue_solar.sources.iris.export_iris_fits(filename, data)`` and
``glue_solar.sources.iris.export_ecsv(filename, data)`` write the same files.
