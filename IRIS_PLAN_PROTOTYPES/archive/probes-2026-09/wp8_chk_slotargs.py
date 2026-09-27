# does a no-arg Python method survive clicked(bool) / finished(int) on PyQt6?
from glue_qt.utils import get_qapp
from qtpy import QtWidgets
app = get_qapp()
class D(QtWidgets.QDialog):
    def __init__(self):
        super().__init__(); self.hits = []
        self.b = QtWidgets.QPushButton(self); self.b.clicked.connect(self.noargs); self.finished.connect(self.noargs)
    def noargs(self):
        self.hits.append("ok")
d = D()
try:
    d.b.click(); print("clicked -> no-arg slot:", d.hits)
except TypeError as e:
    print("clicked -> TypeError:", e)
try:
    d.reject(); print("finished -> no-arg slot:", d.hits)
except TypeError as e:
    print("finished -> TypeError:", e)
bar = QtWidgets.QProgressBar(); bar.setFormat("%p%"); bar.setRange(0, 0)
print("busy bar text():", repr(bar.text()), "| format():", repr(bar.format()))
bar.setRange(0, 100); print("after setRange(0,100) text():", repr(bar.text()))
