"""glue-qt ImageViewer offscreen: (1) 1D scatter + subset overlays accepted; (2) lon/lat-only link: which
direction of ROI selection propagates; (3) side effects of the transitive-closure axis_correlation_matrix."""
import os, sys, warnings; warnings.simplefilter("ignore")
import numpy as np
from glue.core import Data
from glue.core.link_helpers import LinkSame
from glue.core.roi import RectangularROI
from glue.core.exceptions import IncompatibleAttribute
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders import iris as loader

PATCH = os.environ.get("PATCH") == "1"
if PATCH:
    def acm(self):
        m = self._wcs.axis_correlation_matrix
        closure = m.copy()
        for _ in range(m.shape[0]):
            closure = closure | ((closure @ closure.T.astype(int)) > 0) @ m
        return closure
    loader._GlueWCS.axis_correlation_matrix = property(acm)

files = [str(f) for f in get_test_data_filenames() if str(f).endswith(".fits")]
sji = loader.image_data([f for f in files if "sns/" in f and "SJI_1400" in f][0])
[ras] = loader.raster_data([f for f in files if "sns/" in f and "raster" in f], ["C II 1336"])
app = GlueApplication()
dc = app.data_collection
dc.append(sji); dc.append(ras)
print(f"PATCH={PATCH} matrix={sji.coords.axis_correlation_matrix.astype(int).tolist()}")

# (1) glue-qt ImageViewer accepts a 1D scatter Data pixel-linked, and a subset overlay
ny = ras.shape[1]
slit = Data(label="slit-px", x=np.full(ny, 18.7), y=np.arange(ny, dtype=float))
dc.append(slit)
dc.add_link(LinkSame(slit.id["x"], sji.pixel_component_ids[2])); dc.add_link(LinkSame(slit.id["y"], sji.pixel_component_ids[1]))
v = app.new_data_viewer(ImageViewer, data=sji)
v.add_data(slit)
print("qt ImageViewer layers:", [(type(l).__name__, l.enabled) for l in v.layers])
v.figure.canvas.draw()
print("  WCSAxes coords:", [(c.get_axislabel() or c._wcs_orig.world_axis_names[i] if hasattr(c,'_wcs_orig') else '', ) for i, c in enumerate(v.axes.coords)] if hasattr(v.axes, 'coords') else 'no coords')
try:
    print("  n WCSAxes coords:", len(list(v.axes.coords)), "| xlabel:", v.axes.get_xlabel()[:40], "| ylabel:", v.axes.get_ylabel()[:40])
    for i, c in enumerate(v.axes.coords):
        print(f"   coord[{i}] axislabel={c.get_axislabel()!r} ticks_visible={c.ticks.get_visible()} ticklabels_visible={c.ticklabels.get_visible()}")
except Exception as e:
    print("  WCSAxes introspection failed:", type(e).__name__, e)
v.state.slices = (30, 0, 0); v.figure.canvas.draw()
print("  slider to 30 + redraw OK; slit layer enabled:", v.layers[1].enabled)
# status-bar style world coordinate string at a pixel
try:
    print("  coords string at (18,20):", v._coords_status_string(18, 20) if hasattr(v, "_coords_status_string") else v.axes.format_coord(18, 20)[:120])
except Exception as e:
    print("  coord string failed:", type(e).__name__, e)

# Profile viewer on SJI along time
try:
    pv = app.new_data_viewer(ProfileViewer, data=sji)
    pv.state.x_att = sji.world_component_ids[0]
    pv.figure.canvas.draw()
    lay = pv.layers[0]
    print("  ProfileViewer x=Time OK; enabled:", lay.enabled, "| x range", np.round(lay.state.profile[0][[0, -1]], 1) if lay.state.profile is not None else None)
except Exception as e:
    print("  ProfileViewer failed:", type(e).__name__, e)

# (2) lon/lat-only LinkSame (docs / P1.4 style): ROI propagation direction
dc.add_link(LinkSame(ras.world_component_ids[0], sji.world_component_ids[2]))
dc.add_link(LinkSame(ras.world_component_ids[1], sji.world_component_ids[1]))
vr = app.new_data_viewer(ImageViewer, data=ras)
vr.state.x_att = ras.pixel_component_ids[0]; vr.state.y_att = ras.pixel_component_ids[1]   # (step, slit) map
vr.apply_roi(RectangularROI(50, 100, 10, 30))       # drawn on raster
sub = dc.subset_groups[-1]
def mask(d):
    try:
        m = d.subsets[-1].to_mask(); return f"OK n={int(m.sum())}"
    except IncompatibleAttribute as e:
        return f"IncompatibleAttribute({e})"
print("ROI drawn on RASTER viewer -> mask on raster:", mask(ras), "| on SJI:", mask(sji))
print("   SJI viewer shows raster-drawn subset layer enabled:", [l.enabled for l in v.layers if l.layer is sji.subsets[-1]])
v.apply_roi(RectangularROI(10, 25, 5, 35))          # drawn on SJI (new subset)
from glue.core.edit_subset_mode import EditSubsetMode
print("ROI drawn on SJI viewer -> mask on SJI:", mask(sji), "| on raster:", mask(ras))
print("   raster viewer shows SJI-drawn subset layer enabled:", [l.enabled for l in vr.layers if l.layer is ras.subsets[-1]])
print("   raster x/y att world options:", [c.label for c in vr.state.x_att_world_helper.choices][:4] if hasattr(vr.state, 'x_att_world_helper') else '')
app.close()
