# PyInstaller spec of Glue Solar.app: glue with glue-solar, irispy and sunpy on PyQt6, for macOS. It follows
# glue-viz/glue-standalone-apps' glue_app.spec and hooks; build_app.sh builds it (docs/dev_guide/macos-app.rst).
import importlib.metadata
import importlib.resources
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# The metadata of glue-solar and of what it needs: glue finds its plugins by their entry points, and packages read their
# versions
datas, hiddenimports = copy_metadata("glue-solar", recursive=True), []
# glue imports its plugins' modules by name, which PyInstaller does not follow
for package in ("glue", "glue_qt", "glue_solar"):
    hiddenimports += collect_submodules(package, filter=lambda name: not {"tests", "conftest"} & {*name.split(".")})
# Data files that PyInstaller's own hooks leave out: glue's, asdf's schemas, which astropy reads as it imports
# asdf-astropy, and irispy's response files, without its test files
for package in ("glue", "glue_qt", "glue_solar", "asdf", "irispy"):
    datas += collect_data_files(package, excludes=["**/tests/", "data/test/"])

a = Analysis(
    [os.path.join(SPECPATH, "start_glue_solar.py")],
    datas=datas,
    hiddenimports=hiddenimports,
    hooksconfig={"matplotlib": {"backends": "all"}},  # Save takes each format from its backend
    excludes=["tkinter", "PyQt5", "PySide2", "PySide6"],  # PyQt6 only: glue-solar refuses Qt 5
)
exe = EXE(PYZ(a.pure), a.scripts, exclude_binaries=True, name="glue-solar", console=False)
app = BUNDLE(
    COLLECT(exe, a.binaries, a.datas, name="glue-solar"),
    name="Glue Solar.app",
    icon=str(importlib.resources.files("glue") / "icons" / "app_icon.png"),  # glue's own, made .icns by PyInstaller
    bundle_identifier="org.sunpy.glue-solar",
    version=importlib.metadata.version("glue-solar"),
)
