.. _glue-solar:

glue-solar documentation
========================

``glue-solar`` is a project to provide solar physics specific functionality to `glue <https://glueviz.org>`__, to facilitate multi-instrument interactive visualization.

Installing and running
----------------------

Requirements
^^^^^^^^^^^^

For the requirements of ``glue``, please refer to their official documentation on `installing and running glue <http://docs.glueviz.org/en/stable/installation/installation.html>`__.

Installing glue-solar
^^^^^^^^^^^^^^^^^^^^^

In order to use ``glue`` with the ``glue-solar`` plugin, you will need to have both packages installed on your computer.
For the time being before an official release, the only way to install ``glue-solar`` is to download with GitHub, where the repository for the package is hosted.

This assumes that you already have ``pip`` and a Python virtual environment created and active.

To download the entire glue-solar repository locally, first make sure you have Git installed locally, then to clone over HTTPS::

    $ git clone https://github.com/glue-viz/glue-solar.git

After that, change directory (cd) to glue-solar::

    $ cd glue-solar

Finally, do the following while at the root (highest level) of the glue-solar directory::

    $ pip install -e ".[all]"

Started up Glue
^^^^^^^^^^^^^^^

Once both ``glue`` and ``glue-solar`` have been properly installed, to start the application via the command line::

    $ glue

This will launch the ``glue`` graphical user interface (GUI) from your terminal.

On Windows operating systems, installation creates an executable ``glue.exe`` file within the Python script directory (e.g., ``C:\Python310\Scripts``).
Windows users can create a desktop shortcut for this file upon installation

User Interface Guide
^^^^^^^^^^^^^^^^^^^^

For a walk through of the user interface of ``glue``, please refer to the `getting started section of the glue documentation. <http://docs.glueviz.org/en/stable/getting_started/index.html>`__

.. toctree::
   :maxdepth: 2

   user_guide/index
   dev_guide/index
   api_reference
