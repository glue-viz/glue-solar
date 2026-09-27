"""(f) slice sync end-to-end in a real offscreen GlueApplication with Qt sliders, link_hpc + link_time present."""
import os, warnings; warnings.simplefilter("ignore")
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["MPLBACKEND"] = "agg"
import numpy as np
from irispy.io import read_files
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data
from wp4_common import add_time, link_hpc, link_time, nearest, sync_slices, whisker
fs = [str(f) for f in get_test_data_filenames()]
sji_path = [f for f in fs if "sns" in f and "SJI_1400" in f][0]
sji = image_data(sji_path); add_time(sji, read_files(sji_path, memmap=False, uncertainty=False))
ras = raster_data([[f for f in fs if "sns" in f and "raster_t000" in f][0]], windows=["Si IV 1403"])[0]
near = nearest(sji["Time"][:, 0, 0], ras["Time"][:, 0, 0]); back = nearest(ras["Time"][:, 0, 0], sji["Time"][:, 0, 0])
app = GlueApplication(); dc = app.data_collection; app.add_datasets([sji, ras])
dc.add_link(link_hpc(dc)); link_time(dc, sji, ras)
va = app.new_data_viewer(ImageViewer, data=sji)                       # SJI: slider = frame
vb = app.new_data_viewer(ImageViewer, data=ras)                       # raster default: x=wl, y=slit, slider = step
hooked = sync_slices(app)(None); sync_slices(app)  # twice: must be idempotent
vc = whisker(app, ras, slit_index=20)                                 # opened AFTER the action: x=wl, y=step, slider = slit
vd = app.new_data_viewer(ImageViewer, data=ras); vd.state.x_att, vd.state.y_att = ras.pixel_component_ids[0], ras.pixel_component_ids[1]  # map: slider = wl
print("hooked states after calling sync_slices twice:", len(hooked), "| viewers:", len(app.viewers[0]))
def slider(v, i=0):
    lay = v.options_widget().slice_helper.layout
    return [(w.state.label, w.state.slice_center) for w in (lay.itemAt(k).widget() for k in range(lay.count())) if w is not None and hasattr(w, "state")]
def qslider(v): return next(s for s in v.options_widget().slice_helper._sliders if s is not None)
sa, sb = qslider(va), qslider(vb)
sa.state.slice_center = 5; app.app.processEvents()
print(f"A slider -> 5: A {va.state.slices} B {vb.state.slices} (expect step {near[5]}) B slider {slider(vb)} | C (whisker) {vc.state.slices} (slit untouched=20) | D (map) {vd.state.slices} (wl untouched)")
sb.state.slice_center = 100; app.app.processEvents()
print(f"B slider -> 100: B {vb.state.slices} A {va.state.slices} (expect frame {back[100]}) A slider {slider(va)}")
qslider(vc).state.slice_center = 30; app.app.processEvents()
print(f"C (whisker) slit slider -> 30: C {vc.state.slices} | A {va.state.slices} B {vb.state.slices} (unchanged: whisker does not drive)")
qslider(vd).state.slice_center = 7; app.app.processEvents()
print(f"D (map) wl slider -> 7: D {vd.state.slices} | B {vb.state.slices} (B shows wl on x: untouched) A {va.state.slices}")
sb.state.slice_center = 0; app.app.processEvents()
print(f"B slider -> 0: A {va.state.slices} (expect frame {back[0]}) | D {vd.state.slices} (D displays step: untouched) | C {vc.state.slices}")
for v in (va, vb, vc, vd): v.figure.canvas.draw()
print("all four drew | layers enabled:", [[l.enabled for l in v.layers] for v in (va, vb, vc, vd)])
# sweep: no echo drift
drift = []
for f in range(sji.shape[0]):
    va.state.slices = (f, 0, 0)
    if va.state.slices[0] != f: drift.append(f)
print("echo drift over 62 frames:", drift)
app.close(); print("OK")
