"""
A reader for IRIS data.
"""

from glue.config import data_factory, importer, qglue_parser
from glue.core.component import Component
from glue.core.coordinates import WCSCoordinates
from glue.core.data import Data
from glue.core.data_factories import is_fits
from glue.core.visual import VisualAttributes
from irispy.io import read_files
from irispy.spectrograph import IRISSpectrogramCube
from qtpy import QtWidgets

from .loaders.iris import QtIRISImporter

__all__ = ["import_iris", "read_iris_raster", "_parse_iris_raster"]


@qglue_parser(IRISSpectrogramCube)
def _parse_iris_raster(data, label):
    """
    Parse IRIS Level 2 raster files so that it can be loaded by glue.
    """
    w_data = None
    for window, window_data in data.items():
        for i, scan_data in enumerate(window_data):
            w_data = Data(
                label=f"{window.replace(' ', '_')}-{scan_data.meta['OBSID']}-scan-{i}"
            )
            w_data.coords = WCSCoordinates(scan_data.wcs.to_header())
            w_data.add_component(
                Component(scan_data.data),
                f"{window.replace(' ', '_')}-{scan_data.meta['OBSID']}-scan-{i}",
            )
            w_data.meta = scan_data.meta
            w_data.style = VisualAttributes(color="#5A4FCF")
    return w_data


@data_factory("IRIS Spectrograph", is_fits)
def read_iris_raster(raster_file):
    """
    To read Raster data as contained in IRIS level 2 raster fits files.
    """
    raster_data = _parse_iris_raster(
        read_files(raster_file, uncertainty=False, memmap=False),
        label="iris",
    )
    return raster_data


def pick_directory(caption):
    dialog = QtWidgets.QFileDialog(caption=caption)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    directory = dialog.exec_()
    if directory == QtWidgets.QDialog.Rejected:
        return []
    directory = dialog.selectedFiles()
    return directory[0]


@importer("Import IRIS OBS Directory")
def import_iris():
    """
    To import IRIS raster and SJI fits files for the same observation from directory.
    """
    caption = "Select a directory containing files from one IRIS OBS."
    directory = pick_directory(caption)
    wi = QtIRISImporter(directory)
    wi.exec_()
    return wi.datasets
