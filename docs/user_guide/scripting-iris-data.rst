.. _glue_solar_users_guide_scripting_iris_data:

=========
Scripting
=========

glue's "Terminal" button, in the toolbar, opens an IPython shell inside glue. It holds
``data_collection`` (also ``dc``), ``application``, ``session`` and ``hub``. What you add to
``data_collection`` there shows in every viewer.

Loading data
------------

``raster_data`` loads chosen windows of one or more raster files of an observation, and
``image_data`` a slit-jaw image, an aligned AIA cutout or a Hinode/SOT cube, as the observation
browser does::

    from glue_solar.sources.loaders.iris import image_data, raster_data

    rasters = raster_data(["iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"], ["Si IV 1403"])
    sji = image_data("iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    data_collection.extend([*rasters, sji])

Pass ``stack=True`` to ``raster_data`` to stack the scans of each window.

``find_observation_files`` finds the files of the observations below a folder that run between a
start and an end, the same time for the observation running then, and ``pattern`` picks among their
names. ``scan_directory`` takes the same arguments and gives the observations, as the browser lists
them::

    from glue_solar.sources.loaders.scan import find_observation_files

    files = find_observation_files("/data/IRIS", "2021-09-05T00:30", "2021-09-05T00:30", pattern="*_raster_t*")
    data_collection.extend(raster_data(files, ["Si IV 1403"]))

Linking
-------

Data added in the terminal are not linked. ``link_hpc`` gives the helioprojective links the browser
makes between the IRIS data, and to the datasets named in ``others``, such as an AIA cutout, a map or
an SST cube, leaving out links already made. ``others=data_collection`` links every dataset, as
"IRIS: link helioprojective coordinates" does::

    from glue_solar.sources.loaders.iris import link_hpc

    data_collection.add_link(link_hpc(data_collection))  # the IRIS data
    data_collection.add_link(link_hpc(data_collection, others=[aia]))  # and an AIA cutout, aia

Opening a quicklook
-------------------

``quicklook`` opens the quicklook of datasets of one observation in a new tab, adding those not yet in
the data collection. ``window`` names the raster windows to show, and ``main`` the main window::

    from glue_solar.quicklook import quicklook

    quicklook(application, [*rasters, sji], window="Si IV 1403")

Coordinates and times
---------------------

A raster is indexed ``[step, slit, wavelength]``, a stack ``[scan, step, slit, wavelength]`` and a
slit-jaw image ``[frame, y, x]``. ``coords.pixel_to_world_values`` takes the pixel indices in the
opposite order, fastest axis first, and gives the world values in that order: for a raster, the
wavelength in Angstrom, then the helioprojective latitude and longitude in arcsec. The Image viewer's
readout shows the same values. On a sit-and-stare raster such as this one, the map (step against
slit) reads only the latitude, along the slit::

    raster = rasters[0]
    step, slit, pixel = 90, 20, 14
    wavelength, latitude, longitude = raster.coords.pixel_to_world_values(pixel, slit, step)

``Time`` holds the UTC time of each raster step or slit-jaw frame as ``numpy.datetime64``::

    times = raster["Time"][:, 0, 0]
    frame_times = sji["Time"][:, 0, 0]

``sji_to_raster`` gives the raster pixel under a slit-jaw pixel, placed with that frame's pointing:
``(step, slit)``, ``(scan, step, slit)`` on a stack, or None off the raster. On a sit-and-stare
raster, the exposure is the one nearest the frame's time, within half its cadence, and the slit row
the one level with the pixel::

    from glue_solar.quicklook import sji_to_raster

    frame, x, y = 30, 18.5, 20.0
    index = sji_to_raster(sji, frame, x, y, raster)

Spectra
-------

The data values are ``raster[raster.main_components[0]]``, with NaN for missing samples. Data stored
as 16-bit integers, as Level 2 files store them, are read from the file only when computed: a view in
the brackets, such as ``raster[cid, step, slit]``, reads only what it selects. ``compute_statistic``
gives the Profile viewer's Mean, which leaves out the missing and :ref:`saturated
<glue_solar_users_guide_iris_saturation>` samples::

    cid = raster.main_components[0]
    mean_spectrum = raster.compute_statistic("mean", cid, axis=(0, 1))  # over every step and slit position
    point_spectrum = raster[cid, step, slit]

Analyses and exports
--------------------

Each analysis and data action has a function that makes the same dataset with other settings: see
"In glue's terminal" on :ref:`Analyses <glue_solar_users_guide_analyses>` and :ref:`Data actions
<glue_solar_users_guide_data_actions>`. To write a result to a file, see :ref:`Exporting derived data
<glue_solar_users_guide_exporting_derived_data>`.
