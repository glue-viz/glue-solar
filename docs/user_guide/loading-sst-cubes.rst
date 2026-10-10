.. _glue_solar_users_guide_loading_sst_cubes:

===================================
Opening SST CRISP and CHROMIS cubes
===================================

What loads
----------

File → Open Data Set opens a CRISP or CHROMIS cube from the SST data archive, one of the SOLARNET FITS
files its SSTRED pipeline exports (``nb_6563_…_im.fits`` and the like), as one dataset. glue-solar's
reader, "SST CRISP or CHROMIS cube (SOLARNET FITS)", takes these files ahead of glue's "FITS file",
which gave each cube 32 more datasets: its cavity map, and an empty one for each of its tables. In
glue's terminal, ``sst_data`` loads one the same way::

    from glue_solar.sources.sst import sst_data

    data_collection.append(sst_data("nb_8542_2023-09-19T10:43:01_mosaic_…_im.fits"))

The dataset's axes are the file's, in numpy order: scan, Stokes, tuning, y and x, with a Stokes axis
of length 1 in a cube of intensities. Its values stay in the file, memory-mapped: opening a cube reads
only its headers and coordinate table, in 0.02 to 0.04 s for the cubes of 0.4 to 9.9 GB tried, and a
viewer reads the planes it shows.

Its coordinates are the file's tabulated WCS: the helioprojective longitude and latitude of each scan,
which move from scan to scan in a mosaic, the nominal wavelength of each tuning, in nm, and the time
of each tuning of each scan, in seconds since the file's ``DATEREF``. ``Time`` gives that time in UTC
at every pixel, as the file's ``DATE-AVG`` table does. A scan's tunings span from 2 s, the 11
H-alpha tunings of the archive's obs 171, to 26 s, the 21 Ca II 8542 tunings of its obs 492; glue's
own reader gave every tuning the time of the first. A file whose header has no ``SPECSYS``, as the
archive's 2020 exports have none, is given ``TOPOCENT``, without which no viewer showed it. The file's
other tables (``VAR-EXT-…``, such as the seeing and the exposure times) are not loaded.

Cavity error
------------

``Cavity error`` is the shift of each pixel's wavelength from the nominal one at each scan, in nm,
from the cavity map of the Fabry–Pérot that SSTRED stores in the file (``WCSDVARR``): up to
0.006 nm on obs 171, 2.8 km/s at H-alpha. The wavelength axis keeps the nominal wavelengths. To
correct one, or a line position measured on them, add the cavity error, with glue's arithmetic
attribute editor for example: ``{Wavelength} + {Cavity error}``, or as a velocity at 656.28 nm,
``{Cavity error} / 656.28 * 299792.458`` in km/s. A CHROMIS Ca II H & K cube has a map for each
prefilter, each applied to its own tunings, and none for its continuum tuning, where the cavity error
is NaN. The maps too stay in the file until they are viewed.

Linking to IRIS data
--------------------

An SST cube is linked to IRIS data only on request, with "IRIS: link helioprojective coordinates" in
the "Plugins" menu (see :ref:`glue_solar_users_guide_iris_linking`). Once it is linked, a region drawn
on the cube selects, in each slit-jaw frame and each raster exposure or step, the IRIS pixels at its
place on the Sun in the cube's scan nearest that frame's time, timed by its middle tuning, at that
scan's own pointing. A Pixel point on the cube, which glue places at its first scan and tuning, reaches
the raster pixel at its place, and in the slit-jaw frame nearest that scan, the pixel there.

Saving sessions
---------------

A session refers to the cube's file, as it does to IRIS data's (see "Saving sessions" in
:ref:`Viewer tools and windows <glue_solar_users_guide_viewer_tools_and_windows>`), and reads it again
as it opens; "IRIS: restore last session" opens the one glue-solar keeps as glue closes.

What is not supported
---------------------

The Level 3 files of the IRIS–SST coordinated observations, made for CRISPEX
(``iris_l3_…_im.fits``), are not SSTRED exports: glue's own "FITS file" reader opens them, without
these coordinates, times and cavity maps.

A cube whose table gives the pointing at more points than the field's four corners, which SSTRED does
not write, takes wcslib's own inverse of its coordinates, so once linked a region drawn on it selects
no IRIS pixels.

Opening a map, or other data with sky coordinates and a different number of axes, after an SST cube
shows glue's "Could not load data … Cannot slice WCS" from its autolinker, though the map loads; open
the map first to avoid it.
