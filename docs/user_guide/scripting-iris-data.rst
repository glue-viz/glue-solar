.. _glue_solar_users_guide_scripting_iris_data:

=========================
Scripting with IRIS data
=========================

Glue's "Terminal" button (in the toolbar at the top of the main window) opens an IPython shell
running inside glue. It already holds ``data_collection`` (also ``dc``), ``application``, ``session``
and ``hub``, and whatever you load there appears in the data collection and in every viewer.

Loading data
------------

``raster_data`` loads chosen spectral windows of one or more raster files of an observation, and
``image_data`` a slit-jaw file or an aligned AIA cutout; both give the same datasets as the
observation browser::

    from glue_solar.sources.loaders.iris import image_data, raster_data

    rasters = raster_data(["iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"], ["Si IV 1403"])
    sji = image_data("iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    data_collection.extend([*rasters, sji])

Pass ``stack=True`` to ``raster_data`` to stack the scans of each window, as "Stack sequential raster
scans" does.

Coordinates and times
---------------------

A raster is indexed ``[step, slit, wavelength]`` (a stack ``[scan, step, slit, wavelength]``), and a
slit-jaw image ``[frame, y, x]``. ``data.coords.pixel_to_world_values`` takes the pixel indices in
the opposite order, fastest axis first, and returns the world values in that order too: for a raster,
wavelength (in metres), then helioprojective latitude and longitude (in arcsec)::

    raster = rasters[0]
    step, slit, pixel = 90, 20, 14
    wavelength, latitude, longitude = raster.coords.pixel_to_world_values(pixel, slit, step)

These are the values the Image viewer's readout shows at that position, latitude first.
Each dataset's ``Time`` component holds the acquisition time as ``numpy.datetime64``, one value per
raster step or slit-jaw frame::

    times = raster["Time"][:, 0, 0]
    frame_times = sji["Time"][:, 0, 0]

Spectra
-------

The data values are ``raster[raster.main_components[0]]``, with NaN for missing samples. For data
stored as 16-bit integers, as Level 2 files store them, this is a dask array, which reads the file
only when computed: ``np.asarray`` computes a result, and a view in the brackets, such as
``raster[cid, step, slit]``, reads only what it selects. The Profile viewer's Mean of a raster
against ``Wavelength`` is the mean spectrum over every step and slit position::

    import numpy as np

    cid = raster.main_components[0]
    mean_spectrum = np.asarray(np.nanmean(raster[cid], axis=(0, 1), dtype=float))  # float64 sums, as glue uses
    point_spectrum = raster[cid, step, slit]
