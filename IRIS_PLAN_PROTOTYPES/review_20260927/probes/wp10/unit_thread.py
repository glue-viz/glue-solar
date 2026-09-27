"""Candidate CI regression test (bundled irispy fixture, no Qt): two threads hammer one _GlueWCS. argv: none|lock"""
import sys, threading, warnings
sys.path[:0] = ["<session-scratch>/tools", "<session-scratch>/feas-robustness-perf"]
import qs_isolate  # noqa
import faulthandler; faulthandler.enable()
import numpy as np
warnings.simplefilter("ignore")
from irispy.data.test import get_test_data_filenames
import glue_solar.sources.loaders.iris as L
if sys.argv[1] != "none":
    import fixes; fixes.apply(sys.argv[1])
f = next(p for p in get_test_data_filenames() if p.name.startswith("iris_l2_20210905_001833_3620258102_raster_t000_r00000"))
d = L.raster_data([f], ["Si IV 1403"])[0]
w = d.coords
print(f.name, d.shape, flush=True)
px = [np.arange(1000.0) % s for s in w.pixel_shape]
stop = []
def spin():
    while not stop:
        w.pixel_to_world_values(*px); w.axis_correlation_matrix
t = threading.Thread(target=spin); t.start()
for i in range(20000):
    w.pixel_to_world_values(*px)
stop.append(1); t.join()
print("NO CRASH", flush=True)
