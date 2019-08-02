"""
A reader for IRIS data.
"""
from glue.config import qglue_parser
from glue.core import Data, Component
from glue.core.coordinates import WCSCoordinates
from irispy.spectrograph import (IRISSpectrograph,
                                 read_iris_spectrograph_level2_fits)


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
                          
def is_fits(filename, **kwargs):
    return filename.endswith('.fits')

@data_factory('IRIS Spectrograph', is_fits)
def read_iris_raster(raster_file):
    raster_data = _parse_iris_raster(read_iris_spectrograph_level2_fits(raster_file), 'iris')
    return raster_data
