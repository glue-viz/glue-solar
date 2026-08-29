"""
IRIS Level 2 support: a file reader for File -> Open, and the observation browser.
"""

from glue.config import data_factory, menubar_plugin
from qtpy import QtWidgets

from astropy.io import fits

from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, last_directory

__all__ = ["browse_iris", "read_iris_file"]


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
