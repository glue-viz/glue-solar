"""
IRIS Level 2 support: a file reader for File -> Open, and the observation browser.
"""

import re

from glue.config import data_factory, layer_artist_maker, menubar_plugin, startup_action
from glue.viewers.image.viewer import MatplotlibImageMixin
from qtpy import QtWidgets

from astropy.io import fits

from glue_solar.quicklook import observation_key, quicklook
from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, keep_hpc_linked, last_directory

__all__ = ["browse_iris", "iris_image_layer", "iris_quicklook", "link_iris", "quicklook_iris", "read_iris_file"]


def is_iris_fits(filename, **_kwargs):
    try:
        return fits.getheader(filename).get("TELESCOP") == "IRIS"
    except OSError:
        return False


@data_factory("IRIS Level 2 FITS", is_iris_fits, priority=200)  # glue's own "FITS file" is 100
def read_iris_file(file_path):
    """
    Read one IRIS Level 2 file: an SJI cube, or every spectral window of a raster file.
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

    With "Open quicklook" ticked, each loaded observation opens as a quicklook, of the raster window
    ticked when only one was; otherwise, or with no raster or slit-jaw image loaded, the first image
    opens in an Image Viewer.
    """
    app = session.application
    directory = QtWidgets.QFileDialog.getExistingDirectory(
        app, "Select a folder containing IRIS Level 2 files", last_directory()
    )
    if not directory:
        return
    dialog = QtIRISImporter(directory, parent=app)
    if dialog.exec() != QtWidgets.QDialog.Accepted or not dialog.datasets:
        return
    # not app.add_datasets: its autolinker would ask about WCS links in a dialog before the quicklook
    # opens (with glue-viz/glue#2595), and keep_hpc_linked links IRIS datasets
    data_collection.extend(dialog.datasets)
    keep_hpc_linked(data_collection)
    if dialog.quicklook.isChecked():
        observations = {}  # observation -> (its datasets, its ticked raster windows)
        for observation, kind, name, datasets in dialog.loaded:
            loaded, windows = observations.get(id(observation), ([], []))
            observations[id(observation)] = (loaded + datasets, windows + [name] * (kind == "raster"))
        opened = False
        for datasets, windows in observations.values():
            if any(data.meta.get("INSTRUME") in ("SPEC", "SJI") for data in datasets):
                # one ticked window is the one to show; with several the quicklook's default applies
                quicklook(app, datasets, window=windows[0] if len(windows) == 1 else None)
                opened = True
        if opened:
            return
    if dialog.first_image is not None:
        from glue_qt.viewers.image import ImageViewer

        app.new_data_viewer(ImageViewer, data=dialog.first_image)


@menubar_plugin("IRIS: link helioprojective coordinates")
def link_iris(session, data_collection):
    """
    Link the helioprojective longitude and latitude of every loaded IRIS dataset.

    Selections then carry over between slit-jaw images, rasters and aligned AIA cutouts through
    their world coordinates. The observation browser does this when it loads data, and the links
    are kept when a dataset is removed.
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
