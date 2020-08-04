.. _users_guide:

============
User's Guide
============

Requirements
------------
For the requirements of glue, please refer to their official documentation on
`installing and running glue <http://docs.glueviz.org/en/stable/installation/installation.html>`__.

For glue-solar, the basic requirements for installation are:

* ``astropy``
* ``glue-core``
* ``sunpy``
* ``ndcube``
* ``sunraster``
* ``reproject``
* ``dask[array]``

Installing and Running Glue with Glue-solar
-------------------------------------------
In order to use glue with the glue-solar plugin, you will need to have both packages
installed on your computer. For the time being before an official release, the only way to install
glue-solar is to download with GitHub, where the repository for the package is hosted.

To download the entire glue-solar repository locally, first make sure you have Git installed
locally, then to clone over HTTPS do::

    git clone https://github.com/glue-viz/glue-solar.git

After that, change directory (cd) to glue-solar::

    cd glue-solar

Finally, do the following while at the root (highest level) of the glue-solar directory::

    pip install -e .

This is assuming that you already have ``pip``, the Python standard package-management system installed.

Started up Glue
---------------
Once both glue and glue-solar have been properly installed, to start the application via the command line do::

    glue

This should launch the glue graphcial user interface (GUI) on your computer from the terminal. If you have run
into any problems when launching, you can use the verbose ``-v`` flag together with the above to print the verbose
output to console. This will help diagnose what issues you are having and help with troubleshooting::

    glue -v

As per usual, the help ``-h`` option is available for you to get additional information on the usage of glue as well
as all the options you can use::

    glue -h

On Windows operating systems, installation creates an executable ``glue.exe`` file within the python script directory
(e.g., ``C:\Python37\Scripts``). Windows users can create a desktop shortcut for this file upon installation,
and run Glue by double clicking on the icon instead.

At this point you should be able to use the functionality offered by both glue and glue-solar.

User Interface Guide
--------------------
For a walk through of the user interface of glue, please refer to the
`Getting Started <http://docs.glueviz.org/en/stable/getting_started/index.html>`__ section of the official glue
documentation. There, you will be provided with a sample file to visualize and get acquainted with the GUI.
