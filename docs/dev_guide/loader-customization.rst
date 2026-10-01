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
The implementation under ``glue_solar/sources/loaders`` has five responsibilities:

1. ``scan.py`` reads primary headers to group standard IRIS filenames by observation.
   It does not load science arrays while browsing.
2. ``iris.py`` asks ``irispy.io.read_files`` to decode SJI, aligned AIA, and raster
   files, then converts the returned cubes into :class:`glue.core.data.Data` objects.
3. ``lazy.py`` holds data stored as int16, as Level 2 files store it, without scaling it
   in memory. ``RawComponent``, a glue ``DaskComponent``, keeps the raw integers (a
   memory map, or an array for a ``.fits.gz`` file) and scales only what a view selects,
   astropy's way, with the fill codes as NaN; a read of the whole component goes through
   dask. ``LazyData`` answers glue's sampled statistics, such as colour limits, from a
   count of the raw values. ``RawStack`` stacks scans along a new leading axis without
   copying them.
4. ``stack_spectrograms.py`` gives a stack of two or more raster scans its WCS
   (``stack_wcs``, scan 0's with a leading scan-number axis) and its exact acquisition
   times (``stack_times``), and stacks floating-point scans without resampling into a
   memory-mapped temporary file of dtype ``np.result_type(first scan, float32)``.
5. ``iris_loader.ui`` and ``QtIRISImporter`` present the observation and spectral-window
   selection dialog.

``irispy`` remains responsible for instrument detection, FITS interpretation, metadata
normalization, units, and each input cube's WCS and exposure times. The Glue adapter keeps
those and changes only missing data: the IRIS fill values -200 and -199 (only -200 in aligned
AIA cutouts) become NaN. Each dataset's ``<label> mask`` component is ``isnan(data)`` as
``uint8``, since Glue would store a boolean component as ``int64``, so saturated samples,
which are +Inf, stay unmasked; for int16 data it is a glue derived component of the data
(``lazy.fill_mask``). Raster times are a separate ``Time`` component.

Data stored as int16 load through irispy's memory map (``read_files(memmap=True)``), which
gives the raw integers of raster windows, flipped as irispy flips negative-step rasters; each
window's BSCALE and BZERO come from its own header. A slit-jaw or AIA file's raw integers are
read by glue-solar itself, since irispy's memory-mapped cube writes 0 over the fill, and irispy
supplies the coordinates and metadata. Files of any other type load as float32 in memory,
through irispy's usual reader. Setting ``glue_solar.sources.loaders.iris.LAZY = False`` before
loading reads everything that way, as glue-solar did before lazy loading, for example to compare
the two or for files on a drive that may disconnect. Lazy loading raises the process's soft
limit on open files (``lazy.allow_open_files``), as every memory-mapped file stays open.

Extending a loader
------------------

Register a focused data factory for a new file type and convert the authoritative
reader's output into one or more :class:`glue.core.data.Data` objects. Add a Qt menu
plugin only when users need selection beyond "File -> Open Data Set". Keep inexpensive
file discovery separate from full data decoding, and test the registered production
path with a representative file.

For the available registration hooks, see
`Glue's customization guide <https://docs.glueviz.org/en/stable/customizing_guide/customization.html>`__.
