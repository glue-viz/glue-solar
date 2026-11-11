import os, sys, traceback
cfg = os.path.join(os.environ["HOME"], ".glue"); os.makedirs(cfg, exist_ok=True)
open(os.path.join(cfg, "plugins.cfg"), "w").write("[plugins]\nglue_solar = 0\n")
import numpy as np
from glue.core import Data
from glue.viewers.common.viewer import Viewer
from glue_qt.utils import get_qapp, process_events
qapp = get_qapp()
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.common import data_viewer as dv
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
a = GlueApplication(); a.show(); process_events()
d = Data(label="big", x=np.zeros((4, 5, 5)))
a.data_collection.append(d)
ProfileViewer.large_data_size = 10
dv.warn = lambda *args, **kw: False  # Cancel on 'Add large data set?'
v = a.new_data_viewer(ProfileViewer, data=d)
process_events()
print("cancelled viewer returned:", v, "| hub still has LayerArtistView:", 
      any(type(s).__name__ == "LayerArtistView" for s in a.session.hub._subscriptions))
v2 = ImageViewer(a.session)
try:
    Viewer.add_data(v2, d)  # unwrapped: the exception instead of the message box
    print("later Image viewer add_data: OK")
except Exception:
    tb = traceback.format_exc().splitlines()
    print("later Image viewer add_data FAILED:")
    print("\n".join(l for l in tb if l.strip().startswith(("File", "RuntimeError", "glue"))))
a.close()
