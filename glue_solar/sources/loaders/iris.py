import base64
import gzip
import inspect
import io
import itertools
import json
import os
import re
import tarfile
import threading
import traceback
import warnings
from collections import OrderedDict
from functools import cached_property, partial
from operator import attrgetter
from pathlib import Path

import numpy as np
from glue.core.component import Component
from glue.core.component_id import ComponentID
from glue.core.component_link import ComponentLink
from glue.core.data import Data
from glue.core.data_factories import LoadLog
from glue.core.hub import HubListener
from glue.core.link_helpers import LinkSame, LinkSameWithUnits
from glue.core.message import DataCollectionDeleteMessage
from glue.core.state import GlueSerializeError
from glue_qt.utils import load_ui
from glue_qt.utils.threading import Worker
from qtpy import QtGui, QtWidgets
from qtpy.QtCore import QSettings, Qt, QTimer, Signal

import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS, WCSHDO_P17, WCSHDO_all
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper, SlicedLowLevelWCS

from ..maps import _Style
from .lazy import LazyData, RawComponent, RawStack, allow_open_files, fill_mask
from .scan import _primary_header, extract_archive, scan_directory
from .stack_spectrograms import MISSING_VALUES, _PerScanWCS, stack_spectrogram_sequence, stack_times, stack_wcs

__all__ = [
    "WCS_LOCK",
    "QtIRISImporter",
    "image_data",
    "iris_data",
    "keep_hpc_linked",
    "last_directory",
    "load_entry",
    "link_hpc",
    "raster_data",
    "raster_files_data",
]

# Load data stored as int16, as Level 2 files store it, lazily: the raw integers stay in the file (in memory for a
# .fits.gz file) and are scaled where glue reads them. False loads everything in memory through irispy, as before
# (float32 where fill becomes NaN).
LAZY = True

UI_MAIN = os.path.join(os.path.dirname(__file__), "iris_loader.ui")
_SETTINGS = ("glue-solar", "glue-solar")
_LAST_DIR = "iris/last_dir"
_RECENT = "iris/recent"  # JSON [[folder, start, end], ...] of the latest searches, newest first
_PLACES = "iris/places"  # JSON [[name, folder], ...] of the saved folders
_OPTIONS = ("recursive", "stack", "quicklook")  # the browser's tick boxes, kept as left under iris/<name>
_RECENT_SEARCHES = 10
# One name per axis type for every IRIS dataset, so Glue lines up SJI and raster axes: FITS-based irispy
# WCSes carry no axis names (Glue would say "World N") and gWCS ones say "Longitude" and "Latitude".
# Time keeps its own name, since the loader adds a "Time" component.
_AXIS_NAMES = {
    "em.wl": "Wavelength",
    "custom:pos.helioprojective.lon": "Helioprojective Longitude",
    "custom:pos.helioprojective.lat": "Helioprojective Latitude",
}
_HPC = ("custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat")


# wcslib is not thread-safe (astropy/astropy#19174), and Glue computes profiles and histograms in
# worker threads while WCSAxes draws on the GUI thread, all through the same raster WCS. Re-entrant
# because a _GlueWCS can wrap another; one lock for all, because derived datasets share a WCS.
# Code that uses the astropy WCS directly must hold it too. Always on, since the race cannot be probed
# safely; it can go once an astropy release fixes #19174 and the thread test passes without it.
WCS_LOCK = threading.RLock()

# WCSAxes converts the same pixels about twice in each draw, and all of them again at every redraw; one
# raster's three quicklook panels ask about 60 different questions. Bounded by entries, and by samples per
# input and output array: at most about 25 MB per dataset. Always on; it can go once WCSAxes memoizes its
# own conversions in each tick placement (wp0-perf-astropy-irispy).
_MEMO_ENTRIES = 128
_MEMO_SAMPLES = 4096


def _copies(values):
    """``values`` with its arrays copied; scalars cannot be changed."""
    return tuple(value.copy() if isinstance(value, np.ndarray) else value for value in values)


def _shown_unit(physical_type):
    """The unit Glue is shown a world axis of this physical type in, or None for the wrapped WCS's own."""
    if physical_type == "em.wl":
        return u.AA
    if physical_type and physical_type.startswith("custom:pos.helioprojective."):
        return u.arcsec
    return None


class _GlueWCS(BaseWCSWrapper):
    """
    Present named, signed helioprojective coordinates in arcseconds and wavelengths in Angstrom to Glue,
    through its values, units and high-level objects alike.
    """

    # glue's WCS link falls back to astropy FITS-WCS attributes (celestial, wcs.lng, ...) when a
    # WCS says it has celestial axes; this wrapper has none of them, so send glue down its APE-14 path.
    # Always on, and harmless once glue checks for an astropy WCS instead (glue-viz/glue#2595, draft).
    has_celestial = False
    # Arcsec added to the wrapped WCS's helioprojective longitude and latitude ('Shift pointing…'): a shift in the
    # plane of the sky, small enough to add to both. Set it whole, never in place: the memo keys on it.
    pointing_offset = (0.0, 0.0)

    def __init__(self, wcs):
        super().__init__(wcs)
        self._memo = OrderedDict()  # pixel_to_world_values by its exact inputs, least recently used first
        # glue converts on worker threads too. The memo has its own lock, held only to read or add an entry:
        # holding WCS_LOCK through the unit arithmetic as well lets a busy thread starve the others.
        self._memo_lock = threading.Lock()

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
            unit if (shown := _shown_unit(physical_type)) is None else shown.to_string()
            for unit, physical_type in zip(self._wcs.world_axis_units, self._wcs.world_axis_physical_types)
        )

    @cached_property
    def _converted(self):
        """
        Each world axis shown in another unit: its index, its unit's scale to the shown unit and back, for the
        longitude the full circle in its unit, and for an angle its place in `pointing_offset`; worked out once, since
        WCSAxes converts every draw.
        """
        axes = []
        for i, (unit, physical_type) in enumerate(zip(self._wcs.world_axis_units, self.world_axis_physical_types)):
            shown = _shown_unit(physical_type)
            if shown is not None:
                unit = u.Unit(unit)
                full_circle = (360 * u.deg).to_value(unit) if physical_type.endswith(".lon") else None
                angle = _HPC.index(physical_type) if physical_type in _HPC else None
                # the scales a Quantity conversion multiplies by
                axes.append((i, unit.to(shown), shown.to(unit), full_circle, angle))
        return axes

    def pixel_to_world_values(self, *pixel_arrays):
        # The same inputs give the same values: the wrapped WCS is never changed once loaded (glue-solar
        # changes none, and WCSAxes calls wcs.set() only on an astropy WCS it is given, never through this
        # wrapper). So identical inputs reuse the values, each caller with its own copy. Identical means
        # the same type (a scalar and a 0-d array can come back differently), dtype, shape and bytes, at one offset.
        arrays = [np.asarray(pixel) for pixel in pixel_arrays]
        key, offset = None, self.pointing_offset
        if all(array.dtype.kind in "biuf" and array.size <= _MEMO_SAMPLES for array in arrays):
            key = (offset, *((type(p), a.dtype.str, a.shape, a.tobytes()) for p, a in zip(pixel_arrays, arrays)))
            with self._memo_lock:
                kept = self._memo.get(key)
                if kept is not None:
                    self._memo.move_to_end(key)
            if kept is not None:
                return _copies(kept)
        with WCS_LOCK:
            values = list(self._wcs.pixel_to_world_values(*pixel_arrays))
        for i, to_shown, _, full_circle, angle in self._converted:
            values[i] = np.asarray(values[i])
            if full_circle is not None:
                values[i] = (values[i] + full_circle / 2) % full_circle - full_circle / 2
            values[i] = values[i] * to_shown
            if angle is not None and offset[angle]:
                values[i] = values[i] + offset[angle]
        if key is not None and all(np.size(value) <= _MEMO_SAMPLES for value in values):  # inputs can broadcast
            kept = _copies(values)
            with self._memo_lock:
                self._memo[key] = kept
                if len(self._memo) > _MEMO_ENTRIES:
                    self._memo.popitem(last=False)
        return tuple(values)

    def world_to_pixel_values(self, *world_arrays):
        values, offset = list(world_arrays), self.pointing_offset
        for i, _, from_shown, full_circle, angle in self._converted:
            values[i] = np.asarray(values[i])
            if angle is not None and offset[angle]:
                values[i] = values[i] - offset[angle]
            values[i] = values[i] * from_shown
            if full_circle is not None:  # a longitude in any turn, as a sunpy map's run from 0 to 360 degrees
                values[i] = (values[i] + full_circle / 2) % full_circle - full_circle / 2
        with WCS_LOCK:
            return self._wcs.world_to_pixel_values(*values)

    @cached_property
    def world_axis_object_components(self):
        # The wrapped WCS's, with each converted value in its shown unit, so that high-level objects (glue's WCS
        # link) agree with the values. A SkyCoord gives a helioprojective longitude within +-180 deg already.
        with WCS_LOCK:  # an astropy WCS reads wcslib for these
            components = list(self._wcs.world_axis_object_components)
        for i, to_shown, *_ in self._converted:
            key, attr, value = components[i]
            value = value if callable(value) else attrgetter(value)
            components[i] = (key, attr, lambda obj, value=value, scale=to_shown: np.asarray(value(obj)) * scale)
        return components

    @cached_property
    def world_axis_object_classes(self):
        # The wrapped WCS's, each built from values in their shown units: back to the wrapped WCS's units first
        with WCS_LOCK:
            components, classes = self._wcs.world_axis_object_components, dict(self._wcs.world_axis_object_classes)
        scales = {}
        for i, _, from_shown, *_ in self._converted:
            key, attr, _ = components[i]
            scales.setdefault(key, {})[attr] = from_shown
        for key, scale in scales.items():
            klass, args, kwargs, *factory = classes[key]

            def build(*values, _make=factory[0] if factory else klass, _cls=klass, _scale=scale, **named):
                # high-level objects, as world_to_pixel passes them, go through as they are
                values = [v * _scale[n] if n in _scale and not isinstance(v, _cls) else v for n, v in enumerate(values)]
                named = {n: v * _scale[n] if n in _scale and not isinstance(v, _cls) else v for n, v in named.items()}
                return _make(*values, **named)

            classes[key] = (klass, args, kwargs, build)
        return classes

    # glue saves a dataset's coordinates in its session, those of data it reloads from a file too
    def __gluestate__(self, context):
        with WCS_LOCK:  # astropy writes a FITS WCS's header through wcslib
            wcs = _wcs_state(self._wcs)
        return {"wcs": wcs, "pointing_offset": [float(offset) for offset in self.pointing_offset]}

    @classmethod
    def __setgluestate__(cls, rec, context):
        wcs = cls(_wcs_from_state(rec["wcs"]))
        wcs.pointing_offset = tuple(rec["pointing_offset"])
        return wcs


def _lookup_table(wcs, header):
    """
    The lookup table of ``wcs``, an irispy raster's FITS-TAB WCS of FITS ``header``, as a FITS file: astropy reads the
    table of a WCS but cannot write it.
    """
    # ponytail: irispy's layout (irispy.io.spectrograph._create_tabular_wcs): one table, an identity PC matrix, and an
    # index vector, where an axis has one, linear from its first pixel to its last, since astropy gives a table's
    # coordinates but not its index vectors; the session tests fail if irispy's layout changes.
    (table,) = wcs.wcs.tab
    columns = {header[f"PS{table.map[0] + 1}_1"]: table.coord}
    for m, i in enumerate(table.map):
        if f"PS{i + 1}_2" in header:
            psi = wcs.wcs.crval[i] + wcs.wcs.cdelt[i] * (np.array([1, wcs.pixel_shape[i]]) - wcs.wcs.crpix[i])
            columns[header[f"PS{i + 1}_2"]] = np.linspace(*psi, table.K[m])
    row = np.array([tuple(columns.values())], dtype=[(name, float, value.shape) for name, value in columns.items()])
    buffer = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(row, name=header[f"PS{table.map[0] + 1}_0"])]).writeto(buffer)
    return buffer.getvalue()


def _wcs_state(wcs):
    """
    A JSON record of ``wcs``, the low-level WCS of any dataset glue-solar makes, for a session: each wrapper with what
    it wraps, a gWCS in ASDF, its own format, and a FITS WCS as its header and lookup table.
    """
    from ndcube.wcs.wrappers import ResampledLowLevelWCS

    from gwcs import WCS as GWCS

    from glue_solar.regrid import _Broadcast, _NorthUp, _Regridded  # which imports this module

    if isinstance(wcs, GWCS):  # a slit-jaw image's
        import asdf

        buffer = io.BytesIO()
        asdf.AsdfFile({"wcs": wcs}).write_to(buffer)
        return {"type": "gwcs", "asdf": base64.b64encode(buffer.getvalue()).decode()}
    if isinstance(wcs, WCS):
        header = wcs.to_header_string(relax=WCSHDO_all | WCSHDO_P17)  # every keyword, every digit
        table = _lookup_table(wcs, fits.Header.fromstring(header)) if wcs.wcs.tab else b""  # a raster's
        return {"type": "fits", "header": header, "shape": wcs.pixel_shape, "table": base64.b64encode(table).decode()}
    if isinstance(wcs, _GlueWCS):  # a north-up grid's
        return {"type": "_GlueWCS", **wcs.__gluestate__(None)}
    if isinstance(wcs, _PerScanWCS):  # `stack_wcs` of its scans'
        return {"type": "_PerScanWCS", "scans": [_wcs_state(scan) for scan in wcs._wcses]}
    if not isinstance(wcs, (SlicedLowLevelWCS, ResampledLowLevelWCS, _Regridded, _NorthUp, _Broadcast)):
        raise GlueSerializeError(f"A session cannot save coordinates of type {type(wcs).__name__}")
    state = {"type": type(wcs).__name__, "wcs": _wcs_state(wcs._wcs)}
    if isinstance(wcs, SlicedLowLevelWCS):
        state["slices"] = [[s.start, s.stop, s.step] if isinstance(s, slice) else int(s) for s in wcs._slices_array]
    elif isinstance(wcs, ResampledLowLevelWCS):
        state.update(factor=wcs._factor.tolist(), offset=wcs._offset.tolist())
    elif isinstance(wcs, _Regridded):
        state["positions"] = wcs._positions.tolist()
    elif isinstance(wcs, _NorthUp):
        state.update(tan=_wcs_state(wcs._tan), times=np.asarray(wcs._times).tolist())
    return state


def _wcs_from_state(state):
    """The low-level WCS of a `_wcs_state` record."""
    from ndcube.wcs.wrappers import ResampledLowLevelWCS

    from glue_solar.regrid import _Broadcast, _NorthUp, _Regridded

    kind = state["type"]
    if kind == "gwcs":
        import asdf

        with asdf.open(io.BytesIO(base64.b64decode(state["asdf"])), lazy_load=False, memmap=False) as file:
            return file["wcs"]
    if kind == "fits":
        table = base64.b64decode(state["table"])
        wcs = WCS(fits.Header.fromstring(state["header"]), fits.open(io.BytesIO(table)) if table else None)
        wcs.pixel_shape = state["shape"]  # which a header leaves out
        return wcs
    if kind == "_GlueWCS":
        return _GlueWCS.__setgluestate__(state, None)
    if kind == "_PerScanWCS":
        return stack_wcs([_wcs_from_state(scan) for scan in state["scans"]])
    wcs = _wcs_from_state(state["wcs"])
    if kind == "SlicedLowLevelWCS":
        return SlicedLowLevelWCS(wcs, [slice(*s) if isinstance(s, list) else s for s in state["slices"]])
    if kind == "ResampledLowLevelWCS":
        return ResampledLowLevelWCS(wcs, state["factor"], state["offset"])
    if kind == "_Regridded":
        return _Regridded(wcs, np.array(state["positions"]))
    if kind == "_NorthUp":
        return _NorthUp(wcs, _wcs_from_state(state["tan"]), np.array(state["times"]))
    return _Broadcast(wcs)


# Per-frame SJI pointing that irispy keeps as extra coordinates; the frame time tool shows it
_SJI_POINTING = ("pztx", "pzty", "xcenix", "ycenix", "slit x position")


def _per_frame(values, shape):
    """Broadcast values given for the leading axes of ``shape`` over the remaining axes, without copying."""
    values = np.asarray(values)
    return np.broadcast_to(values.reshape(values.shape + (1,) * (len(shape) - values.ndim)), shape)


def per_second(flux, exposure):
    """``flux`` over a positive ``exposure`` time, else NaN, in the precision of ``flux`` (float32 for IRIS data)."""
    return flux / np.where(exposure > 0, exposure, np.nan).astype(np.float32)


def _add_exposure(data, exposure):
    """
    Add ``Exposure time``, ``exposure`` in seconds over the leading axes, and ``<label> DN/s``, the data over it as a
    glue derived component.
    """
    seconds = data.add_component(Component(_per_frame(exposure, data.shape), units="s"), "Exposure time")
    flux = data.main_components[0]
    rate = ComponentLink([flux, seconds], ComponentID(f"{flux.label} DN/s", parent=data), using=per_second)
    data.add_component_link(rate).units = "DN/s"


def _dataset(wcs, meta, unit, values, label, *, color=None, cmap=None, missing=MISSING_VALUES, scaling=None):
    """
    A Glue dataset of ``values`` and their mask, with the ``missing`` data codes as NaN.

    ``scaling`` is the ``(BSCALE, BZERO)`` of ``values`` that are a file's raw int16 (`_raw_scaling`), which then
    stay where they are and are scaled where glue reads them.
    """
    data = (Data if scaling is None else LazyData)(label=label)
    data.coords = _GlueWCS(wcs)
    data.meta = meta
    data.style = _Style(color=color, preferred_cmap=cmap)
    if scaling is not None:
        cid = data.add_component(RawComponent(values, *scaling, missing, units=str(unit)), label)
        # a glue derived component, computed from the values glue reads
        data.add_component_link(ComponentLink([cid], ComponentID(f"{label} mask", parent=data), using=fill_mask))
        return data
    # From the values: irispy's eager reads leave the missing codes in raster windows and -200 in integer AIA cutouts
    fill = np.isin(values, missing) if missing else None
    if fill is not None and fill.any():
        # In place for float data: this writes into irispy's cube, which the loader discards.
        values = values.astype(np.result_type(values.dtype, np.float32), copy=False)
        values[fill] = np.nan
    data.add_component(Component(values, units=str(unit)), label)
    # Glue stores a bool component as int64, so view the NaN mask as one byte per sample
    data.add_component(Component(np.isnan(values).view(np.uint8)), f"{label} mask")
    return data


def _cube_data(cube, label, *, values=None, unit=None, color=None, cmap=None, missing=MISSING_VALUES, scaling=None):
    """
    Convert one irispy cube into one Glue dataset (`_dataset`), with its times and exposure times.

    ``values`` and ``unit`` replace the cube's own data and unit.
    """
    values, unit = cube.data if values is None else values, cube.unit if unit is None else unit
    data = _dataset(cube.wcs.low_level_wcs, cube.meta, unit, values, label, color=color, cmap=cmap, missing=missing,
                    scaling=scaling)
    times = _frame_times(cube)
    if times is not None:
        data.add_component(_per_frame(times, cube.shape), "Time")
    if getattr(cube, "exposure_time", None) is not None:
        _add_exposure(data, cube.exposure_time.to_value(u.s))  # per raster step or SJI frame, in the data's order
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


def _warn_repeated_positions(datasets):
    """
    Warn once per observation of ``datasets`` whose rasters take several exposures at each of several positions
    (``NEXP_PRP`` and ``NRASTERP`` over 1), which world to pixel cannot tell apart; a sit-and-stare raster, whose one
    position takes them all (``NRASTERP`` 1), steps through time instead.
    """
    repeated = {}
    for data in datasets:
        meta = data.meta
        if meta.get("INSTRUME") == "SPEC" and int(meta.get("NEXP_PRP") or 1) > 1 and int(meta.get("NRASTERP") or 1) > 1:
            repeated[_observation_label(meta)] = int(meta["NEXP_PRP"])
    for observation, exposures in repeated.items():
        warnings.warn(
            f"{observation} takes {exposures} exposures at each raster position (NEXP_PRP), which world to pixel "
            "cannot tell apart: a click on a quicklook's slit-jaw image lands on one of them.",
            stacklevel=3,
        )


def _raw_scaling(header):
    """
    ``(BSCALE, BZERO)`` of an image HDU of int16, as Level 2 files store their data, which then loads lazily; None
    for any other data, such as irispy's float32 test files, or with `LAZY` off.
    """
    if LAZY and header["BITPIX"] == 16:
        return header.get("BSCALE", 1), header.get("BZERO", 0)
    return None


def _window_scaling(path):
    """
    The `_raw_scaling` of each spectral window of a raster file by its ``TDESC`` name, or None unless every window
    loads lazily.
    """
    with fits.open(path) as hdulist:  # headers only
        header = hdulist[0].header
        scaling = {header[f"TDESC{i}"]: _raw_scaling(hdulist[i].header) for i in range(1, header["NWIN"] + 1)}
    return None if None in scaling.values() else scaling


def _raster_collection_data(collection, windows=None, stack=False, scaling=None):
    """``scaling``: each window's ``(BSCALE, BZERO)`` when the collection holds the files' raw int16."""
    datasets = []
    for window, sequence in collection.items():
        name = str(window).replace(" ", "_")
        cmap = f"irissji{sequence[0].meta.detector_band}"  # sunpy's slit-jaw colormap of its detector, FUV or NUV
        if stack and len(sequence) > 1:
            label = f"{name}-{_observation_label(sequence[0].meta)}-stack"
            if scaling:
                raw = RawStack([scan.data for scan in sequence])
                wcs = stack_wcs([scan.wcs for scan in sequence])
                data = _dataset(wcs, dict(sequence[0].meta), sequence[0].unit, raw, label,
                                color="#7A617C", cmap=cmap, scaling=scaling[window])
                times = stack_times(sequence)
            else:
                cube, times = stack_spectrogram_sequence(sequence)
                # the stack already holds NaN
                data = _dataset(cube.wcs.low_level_wcs, cube.meta, cube.unit, cube.data, label, color="#7A617C",
                                cmap=cmap, missing=())
            # its meta is scan 0's, so exposure times and raster files come per scan
            _add_exposure(data, np.stack([scan.exposure_time.to_value(u.s) for scan in sequence]))
            data.meta["raster files"] = tuple(name for scan in sequence for name in scan.meta.get("raster files", ()))
            data.add_component(_per_frame(times, data.shape), "Time")
            datasets.append(data)
            continue
        for i, scan in enumerate(sequence):
            label = f"{name}-{_observation_label(scan.meta)}-scan-{i}"
            datasets.append(_cube_data(scan, label, color="#5A4FCF", cmap=cmap, scaling=scaling and scaling[window]))
    return datasets


def _image_cube_data(cube, path, scaling=None):
    """
    A Glue dataset of irispy's SJI or AIA cube; ``scaling`` is the ``(BSCALE, BZERO)`` of a cube irispy read with
    ``memmap=True``, whose data are the file's raw int16, fill included.
    """
    desc = str(cube.meta["TDESC1"])
    if "_deconvolved." in Path(path).name:  # the header does not say, the filename does
        desc += "_deconvolved"
    wave = int(cube.meta["TWAVE1"])
    label = f"{desc}-{_observation_label(cube.meta)}"
    cmap = f"irissji{wave}" if desc.startswith("SJI") else f"sdoaia{wave}"
    # irispy's FITS WCS header of each frame, in a tuple, which sessions save, rather than an array of objects
    # ponytail: a session restores each header as a dict, not irispy's MetaDict, so irispy's fits_wcs of one frame of a
    # cube rebuilt from restored meta fails (glue-solar never does); a glue loader(MetaDict) if that is ever needed.
    cube.meta["frame_wcs_headers"] = tuple(cube.meta["frame_wcs_headers"])
    if scaling is None:
        return _cube_data(cube, label, cmap=cmap)
    from irispy.utils.constants import DN_UNIT

    cube.meta["scaled"] = True  # the values glue reads are; irispy's unit for the raw values says otherwise
    return _cube_data(cube, label, unit=DN_UNIT["SJI"], cmap=cmap, scaling=scaling)


def _logged(datasets, path, factory, **kwargs):
    """
    ``datasets`` with the load log glue's ``load_data(path, factory=factory, **kwargs)`` gives them, so that a session
    refers to their file, and reads them from it again, rather than holding their values.
    """
    log = LoadLog(str(path), factory, kwargs)
    for data in datasets:
        log.log(data)
        data._loaded_meta = frozenset(data.meta)  # what the file gives, which `LazyData` leaves out of a session
        for cid in data.coordinate_components + data.main_components:  # load_data's order, which a restore reads
            log.log(data.get_component(cid))
    return datasets


def last_directory():
    """The folder the user browsed last time (home directory if never)."""
    return str(QSettings(*_SETTINGS).value(_LAST_DIR, str(Path.home())))


def image_data(path):
    """
    Load an SJI or AIA-cutout file through irispy.

    Data stored as int16, as Level 2 files store them, stay in the file and are scaled where glue reads them
    (`LAZY`); a ``.fits.gz`` file is decompressed once, and its data held in memory as int16. A glue session refers to
    the file rather than holding the values.

    Returns
    -------
    `~glue.core.data.Data`
    """
    from irispy.io.sji import read_sji_lvl2  # with the first file rather than at glue's launch

    with open(path, "rb") as file:
        gzipped = file.read(2) == b"\x1f\x8b"
    if gzipped:  # as bytes, whose raw int16 irispy's memmap=True read views rather than copies
        with gzip.open(path) as file:
            content = file.read()
    scaling = _raw_scaling(fits.Header.fromfile(io.BytesIO(content) if gzipped else path))
    if scaling:
        allow_open_files()
    cube = read_sji_lvl2(content if gzipped else path, memmap=bool(scaling), uncertainty=False)
    return _logged([_image_cube_data(cube, path, scaling)], path, image_data)[0]


def iris_data(path):
    """
    Load one IRIS Level 2 file through irispy and convert its return shape.

    A raster file's windows are labelled by its raster number (``…-r00003``), so that the files of a
    multi-scan observation opened one by one keep distinct labels.
    """
    if _primary_header(path).get("INSTRUME") != "SPEC":
        return image_data(path)
    datasets = raster_data([path])
    number = re.search(r"_r(\d{5})", Path(path).name)
    if number:
        for data in datasets:
            data.label = data.label.replace("-scan-0", f"-r{number.group(1)}")
    return datasets


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
        with a leading ``Scan`` axis. Each scan keeps its own coordinates (`stack_wcs`) and exact
        acquisition times are stored in the ``Time`` component. A window containing one scan
        loads normally as a 3D dataset.

    Returns
    -------
    list of `~glue.core.data.Data`
        One per scan and window, or one per window when ``stack`` is set. Windows stored as int16, as Level 2
        files store them, stay in their files and are scaled where glue reads them (`LAZY`), if every file stores
        them alike. A glue session refers to the files of each window (`raster_files_data`) rather than holding the
        values.

    Warns
    -----
    UserWarning
        If the rasters take several exposures at each position (``NEXP_PRP``), as world to pixel gives the first.
    """
    datasets = [data for datasets in _raster_windows_data(files, windows, stack).values() for data in datasets]
    _warn_repeated_positions(datasets)
    return datasets


def raster_files_data(path, files=(), windows=None, stack=False):
    """
    `raster_data` as a glue data factory, which a session's load log calls: ``path`` is the first raster file, and
    ``files`` every one by its path relative to the folder of ``path``, so that a session with relative paths finds
    them all where it finds ``path``.
    """
    return raster_data([Path(path).parent / name for name in files] or [path], windows, stack)


def _raster_windows_data(files, windows=None, stack=False, stop=None, step=None):
    """
    `raster_data` by window name, from one read of each file for every window, which maps each file once.

    None once ``stop``, a `threading.Event`, is set between files; ``step()`` is called after each file.
    """
    scaling = _window_scaling(files[0])
    if any(_window_scaling(path) != scaling for path in files[1:]):
        scaling = None
    if scaling:
        allow_open_files()
    from irispy.io import read_files

    scans = {}
    for path in sorted(files):  # as irispy orders them
        if stop is not None and stop.is_set():
            return None
        for window, sequence in read_files([path], spectral_windows=windows, memmap=bool(scaling),
                                           uncertainty=False).items():
            for scan in sequence:
                scan.meta["raster files"] = (Path(path).name,)  # which tell the files of an observation apart
            scans.setdefault(window, []).extend(sequence)
        if step is not None:
            step()
    first = sorted(files)[0]
    names = [os.path.relpath(path, Path(first).parent) for path in sorted(files)]
    result = {}
    for window, cubes in scans.items():  # each with its own log, which a session reads back alone
        datasets = _raster_collection_data({window: cubes}, stack=stack, scaling=scaling)
        result[window] = _logged(datasets, first, raster_files_data, files=names, windows=[str(window)], stack=stack)
    return result


class _ScanAt:
    """
    A stack's ``Scan`` at each index along another dataset's first axis, its frames, exposures or steps (`link_hpc`),
    and NaN off it: ``scans``. Saved in sessions.
    """

    __name__ = "nearest_scan"  # glue's name of a link function, as its own link helpers set it
    __signature__ = inspect.signature(lambda index: None)  # one input to glue and its link editor, not self too

    def __init__(self, scans):
        self.scans = np.asarray(scans, dtype=float)

    def __call__(self, index):
        index = np.round(np.asarray(index, dtype=float))
        inside = (index >= 0) & (index < len(self.scans))  # not NaN
        return np.where(inside, self.scans[np.where(inside, index, 0).astype(int)], np.nan)

    def __gluestate__(self, context):
        return {"scans": self.scans.tolist()}

    @classmethod
    def __setgluestate__(cls, rec, context):
        return cls(rec["scans"])


def link_hpc(data_collection):
    """
    Links pairing the helioprojective longitude and latitude of every IRIS dataset, and of any other dataset such as
    a sunpy map, with those of the first IRIS dataset, and giving every stack of raster scans its ``Scan`` on each
    IRIS dataset with a ``Time`` but a stack.

    Datasets are matched by world axis physical type, not by component name. IRIS datasets are all in arcsec and
    linked with `~glue.core.link_helpers.LinkSame`; others, such as a sunpy map in degrees, with
    `~glue.core.link_helpers.LinkSameWithUnits`, which converts. Without IRIS data nothing is linked: glue's own
    WCS autolinker links sunpy maps to each other. No link pairs times, so a slit-jaw image frame is placed with
    its own pointing. Pairs that are already linked, either way round, are skipped, so calling this again after
    loading more data is safe. The caller adds the links::

        data_collection.add_link(link_hpc(data_collection))

    Every dataset links to the first, not to every other: glue rediscovers all links at each change, which
    takes 0.3 s for the 70 links of 36 datasets but 4 s for the 1260 links of every pair. Removing the first
    dataset drops the links of all the others; `keep_hpc_linked` links them again.

    A stack's pixel at a place depends on its scan, each with its own pointing (`stack_wcs`), so the frames, exposures
    or steps of each IRIS dataset with a ``Time`` but a stack get the scan nearest their time, however far, and those
    without a time none, scans timed by their middle raster step as the quicklook times them: a
    `~glue.core.component_link.ComponentLink` from the dataset's first pixel axis to the stack's ``Scan``.

    Returns
    -------
    list of `~glue.core.link_helpers.LinkSame`, `~glue.core.link_helpers.LinkSameWithUnits` and
    `~glue.core.component_link.ComponentLink`
    """
    from glue_solar.quicklook import _times, nearest  # which imports this module

    linked = {frozenset((link.get_to_id(), *link.get_from_ids())) for link in data_collection.links}
    anchors, links = {}, []
    # IRIS datasets first, so that the first of them is the one every dataset links to
    for data in sorted(data_collection, key=lambda data: not isinstance(data.coords, _GlueWCS)):
        iris = isinstance(data.coords, _GlueWCS)
        # glue's world components are in numpy order, the reverse of the WCS world axes
        physical_types = getattr(data.coords, "world_axis_physical_types", None) or ()
        for physical_type, cid in zip(physical_types[::-1], data.world_component_ids):
            if physical_type and physical_type.startswith("custom:pos.helioprojective."):
                # never another dataset: with no IRIS dataset, one is its own anchor and gets no link
                anchor = anchors.setdefault(physical_type, cid) if iris else anchors.get(physical_type, cid)
                if anchor is not cid and frozenset((anchor, cid)) not in linked:
                    links.append((LinkSame if iris else LinkSameWithUnits)(anchor, cid))
    datasets = [data for data in data_collection if isinstance(data.coords, _GlueWCS)]
    scans = {data: cid for data in datasets for cid in data.world_component_ids if cid.label == "Scan"}
    # ponytail: a link per stack and other dataset, not a star: 104 for 8 stacks and 13 slit-jaw images add 0.03 s to
    # glue's link rediscovery at each change; fewer if that grows
    for stack, scan in scans.items():
        if stack.find_component_id("Time") is None:  # a stack's line moments
            continue
        times = _times(stack, stack.shape[1] // 2)  # whose indices are the scan numbers (stack_wcs)
        for data in datasets:
            frame = data.pixel_component_ids[0]
            if data in scans or frozenset((scan, frame)) in linked or data.find_component_id("Time") is None:
                continue
            when = _times(data, 0)
            nearby = np.where(np.isnat(when), np.nan, nearest(when, times)[0])  # none for a frame without a time
            links.append(ComponentLink([frame], scan, using=_ScanAt(nearby)))
    return links


class _Relinker(HubListener):
    """Link the IRIS datasets of a collection again, once, after datasets are removed from it."""

    def __init__(self, data_collection):
        self.data_collection = data_collection
        # one relink after a burst of removals, such as clearing the collection
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._relink)
        data_collection.hub.subscribe(self, DataCollectionDeleteMessage, handler=self._removed)

    def _removed(self, message):
        self._timer.start()

    def _relink(self):
        links = link_hpc(self.data_collection)
        if links:  # glue rediscovers every dataset's links on each add_link, even an empty one
            self.data_collection.add_link(links)


def keep_hpc_linked(data_collection):
    """
    Add the `link_hpc` links to ``data_collection``, and add them again after any dataset is removed.

    Removing the dataset the others are linked through drops their links, so they are then linked
    through the new first dataset. Datasets loaded later need another call.
    """
    links = link_hpc(data_collection)
    if links:
        data_collection.add_link(links)
    if not hasattr(data_collection, "_solar_relinker"):
        data_collection._solar_relinker = _Relinker(data_collection)  # the hub holds its listeners weakly


def load_entry(observation, kind, name, stack=False):
    """
    Load one entry of the observation browser: a slit-jaw channel, an AIA cutout, or a raster window.

    Returns
    -------
    list of `~glue.core.data.Data`
        One per scan of a raster window (one stack with ``stack``), else one.
    """
    if kind == "raster":
        return raster_data(observation.rasters, [name], stack=stack)
    return [image_data(observation.sji[name] if kind == "sji" else observation.sdo[name])]


def _failing_file(observation, kind, name, windows, stop):
    """
    The name of the file of a browser entry that failed to load: for a raster window, the first raster file that fails
    on its own, as the error does not name it, looked for until ``stop`` is set.
    """
    if kind != "raster":
        return (observation.sji[name] if kind == "sji" else observation.sdo[name]).name
    for path in observation.rasters:
        if stop.is_set():
            break
        try:
            _raster_windows_data([path], windows)
        except Exception:  # noqa: BLE001 - whatever the read of every file raised
            return path.name
    return f"{len(observation.rasters)} raster files"  # each loads on its own but not together, or Stop ended the look


def _load(load, observations, picks, stack, shown, stop, report):
    """
    Read the browser's ticked entries on glue-qt's worker thread, until ``stop`` is set: ``report(load, percent)``
    after each raster, slit-jaw or AIA file, and after the count of the colour limits of the datasets
    ``shown(loaded)`` gives, unless it is None, which the GUI thread would otherwise count as their first viewers
    open. What Stop keeps is counted too.

    Returns ``(load, loaded, error)``: the entries read in full, as `QtIRISImporter.loaded` holds them, and the text
    of a reader error, which loads nothing.
    """
    windows, rasters, loaded = {}, {}, []  # each observation's ticked raster windows, read together
    for i, kind, name in picks:
        if kind == "raster":
            windows.setdefault(i, []).append(name)
    # one step per file, and one for the colour limits
    files = sum(len(observations[i].rasters) for i in windows) + sum(kind != "raster" for _, kind, _ in picks) + 1
    done = itertools.count(1)

    def step():
        report(load, 100 * next(done) // files)

    for i, kind, name in picks:
        if stop.is_set() and (kind != "raster" or i not in rasters):  # another window of a raster read is read in full
            break
        obs = observations[i]
        try:
            if kind == "raster":
                if i not in rasters:
                    rasters[i] = _raster_windows_data(obs.rasters, windows[i], stack=stack, stop=stop, step=step)
                if rasters[i] is None:  # stopped between its files
                    break
                datasets = rasters[i][name]
            else:
                datasets = load_entry(obs, kind, name)
                step()
        except Exception as error:  # noqa: BLE001 - third-party reader errors must stay inside the dialog
            failing = _failing_file(obs, kind, name, windows.get(i), stop)
            return load, [], f"Loading {name} from {failing} failed: {error}"
        loaded.append((obs, kind, name, datasets))
    for data in shown(loaded) if shown else ():
        component = data.get_component(data.main_components[0])
        if isinstance(component, RawComponent):
            component._sample()
    step()
    return load, loaded, None


def _extract(load, archives, stop, report):
    """
    Unpack the browser's ticked archives on glue-qt's worker thread, until ``stop`` is set: ``report(load, percent)``
    after each.

    Returns ``(load, extracted, error)``: how many were unpacked, and the text of an extraction error.
    """
    for n, archive in enumerate(archives):
        if stop.is_set():
            return load, n, None
        try:
            extract_archive(archive)
        except (OSError, tarfile.TarError) as error:
            return load, n, f"Extraction failed: {error}"
        report(load, 100 * (n + 1) // len(archives))
    return load, len(archives), None


def _scan(load, directory, recursive, start, end, stop, report):
    """
    `scan_directory` from ``start`` to ``end`` on glue-qt's worker thread, until ``stop`` is set: ``report(load,
    percent)`` before each file.

    Returns ``(load, observations, skipped)``: what it found, and the raster files that are not Level 2.
    """
    skipped = []
    return load, scan_directory(directory, recursive, skipped, stop, partial(report, load), start, end), skipped


# glue-qt's workers that are still running: Python would delete one that nothing holds, which aborts the process
_RUNNING = set()


def _fmt(value):
    return "" if value is None else f"{round(value, 1) + 0.0:.1f}"  # + 0.0 turns -0.0 into 0.0


def _window_time(text, end=False):
    """
    The UTC time ``text`` names, such as 2014-03-29T14:00, 2014-03-29 or 2014-03, or None if empty; as ``end``, one
    that names no second runs to the last second of the minute, hour, day, month or year it names.
    """
    if not text:
        return None
    time = np.datetime64(text)
    unit = np.datetime_data(time.dtype)[0]
    if end and unit in ("Y", "M", "D", "h", "m"):
        time = (time + np.timedelta64(1, unit)).astype("datetime64[s]") - np.timedelta64(1, "s")
    return time


class QtIRISImporter(QtWidgets.QDialog):
    """
    Browse a folder of IRIS Level 2 files by observation and load a selection.

    After ``exec()`` returns ``Accepted``, ``datasets`` holds the loaded
    `~glue.core.data.Data` objects and ``first_image`` the first SJI/AIA cube
    (the natural thing to open in an image viewer). ``loaded`` records what each
    ticked entry gave, as ``(observation, kind, name, datasets)``.

    Load selected reads in the background, a file at a time, and the progress bar
    counts the files. Meanwhile Cancel reads Stop, which closes the dialog with the
    entries read in full; Esc or closing the dialog drops the load. ``shown``, if
    given, names the datasets the first viewers will show of what is loaded, as
    ``shown(loaded, quicklooks)`` with whether Open quicklook is ticked: their
    colour limits are counted in the background too.

    The folder is scanned in the background as well, a header at a time, where
    Stop lists what the scan found so far.

    The Filter field lists only the observations whose row or entries contain its
    text, in any case, across rescans; Load selected still loads the ticks it hides.

    Start and End list only the observations that run at some time between them:
    the scan reads the headers only of the files whose names are stamped from a day
    before Start to End, and of those with no stamp. The saved folders and the last
    10 searches, each a folder with its Start and End, are kept in the settings, and
    the latest search's Start and End fill the next browser's. Its tick boxes open
    as the last browser left them.

    A folder typed in the Folder field is searched once Return is pressed or the
    field is left. A double-click on an entry loads it alone, whatever is ticked,
    and one on its tick box only ticks and un-ticks it; on an observation of several
    entries it expands or collapses the row.
    """

    progressed = Signal(int, int)  # (load, percent), from the worker thread

    def __init__(self, directory=None, parent=None, shown=None):
        super().__init__(parent)
        self.ui = load_ui(UI_MAIN, self)
        settings = QSettings(*_SETTINGS)
        for name in _OPTIONS:  # before they are connected to a rescan
            box, key = getattr(self, name), f"iris/{name}"
            box.setChecked(settings.value(key, box.isChecked(), type=bool))
            box.toggled.connect(lambda checked, key=key: QSettings(*_SETTINGS).setValue(key, checked))
        self.cancel.clicked.connect(self._cancel)
        self.ok.clicked.connect(lambda: self.finalize(self.selected()))
        self.obs_tree.itemDoubleClicked.connect(self._double_clicked)
        self.progressed.connect(self._progressed)
        self.change.clicked.connect(self.choose_directory)
        self.recursive.toggled.connect(lambda _checked: self.set_directory(self.directory.text()))
        self.filter.textChanged.connect(self._filter)
        for field in (self.directory, self.start, self.end):
            field.editingFinished.connect(self._search_edited)
        self.places.activated.connect(lambda i: self.set_directory(self._places[i][1]))
        self.add_place.clicked.connect(self._add_place)
        self.remove_place.clicked.connect(self._remove_place)
        self.recent.activated.connect(self._restore)
        self._places = json.loads(settings.value(_PLACES, "[]"))
        self._recent = json.loads(settings.value(_RECENT, "[]"))
        self._store_places(-1)
        self._list_recent()
        if self._recent:
            self.start.setText(self._recent[0][1])
            self.end.setText(self._recent[0][2])
        self.observations = []
        self.datasets = []
        self.first_image = None
        self.loaded = []
        self._payloads = []
        self._load, self._stop = 0, threading.Event()  # the latest load, and its stop
        self.shown = shown
        self.stack.setToolTip(
            "Stack two or more raster scans by detector position into one 4D cube. "
            "Each scan keeps its own spatial coordinates and exact acquisition times."
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
        directory = str(directory or "").strip()
        if not directory:
            return
        directory = os.path.normpath(os.path.expanduser(directory))  # one spelling for a typed ~ or trailing slash
        if not Path(directory).is_dir():  # a saved or recent folder since removed or unmounted
            self.progress.setFormat(f"No such folder: {directory}")
            return
        self.directory.setText(str(directory))
        QSettings(*_SETTINGS).setValue(_LAST_DIR, str(directory))
        self._rescan()

    def _search(self):
        """The folder, Start and End."""
        return [self.directory.text(), self.start.text().strip(), self.end.text().strip()]

    def _rescan(self, note=None):
        """
        List the folder's observations from Start to End in the background, as the latest recent search; ``note`` then
        replaces the progress text.
        """
        search = self._search()
        try:
            start, end = _window_time(search[1]), _window_time(search[2], end=True)
        except ValueError as error:
            self.progress.setFormat(f"Start and End take UTC times, such as 2014-03-29T14:00 or 2014-03: {error}")
            self._busy(False)  # after an archive is unpacked
            return
        self._recent = [search, *(kept for kept in self._recent if kept != search)][:_RECENT_SEARCHES]
        QSettings(*_SETTINGS).setValue(_RECENT, json.dumps(self._recent))
        self._list_recent()
        self.progress.setFormat("Scanning the folder: %p%")
        self._start(partial(self._scanned, note), _scan, search[0], self.recursive.isChecked(), start, end)

    def _search_edited(self):
        if self._recent[:1] != [self._search()]:  # editingFinished also comes as an unchanged field loses focus
            self.set_directory(self.directory.text())

    def _restore(self, i):
        """Search the folder of recent search ``i`` from its Start to its End again."""
        folder, start, end = self._recent[i]
        self.start.setText(start)
        self.end.setText(end)
        self.set_directory(folder)

    def _list_recent(self):
        self.recent.clear()
        self.recent.addItems(
            f"{start or '…'} to {end or '…'} in {folder}" if start or end else folder
            for folder, start, end in self._recent
        )

    def _add_place(self):
        """Save the folder under a name the user gives, in place of a folder saved under that name."""
        folder = self.directory.text()
        if not folder:
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "Add current folder", "Name:", text=Path(folder).name)
        if ok and name.strip():
            self._places = [place for place in self._places if place[0] != name.strip()] + [[name.strip(), folder]]
            self._store_places(len(self._places) - 1)

    def _remove_place(self):
        if self.places.currentIndex() >= 0:
            del self._places[self.places.currentIndex()]
            self._store_places(-1)

    def _store_places(self, index):
        """Keep the saved folders in the settings and list them, showing the one at ``index``."""
        QSettings(*_SETTINGS).setValue(_PLACES, json.dumps(self._places))
        self.places.clear()
        for i, (name, folder) in enumerate(self._places):
            self.places.addItem(name)
            self.places.setItemData(i, folder, Qt.ToolTipRole)
        self.places.setCurrentIndex(index)

    def _scanned(self, note, result):
        load, observations, skipped = result
        if load != self._load:
            return
        self._busy(False)
        self.observations = observations
        self.populate()
        if self.progress.value() < 100:  # Stop broke the scan off before it read every file
            self.progress.setFormat("Scan stopped at %p% of the files: observations may be missing or incomplete")
            return
        if skipped and not note:
            note = f"Skipped {len(skipped)} raster file(s) that are not Level 2"
        self.progress.setFormat(note or "%p%")

    def populate(self):
        self.obs_tree.clear()
        self._payloads, children = [], []
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
                    children.append(self._make_checkable(QtWidgets.QTreeWidgetItem(top, [text]), payload))
        # don't squeeze their labels into the STARTOBS column; once every row is in, as Qt moves every spanned row at
        # each row added after it (2 s for the 15000 rows of 5000 observations, against 0.05 s)
        for child in children:
            child.setFirstColumnSpanned(True)
        for column in range(self.obs_tree.columnCount()):
            self.obs_tree.resizeColumnToContents(column)
        self._filter()

    def _filter(self):
        """List only the observations whose row or entries contain the filter's text, in any case."""
        text, columns = self.filter.text().casefold(), range(self.obs_tree.columnCount())
        for top in map(self.obs_tree.topLevelItem, range(self.obs_tree.topLevelItemCount())):
            texts = [*map(top.text, columns), *(top.child(j).text(0) for j in range(top.childCount()))]
            top.setHidden(text not in "\n".join(texts).casefold())  # within one text: no line break can be typed

    def _make_checkable(self, item, payload):
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Unchecked)
        item.setData(0, Qt.UserRole, len(self._payloads))
        self._payloads.append(payload)
        if payload[1] == "raster":
            item.setToolTip(0, self.observations[payload[0]].window_tips.get(payload[2], ""))
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

    def _double_clicked(self, item):
        if item.data(0, Qt.UserRole) is None:  # an observation's row of several entries
            return
        tree, option = self.obs_tree, QtWidgets.QStyleOptionViewItem()
        option.initFrom(tree)  # the tick box's rect, as the style lays out the item and Qt toggles it
        option.rect = tree.visualRect(tree.indexFromItem(item))  # past its indentation, as an entry spans the row
        option.features = QtWidgets.QStyleOptionViewItem.HasCheckIndicator
        box = tree.style().subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, tree)
        if not box.contains(tree.viewport().mapFromGlobal(QtGui.QCursor.pos())):
            self.finalize([self._payloads[item.data(0, Qt.UserRole)]])

    def finalize(self, picks):
        """Load ``picks``, as `selected` gives them, or unpack the archives among them."""
        self.progress.setFormat("%p%")
        archives = [name for _, kind, name in picks if kind == "archive"]
        if archives:  # unpack, rescan and stay open so the user can pick from what was inside
            self._start(self._extracted, _extract, archives)
        else:
            shown = self.shown and partial(self.shown, quicklooks=self.quicklook.isChecked())
            self._start(self._loaded, _load, self.observations, picks, self.stack.isChecked(), shown)

    def _start(self, done, function, *args):
        """Run ``function(load, *args, stop, report)`` on glue-qt's worker thread, and ``done`` with its result."""
        self._busy(True)
        self.progress.setValue(0)
        self._load += 1
        self._stop = threading.Event()
        worker = Worker(function, self._load, *args, self._stop, self.progressed.emit)
        worker.result.connect(done)
        worker.error.connect(partial(self._failed, self._load))
        _RUNNING.add(worker)
        worker.finished.connect(lambda: _RUNNING.discard(worker))
        worker.start()

    def _busy(self, busy):
        """While a load runs, only Stop: the ticks and boxes it was started with stay as they were."""
        searching = self.directory, self.change, self.recursive, self.start, self.end, self.places, self.recent
        for widget in (self.ok, *searching, self.obs_tree, self.stack, self.quicklook):
            widget.setEnabled(not busy)
        self.cancel.setText("Stop" if busy else "Cancel")

    def _cancel(self):
        if self.ok.isEnabled():
            self.reject()
        else:
            self._stop.set()  # the load ends with what is read in full

    def reject(self):
        self._load += 1  # its result is dropped
        self._stop.set()
        self._busy(False)
        super().reject()

    def _progressed(self, load, percent):
        if load == self._load:
            self.progress.setValue(percent)

    def _failed(self, load, exc_info):
        traceback.print_exception(*exc_info)  # not a reader error, so a bug: the dialog shows only its text
        self._loaded((load, [], f"Loading failed: {exc_info[1]}"))

    def _extracted(self, result):
        load, extracted, error = result
        if load == self._load:
            self._rescan(error or f"Extracted {extracted} archive(s) — now tick what to load")

    def _loaded(self, result):
        load, loaded, error = result
        if load != self._load:
            return
        self._busy(False)
        if error:
            self.progress.setFormat(error)
            return
        self.loaded = loaded
        self.datasets = [data for *_, datasets in loaded for data in datasets]
        _warn_repeated_positions(self.datasets)  # here, on the GUI thread, which glue's Error Console must be used from
        self.first_image = next((datasets[0] for _, kind, _, datasets in loaded if kind != "raster"), None)
        self.progress.setValue(100)
        self.accept()
