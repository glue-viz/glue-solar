"""Checker: JoinLink side effects. Any subset that is IncompatibleAttribute on the partner falls back to the key join,
which maps 'any flagged pixel in frame f' to whole exposures. Compare with identity ComponentLinks only."""
import os, warnings; warnings.simplefilter("ignore")
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["MPLBACKEND"] = "agg"
import numpy as np
from irispy.io import read_files
from glue.core import DataCollection
from glue.core.exceptions import IncompatibleAttribute
from glue.core.link_helpers import JoinLink
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue.core.state import GlueSerializer, GlueUnSerializer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_time, add_slit, slit_subset_state, link_hpc, link_time
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
def load():
    cube = read_files(sji_path, memmap=False, uncertainty=False)
    sji = image_data(sji_path); add_time(sji, cube); add_slit(sji, cube)
    ras = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"])[0]
    return sji, ras
def count(data, state):
    try:
        m = data.get_mask(state); return f"{m.sum()}/{m.size} px"
    except IncompatibleAttribute:
        return "IncompatibleAttribute (layer disabled)"
for join in (True, False):
    sji, ras = load(); dc = DataCollection([sji, ras]); dc.add_link(link_hpc(dc)); links = link_time(dc, sji, ras)
    if not join:
        for l in links:
            if isinstance(l, JoinLink): dc.remove_link(l)
    sp, rp = sji.pixel_component_ids, ras.pixel_component_ids
    print(f"=== JoinLink {'present' if join else 'removed'}: external links {len(dc.external_links)} | key joins {len(sji._key_joins)}")
    pt = (np.array([5]), np.array([0]), np.array([0])); pt2 = (np.array([100]), np.array([0]), np.array([0]))
    print("  slice translation: sji[ras step, frame 5] =", sji[rp[0], pt], "| ras[sji frame, exposure 100] =", ras[sp[0], pt2])
    st = (sp[0] >= 10) & (sp[0] <= 11); m = ras.get_mask(st); print("  SJI frames 10..11 -> raster exposures", np.nonzero(m.any(axis=(1, 2)))[0])
    st = (rp[0] >= 30) & (rp[0] <= 35); m = sji.get_mask(st); print("  raster exposures 30..35 -> SJI frames", np.nonzero(m.any(axis=(1, 2)))[0])
    roi = RoiSubsetState(xatt=sp[2], yatt=sp[1], roi=RectangularROI(10, 20, 10, 20))
    print("  SJI viewer rectangle ROI (x 10-20, y 10-20) -> raster:", count(ras, roi), "| on SJI itself:", count(sji, roi))
    roi = RoiSubsetState(xatt=rp[0], yatt=rp[1], roi=RectangularROI(40, 60, 10, 20))
    print("  raster MAP ROI (step 40-60, slit 10-20) -> SJI:", count(sji, roi))
    roi = RoiSubsetState(xatt=rp[2], yatt=rp[1], roi=RectangularROI(5, 10, 10, 20))
    print("  raster SPECTROHELIOGRAM ROI (wl 5-10, slit 10-20) -> SJI:", count(sji, roi))
    print("  Slit subset state -> raster:", count(ras, slit_subset_state(sji)))
    if not join:
        for d in (sji, ras): d.meta = {}; d.coords = None; d.style.preferred_cmap = None
        s = GlueSerializer(dc).dumps(); dc2 = GlueUnSerializer.loads(s).object("__main__"); a, b = dc2
        print("  session round trip without JoinLink:", len(s) // 1024, "KB | after reload sji[ras step, frame 5] =", a[b.pixel_component_ids[0], pt], "| external links", len(dc2.external_links))
# Link Editor listing (identity ComponentLinks are visible/removable there)
from glue_qt.app.application import GlueApplication
from glue_qt.dialogs.link_editor import LinkEditor
sji, ras = load(); app = GlueApplication(); dc = app.data_collection; app.add_datasets([sji, ras]); dc.add_link(link_hpc(dc)); links = link_time(dc, sji, ras)
dc.remove_link([l for l in links if isinstance(l, JoinLink)][0])
ed = LinkEditor(dc); st = ed.state; st.data1, st.data2 = sji, ras
print("Link Editor rows for the pair:", [(l.link.__class__.__name__, getattr(l, 'display', ''))[0] for l in st.links], "|", [str(l) for l in st.links][:4])
ed.close(); app.close(); print("OK")
