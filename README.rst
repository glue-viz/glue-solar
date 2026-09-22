Solar Physics Plugin for glue
=============================

Installation
------------

As this plugin is still in development, you can only install it from this repository.
You will want to do the following steps::

    $ git clone https://github.com/glue-viz/glue-solar.git

Then change directory to glue-solar and install with::

    pip install -e .

This installs the Qt binding used by the interactive plugin, auto-registers it with glue,
and installs glue itself.

Using
-----

At the moment, this plugin provides a reader for solar data, you can give glue some solar data file in the FITS format.
For example, you can start glue by using::

    glue mydata.fits

and you can also load files from inside glue.
