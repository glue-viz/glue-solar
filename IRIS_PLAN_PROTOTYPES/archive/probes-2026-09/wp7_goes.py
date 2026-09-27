"""WP7 GOES: real TimeSeries on local files -> glue Data -> ScatterViewer offscreen; epoch check.
Run with EPOCH=1 to set rcParams['date.epoch'] before any plotting (the workaround under test)."""
import faulthandler, os, sys, warnings; faulthandler.dump_traceback_later(120, exit=True)
warnings.filterwarnings("ignore")
import numpy as np, matplotlib
if os.environ.get("EPOCH"):
    matplotlib.rcParams["date.epoch"] = "0000-12-31T00:00:00"   # glue's datetime64_to_mpl origin
import matplotlib.dates as md
import parfive, inspect
print("parfive.Results.append sig:", inspect.signature(parfive.Results.append))
r = parfive.Results(); r.append(path="/tmp/x", url="file:///tmp/x"); print("Results:", list(r), "errors:", r.errors)
import sunpy.data.test
from sunpy.timeseries import TimeSeries
from sunpy.net import attrs as a, Fido
print("Fido.search sig:", inspect.signature(Fido.search))
# 1. real reader on sunpy's shipped GOES-16 avg1m test file (no network)
f = sunpy.data.test.get_test_filepath("sci_xrsf-l2-avg1m_g16_d20210101_truncated.nc")
ts = TimeSeries(f, source="xrs")
print("test nc:", type(ts).__name__, ts.time.min().isot, ts.time.max().isot, "cols:", ts.columns, "n:", len(ts.to_dataframe()))
tr = ts.truncate("2021-01-01T22:30:00", "2021-01-01T23:10:00")
df = tr.to_dataframe()
print("truncate ->", len(df), "rows", df.index[0], df.index[-1], "index dtype:", df.index.dtype, "meta sat:", ts.observatory)
# 2. concatenate two consecutive cached daily files if present (~/sunpy/data, already on disk)
cached = [os.path.expanduser(f"~/sunpy/data/sci_xrsf-l2-avg1m_g15_d2012100{d}_v2-2-1.nc") for d in (5, 6)]
if all(os.path.exists(c) for c in cached):
    ts2 = TimeSeries(cached, source="xrs", concatenate=True).truncate("2012-10-05T23:00", "2012-10-06T01:00")
    d2 = ts2.to_dataframe(); print("concat 2 days ->", len(d2), d2.index[0], d2.index[-1])
# 3. glue Data
from glue.core import Data, DataCollection
t = df.index.values
print("df.index.values dtype:", t.dtype)
d = Data(label="GOES-16 XRS", time=t, xrsa=df["xrsa"].to_numpy(), xrsb=df["xrsb"].to_numpy())
print("kinds:", [(str(c), d.get_kind(c)) for c in d.main_components])
print("mpl _epoch before glue_qt import:", md._epoch)
from glue_qt.app import GlueApplication
from glue_qt.viewers.scatter import ScatterViewer
print("mpl _epoch after glue_qt import:", md._epoch)
app = GlueApplication(DataCollection([d]))
print("mpl _epoch after GlueApplication():", md._epoch)
sv = app.new_data_viewer(ScatterViewer, data=d)
sv.state.x_att, sv.state.y_att = d.id["time"], d.id["xrsb"]; sv.state.y_log = True
sv.figure.canvas.draw()
ax = sv.axes
print("x_kinds:", sv.state.x_kinds, "| state x_min/x_max:", sv.state.x_min, sv.state.x_max, "| y_log:", sv.state.y_log, "yscale:", ax.get_yscale())
print("mpl epoch now:", md.get_epoch(), "| num2date(xlim):", [md.num2date(v).isoformat() for v in ax.get_xlim()])
print("tick labels:", [l.get_text() for l in ax.get_xticklabels()])
os._exit(0)
