"""(c) slit subset on the SJI from SLTPX1IX: sit-and-stare (sns) and sweeping raster (2023); group vs data-only subset."""
import os, warnings; warnings.simplefilter("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg")
import numpy as np
from irispy.io import read_files
from glue.core.exceptions import IncompatibleAttribute
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_slit, add_time, slit_x, slit_subset_state, link_hpc, link_time
fs = [str(f) for f in get_test_data_filenames()]
for tag in ("3620258102_SJI_1400", "3880012095_SJI_1400"):
    path = [f for f in fs if tag in f][0]
    cube = read_files(path, memmap=False, uncertainty=False)
    print(tag, "NAXIS1", cube.data.shape[-1], "extra_coords keys", list(cube.extra_coords.keys())[:4], "...")
    print("   slit x per frame:", np.round(slit_x(cube), 2))
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
sji = image_data(sji_path); cube = read_files(sji_path, memmap=False, uncertainty=False); add_time(sji, cube); add_slit(sji, cube)
[ras] = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"])
app = GlueApplication(); dc = app.data_collection; app.add_datasets([sji, ras])
v = app.new_data_viewer(ImageViewer, data=sji)
group = dc.new_subset_group("Slit", slit_subset_state(sji))
mask = sji.subsets[0].to_mask()
print("group subset: frame-0 flagged columns", np.unique(np.where(mask[0])[1]), "| true px per frame", np.unique(mask.sum(axis=(1, 2))))
layer = [l for l in v.layers if l.layer is sji.subsets[0]][0]
bounds = [(0, sji.shape[1] - 1, sji.shape[1]), (0, sji.shape[2] - 1, sji.shape[2])]
for s in (0, 30, 61):
    v.state.slices = (s, 0, 0); v.figure.canvas.draw()
    arr = np.asarray(layer.subset_array(bounds))
    print(f"   rendered at slice {s}: shape {arr.shape} flagged column {np.unique(np.where(arr > 0)[1])}")
print("edit subset after new_subset_group:", [s.label for s in app.session.edit_subset_mode.edit_subset])
print("group evaluated on the raster (no links):", end=" ")
try: print(ras.subsets[0].to_mask().sum(), "px")
except IncompatibleAttribute as e: print("IncompatibleAttribute", e)
dc.add_link(link_hpc(dc)); links = link_time(dc, sji, ras)
print("group evaluated on the raster WITH link_hpc + link_time (identity links, no JoinLink):", end=" ")
try: m = ras.subsets[0].to_mask(); print(m.sum(), "of", m.size, "px selected")
except IncompatibleAttribute as e: print("IncompatibleAttribute (raster layer disabled)")
from glue.core.link_helpers import JoinLink
join = JoinLink(cids1=[ras.id[f"Nearest frame: {sji.label}"]], cids2=[sji.pixel_component_ids[0]], data1=ras, data2=sji); dc.add_link(join)
m = ras.subsets[0].to_mask(); print("   ...and with a JoinLink added on top (rejected design):", m.sum(), "of", m.size, "px selected"); dc.remove_link(join)
# data-only alternative
s2 = sji.new_subset(slit_subset_state(sji), label="Slit (data-only)")
v2 = app.new_data_viewer(ImageViewer, data=sji); v2.figure.canvas.draw()
print("data-only subset: layers in a viewer opened afterwards:", [(type(l).__name__, l.layer.label[:16]) for l in v2.layers], "| dc.subset_groups", len(dc.subset_groups), "| raster subsets", [s.label for s in ras.subsets])
# 2023 sweeping slit
p23 = [f for f in fs if "3880012095_SJI_1400" in f][0]
s23 = image_data(p23); c23 = read_files(p23, memmap=False, uncertainty=False); add_slit(s23, c23)
dc.append(s23); m23 = s23.new_subset(slit_subset_state(s23), label="Slit 2023").to_mask()
print("2023 SJI: flagged column per frame", [np.unique(np.where(m23[f])[1]).tolist() for f in range(s23.shape[0])], "(slit sweeps across the SJI: overlay must be per frame)")
app.close(); print("OK")
