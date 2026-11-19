Solar Physics Plugin for glue
=============================

glue-solar adds solar data to `glue <https://glueviz.org>`__, a desktop program for exploring linked datasets:

- an observation browser for IRIS Level 2 files and SST CRISP and CHROMIS cubes;
- a loader for DKIST Level 1 datasets;
- a quicklook, one tab of linked panels for an observation kept on one selected point, in the manner of CRISPEX;
- viewer tools for time, wavelength and Doppler velocity;
- analyses through irispy, such as line maps and fits of every spectrum;
- AIA and HMI maps beside them.

The `user guide <https://glue-solar.readthedocs.io/en/latest/>`__ starts with an IRIS observation opened in a quicklook.

Installation
------------

As this plugin is still in development, you can only install it from this repository::

    $ git clone https://github.com/glue-viz/glue-solar.git
    $ cd glue-solar
    $ pip install -e .

This installs glue and PyQt6 (glue-solar needs Qt 6), and registers the plugin with glue.

Using
-----

Start glue with ``glue`` and choose "Browse observations…" in the "Plugins" menu, or give glue your files::

    glue raster.fits sji.fits

"File → Open Data Set" inside glue reads them too.
