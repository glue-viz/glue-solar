.. _glue-solar-index:

========================
glue-solar documentation
========================

``glue-solar`` provides solar physics functionality to `glue <https://glueviz.org>`__, for multi-instrument interactive visualization.

Installing and running
----------------------

Installing glue-solar
^^^^^^^^^^^^^^^^^^^^^

Until its first release, ``glue-solar`` installs only from its repository on GitHub.
With Git, ``pip`` and an active Python virtual environment::

    $ git clone https://github.com/glue-viz/glue-solar.git
    $ cd glue-solar
    $ pip install -e .

This installs glue and PyQt6: glue-solar needs Qt 6, and says so as glue starts under Qt 5.

The O IV density preset of the line ratio diagnostic needs fiasco, in the ``density`` extra::

    $ pip install -e ".[density]"

fiasco downloads and builds the CHIANTI atomic database, a few GB, on its first use.

Starting up Glue
^^^^^^^^^^^^^^^^

Start glue from a terminal::

    $ glue

On Windows, installation creates ``glue.exe`` in the Python script directory (e.g., ``C:\Python313\Scripts``), for which you can create a desktop shortcut.

On a Mac, glue-solar can also be built into an app, ``Glue Solar.app``, which opens from the Finder, the Dock or Launchpad: see :ref:`glue_solar_dev_docs_macos_app`.

.. toctree::
   :maxdepth: 2

   user_guide/index
   dev_guide/index
   api_reference
   whatsnew/index
