# PyInstaller spec of Glue Solar.app: glue with glue-solar, irispy and sunpy on PyQt6, for macOS. It follows
# glue-viz/glue-standalone-apps' glue_app.spec and hooks; build_app.sh builds it (docs/dev_guide/macos-app.rst).
import importlib.metadata
import importlib.resources
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# The metadata of glue-solar and of what it needs, and of fiasco, of its density extra, which copy_metadata does not
# follow: glue finds its plugins by their entry points, and packages read their versions
datas = copy_metadata("glue-solar", recursive=True) + copy_metadata("fiasco", recursive=True)
hiddenimports = []
# glue imports its plugins' modules by name, which PyInstaller does not follow
for package in ("glue", "glue_qt", "glue_solar"):
    hiddenimports += collect_submodules(package, filter=lambda name: not {"tests", "conftest"} & {*name.split(".")})
# Data files that PyInstaller's own hooks leave out: glue's, asdf's schemas, which astropy reads as it imports
# asdf-astropy, irispy's response files, fiasco's tables and plasmapy's particle data, without their test files
for package in ("glue", "glue_qt", "glue_solar", "asdf", "irispy", "fiasco", "plasmapy"):
    datas += collect_data_files(package, excludes=["**/tests/", "data/test/"])

a = Analysis(
    [os.path.join(SPECPATH, "start_glue_solar.py")],
    # ffmpeg, which matplotlib saves MP4 movies with, in a folder that start_glue_solar.py puts on the PATH
    binaries=[(os.path.join(sys.prefix, "bin", "ffmpeg"), "bin")],
    datas=datas,
    hiddenimports=hiddenimports,
    # QtAgg, and the backends Save takes PNG (Agg), PDF and SVG from
    hooksconfig={"matplotlib": {"backends": ["QtAgg", "PDF", "SVG"]}},
    # PyQt6 only, as glue-solar refuses Qt 5; no debugpy, ipykernel's debugger, whose vendored pydevd PyInstaller leaves
    # out, which breaks glue's terminal; and none of what conda-forge's dask and astropy bring for cloud storage,
    # Parquet, dashboards or clusters
    excludes=["tkinter", "PyQt5", "PySide2", "PySide6", "debugpy", "botocore", "pyarrow", "bokeh", "distributed"],
)
exe = EXE(PYZ(a.pure), a.scripts, exclude_binaries=True, name="glue-solar", console=False)
app = BUNDLE(
    COLLECT(exe, a.binaries, a.datas, name="glue-solar"),
    name="Glue Solar.app",
    icon=str(importlib.resources.files("glue") / "icons" / "app_icon.png"),  # glue's own, made .icns by PyInstaller
    bundle_identifier="org.sunpy.glue-solar",
    version=importlib.metadata.version("glue-solar"),
)
