.. _glue_solar_dev_docs_loader_customization:

===============================
Data Loader Customization Guide
===============================

The ``glue`` data visualization tool is highly customizable for different data types, such as FITS files that are often used in solar physics research.
There are two ways to customize ``glue`` using the ``glue-solar`` plugin:

1. The first option is to develop a custom loader for the solar data taken from practically any (ground-based or satellite-borne) instrument.

2. The second option is to develop a custom viewer to enable a specific way to view your data.
   Such as an alternative of the existing 2D image viewer that presents your data in a manner you like; e.g. color-coding the lines or data points.

While these two options serve different needs, the former is often needed to load your post-processed data, if they are not FITS.
``glue`` already has the functionality to open and display FITS files.
Hence in this guide, we walk through how to construct a custom data loader for your solar physics use case.

The Case of the IRIS subpackage
-------------------------------

If we look at the ``glue_solar/instruments/iris`` directory, we can find (at least at the time of writing of this
guide) the files within follows:

1. __init__.py: This is the typical ``init`` file that is used for containing the code snippets that are
used for initializing the subpackage, and is required for running unit tests with ``pytest``.

2. ``iris.py``: This serves as the "main" file for running the basic loader code in this ``iris`` subpackage. The
module contains three methods needed to load the typical IRIS Level 2 Raster Scan into ``glue``. They are the
``import_iris``, ``read_iris_raster``, and the (hidden) ``_parse_iris_raster`` methods. As an aside, to load
IRIS Level 2 SJI Cubes, one will need to use the FITS loader instead.

3. ``loader.py``: This serves as the file containing the ``QtIRISImporter`` class which is used in conjunction
with ``loader.ui``. This ``loader`` module is the primary means we communicate with the UI component called "loader".

4. ``loader.ui``: This is the Designer UI file used in this Qt application. Simply put this is a fancy way of saying
that this file gives the look and feel of the dialog box we will use for loading the FITS files taken with
the instrument concerned.

5. ``stack_spectrograms.py``: This file can alternately be named ``utils.py`` instead. As this suggestion would
indicate, it provides a utility called ``stack_spectrogram_sequence``

Basic subpackage structure
--------------------------

So using the above example and thinking deductively, we can tell the following basic directory structure for any new
instrument submodule:

1. The ``__init__.py`` file

2. The "main" instrument module as in the C-family parlance, this is where the main action takes place.

3. The ``loader.py`` file for controlling or interacting with the ``loader.ui`` Qt Designer file.

4. The corresponding ``loader.ui`` file providing the UI of the pop-up dialog box. One suggestion is to use the
IRIS version as a template, and then use Qt's Designer application to edit it to suit once needs.

5. Some module akin to the ``utils.py`` for storing all the helper functions one will need in the other modules within
the same instrument subpackage.

Basically the most important thing to keep in mind is to make sure your main instrument module (``iris.py`` in the
case of the ``IRIS`` satellite) contains three essential ingredients; they are namely the parser (note the use of the
``@qglue_parser`` decorator for this), the data factory (note the use of the ``@data_factory`` decorator), and the
importer (note the use of the ``@importer`` decorator). Please note also that the way to convert instrument-specific
data to the ``glue.core.data.Data`` object is highly dependent on the pipeline used for such observations. But in
general the ``astropy.io.fits`` methods should be able to handle most but not all as an instrument-agnostic option.

For more details about the ``glue`` loader customization, please see
`the official glue customization guide <http://docs.glueviz.org/en/stable/customizing_guide/customization.html>`_.
