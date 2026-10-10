.. _glue_solar_dev_docs_macos_app:

======================
Building the macOS app
======================

``packaging/macos/`` builds ``Glue Solar.app``: glue with glue-solar, irispy's git main and sunpy on PyQt6, for
Apple silicon, and ``Glue Solar.dmg``, which holds the app beside a link to ``/Applications``. It follows the
PyInstaller recipe of `glue-standalone-apps <https://github.com/glue-viz/glue-standalone-apps>`__, glue's own
installers, with the spec ``glue_solar.spec``, the entry point ``start_glue_solar.py``, which runs glue's ``glue``
command, and ``build_app.sh``.

The app is not signed with a Developer ID or notarized; PyInstaller signs it ad hoc, as Apple silicon needs. It is
for the Mac it is built on: macOS opens it from a disk image built there, but blocks a copy that was downloaded or
sent, which it marks as quarantined, until the mark is removed with
``xattr -dr com.apple.quarantine "/Applications/Glue Solar.app"``.

The environment
---------------

Build in a new micromamba environment holding only what the app needs, as PyInstaller takes in whatever the code
imports. glue-qt and irispy come from pip without their dependencies, which come from conda-forge, where
``qtconsole-base`` stands in for ``qtconsole``, which brings PyQt5. glue-solar is installed from the checkout as a
package, not editable::

    micromamba create -y -n glue-solar-app -c conda-forge python=3.13 pyinstaller pyqt6=6.11 qtpy qtconsole-base \
        glue-core=1.27.0 astropy=8.0.1 sunpy=8.0.0 ndcube "dask>=2024.7" sunraster dkist gwcs scipy mpl_animators \
        filelock ipykernel "ipython<9" pvextractor pip
    micromamba run -n glue-solar-app pip install --no-deps glue-qt==0.4.2 \
        "irispy-lmsal @ git+https://github.com/LM-SAL/irispy.git"
    micromamba run -n glue-solar-app pip install --no-deps .

Install glue-solar again after each change to the checkout. The app holds no PyQt5, PySide or tkinter, and not
fiasco, which glue-solar's ``density`` extra adds, or ffmpeg: opened from the Finder, it saves movies as GIF, not
MP4.

Building
--------

From the checkout::

    micromamba run -n glue-solar-app packaging/macos/build_app.sh

It takes about 2.5 minutes and writes ``packaging/macos/dist/Glue Solar.dmg``, about 350 MB, and the app it holds in
``packaging/macos/dist/app``, about 720 MB. Both folders, ``build`` and ``dist``, are left out of git and the source
distribution.

Checking the app
----------------

``smoke.py`` checks a built app without showing it: run with ``GLUE_SOLAR_APP_CHECK`` naming it, the app runs it in
place of glue (glue's own ``-x`` fails in glue-qt 0.4.2). It starts glue, checks glue-solar's menu entries, opens the
quicklook of the files it is given, adds irispy's radiometric calibration of the raster, which needs irispy's response
files, and exits 1 at the first failure::

    T=$(micromamba run -n glue-solar-app python -c "import irispy.data.test as t; print(t.ROOTDIR)")/sns
    env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen GLUE_SOLAR_APP_CHECK=packaging/macos/smoke.py \
        "packaging/macos/dist/app/Glue Solar.app/Contents/MacOS/glue-solar" $T/*raster*.fits $T/*SJI_1400*.fits

Installing
----------

Open ``Glue Solar.dmg`` in the Finder, drag ``Glue Solar`` onto ``Applications`` and eject the disk image. Glue Solar
then opens from the Applications folder or Launchpad, and **Plugins → IRIS: browse observations…** opens an
observation's quicklook.
