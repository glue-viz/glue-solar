.. _glue_solar_dev_docs_loader_customization:

===============================
Data Loader Customization Guide
===============================

``glue`` can discover file readers through data factories and interactive tools through
menu plugins. The IRIS support provides a compact example of both.

Current IRIS loader structure
-----------------------------

``glue_solar/sources/iris.py`` registers the IRIS Level 2 data factory used by
"File -> Open Data Set" and the "IRIS: browse observations..." menu action.
The implementation under ``glue_solar/sources/loaders`` has four responsibilities:

1. ``scan.py`` reads primary headers to group standard IRIS filenames by observation.
   It does not load science arrays while browsing.
2. ``iris.py`` asks ``irispy.io.read_files`` to decode SJI, aligned AIA, and raster
   files, then converts the returned cubes into :class:`glue.core.data.Data` objects.
3. ``stack_spectrograms.py`` optionally stacks two or more raster scans without
   resampling. The 4D result has a leading scan-number axis, a separate exact
   acquisition-time component, and scan 0's WCS as its nominal spatial frame.
4. ``iris_loader.ui`` and ``QtIRISImporter`` present the observation and spectral-window
   selection dialog.

``irispy`` remains responsible for instrument detection, FITS interpretation, bad-pixel
masks, metadata normalization, units, and each input cube's WCS and exposure times. The
Glue adapter preserves those values and exposes masks and raster times as separate Glue
components.

Extending a loader
------------------

Register a focused data factory for a new file type and convert the authoritative
reader's output into one or more :class:`glue.core.data.Data` objects. Add a Qt menu
plugin only when users need selection beyond "File -> Open Data Set". Keep inexpensive
file discovery separate from full data decoding, and test the registered production
path with a representative file.

For the available registration hooks, see
`Glue's customization guide <https://docs.glueviz.org/en/stable/customizing_guide/customization.html>`__.
