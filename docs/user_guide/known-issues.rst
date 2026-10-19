.. _glue_solar_users_guide_known_issues:

============
Known issues
============

These come from glue, glue-qt and the libraries glue-solar builds on, as of glue-core 1.27.0 and
glue-qt 0.4.2. To report another, choose "glue-solar user guide and issues" in the "Plugins" menu, which
opens glue-solar's `issues <https://github.com/glue-viz/glue-solar/issues>`__.

Installing
----------

- **PyQt5 beside PyQt6:** set ``QT_API=pyqt6`` before starting glue, as qtpy takes PyQt5 first.
- **The O IV density preset:** keep ``em`` and ``ip`` out of the path of ``~/.fiasco``, as in a
  folder named emily or Temp, or fiasco builds no ions. If glue quits while fiasco builds the CHIANTI
  database, delete the unfinished ``chianti_dbase.h5`` before the next use.

Loading
-------

- **Files in use:** don't overwrite, move or unplug a file while its data are loaded. They are read
  from it as they are viewed, and glue can crash.
- **SST cubes:** open maps before SST cubes, and cubes without Stokes before those with, or glue's
  autolinker reports an error, although the data load.

Viewers
-------

- **Time axes:** glue's axes are index axes, so exposures, scans and frames show evenly spaced
  whatever their cadence. Use :ref:`"IRIS: regrid on time" <glue_solar_users_guide_iris_regrid>`.
- **Regions:** to change a region, pick it as the toolbar's "Active Subset" first, and pick "Point"
  again before moving the point.
- **Regions from other viewers:** draw regions on a quicklook's panels. One drawn on a raster in
  another Image viewer is slow to show on a slit-jaw image.
- **Navigate and Collapse:** keep the Profile viewer's "x unit" at ``Angstrom``, the data's own.
- **Collapse:** drag over two samples or more, as the last is left out. The collapsed map lasts until
  a slider moves; for a band that follows the slider, use "Wavelength band…".
- **Keys:** :kbd:`U` and :kbd:`L` act only while the toolbar has the keyboard: click the toolbar
  first.
- **Backspace in the data collection** deletes the selected datasets and subsets at once, without
  undo.

Saving
------

- **"Per-frame limits":** turn them off before saving a session. A session saved with them on in any
  Image viewer but a quicklook's panels does not open ("'NoneType' object has no attribute
  'add_callback'").
- **"Glue Session including data"** fails on IRIS data read from their files as they are viewed and
  on SST cubes: save with relative paths to data.
- **Data regridded on time** from data read as they are viewed do not save ("Don't know how to
  serialize dask.array"): remove them before saving, and regrid again after opening.
- **glue's "Comma-separated table"** writes times as nanoseconds since 1970: export 1-D data with
  "ECSV (with Time)".
