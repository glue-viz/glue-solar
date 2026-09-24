"""Checker: the identity ComponentLinks are listed (and thus removable) in the glue-qt Link Editor without a JoinLink."""
import os, warnings; warnings.simplefilter("ignore")
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["MPLBACKEND"] = "agg"
from irispy.io import read_files
from glue_qt.app.application import GlueApplication
from glue_qt.dialogs.link_editor.link_editor import LinkEditorWidget
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_time, link_hpc, link_time
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
sji = image_data(sji_path); add_time(sji, read_files(sji_path, memmap=False, uncertainty=False))
ras = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"])[0]
app = GlueApplication(); dc = app.data_collection; app.add_datasets([sji, ras]); dc.add_link(link_hpc(dc)); links = link_time(dc, sji, ras)
w = LinkEditorWidget(dc); st = w.state; st.data1, st.data2 = sji, ras
rows = [(type(l.link).__name__, [c.label[:22] for c in l.link.get_from_ids()] + ["->", l.link.get_to_id().label[:22]]) if not hasattr(l.link, "cids1") else (type(l.link).__name__, [c.label[:22] for c in l.link.cids1] + ["<->"] + [c.label[:22] for c in l.link.cids2]) for l in st.links]
print("external links:", len(dc.external_links), "| Link Editor rows for SJI<->raster:", len(st.links))
for r in rows: print("  ", r)
st.current_link = st.links[-1]; st.remove_link(); print("after removing the last row via the editor:", len(st.links), "rows; dc.external_links after update:", end=" ")
st.update_links_in_collection(); print(len(dc.external_links))
app.close(); print("OK")
