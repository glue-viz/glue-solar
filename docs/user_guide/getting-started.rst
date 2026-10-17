.. _glue_solar_users_guide_getting_started:

===============
Getting started
===============

Open an IRIS observation in a quicklook and take a first look at it.

1. Start glue with ``glue`` and choose "IRIS: browse observations…" in the "Plugins" menu.
2. In "Folder", give the folder that holds your IRIS Level 2 files or their downloaded archives. The
   browser lists each observation it finds, one row per OBSID and start time. For a packed archive,
   tick its "Extract …" entry and press "Load selected" first.
3. Tick an observation, or expand it and tick the raster windows and slit-jaw channels you want, and
   press "Load selected". With "Open quicklook" ticked, as it is at first, the observation opens in a
   quicklook in a new tab.

.. image:: images/quicklook.png
   :width: 800
   :alt: The quicklook of OBSID 4000255147, a sit-and-stare observation of Mg II k 2796 and SJI 1400

The top row shows the raster: the map, the spectrogram at the point and wavelength against time.
Below are the slit-jaw image, with the point as a red cross, and the spectrum at the point. The Point
window and the Panels list sit at the bottom.

4. Click the map to move the point. The spectrogram, the wavelength panel, the slit-jaw image and the
   spectrum follow.
5. Press :kbd:`D` and :kbd:`F` to step back and on in time, :kbd:`A` and :kbd:`S` to step in
   wavelength, and :kbd:`Space` to play.
6. With several raster windows loaded, tick another in the Panels list to compare its spectrum at
   the same point.
7. To save frames or a movie, choose "IRIS: save frames or movie…" in a panel's save menu, the disk
   icon.

From a terminal, ``glue --startup=iris_quicklook raster.fits sji.fits`` opens the same quicklook.

Next, see :ref:`Quicklook <glue_solar_users_guide_iris_quicklook>` for all the panels do,
:ref:`Viewer tools <glue_solar_users_guide_viewer_tools_and_windows>` for each tool, menu entry and
key, and :ref:`Browsing and loading IRIS data
<glue_solar_users_guide_loading_iris_level_2_raster_and_sji_files>` for the browser's options.
