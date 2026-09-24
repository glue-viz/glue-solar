"""(e) time link: identity ComponentLinks + JoinLink on precomputed int32 nearest indices; 3D real pair and 4D stack; serializable."""
import warnings; warnings.simplefilter("ignore")
import numpy as np
from irispy.io import read_files
from glue.core import Data, DataCollection
from glue.core.exceptions import IncompatibleAttribute
from glue.core.fixed_resolution_buffer import translate_pixel
from glue.core.state import GlueSerializer, GlueUnSerializer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_time, link_hpc, link_time, nearest
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
def load():
    sji = image_data(sji_path); add_time(sji, read_files(sji_path, memmap=False, uncertainty=False))
    ras = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"])[0]
    return sji, ras
for order in ("time only", "hpc then time", "time then hpc"):
    sji, ras = load(); dc = DataCollection([sji, ras])
    if order == "hpc then time": dc.add_link(link_hpc(dc))
    links = link_time(dc, sji, ras)
    if order == "time then hpc": dc.add_link(link_hpc(dc))
    near = nearest(sji["Time"][:, 0, 0], ras["Time"][:, 0, 0]); back = nearest(ras["Time"][:, 0, 0], sji["Time"][:, 0, 0])
    pt = (np.array([5]), np.array([0]), np.array([0]))
    print(f"[{order}] links {len(links)} | sji[ras step, frame 5] = {sji[ras.pixel_component_ids[0], pt]} expect {near[5]} | ras[sji frame, exposure 100] = {ras[sji.pixel_component_ids[0], (np.array([100]), np.array([0]), np.array([0]))]} expect {back[100]}")
sji, ras = load(); dc = DataCollection([sji, ras]); link_time(dc, sji, ras)
try: translate_pixel(sji, [np.array([5.]), np.array([0.]), np.array([0.])], ras.pixel_component_ids[0])
except Exception as e: print("translate_pixel refuses:", type(e).__name__, e)
# JoinLink semantics both ways
g = dc.new_subset_group("frames 10..11", (sji.pixel_component_ids[0] >= 10) & (sji.pixel_component_ids[0] <= 11))
m = ras.get_mask(g.subset_state); print("SJI frames 10..11 -> raster exposures", np.nonzero(m.any(axis=(1, 2)))[0], "| expect exposures whose nearest frame is 10 or 11:", np.nonzero(np.isin(back, [10, 11]))[0])
g2 = dc.new_subset_group("exposures 30..35", (ras.pixel_component_ids[0] >= 30) & (ras.pixel_component_ids[0] <= 35))
m2 = sji.get_mask(g2.subset_state); print("raster exposures 30..35 -> SJI frames", np.nonzero(m2.any(axis=(1, 2)))[0], "| expect frames that are nearest to one of them:", np.unique(back[30:36]))
# WP6 owns the _GlueWCS / meta savers; strip both here so only the links are under test
sji, ras = load(); dc = DataCollection([sji, ras]); link_time(dc, sji, ras)
for d in (sji, ras): d.meta = {}; d.coords = None; d.style.preferred_cmap = None
s = GlueSerializer(dc).dumps(); dc2 = GlueUnSerializer.loads(s).object("__main__"); sji2, ras2 = dc2
print("session round trip:", len(s) // 1024, "KB | after reload sji[ras step, frame 5] =", sji2[ras2.pixel_component_ids[0], pt], "| external links", len(dc2.external_links), "| key joins", len(sji2._key_joins))
# ---- 4D stack + synthetic SJI whose Time spans the stack
stack = raster_data(sorted(f for f in fs if "20140329" in f and "raster_t000_r0000" in f)[:3], ["Mg II k 2796"], stack=True)[0]
t = stack["Time"][:, :, 0, 0]; nscan, nstep = t.shape
t_sji = np.linspace(t[0, 0].astype("int64"), t[-1, -1].astype("int64"), 11).astype("datetime64[ns]")
sji4 = Data(label="fake_sji", x=np.zeros((11, 4, 4))); sji4.add_component(np.broadcast_to(t_sji[:, None, None], sji4.shape), "Time")
dc4 = DataCollection([sji4, stack]); links4 = link_time(dc4, sji4, stack)
print("stack", stack.shape, "| links", [type(l).__name__ for l in links4], "| SJI comps", [c.label for c in sji4.components if c.label.startswith("Nearest")])
flat = nearest(t_sji, t.ravel()); print("frame 7 -> (scan, step)", np.unravel_index(flat[7], t.shape), "| via links:", sji4[stack.pixel_component_ids[0], (np.array([7]), np.array([0]), np.array([0]))], sji4[stack.pixel_component_ids[1], (np.array([7]), np.array([0]), np.array([0]))])
p4 = (np.array([2]), np.array([3]), np.array([0]), np.array([0])); print("stack (scan 2, step 3) -> frame", stack[sji4.pixel_component_ids[0], p4], "| expect", nearest(t[2:3, 3], t_sji))
stack.meta = {}; stack.coords = None; s4 = GlueSerializer(dc4).dumps(); d4 = GlueUnSerializer.loads(s4).object("__main__"); a, b = d4
print("4D session round trip:", len(s4) // 1024, "KB | frame 7 ->", a[b.pixel_component_ids[0], (np.array([7]), np.array([0]), np.array([0]))], a[b.pixel_component_ids[1], (np.array([7]), np.array([0]), np.array([0]))])
