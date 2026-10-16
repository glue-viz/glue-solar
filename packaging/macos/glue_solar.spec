# PyInstaller spec of Glue Solar.app: glue with glue-solar, irispy and sunpy on PyQt6, for macOS. It and hooks/, which
# adds what PyInstaller misses, are adapted from glue-viz/glue-standalone-apps' glue_app.spec and hooks (4e35d18), used
# with the glue team's permission; build_app.sh builds it (docs/dev_guide/macos-app.rst).
import importlib.metadata
import os
import sys

a = Analysis(
    [os.path.join(SPECPATH, "start_glue_solar.py")],
    # ffmpeg, which matplotlib saves MP4 movies with, in a folder that start_glue_solar.py puts on the PATH
    binaries=[(os.path.join(sys.prefix, "bin", "ffmpeg"), "bin")],
    hiddenimports=["glue_solar"],  # which glue finds by its entry point
    hookspath=[os.path.join(SPECPATH, "hooks")],
    # QtAgg, and the backends Save takes PNG (Agg), PDF, SVG, EPS and PS (PS) from
    hooksconfig={"matplotlib": {"backends": ["QtAgg", "PDF", "SVG", "PS"]}},
    # PyQt6 only, as glue-solar refuses Qt 5; no debugpy, ipykernel's debugger, whose vendored pydevd PyInstaller leaves
    # out, which breaks glue's terminal; and none of what conda-forge's dask and astropy bring for cloud storage,
    # Parquet, dashboards or clusters
    excludes=["tkinter", "PyQt5", "PySide2", "PySide6", "debugpy", "botocore", "pyarrow", "bokeh", "distributed"],
)
# argv_emulation: the files the Finder or the Dock open the app with become glue's command line, as it starts
exe = EXE(PYZ(a.pure), a.scripts, exclude_binaries=True, name="glue-solar", console=False, argv_emulation=True)
app = BUNDLE(
    COLLECT(exe, a.binaries, a.datas, name="glue-solar"),
    name="Glue Solar.app",
    icon=os.path.join(SPECPATH, "icon.png"),  # its own, made .icns by PyInstaller
    bundle_identifier="org.glueviz.glue-solar",
    version=importlib.metadata.version("glue-solar"),
    # Sessions open in the app when double-clicked, ranked below glue's own app, their owner; FITS files keep their
    # default app and open in it from Open With or dropped on it, gzipped ones (any .gz) dropped on it only
    info_plist={
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Glue Session Files",
                "CFBundleTypeExtensions": ["glu"],
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Default",
            },
            {
                "CFBundleTypeName": "FITS File",
                "CFBundleTypeExtensions": ["fits", "fit", "fts"],
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
            },
            {
                "CFBundleTypeName": "Gzip Archive",
                "LSItemContentTypes": ["org.gnu.gnu-zip-archive"],
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "None",
            },
        ]
    },
)
