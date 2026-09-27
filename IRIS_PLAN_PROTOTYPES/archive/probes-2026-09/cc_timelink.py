"""Q2/Q4: serializable time link = precomputed nearest-index component + identity ComponentLink (no closures)."""
import warnings, numpy as np; warnings.simplefilter("ignore")
from glue.core import Data, DataCollection
from glue.core.component_link import ComponentLink
from glue.core.link_helpers import JoinLink
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue.core.fixed_resolution_buffer import translate_pixel
sji = Data(label="sji", x=np.zeros((5, 3, 3)))          # 5 frames
ras = Data(label="ras", y=np.zeros((7, 3)))             # 7 exposures
near = np.array([0, 1, 3, 5, 6])                        # nearest raster exposure per SJI frame (precomputed)
back = np.array([0, 1, 1, 2, 2, 3, 4])                  # nearest SJI frame per exposure
sji.add_component(np.broadcast_to(near[:, None, None], sji.shape).astype(np.int32), "nearest_exposure")
ras.add_component(np.broadcast_to(back[:, None], ras.shape).astype(np.int32), "nearest_frame")
dc = DataCollection([sji, ras])
dc.add_link(ComponentLink([sji.id["nearest_exposure"]], ras.pixel_component_ids[0]))   # identity, no closure
dc.add_link(ComponentLink([ras.id["nearest_frame"]], sji.pixel_component_ids[0]))
dc.add_link(JoinLink(cids1=[sji.id["nearest_exposure"]], cids2=[ras.pixel_component_ids[0]], data1=sji, data2=ras))
print("translate sji frame 3 -> exposure", sji[ras.pixel_component_ids[0], (3, 0, 0)], "(expect 5)")
print("translate exposure 6 -> frame", ras[sji.pixel_component_ids[0], (6, 0)], "(expect 4)")
s = GlueSerializer(dc).dumps(); print("serialized OK,", len(s), "bytes, links:", s.count("ComponentLink"), "ComponentLink refs")
dc2 = GlueUnSerializer.loads(s).object("__main__")
sji2, ras2 = dc2
print("after reload translate frame 3 ->", sji2[ras2.pixel_component_ids[0], (3, 0, 0)], "| key joins:", len(sji2._key_joins))
