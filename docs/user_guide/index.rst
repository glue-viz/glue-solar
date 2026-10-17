.. _glue_solar_users_guide_index:

==========
User Guide
==========

In glue, "IRIS: user guide and issues" in the "Plugins" menu opens this guide, and glue-solar's
issues on GitHub to report a problem, in the web browser.

glue-solar's four entries in the "Plugins" menu, its data actions in the data collection's
right-click menu, which the "Data Manager" menu repeats, and its entries in glue's save menus,
"IRIS: save frames or movie…" and "IRIS: save profiles as ECSV…", start with "IRIS: ", but for
the data action "Quicklook…", which opens the quicklook of an IRIS raster or slit-jaw image, an SST
cube or another spectral cube (see :ref:`Quicklook <glue_solar_users_guide_iris_quicklook>`). The
data actions are listed by data kind, the spectral analyses first, then the image actions and the
coordinates, and each is offered only for data it takes; one that takes few kinds names them, as
"IRIS: remove dust (SJI)" does. One whose check of the data fails with an error other than its own
refusal stays offered, so that choosing it shows the error. The entries in glue-solar's own toolbar
menus have no prefix.

.. toctree::
   :maxdepth: 2

   getting-started
   loading-aia-and-hmi
   loading-iris-level-2-raster-and-sji-data
   loading-sst-cubes
   iris-quicklook
   viewer-tools-and-windows
   iris-line-moments
   iris-mg-features
   iris-calibration
   iris-bursts
   data-actions
   saving
   scripting-iris-data
