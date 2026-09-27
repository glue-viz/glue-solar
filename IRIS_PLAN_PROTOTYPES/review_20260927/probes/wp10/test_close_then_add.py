"""Does a normally closed Profile viewer (vs one closed by the Cancel path) break the next add_data?"""
import os

from glue.core import DataCollection
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
from glue_qt.viewers.image import ImageViewer
from irispy.data.test import get_test_data_filenames

import glue_solar.sources.loaders.iris as L


def test_close_then_add(qtbot, monkeypatch):
    f = next(p for p in get_test_data_filenames() if p.name.startswith("iris_l2_20210905_001833_3620258102_raster_t000_r00000"))
    d = L.raster_data([f], ["Si IV 1403"])[0]
    app = GlueApplication(DataCollection([d])); qtbot.addWidget(app)
    mode = os.environ["MODE"]
    if mode == "cancel":
        monkeypatch.setattr(ProfileViewer, "large_data_size", 1)
        monkeypatch.setattr(ProfileViewer, "warn", lambda self, *a, **k: False)
        print("CANCEL returned", app.new_data_viewer(ProfileViewer, data=d), flush=True)
        monkeypatch.setattr(ProfileViewer, "large_data_size", None)
    else:
        v = app.new_data_viewer(ProfileViewer, data=d)
        v.close(warn=False)
        print("CLOSED normally", flush=True)
    w = app.new_data_viewer(ImageViewer, data=d)
    print("NEXT image viewer layers", len(w.layers), flush=True)
    p = app.new_data_viewer(ProfileViewer, data=d)
    print("NEXT profile viewer layers", len(p.layers), flush=True)
    app.close()
