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

glue-solar needs Python 3.13 or later and Git. It has no release yet, so it installs from this repository. In a new
environment::

    pip install git+https://github.com/glue-viz/glue-solar.git

This downloads glue and everything else it needs. The `documentation
<https://glue-solar.readthedocs.io/en/latest/>`__ has every step, from installing Python, for Windows, macOS and
Linux.

Using
-----

Start glue with ``glue`` and choose "Browse observations…" in the "Plugins" menu, or give glue your files::

    glue raster.fits sji.fits

"File → Open Data Set" inside glue reads them too.
