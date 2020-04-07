Experimental Solar Physics plugin for glue
==========================================

.. image:: https://dev.azure.com/glue-viz/glue-solar/_apis/build/status/glue-viz.glue-solar?branchName=master
   :target: https://dev.azure.com/glue-viz/glue-solar/_build/

Requirements
------------

Note that this plugin requires `glue <http://glueviz.org/>`_ to be installed - see this
`page <http://glueviz.org/install.html>`_ for instructions on installing glue.

Installing
----------

If you are using pip, you can easily install this plugin and its required dependencies by first cloning
the repo with::

    git clone https://github.com/glue-viz/glue-solar.git

Then change directory to glue-solar and install with::

    pip install -e .

This will auto-register the plugin with glue.

Using
-----

At the moment, this plugin provides a reader for solar data. You can
give glue some solar data file (e.g. SJI, rasters) in the FITS format for slit-jaw and spectrograph files.
For example, you can start glue by using::

    glue mydata.fits

and you can also load files from inside glue.

Testing
-------
To run the tests, do::

    py.test glue_solar

at the root of the repository. This requires the
`pytest <http://pytest.org>`__ module to be installed.