"""Q3: glue-core RegionData for IRIS FOV polygon on a sunpy-map Data (WCS coords); renders?"""
import warnings, numpy as np; warnings.simplefilter("ignore")
import shapely
from glue.core.data_region import RegionData
from glue.core.link_helpers import LinkSame
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
import sunpy.map, sunpy.data.test
from glue_solar.sources.maps import _parse_sunpy_map
aia = sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits"))
d = _parse_sunpy_map(aia, "aia"); import os; d.coords = None if os.environ.get("NOCOORDS") else d.coords
poly = shapely.Polygon([(40, 40), (80, 40), (80, 90), (40, 90)])
reg = RegionData(label="IRIS FOV", regions=np.array([poly]))
app = GlueApplication(); dc = app.data_collection; dc.append(d); dc.append(reg)
v = app.new_data_viewer(ImageViewer, data=d); ok = v.add_data(reg)
dc.add_link(LinkSame(reg.center_x_id, d.pixel_component_ids[1])); dc.add_link(LinkSame(reg.center_y_id, d.pixel_component_ids[0]))
v.figure.canvas.draw()
print("add_data:", ok, "layers:", [(type(l).__name__, l.enabled) for l in v.layers], "| aia coords:", type(d.coords).__name__)
# does it follow world links too? link centers to the map's WORLD cids instead (region in arcsec)
reg2 = RegionData(label="FOV-world", regions=np.array([shapely.Polygon([(-60, -400), (-50, -400), (-50, -390), (-60, -390)])]))
dc.append(reg2); v.add_data(reg2)
w = {n: c for n, c in zip(d.coords.world_axis_names[::-1], d.world_component_ids)}; print("world cids:", list(w))
dc.add_link(LinkSame(reg2.center_x_id, w["Hpln"] if "Hpln" in w else d.world_component_ids[1])); dc.add_link(LinkSame(reg2.center_y_id, w["Hplt"] if "Hplt" in w else d.world_component_ids[0]))
try:
    v.figure.canvas.draw(); print("world-linked region layer:", [(type(l).__name__, l.enabled) for l in v.layers][-1])
except Exception as e:
    print("world-linked region FAILED:", type(e).__name__, str(e)[:150])
