.. _glue_solar_dev_docs_macos_app:

======================
Building the macOS app
======================

``packaging/macos/`` builds ``Glue Solar.app``: glue with glue-solar, irispy's git main and sunpy on PyQt6, for Apple
silicon, and ``Glue Solar.dmg``, which holds the app beside a link to ``/Applications``. Its spec ``glue_solar.spec``
and the PyInstaller hooks in ``hooks/``, which add the modules, data files and package metadata PyInstaller misses, are
adapted from those of `glue-standalone-apps <https://github.com/glue-viz/glue-standalone-apps>`__, glue's own
installers, with the glue team's permission. ``start_glue_solar.py`` is the entry point, which runs glue's ``glue``
command, ``icon.png`` the app's icon and ``build_app.sh`` the build.

The app is not signed with a Developer ID or notarized; PyInstaller signs it ad hoc, as Apple silicon needs. It is
for the Mac it is built on: macOS opens it from a disk image built there, but blocks a copy that was downloaded or
sent, which it marks as quarantined, until the mark is removed with
``xattr -dr com.apple.quarantine "/Applications/Glue Solar.app"``.

The environment
---------------

Build in a new micromamba environment holding only what the app needs, as PyInstaller takes in whatever the code
imports. glue-qt, irispy and fiasco come from pip without their dependencies, which come from conda-forge, where
``qtconsole-base`` stands in for ``qtconsole``, which brings PyQt5. irispy is pinned to the commit glue-solar is
tested against: move the pin with each irispy update, and replace it with a version once irispy releases. glue-solar
is installed from the checkout as a package, not editable::

    micromamba create -y -n glue-solar-app -c conda-forge python=3.13 pyinstaller pyqt6=6.11 qtpy qtconsole-base \
        glue-core=1.27.0 astropy=8.0.1 sunpy=8.0.0 ndcube "dask>=2024.7" sunraster dkist gwcs scipy mpl_animators \
        filelock ipykernel "ipython<9" pvextractor plasmapy h5py fortranformat ffmpeg pip
    micromamba run -n glue-solar-app pip install --no-deps glue-qt==0.4.2 \
        "irispy-lmsal @ git+https://github.com/LM-SAL/irispy.git@8c220d49481b0643e612e71ec2af0875c3c7ca69" \
        "fiasco @ git+https://github.com/wtbarnes/fiasco.git"
    micromamba run -n glue-solar-app pip install --no-deps .

Install glue-solar again after each change to the checkout. The app holds no PyQt5, PySide or tkinter. It holds
fiasco, which glue-solar's ``density`` extra adds, so the line ratio diagnostic offers its O IV preset; as outside the
app, fiasco downloads and builds the CHIANTI database in ``~/.fiasco`` on its first use (see
:ref:`glue_solar_users_guide_iris_line_moments`). It holds the environment's ffmpeg, which ``start_glue_solar.py``
puts first on the ``PATH``, so that movies save as MP4 in an app opened from the Finder, which gives it no shell
``PATH``. Of matplotlib's backends it holds QtAgg and those that Save takes PNG, PDF, SVG, EPS and PS from: Save
still lists PGF, which needs LaTeX and fails with "No module named". The spec leaves out botocore, pyarrow, bokeh and
distributed, which conda-forge's dask and astropy bring for cloud storage, Parquet, dashboards and clusters, none of
which glue-solar uses; ``dask-core`` and ``astropy-base`` would not keep them out, as the reproject and spectral-cube
that sunpy and pvextractor need depend on the full packages.

Building
--------

From the checkout::

    micromamba run -n glue-solar-app packaging/macos/build_app.sh

It takes about 2 minutes and writes ``packaging/macos/dist/Glue Solar.dmg``, about 300 MB, and the app it holds in
``packaging/macos/dist/app``, about 585 MB. Both folders, ``build`` and ``dist``, are left out of git and the source
distribution.

Checking the app
----------------

``smoke.py`` checks a built app without showing it: run with ``GLUE_SOLAR_APP_CHECK`` naming it, the app runs it in
place of glue (glue's own ``-x`` fails in glue-qt 0.4.2). It starts glue, checks glue-solar's menu entries and glue's
IPython terminal, that fiasco has the line_ratio of the O IV preset, that sunpy.map finds its extra dependencies and
that matplotlib runs the bundled ffmpeg and saves a two-frame MP4 through it, opens the quicklook of the files it is
given, adds irispy's radiometric calibration of the raster, which needs irispy's response files, saves and restores
the session, which needs asdf's schemas, and exits 1 at the first failure::

    T=$(micromamba run -n glue-solar-app python -c "import irispy.data.test as t; print(t.ROOTDIR)")/sns
    env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen GLUE_SOLAR_APP_CHECK=packaging/macos/smoke.py \
        "packaging/macos/dist/app/Glue Solar.app/Contents/MacOS/glue-solar" $T/*raster*.fits $T/*SJI_1400*.fits

To check it as the Finder opens it, start it with ``open`` and the ``PATH`` the Finder gives apps, since ``open``
would pass the shell's. The app's window shows meanwhile; what the check prints goes to the two files, and a
traceback there says what failed::

    H=$(mktemp -d)
    open -n -W --env PATH=/usr/bin:/bin:/usr/sbin:/sbin --env HOME="$H" \
        --env GLUE_SOLAR_APP_CHECK="$PWD/packaging/macos/smoke.py" --stdout "$H/out.txt" --stderr "$H/err.txt" \
        "packaging/macos/dist/app/Glue Solar.app" --args $T/*raster*.fits $T/*SJI_1400*.fits
    cat "$H/out.txt" "$H/err.txt"

``open -a "packaging/macos/dist/app/Glue Solar.app" session.glu`` sends the app the open-document event that a
double-click in the Finder or a drop on its Dock icon sends. macOS registers the document types of a built app as it
finds it: unregister a build before deleting it, so that sessions do not keep opening a deleted app::

    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
        -u "packaging/macos/dist/app/Glue Solar.app"

Installing
----------

Open ``Glue Solar.dmg`` in the Finder, drag ``Glue Solar`` onto ``Applications`` and eject the disk image. Glue Solar
then opens from the Applications folder or Launchpad, and **Plugins → IRIS: browse observations…** opens an
observation's quicklook.

A session (``.glu``) double-clicked in the Finder opens in Glue Solar; where glue's own app is installed too, **Open
With** chooses between them. FITS files (``.fits``, ``.fit``, ``.fts``) keep their default app and open in Glue Solar
from **Open With**; dropped on its icon in the Dock or the Finder, they open in it, gzipped ones too. PyInstaller's argv
emulation makes the files that start the app glue's command line, so only those open: a file opened while Glue Solar
runs is ignored, and opens with **File → Open Data Set** or **File → Open Session** instead.
