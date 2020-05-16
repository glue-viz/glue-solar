"""
A reader for sunpy map data.
"""
import os

from pathlib import Path

from qtpy import QtWidgets

from astropy.io import fits
from astropy.wcs import WCS

import sunpy.map
from sunpy.map.mapbase import GenericMap  # isort:skip

from glue.config import data_factory, importer, qglue_parser
from glue.core import Component, Data
from glue.core.data_factories import load_data
from glue.core.coordinates import WCSCoordinates
from glue.core.visual import VisualAttributes
from glue.core.data_factories import is_fits

from .sunpy_maps.sunpy_maps_loader import QtSunpyMapImporter


__all__ = ['import_sunpy_map', 'read_sunpy_map', '_parse_sunpy_map']


@qglue_parser(GenericMap)
def _parse_sunpy_map(data, label):
    # result = []
    # for window, window_data in data.data.items():
    #     for i, scan_data in enumerate(window_data):
    #         w_data = Data(label=f"{window.replace(' ', '_')}-scan-{i}")
    #         w_data.coords = WCSCoordinates(wcs=scan_data.wcs)
    #         w_data.add_component(Component(scan_data.data),
    #                              f"{window}-scan-{i}")
    #         w_data.meta = scan_data.meta
    #         result.append(w_data)

    scan_map = data
    label = label + '-' + scan_map.name
    result = Data(label=label)
    result.coords = scan_map.wcs
    result.add_component(Component(scan_map.data),
                         scan_map.name)
    result.meta = scan_map.meta
    result.style = VisualAttributes(color='#FDB813', preferred_cmap=scan_map.cmap)

    return result


# def is_fits(filename, **kwargs):
#     return filename.endswith('.fits')


@data_factory('SunPy Map', is_fits)
def read_sunpy_map(sunpy_map_file):
    # label_ext = os.path.split(sunpy_map_file)[1]
    sunpy_map_data = _parse_sunpy_map(sunpy.map.Map(sunpy_map_file), 'sunpy-map')
    return sunpy_map_data


def pick_directory(caption):
    dialog = QtWidgets.QFileDialog(caption=caption)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)

    directory = dialog.exec_()

    if directory == QtWidgets.QDialog.Rejected:
        return []

    directory = dialog.selectedFiles()
    return directory[0]


@importer("Import SunPy Maps Directory")
def import_sunpy_map():
    caption = "Select a directory containing SunPy Map files."
    directory = pick_directory(caption)

    wi = QtSunpyMapImporter(directory)
    wi.exec_()
    return wi.datasets
