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
from irispy.spectrograph import (IRISSpectrograph,
                                 read_iris_spectrograph_level2_fits)

from .stack_spectrograms import stack_spectrogram_sequence


@qglue_parser(IRISSpectrograph)
def _parse_iris_raster(data, label):
    result = []
    for window, window_data in data.data.items():
        for i, scan_data in enumerate(window_data):
            w_data = Data(label=f"{window.replace(' ', '_')}-scan-{i}")
            w_data.coords = WCSCoordinates(wcs=scan_data.wcs)
            w_data.add_component(Component(scan_data.data),
                                 f"{window}-scan-{i}")
            w_data.meta = scan_data.meta
            result.append(w_data)
    return result


def load_sji_fits(filename):
    with fits.open(filename) as hdul:
        hdul.verify("fix")
        sji = hdul[0]
        label = sji.header['TDESC1']
        data = Data(label=label)
        data.coords = WCSCoordinates(sji.header)
        data.meta = sji.header
        data.add_component(Component(sji.data), label)

    return data


def is_fits(filename, **kwargs):
    return filename.endswith('.fits')


@data_factory('IRIS Spectrograph', is_fits)
def read_iris_raster(raster_file):
    raster_data = _parse_iris_raster(read_iris_spectrograph_level2_fits(raster_file, uncertainty=False), 'iris')
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
def import_iris_obs():

    caption = "Select a directory containing files from one IRIS OBS."

    data_path = Path(pick_directory(caption))
    rasters = list(data_path.glob("*raster*"))
    sji = list(data_path.glob("*SJI*"))

    sji_data = []

    for s in sji:
        sji_data.append(load_sji_fits(s))

    raster_data = _parse_iris_raster(
        read_iris_spectrograph_level2_fits(rasters,
                                           uncertainty=False,
                                           memmap=True), 'iris')

    return raster_data + sji_data


@importer("Import IRIS OBS Directory (Stacked)")
def import_iris_obs():

    caption = "Select a directory containing files from one IRIS OBS, and stack all raster scans."

    data_path = Path(pick_directory(caption))
    rasters = list(data_path.glob("*raster*"))
    sji = list(data_path.glob("*SJI*"))

    sji_data = []

    for s in sji:
        sji_data.append(load_sji_fits(s))

    raster_data = read_iris_spectrograph_level2_fits(rasters,
                                                     spectral_windows=['Mg II k 2796'],
                                                     memmap=False, uncertainty=False)

    raster_data = {window: stack_spectrogram_sequence(seq)
                   for window, seq in raster_data.data.items()}

    result = []
    for window, window_data in raster_data.items():
        w_data = Data(label=f"{window.replace(' ', '_')}")
        w_data.coords = WCSCoordinates(wcs=window_data.wcs)
        w_data.add_component(Component(window_data.data),
                             f"{window}")
        result.append(w_data)

    return result + sji_data
