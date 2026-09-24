import sys, time
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
from glue_qt.utils import get_qapp
from qtpy.QtCore import QTimer
from wp8_proto import ProtoImporter
app = get_qapp()
ticks = []
timer = QTimer(); timer.timeout.connect(lambda: ticks.append(1)); timer.start(20)
t0 = time.perf_counter()
dlg = ProtoImporter("/Users/nabil/DATA/IRIS")
while dlg.scanning:
    app.processEvents(); time.sleep(0.005)
dt = time.perf_counter() - t0
print(f"real tree via Worker: {dlg.obs_tree.topLevelItemCount()} rows in {dt:.2f} s, GUI timer ticks meanwhile: {len(ticks)}, populate on GUI thread: {dlg.populate_threads}")
dlg.filter.setText("2014-0")
vis = [dlg.obs_tree.topLevelItem(i).text(0) for i in range(dlg.obs_tree.topLevelItemCount()) if not dlg.obs_tree.topLevelItem(i).isHidden()]
print("filter '2014-0' visible rows:", vis)
