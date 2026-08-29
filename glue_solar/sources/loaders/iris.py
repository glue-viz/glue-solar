import os
import tarfile
from collections.abc import Mapping
from pathlib import Path

import numpy as np
from glue.core.component import Component
from glue.core.data import Data
from glue.core.visual import VisualAttributes
from glue_qt.utils import get_qapp, load_ui
from irispy.io import read_files
from qtpy import QtWidgets
from qtpy.QtCore import QSettings, Qt

import astropy.units as u
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper

from .scan import extract_archive, scan_directory
from .stack_spectrograms import stack_spectrogram_sequence

__all__ = ["QtIRISImporter", "image_data", "iris_data", "last_directory", "raster_data"]

UI_MAIN = os.path.join(os.path.dirname(__file__), "iris_loader.ui")
_SETTINGS = ("glue-solar", "glue-solar")
_LAST_DIR = "iris/last_dir"
# FITS-based irispy WCSes carry no axis names, so Glue would label them "World N"
_AXIS_NAMES = {
    "em.wl": "Wavelength",
    "custom:pos.helioprojective.lon": "Helioprojective Longitude",
    "custom:pos.helioprojective.lat": "Helioprojective Latitude",
    "time": "Time",
}


class _GlueWCS(BaseWCSWrapper):
    """Present named, signed helioprojective coordinates in arcseconds to Glue."""

    @property
    def world_axis_names(self):
        return [
            name or _AXIS_NAMES.get(physical_type) or physical_type or ""
            for name, physical_type in zip(self._wcs.world_axis_names, self._wcs.world_axis_physical_types)
        ]

    @property
    def world_axis_units(self):
        return tuple(
            "arcsec" if physical_type and physical_type.startswith("custom:pos.helioprojective.") else unit
            for unit, physical_type in zip(self._wcs.world_axis_units, self._wcs.world_axis_physical_types)
        )

    def pixel_to_world_values(self, *pixel_arrays):
        values = list(self._wcs.pixel_to_world_values(*pixel_arrays))
        for i, physical_type in enumerate(self.world_axis_physical_types):
            if physical_type and physical_type.startswith("custom:pos.helioprojective."):
                unit = u.Unit(self._wcs.world_axis_units[i])
                values[i] = np.asarray(values[i])
                if physical_type.endswith(".lon"):
                    full_circle = (360 * u.deg).to_value(unit)
                    values[i] = (values[i] + full_circle / 2) % full_circle - full_circle / 2
                values[i] = (values[i] * unit).to_value(u.arcsec)
        return tuple(values)

    def world_to_pixel_values(self, *world_arrays):
        values = list(world_arrays)
        for i, physical_type in enumerate(self.world_axis_physical_types):
            if physical_type and physical_type.startswith("custom:pos.helioprojective."):
                values[i] = (np.asarray(values[i]) * u.arcsec).to_value(u.Unit(self._wcs.world_axis_units[i]))
        return self._wcs.world_to_pixel_values(*values)


def _cube_data(cube, label, *, color=None, cmap=None):
    """Convert one irispy cube into one Glue dataset."""
    data = Data(label=label)
    data.coords = _GlueWCS(cube.wcs.low_level_wcs)
    data.meta = cube.meta
    data.style = VisualAttributes(color=color, preferred_cmap=cmap)
    data.add_component(Component(cube.data, units=str(cube.unit)), label)
    if cube.mask is not None:
        data.add_component(Component(np.asarray(cube.mask, dtype=bool)), f"{label} mask")
    if cube.extra_coords and "time" in cube.extra_coords.keys():
        times = cube.axis_world_coords("time", wcs=cube.extra_coords)[0].utc.to_value("datetime64")
        times = np.broadcast_to(times.reshape((len(times),) + (1,) * (cube.data.ndim - 1)), cube.shape)
        data.add_component(times, "Time")
    return data


def _observation_label(meta):
    obsid = str(meta["OBSID"]).split("_")[-1]
    return "-".join(filter(None, (obsid, str(meta.get("STARTOBS", ""))[:19])))


def _raster_collection_data(collection, windows=None, stack=False):
    datasets = []
    for window, sequence in collection.items():
        name = str(window).replace(" ", "_")
        if stack and len(sequence) > 1:
            cube, times = stack_spectrogram_sequence(sequence)
            label = f"{name}-{_observation_label(cube.meta)}-stack"
            data = _cube_data(cube, label, color="#7A617C")
            data.add_component(np.broadcast_to(times[..., np.newaxis], cube.shape), "Time")
            datasets.append(data)
            continue
        for i, scan in enumerate(sequence):
            label = f"{name}-{_observation_label(scan.meta)}-scan-{i}"
            datasets.append(_cube_data(scan, label, color="#5A4FCF"))
    return datasets


def _image_cube_data(cube):
    desc = str(cube.meta["TDESC1"])
    wave = int(cube.meta["TWAVE1"])
    cmap = f"irissji{wave}" if desc.startswith("SJI") else f"sdoaia{wave}"
    return _cube_data(cube, f"{desc}-{_observation_label(cube.meta)}", cmap=cmap)


def last_directory():
    """The folder the user browsed last time (home directory if never)."""
    return str(QSettings(*_SETTINGS).value(_LAST_DIR, str(Path.home())))


def image_data(path):
    """
    Load an SJI or AIA-cutout file through irispy.

    Returns
    -------
    `~glue.core.data.Data`
    """
    cube = read_files(path, memmap=False, uncertainty=False)
    return _image_cube_data(cube)


def iris_data(path):
    """Load one IRIS Level 2 file through irispy and convert its return shape."""
    loaded = read_files(path, memmap=False, uncertainty=False)
    if isinstance(loaded, Mapping):
        return _raster_collection_data(loaded)
    return _image_cube_data(loaded)


def raster_data(files, windows=None, stack=False):
    """
    Load the given spectral windows from a set of raster files of one observation.

    Parameters
    ----------
    files : list of path-like
        Raster files (``*_raster_t000_r*.fits``) of one observation.
    windows : list of str, optional
        ``TDESC`` names of the spectral windows to load; all of them if omitted.
    stack : bool
        Stack two or more scans of each window without resampling and return a single 4D cube
        with a leading ``Scan`` axis. Scan 0 supplies the nominal spatial WCS and exact
        acquisition times are stored in the ``Time`` component. A window containing one scan
        loads normally as a 3D dataset.

    Returns
    -------
    list of `~glue.core.data.Data`
        One per scan and window, or one per window when ``stack`` is set.
    """
    collection = read_files(files, spectral_windows=windows, memmap=False, uncertainty=False)
    return _raster_collection_data(collection, windows, stack)


def _fmt(value):
    return "" if value is None else f"{round(value, 1) + 0.0:.1f}"  # + 0.0 turns -0.0 into 0.0


class QtIRISImporter(QtWidgets.QDialog):
    """
    Browse a folder of IRIS Level 2 files by observation and load a selection.

    After ``exec()`` returns ``Accepted``, ``datasets`` holds the loaded
    `~glue.core.data.Data` objects and ``first_image`` the first SJI/AIA cube
    (the natural thing to open in an image viewer).
    """

    def __init__(self, directory=None, parent=None):
        super().__init__(parent)
        self.ui = load_ui(UI_MAIN, self)
        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.finalize)
        self.change.clicked.connect(self.choose_directory)
        self.recursive.toggled.connect(lambda _checked: self.set_directory(self.directory.text()))
        self.observations = []
        self.datasets = []
        self.first_image = None
        self._payloads = []
        self.stack.setToolTip(
            "Stack two or more raster scans by detector position into one 4D cube. "
            "Scan 0 supplies the nominal spatial coordinates; exact acquisition times are retained."
        )
        if directory:
            self.set_directory(directory)

    def choose_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select a folder containing IRIS Level 2 files", self.directory.text() or last_directory()
        )
        if directory:
            self.set_directory(directory)

    def set_directory(self, directory):
        if not directory:
            return
        self.directory.setText(str(directory))
        QSettings(*_SETTINGS).setValue(_LAST_DIR, str(directory))
        self.observations = scan_directory(directory, recursive=self.recursive.isChecked())
        self.populate()

    def populate(self):
        self.obs_tree.clear()
        self._payloads = []
        for i, obs in enumerate(self.observations):
            top = QtWidgets.QTreeWidgetItem(
                self.obs_tree,
                [
                    obs.startobs,
                    obs.obsid,
                    obs.description,
                    _fmt(obs.xcen),
                    _fmt(obs.ycen),
                    _fmt(obs.sat_rot),
                    str(obs.nfiles),
                ],
            )
            entries = [(band, (i, "sji", band)) for band in sorted(obs.sji)]
            entries += [(f"{w} — {len(obs.rasters)} raster file(s)", (i, "raster", w)) for w in obs.windows]
            entries += [(f"AIA {band}", (i, "sdo", band)) for band in sorted(obs.sdo)]
            entries += [
                (f"Extract {a.name} ({a.stat().st_size / 1e6:.0f} MB, next to the archive)", (i, "archive", a))
                for a in obs.archives
            ]
            top.setCheckState(0, Qt.Unchecked)
            if len(entries) == 1:
                # one thing to load: the row itself is the tick box, no need for a child
                text, payload = entries[0]
                top.setText(6, f"{obs.nfiles} — {text}")
                self._make_checkable(top, payload)
            else:
                # ticking the observation ticks everything under it
                top.setFlags(top.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
                for text, payload in entries:
                    child = self._make_checkable(QtWidgets.QTreeWidgetItem(top, [text]), payload)
                    child.setFirstColumnSpanned(True)  # don't squeeze the label into the STARTOBS column
        for column in range(self.obs_tree.columnCount()):
            self.obs_tree.resizeColumnToContents(column)

    def _make_checkable(self, item, payload):
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Unchecked)
        item.setData(0, Qt.UserRole, len(self._payloads))
        self._payloads.append(payload)
        return item

    def selected(self):
        """``(observation index, kind, name)`` for every ticked loadable entry."""
        picks = []
        root = self.obs_tree.invisibleRootItem()
        items = [root.child(i) for i in range(root.childCount())]
        items += [top.child(j) for top in items for j in range(top.childCount())]
        for item in items:
            if item.data(0, Qt.UserRole) is not None and item.checkState(0) == Qt.Checked:
                picks.append(self._payloads[item.data(0, Qt.UserRole)])
        return picks

    def finalize(self):
        self.progress.setFormat("%p%")
        picks = self.selected()
        archives = [name for _, kind, name in picks if kind == "archive"]
        if archives:
            # Unpack, rescan and stay open so the user can pick from what was inside.
            for n, archive in enumerate(archives):
                self.progress.setValue(int(100 * n / len(archives)))
                get_qapp().processEvents()
                try:
                    extract_archive(archive)
                except (OSError, tarfile.TarError) as error:
                    self.set_directory(self.directory.text())
                    self.progress.setFormat(f"Extraction failed: {error}")
                    return
            self.set_directory(self.directory.text())
            self.progress.setValue(100)
            self.progress.setFormat(f"Extracted {len(archives)} archive(s) — now tick what to load")
            return
        self.datasets, self.first_image = [], None
        for n, (i, kind, name) in enumerate(picks):
            self.progress.setValue(int(100 * n / len(picks)))
            get_qapp().processEvents()
            obs = self.observations[i]
            try:
                if kind == "raster":
                    self.datasets.extend(raster_data(obs.rasters, [name], stack=self.stack.isChecked()))
                else:
                    image = image_data(obs.sji[name] if kind == "sji" else obs.sdo[name])
                    self.datasets.append(image)
                    self.first_image = self.first_image or image
            except Exception as error:  # noqa: BLE001 - third-party reader errors must stay inside the dialog
                self.progress.setFormat(f"Loading {name} failed: {error}")
                return
        self.progress.setValue(100)
        self.accept()
