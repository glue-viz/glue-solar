"""Preset-side fix for the stock 'Add large data set?' modal: instance large_data_size=None before add_data."""
import time

from glue.core import DataCollection
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer

import glue_solar.sources.loaders.iris as L

RAS = "~/DATA/IRIS/2dd2d12db374b3466aa27a65bec235d3-iris_l2_20130902_163935_4000255147_raster/iris_l2_20130902_163935_4000255147_raster_t000_r00000.fits"


def test_modal(qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr(ProfileViewer, "warn", lambda self, *a, **k: calls.append(a[0]) or False)  # a user who keeps the default Cancel
    d = L.raster_data([RAS], ["Si IV 1403"])[0]
    app = GlueApplication(DataCollection([d])); qtbot.addWidget(app)
    import os, gc
    if os.environ.get("STOCK_FIRST"):
        stock = app.new_data_viewer(ProfileViewer, data=d)
        print("STOCK size", d.size, "returned", stock, "warn calls", calls, flush=True)
        calls.clear()
        if os.environ.get("STOCK_FIRST") == "gc":
            gc.collect()
    prof = app.new_data_viewer(ProfileViewer)
    prof.large_data_size = None  # instance attribute: this viewer only
    t = time.perf_counter()
    ok = prof.add_data(d)
    artist = prof.layers[0]
    qtbot.waitUntil(lambda: artist._worker is not None and not artist.is_computing and artist.state.profile is not None and len(artist.state.profile[0]) > 0, timeout=60000)
    print("PRESET add_data", ok, "layers", len(prof.layers), "warn calls", calls, f"first profile {time.perf_counter() - t:.2f}s", flush=True)
    app.close()
