import gc, sys, time
from glue_qt.utils import Worker, get_qapp
app = get_qapp()
if sys.argv[1] == "drop":       # drop the only reference while the thread runs
    w = Worker(time.sleep, 1.0); w.start(); time.sleep(0.1)
    del w; gc.collect()
    print("survived drop")      # never printed if Qt aborts
else:                            # cooperative stop, then poll the flag after the thread finished
    def loop(stop):
        n = 0
        while not stop():
            n += 1; time.sleep(0.01)
        return n
    w = Worker(loop); w.kwargs["stop"] = w.isInterruptionRequested
    seen = []; w.result.connect(seen.append); w.start(); time.sleep(0.1)
    w.requestInterruption(); w.wait(); app.processEvents()
    print("stopped after", seen, "iterations; isInterruptionRequested() after wait():", w.isInterruptionRequested())
