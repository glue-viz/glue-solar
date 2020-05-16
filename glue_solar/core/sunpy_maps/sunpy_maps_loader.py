import os
from pathlib import Path

from astropy.io import fits

from glue.core import Component, Data
from glue.core.coordinates import WCSCoordinates
from glue.core.visual import VisualAttributes
from glue.utils.qt import get_qapp
from glue.utils.qt.helpers import load_ui

import sunpy.map
import sunpy.data.sample

from qtpy import QtWidgets
from qtpy.QtCore import Qt


__all__ = ["QtSunpyMapImporter"]

UI_MAIN = os.path.join(os.path.dirname(__file__), 'sunpy_map_loader.ui')


class QtSunpyMapImporter(QtWidgets.QDialog):

    def __init__(self, directory):
        super().__init__()

        self.ui = load_ui(UI_MAIN, self)

        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.finalize)

        self.directory = Path(directory)
        self.sunpy_map_files = self.get_sunpy_map_filenames()

        self._sunpy_map_checkboxes = {}
        self.datasets = []

        self.populate_table_sunpy_maps()

    def get_sunpy_map_filenames(self):
        return list(self.directory.glob("*sunpy_map*"))

    def populate_table_sunpy_maps(self):
        windows = self.get_sunpy_map_windows()
        for window in windows:
            sub = QtWidgets.QTreeWidgetItem(self.sunpy_maps.invisibleRootItem())
            sub.setFlags(sub.flags() | Qt.ItemIsUserCheckable)
            sub.setCheckState(0, Qt.Unchecked)
            sub.setText(1, window)
            self._sunpy_map_checkboxes[window] = sub

        self.sunpy_maps.resizeColumnToContents(0)
        self.sunpy_maps.resizeColumnToContents(1)

    def get_sunpy_map_windows(self):
        windows = {}
        for sunpy_map_file in self.sunpy_map_files:
            with sunpy.map.Map(sunpy_map_file) as sunpy_map:
                windows[sunpy_map.name] = sunpy_map_file

        return windows

    def load_sunpy_maps(self, sunpy_maps):
        for sunpy_map in sunpy_maps:
            sunpy_map_loaded = sunpy.map.Map(sunpy_map)
            label = 'sunpy-map-' + sunpy_map_loaded.name
            data = Data(label=label)
            data.coords = sunpy_map_loaded.wcs
            data.meta = sunpy_map_loaded.meta
            data.add_component(Component(sunpy_map_loaded.data), sunpy_map_loaded.name)
            data.style = VisualAttributes(color='#FDB813', preferred_cmap=sunpy_map.cmap)

            self.datasets.append(data)

    def finalize(self):
        sunpy_map_windows = []
        sunpy_map_filenames = self.get_sunpy_map_windows()

        for name in self._sunpy_map_checkboxes:
            if self._sunpy_map_checkboxes[name].checkState(0) > 0:
                sunpy_map_windows.append(sunpy_map_filenames[name])

        n_windows = float(len(sunpy_map_windows))

        for iname, filename in enumerate(sunpy_map_windows):
            self.progress.setValue(iname / n_windows * 100.)

            # update progress bar
            app = get_qapp()
            app.processEvents()

            self.load_sunpy_maps(filename)

        self.progress.setValue(100)
        self.accept()

    def clear(self):
        self._checkboxes.clear()
        self.tree.clear()
