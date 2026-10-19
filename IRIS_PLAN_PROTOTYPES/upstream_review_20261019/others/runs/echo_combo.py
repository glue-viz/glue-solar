import echo, matplotlib
from matplotlib import colormaps
from qtpy.QtWidgets import QApplication, QComboBox
from echo.qt.connect import _find_combo_data, UserDataWrapper
from sunpy.visualization.colormaps import cmlist
app = QApplication([])
combo = QComboBox()
for key in ("goes-rsuvi171", "sdoaia171"):
    combo.addItem(key, UserDataWrapper(cmlist[key]))
idx = _find_combo_data(combo, colormaps["sdoaia171"])
print(f"echo {echo.__version__}: sdoaia171 matched entry {idx} ({combo.itemText(idx)}); equal colors: {cmlist['goes-rsuvi171'] == cmlist['sdoaia171']}")
