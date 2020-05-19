"""
A reader for IRIS data.
"""
from pathlib import Path

from qtpy import QtWidgets

from astropy.io import fits

from glue.config import data_factory, importer, qglue_parser
from glue.core import Component, Data
from glue.core.data_factories import load_data
from glue.core.coordinates import WCSCoordinates
from sunraster.io.iris import read_iris_spectrograph_level2_fits
from sunraster import SpectrogramCube

from .stack_spectrograms import stack_spectrogram_sequence
from .iris_loader import QtIRISImporter


__all__ = ['import_iris', 'read_iris_raster', '_parse_iris_raster']


@qglue_parser(SpectrogramCube)
def _parse_iris_raster(data, label):
    result = []
    for window, window_data in data.items():
        for i, scan_data in enumerate(window_data):
            w_data = Data(label=f"{window.replace(' ', '_')}-scan-{i}")
            w_data.coords = scan_data.wcs
            w_data.add_component(Component(scan_data.data),
                                 f"{window}-scan-{i}")
            w_data.meta = scan_data.meta
            result.append(w_data)
    return result


def is_fits(filename, **kwargs):
    return filename.endswith('.fits')


@data_factory('IRIS Spectrograph', is_fits)
def read_iris_raster(raster_file):
    raster_data = _parse_iris_raster(read_iris_spectrograph_level2_fits(raster_file, uncertainty=False, memmap=True), 'iris')
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
    caption = "Select a directory containing files from one IRIS OBS."
    directory = pick_directory(caption)

    wi = QtIRISImporter(directory)
    wi.exec_()
    return wi.datasets
