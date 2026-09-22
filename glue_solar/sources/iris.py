"""
IRIS Level 2 support: a file reader for File -> Open, and the observation browser.
"""

from glue.config import data_factory, layer_artist_maker, menubar_plugin
from glue.viewers.image.viewer import MatplotlibImageMixin
from qtpy import QtWidgets

from astropy.io import fits

from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, last_directory

__all__ = ["browse_iris", "iris_image_layer", "read_iris_file"]


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
    Browse a folder by observation, load the selection and open the first image in an Image Viewer.
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
    app.add_datasets(dialog.datasets)
    if dialog.first_image is not None:
        from glue_qt.viewers.image import ImageViewer

        app.new_data_viewer(ImageViewer, data=dialog.first_image)
