import gc, sys, time
from glue_qt.utils import Worker, get_qapp
app = get_qapp()
w = Worker(time.sleep, 0.5); w.start(); time.sleep(0.1)
del w; gc.collect()           # only run()'s own frame keeps the wrapper alive now
t0 = time.time()
while time.time() - t0 < 1.5:  # let run() return; the last Python reference then dies in the worker thread
    app.processEvents(); time.sleep(0.01)
print("main loop still alive after the worker finished")
