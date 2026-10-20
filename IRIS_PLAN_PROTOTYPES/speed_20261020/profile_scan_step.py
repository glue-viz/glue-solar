"""cProfile of an SST quicklook's scan step, to idle: python profile_scan_step.py CUBE GLUE_SOLAR_TREE."""
import cProfile
import io
import pstats
import sys
import time

sys.path.insert(0, sys.argv[2])
from glue_qt.app import GlueApplication
from qtpy.QtWidgets import QApplication

import glue_solar
from glue_solar.quicklook import coordinator, quicklook
from glue_solar.sources.sst import sst_data

glue_solar.setup()
app = GlueApplication(); app.resize(1600, 1000); app.show()
qt = QApplication.instance()
cube = sst_data(sys.argv[1])
views = quicklook(app, [cube])
coord = coordinator(app.data_collection)


def busy():
    for tab in app.viewers:
        for viewer in tab:
            canvas = viewer.figure.canvas
            if getattr(canvas, "_draw_pending", False) and canvas.isVisible() and not canvas.visibleRegion().isEmpty():
                return True
            for layer in viewer.layers:
                if getattr(layer, "is_computing", False):
                    return True
    return coord._timer.isActive()


def settle():
    calm = None
    while True:
        qt.processEvents()
        if busy():
            calm = None
        elif calm is None:
            calm = time.perf_counter()
        elif time.perf_counter() - calm > 0.05:
            return
        time.sleep(0.001)


settle()
draws = {}
for index, v in enumerate(viewer for tab in app.viewers for viewer in tab):
    canvas = v.figure.canvas
    name = f"{index} {type(v).__name__} {getattr(v.state, 'title', '') or ''}"[:40]

    def draw(*a, _original=canvas.draw, _name=name, **k):
        start = time.perf_counter()
        result = _original(*a, **k)
        draws.setdefault(_name, []).append(time.perf_counter() - start)
        return result

    canvas.draw = draw
times = []
profile = cProfile.Profile()
for scan in (1, 2, 3, 4, 5, 0):
    slices = list(views["map"].state.slices); slices[0] = scan
    start = time.perf_counter()
    profile.enable()
    views["map"].state.slices = tuple(slices)
    settle()
    profile.disable()
    times.append(time.perf_counter() - start - 0.05)
print("scan steps ms:", [round(t * 1e3) for t in times])
print("draws per panel over the 6 steps (count, total ms):", {k: (len(v), round(sum(v) * 1e3)) for k, v in sorted(draws.items())})
out = io.StringIO()
stats = pstats.Stats(profile, stream=out)
stats.sort_stats("cumulative").print_stats(40)
lines = [l for l in out.getvalue().splitlines() if l.strip()[:1].isdigit()]
stats.print_callees("fixed_resolution_buffer.py.*compute_fixed_resolution_buffer")
stats.print_callees("translate_pixel")
print("\n".join(l[:200] for l in out.getvalue().splitlines()[-40:]))
print("top cumulative (calls, tottime, cumtime, function):")
for l in lines[:40]:
    parts = l.split(None, 5)
    print("  ", parts[0], parts[1], parts[3], parts[5][-110:])
