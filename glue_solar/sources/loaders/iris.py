import os
import tarfile
import threading
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
from .stack_spectrograms import MISSING_VALUES, stack_spectrogram_sequence

__all__ = ["WCS_LOCK", "QtIRISImporter", "image_data", "iris_data", "last_directory", "raster_data"]

UI_MAIN = os.path.join(os.path.dirname(__file__), "iris_loader.ui")
_SETTINGS = ("glue-solar", "glue-solar")
_LAST_DIR = "iris/last_dir"
# One name per axis type for every IRIS dataset, so Glue lines up SJI and raster axes: FITS-based irispy
# WCSes carry no axis names (Glue would say "World N") and gWCS ones say "Longitude" and "Latitude".
# Time keeps its own name, since the loader adds a "Time" component.
_AXIS_NAMES = {
    "em.wl": "Wavelength",
    "custom:pos.helioprojective.lon": "Helioprojective Longitude",
    "custom:pos.helioprojective.lat": "Helioprojective Latitude",
}


# wcslib is not thread-safe (astropy/astropy#19174), and Glue computes profiles and histograms in
# worker threads while WCSAxes draws on the GUI thread, all through the same raster WCS. Re-entrant
# because a _GlueWCS can wrap another; one lock for all, because derived datasets share a WCS.
# Code that uses the astropy WCS directly must hold it too.
WCS_LOCK = threading.RLock()


class _GlueWCS(BaseWCSWrapper):
    """Present named, signed helioprojective coordinates in arcseconds to Glue."""

    # glue's WCS link falls back to astropy FITS-WCS attributes (celestial, wcs.lng, ...) when a
    # WCS says it has celestial axes; this wrapper has none of them, so send glue down its APE-14 path
    has_celestial = False

    @property
    def axis_correlation_matrix(self):
        with WCS_LOCK:
            return self._wcs.axis_correlation_matrix

    @property
    def world_axis_names(self):
        return [
            _AXIS_NAMES.get(physical_type) or name or physical_type or ""
            for name, physical_type in zip(self._wcs.world_axis_names, self._wcs.world_axis_physical_types)
        ]

    @property
    def world_axis_units(self):
        return tuple(
            "arcsec" if physical_type and physical_type.startswith("custom:pos.helioprojective.") else unit
            for unit, physical_type in zip(self._wcs.world_axis_units, self._wcs.world_axis_physical_types)
        )

    def pixel_to_world_values(self, *pixel_arrays):
        with WCS_LOCK:
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
        with WCS_LOCK:
            return self._wcs.world_to_pixel_values(*values)


# Per-frame SJI pointing that irispy keeps as extra coordinates; the frame time tool shows it
_SJI_POINTING = ("pztx", "pzty", "xcenix", "ycenix", "slit x position")


def _per_frame(values, shape):
    """Broadcast values given for the leading axes of ``shape`` over the remaining axes, without copying."""
    values = np.asarray(values)
    return np.broadcast_to(values.reshape(values.shape + (1,) * (len(shape) - values.ndim)), shape)


def _cube_data(cube, label, *, color=None, cmap=None, missing=MISSING_VALUES, exposure=None):
    """
    Convert one irispy cube into one Glue dataset, with the ``missing`` data codes as NaN.

    ``exposure`` gives the exposure times in seconds for cubes that do not carry them, such as stacks.
    """
    data = Data(label=label)
    data.coords = _GlueWCS(cube.wcs.low_level_wcs)
    data.meta = cube.meta
    data.style = VisualAttributes(color=color, preferred_cmap=cmap)
    values = cube.data
    # From the values, not cube.mask: irispy <= 0.9.0 flips STEPS_AV < -0.01 rasters but not their mask.
    fill = np.isin(values, missing) if missing else None
    if fill is not None and fill.any():
        # In place for float data: this writes into irispy's cube, which the loader discards.
        values = values.astype(np.result_type(values.dtype, np.float32), copy=False)
        values[fill] = np.nan
    data.add_component(Component(values, units=str(cube.unit)), label)
    # Glue stores a bool component as int64, so view the NaN mask as one byte per sample
    data.add_component(Component(np.isnan(values).view(np.uint8)), f"{label} mask")
    times = _frame_times(cube)
    if times is not None:
        data.add_component(_per_frame(times, cube.shape), "Time")
    if exposure is None and getattr(cube, "exposure_time", None) is not None:
        exposure = cube.exposure_time.to_value(u.s)  # per raster step or SJI frame, in the data's order
    if exposure is not None:
        data.add_component(Component(_per_frame(exposure, cube.shape), units="s"), "Exposure time")
    if cube.extra_coords and set(_SJI_POINTING) <= set(cube.extra_coords.keys()):
        frames = np.arange(cube.shape[0])
        for name in _SJI_POINTING:
            data.meta[name] = cube.extra_coords[name].wcs.pixel_to_world_values(frames)
    return data


def _frame_times(cube):
    """UTC time of every step along the leading axis: raster exposures (extra coordinate) or SJI frames (gWCS axis)."""
    if cube.extra_coords and "time" in cube.extra_coords.keys():
        times = cube.axis_world_coords("time", wcs=cube.extra_coords)[0]
    elif "time" in cube.wcs.low_level_wcs.world_axis_physical_types:
        times = cube.axis_world_coords("time")[0]
    else:
        return None
    return times.utc.to_value("datetime64")


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
            exposure = np.stack([scan.exposure_time.to_value(u.s) for scan in sequence])
            # the stack already holds NaN, and its meta is scan 0's, so exposure times come per scan
            data = _cube_data(cube, label, color="#7A617C", missing=(), exposure=exposure)
            data.add_component(_per_frame(times, cube.shape), "Time")
            datasets.append(data)
            continue
        for i, scan in enumerate(sequence):
            label = f"{name}-{_observation_label(scan.meta)}-scan-{i}"
            datasets.append(_cube_data(scan, label, color="#5A4FCF"))
    return datasets


def _image_cube_data(cube, path):
    desc = str(cube.meta["TDESC1"])
    if "_deconvolved." in Path(path).name:  # the header does not say, the filename does
        desc += "_deconvolved"
    wave = int(cube.meta["TWAVE1"])
    if desc.startswith("SJI"):
        return _cube_data(cube, f"{desc}-{_observation_label(cube.meta)}", cmap=f"irissji{wave}")
    # -199 is unverified as a missing code in AIA cutouts
    return _cube_data(cube, f"{desc}-{_observation_label(cube.meta)}", cmap=f"sdoaia{wave}", missing=(-200,))


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
    return _image_cube_data(cube, path)


def iris_data(path):
    """Load one IRIS Level 2 file through irispy and convert its return shape."""
    loaded = read_files(path, memmap=False, uncertainty=False)
    if isinstance(loaded, Mapping):
        return _raster_collection_data(loaded)
    return _image_cube_data(loaded, path)


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
