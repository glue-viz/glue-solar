"""(b) quicklook trio on glue 1.27 with link_hpc + link_time + sync."""
import os, warnings; warnings.simplefilter("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg")
import numpy as np
from irispy.io import read_files
from glue.viewers.profile.state import ProfileViewerState
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_time, quicklook
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
sji = image_data(sji_path); add_time(sji, read_files(sji_path, memmap=False, uncertainty=False))   # loader change (d)
rasters = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403", "C II 1336"])
print("ProfileViewerState has slices (fork profile-wcs):", hasattr(ProfileViewerState, "slices"))
app = GlueApplication(); app.add_datasets([sji, *rasters])
p0 = app.new_data_viewer(ProfileViewer, data=rasters[0])
print("ProfileViewer default x_att:", p0.state.x_att, "| function:", p0.state.function)
viewers = quicklook(app, [sji, *rasters])
print("viewers:", [type(v).__name__ for v in viewers], "| external links:", len(app.data_collection.external_links))
s, m, p = viewers
print("SJI viewer: x", s.state.x_att_world, "y", s.state.y_att_world, "slices", s.state.slices)
print("map viewer: x", m.state.x_att_world, "y", m.state.y_att_world, "slices", m.state.slices)
print("profile: x_att", p.state.x_att, "| x_att_pixel", p.state.x_att_pixel, "| function", p.state.function, "| x unit", p.state.x_display_unit)
for v in (s, m, p): v.figure.canvas.draw()
x, y = p.layers[0].state.profile
print("profile x range", x.min(), x.max(), "(metres today; Angstrom after WP1 D3) | n", len(y), "| layers enabled", [l.enabled for l in p.layers])
print("SJI components:", [c.label for c in sji.components if not c.label.startswith("Pixel")])
print("raster components:", [c.label for c in rasters[0].components if not c.label.startswith("Pixel")])
app.close(); print("OK")
