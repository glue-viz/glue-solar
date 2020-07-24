from pathlib import Path

from glue.app.qt.application import GlueApplication
from glue.core.data import Data
from glue.core.data_collection import DataCollection
from glue.core.data_factories import load_data
from glue_solar.instruments.iris import _parse_iris_raster
from sunraster.io.iris import read_iris_spectrograph_level2_fits

from glue.viewers.image.qt import ImageViewer

# create some data
data_path = Path("/home/stuart/sunpy/data/iris_glue/")
rasters = list(data_path.glob("*raster*"))
sji = list(data_path.glob("*SJI*"))

raster_data = _parse_iris_raster(read_iris_spectrograph_level2_fits(rasters), 'iris')
sji_data = []

for s in sji:
    sji_data += load_data(s)

dc = DataCollection(raster_data + sji_data)
ga = GlueApplication(dc)

im1 = ga.new_data_viewer(ImageViewer)
im1.add_data(raster_data[0])

im2 = ga.new_data_viewer(ImageViewer)
im2.add_data(sji_data[0])


class IRISLinker:
    def __init__(self, im1, im2):
        self.im_raster = im1
        self.im_sji = im2

        self.im_raster.state.add_callback("slices", self._raster_update)
        self.im_sji.state.add_callback("slices", self._sji_update)

    def _raster_update(self, *args):
        raster_slice = self.im_raster.state.slices
        sji_slice = raster_slice
        print(raster_slice)
        self.im_sji.state.slices = sji_slice

    def _sji_update(self, *args):
        sji_slice = self.im_sji.state.slices
        raster_slice = sji_slice
        print(sji_slice)
        self.im_raster.state.slices = raster_slice


l = IRISLinker(im1, im2)

ga.start()
