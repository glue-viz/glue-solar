"""_ask dialog builds and returns under offscreen Qt (OK clicked by a timer); layer_action registries are one object."""
import sys, warnings; warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
from qtpy import QtCore, QtWidgets
from glue_qt.utils import get_qapp
import glue.config, glue_qt.config
from wp6_fitting import _ask
app = get_qapp()
print("glue.config.layer_action is glue_qt.config.layer_action:", glue.config.layer_action is glue_qt.config.layer_action)
class D: label = "demo"
def accept():
    dlg = next(w for w in app.topLevelWidgets() if isinstance(w, QtWidgets.QDialog) and w.isVisible())
    combo, edit = dlg.findChild(QtWidgets.QComboBox), dlg.findChild(QtWidgets.QLineEdit)
    combo.setCurrentIndex(1); edit.setText(" 2796.35 ")
    dlg.findChild(QtWidgets.QDialogButtonBox).accepted.emit()
QtCore.QTimer.singleShot(0, accept)
print("_ask ->", _ask(D()))
QtCore.QTimer.singleShot(0, lambda: next(w for w in app.topLevelWidgets() if isinstance(w, QtWidgets.QDialog) and w.isVisible()).reject())
print("_ask cancelled ->", _ask(D()))
