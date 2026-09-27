"""Does component order (time last) let the Profile viewer accept the GOES Data instead of raising?"""
import faulthandler, os, sys, warnings, traceback; faulthandler.dump_traceback_later(120, exit=True)
warnings.filterwarnings("ignore")
import numpy as np
from glue.core import Data, DataCollection
from glue.core.component import Component
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
t = np.arange("2021-09-05T00:18:33", "2021-09-05T01:18:33", 60, dtype="datetime64[s]")
d = Data(label="GOES")
if sys.argv[1] == "time-first":
    d.add_component(t, "time")
d.add_component(Component(1e-8 * np.ones(t.size), units="W / m2"), "xrsa")
d.add_component(Component(1e-7 * np.ones(t.size), units="W / m2"), "xrsb")
if sys.argv[1] == "time-last":
    d.add_component(t, "time")
app = GlueApplication(DataCollection([d]))
pv = ProfileViewer(app.session)
try:
    pv.add_data(d); pv.figure.canvas.draw()
    print(sys.argv[1], "-> Profile viewer OK; x choices:", [str(c) for c in pv.state.x_att_helper.choices], "y attribute:", pv.layers[0].state.attribute)
except Exception as e:
    print(sys.argv[1], "-> Profile viewer FAILS:", type(e).__name__)
os._exit(0)
