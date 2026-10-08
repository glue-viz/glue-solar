"""
IRIS Level 2 support: a file reader for File -> Open, and the observation browser.
"""

import re
from pathlib import Path

from glue.config import data_factory, layer_artist_maker, menubar_plugin, startup_action
from glue.viewers.image.viewer import MatplotlibImageMixin
from qtpy import QtCore, QtGui, QtWidgets

from glue_solar.quicklook import _pick_sjis, _pick_windows, _role, _time_axis, observation_key, quicklook
from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, keep_hpc_linked, last_directory
from glue_solar.sources.loaders.scan import _is_supported_file, _primary_header, strip_pooch

__all__ = [
    "browse_iris",
    "help_iris",
    "iris_image_layer",
    "iris_quicklook",
    "link_iris",
    "quicklook_iris",
    "read_iris_file",
]


def is_iris_fits(filename, **_kwargs):
    """An IRIS file, or an aligned AIA cutout as the observation browser takes it, whose TELESCOP is blank."""
    try:
        header = _primary_header(filename)
    except (OSError, ValueError, EOFError):  # not a FITS file
        return False
    return header.get("TELESCOP") == "IRIS" or _is_supported_file(strip_pooch(Path(filename).name), header)


@data_factory("IRIS Level 2 FITS", is_iris_fits, priority=200)  # glue's own "FITS file" is 100
def read_iris_file(file_path):
    """
    Read one IRIS Level 2 file: an SJI cube, an aligned AIA cutout, or every spectral window of a raster file.
    """
    return iris_data(file_path)


@layer_artist_maker("IRIS: transparent NaN pixels")
def iris_image_layer(viewer, data):
    """
    Give image layers of IRIS datasets transparent NaN pixels, as matplotlib draws them.

    glue's default paints NaN opaque in the colormap's "bad" colour, black for the IRIS
    colormaps, so gaps and off-detector areas look like dark data.
    """
    if not isinstance(viewer, MatplotlibImageMixin) or "OBSID" not in getattr(data, "meta", {}):
        return None  # not an image viewer, a subset, or not an IRIS dataset: glue's default artist
    artist = viewer.get_data_layer_artist(data)
    if hasattr(artist.state, "cmap_bad"):
        artist.state.cmap_bad = (0, 0, 0, 0)
    return artist


@menubar_plugin("IRIS: browse observations…")
def browse_iris(session, data_collection):
    """
    Browse a folder by observation, load the selection and link its helioprojective coordinates.

    With "Open quicklook" ticked, each loaded observation opens as a quicklook of its ticked raster
    windows: Mg II k 2796 if ticked, else the first, with the others beside it; otherwise, or with no
    raster or slit-jaw image loaded, the first image opens in an Image Viewer.
    """
    app = session.application
    directory = QtWidgets.QFileDialog.getExistingDirectory(
        app, "Select a folder containing IRIS Level 2 files", last_directory()
    )
    if not directory:
        return
    dialog = QtIRISImporter(directory, parent=app, shown=_shown)
    if dialog.exec() != QtWidgets.QDialog.Accepted or not dialog.datasets:
        return
    # not app.add_datasets: its autolinker would ask about WCS links in a dialog before the quicklook
    # opens (with glue-viz/glue#2595), and keep_hpc_linked links IRIS datasets
    data_collection.extend(dialog.datasets)
    keep_hpc_linked(data_collection)
    quicklooks = _quicklooks(dialog.loaded) if dialog.quicklook.isChecked() else []
    for datasets, window in quicklooks:
        quicklook(app, datasets, window=window)
    if not quicklooks and dialog.first_image is not None:
        from glue_qt.viewers.image import ImageViewer

        app.new_data_viewer(ImageViewer, data=dialog.first_image)


def _quicklooks(loaded):
    """The ``(datasets, window)`` of each quicklook `browse_iris` opens of the observation browser's ``loaded``."""
    observations = {}  # observation -> (its datasets, its ticked raster windows)
    for observation, kind, name, datasets in loaded:
        got, windows = observations.get(id(observation), ([], []))
        observations[id(observation)] = (got + datasets, windows + [name] * (kind == "raster"))
    return [
        (datasets, windows or None)
        for datasets, windows in observations.values()
        if any(data.meta.get("INSTRUME") in ("SPEC", "SJI") for data in datasets)
    ]


def _shown(loaded, quicklooks):
    """
    The datasets of the observation browser's ``loaded`` that the first viewers `browse_iris` opens show: the raster,
    the other windows with a wavelength panel and the slit-jaw images of each quicklook, with ``quicklooks`` on, else
    the first image.
    """
    quicklooks = _quicklooks(loaded) if quicklooks else []
    if not quicklooks:
        return [datasets[0] for _, kind, _, datasets in loaded if kind != "raster"][:1]
    shown = []
    for datasets, window in quicklooks:
        rasters = [data for data in datasets if _role(data) == "raster"]
        if rasters:
            raster, others = _pick_windows(rasters, window)
            shown += [raster] + [data for data in others if _time_axis(data) is not None]
        shown += _pick_sjis([data for data in datasets if _role(data) == "sji"])[0]
    return shown


@menubar_plugin("IRIS: link helioprojective coordinates")
def link_iris(session, data_collection):
    """
    Link the helioprojective longitude and latitude of every loaded IRIS dataset and sunpy map.

    Selections then carry over between slit-jaw images, rasters, aligned AIA cutouts and sunpy maps
    through their world coordinates. The observation browser does this when it loads data, and the
    links are kept when a dataset is removed.
    """
    keep_hpc_linked(data_collection)


def _observations(data_collection):
    """The datasets of ``data_collection`` by IRIS observation, in the collection's order."""
    observations = {}
    for data in data_collection:
        key = observation_key(data)
        if key is not None:
            observations.setdefault(key, []).append(data)
    return observations


@menubar_plugin("IRIS: quicklook…")
def quicklook_iris(session, data_collection):
    """
    Open the quicklook of an IRIS observation that is already loaded, asking which when several are.
    """
    app = session.application
    observations = _observations(data_collection)
    if not observations:
        QtWidgets.QMessageBox.information(app, "IRIS quicklook", "No IRIS observation is loaded.")
        return
    keys = list(observations)
    labels = [f"{obsid} {str(start)[:19]}" for obsid, start in keys]
    if len(keys) > 1:
        label, chosen = QtWidgets.QInputDialog.getItem(app, "IRIS quicklook", "Observation:", labels, 0, False)
        if not chosen:
            return
        keys = [keys[labels.index(label)]]
    quicklook(app, observations[keys[0]])


@menubar_plugin("IRIS: user guide and issues")
def help_iris(session, data_collection):
    """
    Open glue-solar's user guide and its issues on GitHub, to report a problem, in the web browser.
    """
    for url in (
        "https://glue-solar.readthedocs.io/en/latest/user_guide/index.html",
        "https://github.com/glue-viz/glue-solar/issues",
    ):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))


@startup_action("iris_quicklook")
def iris_quicklook(session, data_collection):
    """
    ``glue --startup=iris_quicklook <files>``: a quicklook of each IRIS observation among the files.

    Files given on the command line load one by one and cannot be stacked, so each observation
    opens on its first raster file (the lowest ``rNNNNN``); stacks of scans need the observation
    browser.
    """
    app = session.application
    several = False
    for datasets in _observations(data_collection).values():
        numbers = sorted({_raster_number(data) for data in datasets} - {None})
        several |= len(numbers) > 1
        first = numbers[0] if numbers else None
        quicklook(app, [data for data in datasets if _raster_number(data) in (None, first)])
    if several:
        note = "Only the first raster file is shown: stacks of scans need Plugins → IRIS: browse observations…"
        app.statusBar().showMessage(f"{app.statusBar().currentMessage()} {note}".strip())


def _raster_number(data):
    """The ``rNNNNN`` of a raster window loaded from one file, else None."""
    match = re.search(r"-r(\d{5})$", data.label)
    return match.group(1) if match else None
