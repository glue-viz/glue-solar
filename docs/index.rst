.. _glue-solar-index:

========================
glue-solar documentation
========================

``glue-solar`` provides solar physics functionality to `glue <https://glueviz.org>`__, for multi-instrument interactive visualization.

Installing
----------

glue-solar needs Python 3.13 or later and Git. The steps below install both, and are the same on Windows, macOS and
Linux after the first. glue-solar has no release yet, so it installs from its repository on GitHub.

1. Install `Miniforge <https://conda-forge.org/download/>`__, which gives you Python and the ``conda`` command. If you
   have conda or mamba already, skip this step.

   - **Windows:** download ``Miniforge3-Windows-x86_64.exe`` from that page and run it, keeping its choices as they
     are. Then open "Miniforge Prompt" from the Start menu. Type the commands of the next steps there.
   - **macOS and Linux:** download the installer for your computer from that page. Open a terminal in the folder it
     is in, usually ``Downloads``, and run::

         bash Miniforge3-$(uname)-$(uname -m).sh

     Answer ``yes`` when it asks to initialize conda. Then close the terminal and open a new one.

2. Make an environment for glue-solar, with Python and Git in it, and activate it::

       conda create -n glue-solar python=3.13 git
       conda activate glue-solar

3. Install glue-solar. This downloads glue and everything else it needs::

       pip install git+https://github.com/glue-viz/glue-solar.git

4. Start glue::

       glue

   glue-solar is loaded if the "Plugins" menu has "Browse observations…". Go on to :ref:`Getting started
   <glue_solar_users_guide_getting_started>`.

Each time you open a new terminal, or a new Miniforge Prompt on Windows, run ``conda activate glue-solar`` before
``glue``. To update glue-solar, run step 3 again with ``--upgrade`` after ``install``.

If you already have Python 3.13 or later and Git, a ``venv`` in place of steps 1 and 2 works as well.

The O IV density preset of the line ratio diagnostic needs one more package, fiasco, which downloads a few GB of
atomic data on its first use. To have it, use this in step 3::

    pip install "glue-solar[density] @ git+https://github.com/glue-viz/glue-solar.git"

To change glue-solar's code, install it from a clone in step 3::

    git clone https://github.com/glue-viz/glue-solar.git
    cd glue-solar
    pip install -e .

.. toctree::
   :maxdepth: 2

   user_guide/index
   dev_guide/index
   api_reference
   whatsnew/index
