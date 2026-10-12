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
``image_data`` a slit-jaw file, an aligned AIA cutout or a Hinode/SOT cube; both give the same
datasets as the observation browser::

    from glue_solar.sources.loaders.iris import image_data, raster_data

    rasters = raster_data(["iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"], ["Si IV 1403"])
    sji = image_data("iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    data_collection.extend([*rasters, sji])

Pass ``stack=True`` to ``raster_data`` to stack the scans of each window, as "Stack sequential raster
scans" does.

``find_observation_files`` finds the files of the observations below a folder that run at some time
from a start to an end, and a glob on the file names picks which of them; ``scan_directory`` takes
the same arguments and gives the observations, as the observation browser lists them. Neither reads a
file whose name is stamped after the end, or more than a day before the start (an observation may run
into the window from the day before)::

    from glue_solar.sources.loaders.scan import find_observation_files

    files = find_observation_files("/data/IRIS", "2021-09-05T00:30", "2021-09-05T00:30", pattern="*_raster_t*")
    data_collection.extend(raster_data(files, ["Si IV 1403"]))

Linking
-------

Data added in the terminal are not linked. ``link_hpc`` gives the links of their helioprojective
longitude and latitude that the observation browser makes, those of the IRIS rasters and slit-jaw
images and of data made from them, and those of other datasets, such as an aligned AIA cutout, a
Hinode/SOT cube, a sunpy map or an SST cube, only where ``others`` names them; it leaves out the
links already made. ``others=data_collection`` links every dataset, as "IRIS: link helioprojective
coordinates" does, though only the menu entry links them again once a dataset is removed (see
:ref:`Linking <glue_solar_users_guide_iris_linking>`)::

    from glue_solar.sources.loaders.iris import link_hpc

    data_collection.add_link(link_hpc(data_collection))  # the IRIS data
    data_collection.add_link(link_hpc(data_collection, others=[aia]))  # and an AIA cutout, aia

Coordinates and times
---------------------

A raster is indexed ``[step, slit, wavelength]`` (a stack ``[scan, step, slit, wavelength]``), and a
slit-jaw image ``[frame, y, x]``. ``data.coords.pixel_to_world_values`` takes the pixel indices in
the opposite order, fastest axis first, and returns the world values in that order too: for a raster,
wavelength (in Angstrom), then helioprojective latitude and longitude (in arcsec)::

    raster = rasters[0]
    step, slit, pixel = 90, 20, 14
    wavelength, latitude, longitude = raster.coords.pixel_to_world_values(pixel, slit, step)

The Image viewer's readout shows those of the displayed axes at that position, latitude first,
angles in arcsec to 0.01″ and wavelengths in Angstrom to 0.001 Å, with the step's time and exposure;
on a sit-and-stare raster such as this one, whose steps are exposures, its map (step against slit)
reads only the latitude, along the slit.
Each dataset's ``Time`` component holds the acquisition time as ``numpy.datetime64``, one value per
raster step or slit-jaw frame::

    times = raster["Time"][:, 0, 0]
    frame_times = sji["Time"][:, 0, 0]

``sji_to_raster`` finds the raster pixel under a slit-jaw pixel, placed with that frame's own pointing:
``(step, slit)``, on a stack ``(scan, step, slit)``, or None outside the raster. A scanning raster's
step is the one at that place; a sit-and-stare raster's exposure, and a stack's scan, are the ones
nearest the frame's time (a sit-and-stare exposure only within half its cadence, else None), and on a
sit-and-stare raster the slit row is the one level with the pixel, even beside the slit::

    from glue_solar.quicklook import sji_to_raster

    frame, x, y = 30, 18.5, 20.0
    index = sji_to_raster(sji, frame, x, y, raster)

Spectra
-------

The data values are ``raster[raster.main_components[0]]``, with NaN for missing samples. For data
stored as 16-bit integers, as Level 2 files store them, this is a dask array, which reads the file
only when computed: ``np.asarray`` computes a result, and a view in the brackets, such as
``raster[cid, step, slit]``, reads only what it selects. The Profile viewer's Mean of a raster
against ``Wavelength`` is the mean spectrum over every step and slit position, glue's
``compute_statistic``, which leaves out the missing samples and the :ref:`saturated
<glue_solar_users_guide_iris_saturation>` ones, +Inf, where numpy's ``nanmean`` would give +Inf::

    cid = raster.main_components[0]
    mean_spectrum = raster.compute_statistic("mean", cid, axis=(0, 1))  # float64, as the Profile draws it
    point_spectrum = raster[cid, step, slit]
