"""
A reader for IRIS data.
"""

from collections.abc import Mapping

from glue.config import data_factory, importer, qglue_parser
from glue.core.component import Component
from glue.core.coordinates import WCSCoordinates
from glue.core.data import Data
from glue.core.data_factories import is_fits
from glue.core.visual import VisualAttributes
from irispy.io import read_files
from irispy.sji import SJICube
from irispy.spectrograph import SpectrogramCube
from qtpy import QtWidgets

from astropy.io import fits

from glue_solar.sources.loaders.iris import QtIRISImporter

__all__ = ["import_iris", "read_iris_files"]


@qglue_parser(SpectrogramCube)
def _parse_iris_raster(data):
    """
    Parse IRIS Level 2 raster files so that it can be loaded by glue.
    """
    datasets = []
    for window, window_data in data.items():
        for i, scan_data in enumerate(window_data):
            label = f"{str(window).replace(' ', '_')}-{scan_data.meta['OBSID']}-scan-{i}"
            w_data = Data(label=label)
            w_data.coords = scan_data.wcs
            w_data.add_component(Component(scan_data.data), label)
            w_data.meta = scan_data.meta
            w_data.style = VisualAttributes(color="#5A4FCF")
            datasets.append(w_data)
    return datasets


@qglue_parser(SJICube)
def _parse_iris_sji(data, file_header):
    """
    Parse IRIS Level 2 SJI files so that it can be loaded by glue.
    """
    wave = int(data.meta["TWAVE1"])
    w_data = Data(label=f"IRIS-SJI-{wave}-{data.meta['OBSID']}")
    # TODO: Construct correct 3D WCS
    header = file_header.copy()
    for key in [k for k in header if k.startswith("CUNIT")]:  # astropy only accepts these spellings with a warning
        header[key] = {"seconds": "s", "arcsecs": "arcsec"}.get(header[key], header[key])
    w_data.coords = WCSCoordinates(header)
    w_data.add_component(Component(data.data), f"{wave}-{data.meta['OBSID']}")
    w_data.meta = data.meta
    w_data.style = VisualAttributes(color="#5A4FCF", preferred_cmap=f"irissji{wave}")
    return w_data


@data_factory("IRIS FITS", is_fits)
def read_iris_files(file_path):
    """
    To read any IRIS Level 2 files.
    """
    # TODO: Memmap in future.
    data = read_files(file_path, uncertainty=False, memmap=False)
    if isinstance(data, SJICube):
        return _parse_iris_sji(data, fits.getheader(file_path))
    elif isinstance(data, Mapping):  # one sequence of scans per spectral window
        return _parse_iris_raster(data)
    else:
        raise ValueError(f"Unrecognised IRIS file type for {file_path}")


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
