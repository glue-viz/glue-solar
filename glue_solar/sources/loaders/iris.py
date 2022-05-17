import os
from pathlib import Path

from glue.core.component import Component
from glue.core.coordinates import WCSCoordinates
from glue.core.data import Data
from glue.core.visual import VisualAttributes
from glue.utils.qt import get_qapp
from glue.utils.qt.helpers import load_ui
from irispy.io import read_files
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from astropy.io import fits

from .stack_spectrograms import stack_spectrogram_sequence

__all__ = ["QtIRISImporter"]

UI_MAIN = os.path.join(os.path.dirname(__file__), "iris_loader.ui")


class QtIRISImporter(QtWidgets.QDialog):
    """
    Qt importer to load IRIS Level 2 data objects from fits files.
    """

    def __init__(self, directory):
        super().__init__()

        self.ui = load_ui(UI_MAIN, self)

        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.finalize)

        self.directory = Path(directory)
        self.raster_files = self.get_raster_filenames()
        self.sji_files = self.get_sji_filenames()

        self._raster_checkboxes = {}
        self._sji_checkboxes = {}
        self.datasets = []

        self.populate_table_raster()
        self.populate_table_sji()

    def get_raster_filenames(self):
        return list(self.directory.glob("*raster*"))

    def get_sji_filenames(self):
        return list(self.directory.glob("*SJI*"))

    def populate_table_raster(self):
        windows = self.get_raster_windows()
        for window in windows:
            sub = QtWidgets.QTreeWidgetItem(self.rasters.invisibleRootItem())
            sub.setFlags(sub.flags() | Qt.ItemIsUserCheckable)
            sub.setCheckState(0, Qt.Unchecked)
            sub.setText(1, window)
            self._raster_checkboxes[window] = sub

        self.rasters.resizeColumnToContents(0)
        self.rasters.resizeColumnToContents(1)

    def populate_table_sji(self):
        windows = self.get_sji_windows().keys()
        for window in windows:
            sub = QtWidgets.QTreeWidgetItem(self.sjis.invisibleRootItem())
            sub.setFlags(sub.flags() | Qt.ItemIsUserCheckable)
            sub.setCheckState(0, Qt.Unchecked)
            sub.setText(1, window)
            self._sji_checkboxes[window] = sub

        self.sjis.resizeColumnToContents(0)
        self.sjis.resizeColumnToContents(1)

    def get_raster_windows(self):
        with fits.open(self.raster_files[0]) as hdulist:
            return list(
                hdulist[0].header["TDESC{0}".format(i)]
                for i in range(1, hdulist[0].header["NWIN"] + 1)
            )

    def get_sji_windows(self):
        windows = {}
        for sji in self.sji_files:
            with fits.open(sji) as hdul:
                windows[hdul[0].header["TDESC1"]] = sji

        return windows

    def load_sji(self, sji):
        with fits.open(sji) as hdul:
            hdul.verify("fix")
            label = hdul[0].header["TDESC1"] + hdul[0].header["OBSID"]
            data = Data(label=label)
            data.coords = WCSCoordinates(hdul[0].header)
            data.meta = hdul[0].header
            preferred_cmap_name = "IRIS " + hdul[0].header["TDESC1"].replace("_", " ")
            data.style = VisualAttributes(preferred_cmap=preferred_cmap_name)
            data.add_component(Component(hdul[0].data), label)

            self.datasets.append(data)

    def load_rasters(self, windows):
        raster_data = read_files(
            self.raster_files, spectral_windows=windows, memmap=False, uncertainty=False
        )

        if self.stack.checkState() > 0:
            raster_data = {
                window: stack_spectrogram_sequence(seq)
                for window, seq in raster_data.items()
            }
            self.load_stacked_sequence(raster_data)
        else:
            self.load_sequence(raster_data)

    def load_sequence(self, raster_data):
        for window, window_data in raster_data.items():
            for i, scan_data in enumerate(window_data):
                w_data = Data(
                    label=f"{window.replace(' ', '_')}-{scan_data.meta['OBSID']}-scan-{i}"
                )
                w_data.coords = scan_data.wcs
                w_data.add_component(
                    Component(scan_data.data), f"{window.replace(' ', '_')}-scan-{i}"
                )
                w_data.meta = scan_data.meta
                w_data.style = VisualAttributes(color="#5A4FCF")
                self.datasets.append(w_data)

    def load_stacked_sequence(self, raster_data):
        for window, window_data in raster_data.items():
            w_data = Data(label=f"{window.replace(' ', '_')}")
            w_data.coords = window_data.wcs
            w_data.add_component(
                Component(window_data.data), f"{window.replace(' ', '_')}"
            )
            w_data.style = VisualAttributes(color="#7A617C")
            self.datasets.append(w_data)

    def finalize(self):
        raster_windows = []
        sji_windows = []
        sji_filenames = self.get_sji_windows()

        for name in self._raster_checkboxes:
            if self._raster_checkboxes[name].checkState(0) > 0:
                raster_windows.append(name)

        for name in self._sji_checkboxes:
            if self._sji_checkboxes[name].checkState(0) > 0:
                sji_windows.append(sji_filenames[name])

        n_windows = float(len(raster_windows) + len(sji_windows))

        for iname, filename in enumerate(sji_windows):
            self.progress.setValue(iname / n_windows * 100.0)

            # update progress bar
            app = get_qapp()
            app.processEvents()

            self.load_sji(filename)

        for iname, name in enumerate(raster_windows):

            self.progress.setValue((iname + len(sji_windows)) / n_windows * 100.0)

            # update progress bar
            app = get_qapp()
            app.processEvents()

            self.load_rasters([name])

        self.progress.setValue(100)
        self.accept()

    def clear(self):
        self._checkboxes.clear()
        self.tree.clear()
