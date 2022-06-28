Solar Physics Plugin for glue
=============================

Installation
------------

As this plugin is still in development, you can only install it from this repository.
You will want to do the following steps::

    $ git clone https://github.com/glue-viz/glue-solar.git

Then change directory to glue-solar and install with::

    pip install -e .

This will auto-register the plugin with glue and install everything needed to run this plugin (including glue).

Using
-----

At the moment, this plugin provides a reader for solar data, you can give glue some solar data file in the FITS format.
For example, you can start glue by using::

    glue mydata.fits

and you can also load files from inside glue.
