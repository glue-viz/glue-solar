import faulthandler, sys, os; faulthandler.dump_traceback_later(60, exit=True)
import numpy as np, warnings, traceback
warnings.filterwarnings("ignore")
from glue.core import Data, DataCollection
from glue.utils.matplotlib import datetime64_to_mpl
import matplotlib.dates as md
x = np.datetime64("2021-09-05T00:00:00")
print("datetime64_to_mpl ->", md.num2date(datetime64_to_mpl(x)), "| mpl epoch:", md.get_epoch(), flush=True)
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
t = np.arange("2021-09-05T00:18:33", "2021-09-05T01:18:33", 60, dtype="datetime64[s]")
d = Data(label="GOES", time=t, xrsb=1e-7*np.ones(t.size))
app = GlueApplication(DataCollection([d]))
pv = ProfileViewer(app.session)
try:
    pv.add_data(d)
    print("profile add_data OK; x choices:", [str(c) for c in pv.state.x_att_helper.choices], "x_att:", pv.state.x_att, flush=True)
    pv.figure.canvas.draw(); print("profile drew", flush=True)
except Exception:
    traceback.print_exc()
os._exit(0)
