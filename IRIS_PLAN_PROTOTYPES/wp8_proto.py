"""WP8 prototype: QtIRISImporter + text filter + Worker-threaded, cancellable scan."""

import functools
from pathlib import Path

from glue_qt.utils import Worker
from qtpy.QtCore import QSettings, QThread
from qtpy.QtWidgets import QApplication

from glue_solar.sources.loaders import iris
from glue_solar.sources.loaders.iris import _LAST_DIR, _SETTINGS, QtIRISImporter

import wp8_scan  # scan.py + `stop` kwarg

iris.UI_MAIN = str(Path(__file__).with_name("wp8_loader.ui"))  # the .ui edit under test


class ProtoImporter(QtIRISImporter):
    def __init__(self, directory=None, parent=None):
        self.worker = None
        self.scanning = False
        self._scan_id = 0
        self.populate_threads = []  # prototype-only: proves populate() runs on the GUI thread
        super().__init__(None, parent)
        self.filter.textChanged.connect(self._apply_filter)
        self.stop_scan.clicked.connect(self._stop_scan)
        self.finished.connect(self._stop_scan)  # closing the dialog never leaves a QThread running
        if directory:
            self.set_directory(directory)

    def set_directory(self, directory):
        if not directory:
            return
        self.directory.setText(str(directory))
        QSettings(*_SETTINGS).setValue(_LAST_DIR, str(directory))
        self._stop_scan()
        self._scan_id += 1  # results of the scan just cancelled are ignored by id
        self.worker = Worker(wp8_scan.scan_directory, str(directory), recursive=self.recursive.isChecked())
        self.worker.kwargs["stop"] = self.worker.isInterruptionRequested
        self.worker.result.connect(functools.partial(self._scanned, self._scan_id))
        self.worker.error.connect(functools.partial(self._scan_failed, self._scan_id))
        self.scanning = True
        self.progress.setRange(0, 0)  # busy
        self.progress.setFormat("%p%")
        self.stop_scan.setEnabled(True)
        self.worker.start()

    def _stop_scan(self, *_args):
        if self.scanning:
            self.worker.requestInterruption()
            self.worker.wait()  # never drop a Worker reference while its thread runs
            self.progress.setFormat("Scan stopped")

    def _scan_over(self, scan_id):
        if scan_id != self._scan_id:
            return False
        self.scanning = False
        self.progress.setRange(0, 100)
        if self.progress.value() < 0:  # preserve a completed extraction at 100
            self.progress.setValue(0)  # leave the reset state so status text is visible
        self.stop_scan.setEnabled(False)
        return True

    def _scanned(self, scan_id, observations):
        if self._scan_over(scan_id):
            self.observations = observations
            self.populate()

    def _scan_failed(self, scan_id, exc_info):
        if self._scan_over(scan_id):
            self.progress.setFormat(f"Scan failed: {exc_info[1]}")

    def populate(self):
        self.populate_threads.append(QThread.currentThread() == QApplication.instance().thread())
        super().populate()
        self._apply_filter()

    def _apply_filter(self):
        text = self.filter.text().casefold()
        for i in range(self.obs_tree.topLevelItemCount()):
            item = self.obs_tree.topLevelItem(i)
            item.setHidden(text not in " ".join(item.text(c) for c in range(3)).casefold())
