"""
A reader for `sunpy.map.Map`.
"""
from glue.config import data_factory, importer, qglue_parser
from glue.core.component import Component
from glue.core.data import Data
from glue.core.data_factories import is_fits
from glue.core.visual import VisualAttributes
from qtpy import QtWidgets

import sunpy.map
from sunpy.map.mapbase import GenericMap

from glue_solar.sources.loaders.maps import QtSunpyMapImporter

__all__ = ["import_sunpy_map", "read_sunpy_map", "_parse_sunpy_map"]


@qglue_parser(GenericMap)
def _parse_sunpy_map(data, label):
    """
    Parse sunpy map so that it can be loaded by ``glue``.
    """
    scan_map = data
    label = label + "-" + scan_map.name
    result = Data(label=label)
    result.coords = scan_map.wcs  # preferred way, preserves more info in some cases
    result.add_component(Component(scan_map.data), scan_map.name)
    result.meta = scan_map.meta
    result.style = VisualAttributes(color="#FDB813", preferred_cmap=scan_map.cmap)

    return result


@data_factory("sunpy Map", is_fits)
def read_sunpy_map(sunpy_map_file):
    """
    For ``glue`` to read in parsed sunpy map.
    """
    sunpy_map_data = _parse_sunpy_map(sunpy.map.Map(sunpy_map_file), "sunpy-map")
    return sunpy_map_data


def pick_directory(caption):
    """
    Pick the directory to load sunpy map files from.
    """
    dialog = QtWidgets.QFileDialog(caption=caption)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)

    directory = dialog.exec_()

    if directory == QtWidgets.QDialog.Rejected:
        return []

    directory = dialog.selectedFiles()
    return directory[0]


@importer("Import sunpy Map Directory")
def import_sunpy_map():
    """
    Import sunpy maps with directory importer.
    """
    caption = "Select a directory containing sunpy Map files."
    directory = pick_directory(caption)

    wi = QtSunpyMapImporter(directory)
    wi.exec_()
    return wi.datasets
