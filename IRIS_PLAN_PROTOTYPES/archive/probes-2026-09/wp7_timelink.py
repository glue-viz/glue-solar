"""Optional bonus: LinkSame GOES time <-> raster Time (datetime64) so a time range on the light curve selects raster steps."""
import faulthandler, os, warnings; faulthandler.dump_traceback_later(200, exit=True)
warnings.filterwarnings("ignore")
import numpy as np
from glue.core import Data, DataCollection
from glue.core.component import Component
from glue.core.link_helpers import LinkSame
from glue.core.subset import RangeSubsetState
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
fs = get_test_data_filenames()
ras = raster_data([str(f) for f in fs if f.name.endswith("3620258102_raster_t000_r00000.fits")][:1], ["Mg II k 2796"])[0]
rt = ras["Time"]; print("raster Time:", rt.dtype, rt.min(), rt.max())
t = np.arange("2021-09-05T00:18:00", "2021-09-05T05:08:00", 60, dtype="datetime64[s]")
goes = Data(label="GOES-16 XRS")
goes.add_component(t, "time")  # Data.add_component wraps datetime64 in DateTimeComponent itself
goes.add_component(Component(1e-7 * np.ones(t.size), units="W / m2"), "xrsb")
dc = DataCollection([goes, ras])
dc.add_link(LinkSame(goes.id["time"], ras.id["Time"]))
st = RangeSubsetState(np.datetime64("2021-09-05T01:00:00"), np.datetime64("2021-09-05T02:00:00"), goes.id["time"])
dc.new_subset_group("hour 1-2", st)
m = ras.subsets[0].to_mask(); steps = np.flatnonzero(m.reshape(187, -1).any(1))
print("GOES time range -> raster steps", steps.min(), "..", steps.max(), "(", steps.size, "steps ) of 187")
from glue_qt.app import GlueApplication
from glue_qt.viewers.scatter import ScatterViewer
app = GlueApplication(dc)
sv = app.new_data_viewer(ScatterViewer, data=goes)
sv.state.x_att, sv.state.y_att, sv.state.y_log = goes.id["time"], goes.id["xrsb"], True
ls = sv.layers[0].state; ls.line_visible, ls.markers_visible = True, False
sv.figure.canvas.draw()
print("layer state attrs ok:", ls.line_visible, ls.markers_visible, "| y label:", sv.axes.get_ylabel(), "| layers:", [type(l).__name__ for l in sv.layers])
os._exit(0)
