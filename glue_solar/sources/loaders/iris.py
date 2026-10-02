import gzip
import io
import os
import re
import tarfile
import threading
from collections import OrderedDict
from functools import cached_property
from operator import attrgetter
from pathlib import Path

import numpy as np
from glue.core.component import Component
from glue.core.component_id import ComponentID
from glue.core.component_link import ComponentLink
from glue.core.data import Data
from glue.core.hub import HubListener
from glue.core.link_helpers import LinkSame
from glue.core.message import DataCollectionDeleteMessage
from glue.core.visual import VisualAttributes
from glue_qt.utils import get_qapp, load_ui
from qtpy import QtWidgets
from qtpy.QtCore import QSettings, Qt, QTimer

import astropy.units as u
from astropy.io import fits
from astropy.wcs.wcsapi.wrappers import BaseWCSWrapper

from .lazy import LazyData, RawComponent, RawStack, allow_open_files, fill_mask
from .scan import _primary_header, extract_archive, scan_directory
from .stack_spectrograms import MISSING_VALUES, stack_spectrogram_sequence, stack_times, stack_wcs

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
]

# Load data stored as int16, as Level 2 files store it, lazily: the raw integers stay in the file (in memory for a
# .fits.gz file) and are scaled where glue reads them. False loads everything in memory through irispy, as before
# (float32 where fill becomes NaN).
LAZY = True

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
        Each world axis shown in another unit: its index, its unit's scale to the shown unit and back, and for the
        longitude the full circle in its unit; worked out once, since WCSAxes converts every draw.
        """
        axes = []
        for i, (unit, physical_type) in enumerate(zip(self._wcs.world_axis_units, self.world_axis_physical_types)):
            shown = _shown_unit(physical_type)
            if shown is not None:
                unit = u.Unit(unit)
                full_circle = (360 * u.deg).to_value(unit) if physical_type.endswith(".lon") else None
                # the scales a Quantity conversion multiplies by
                axes.append((i, unit.to(shown), shown.to(unit), full_circle))
        return axes

    def pixel_to_world_values(self, *pixel_arrays):
        # The same inputs give the same values: the wrapped WCS is never changed once loaded (glue-solar
        # changes none, and WCSAxes calls wcs.set() only on an astropy WCS it is given, never through this
        # wrapper). So identical inputs reuse the values, each caller with its own copy. Identical means
        # the same type (a scalar and a 0-d array can come back differently), dtype, shape and bytes.
        arrays = [np.asarray(pixel) for pixel in pixel_arrays]
        key = None
        if all(array.dtype.kind in "biuf" and array.size <= _MEMO_SAMPLES for array in arrays):
            key = tuple((type(p), a.dtype.str, a.shape, a.tobytes()) for p, a in zip(pixel_arrays, arrays))
            with self._memo_lock:
                kept = self._memo.get(key)
                if kept is not None:
                    self._memo.move_to_end(key)
            if kept is not None:
                return _copies(kept)
        with WCS_LOCK:
            values = list(self._wcs.pixel_to_world_values(*pixel_arrays))
        for i, to_shown, _, full_circle in self._converted:
            values[i] = np.asarray(values[i])
            if full_circle is not None:
                values[i] = (values[i] + full_circle / 2) % full_circle - full_circle / 2
            values[i] = values[i] * to_shown
        if key is not None and all(np.size(value) <= _MEMO_SAMPLES for value in values):  # inputs can broadcast
            kept = _copies(values)
            with self._memo_lock:
                self._memo[key] = kept
                if len(self._memo) > _MEMO_ENTRIES:
                    self._memo.popitem(last=False)
        return tuple(values)

    def world_to_pixel_values(self, *world_arrays):
        values = list(world_arrays)
        for i, _, from_shown, _ in self._converted:
            values[i] = np.asarray(values[i]) * from_shown
        with WCS_LOCK:
            return self._wcs.world_to_pixel_values(*values)

    @cached_property
    def world_axis_object_components(self):
        # The wrapped WCS's, with each converted value in its shown unit, so that high-level objects (glue's WCS
        # link) agree with the values. A SkyCoord gives a helioprojective longitude within +-180 deg already.
        with WCS_LOCK:  # an astropy WCS reads wcslib for these
            components = list(self._wcs.world_axis_object_components)
        for i, to_shown, _, _ in self._converted:
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
        for i, _, from_shown, _ in self._converted:
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
    data.style = VisualAttributes(color=color, preferred_cmap=cmap)
    if scaling is not None:
        cid = data.add_component(RawComponent(values, *scaling, missing, units=str(unit)), label)
        # a glue derived component, computed from the values glue reads
        data.add_component_link(ComponentLink([cid], ComponentID(f"{label} mask", parent=data), using=fill_mask))
        return data
    # From the values, not cube.mask: irispy masks only -200, and nothing in memory-mapped cubes.
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
                data = _dataset(stack_wcs(sequence[0].wcs), dict(sequence[0].meta), sequence[0].unit, raw, label,
                                color="#7A617C", cmap=cmap, scaling=scaling[window])
                times = stack_times(sequence)
            else:
                cube, times = stack_spectrogram_sequence(sequence)
                # the stack already holds NaN
                data = _dataset(cube.wcs.low_level_wcs, cube.meta, cube.unit, cube.data, label, color="#7A617C",
                                cmap=cmap, missing=())
            # its meta is scan 0's, so exposure times come per scan
            _add_exposure(data, np.stack([scan.exposure_time.to_value(u.s) for scan in sequence]))
            data.add_component(_per_frame(times, data.shape), "Time")
            datasets.append(data)
            continue
        for i, scan in enumerate(sequence):
            label = f"{name}-{_observation_label(scan.meta)}-scan-{i}"
            datasets.append(_cube_data(scan, label, color="#5A4FCF", cmap=cmap, scaling=scaling and scaling[window]))
    return datasets


def _image_cube_data(cube, path, raw=None, scaling=None):
    """
    A Glue dataset of irispy's SJI or AIA cube, or with ``scaling`` of the file's ``raw`` int16 instead: irispy's
    memory-mapped cube writes 0, a valid value, over the fill, and so supplies only the coordinates and metadata.
    """
    desc = str(cube.meta["TDESC1"])
    if "_deconvolved." in Path(path).name:  # the header does not say, the filename does
        desc += "_deconvolved"
    wave = int(cube.meta["TWAVE1"])
    label = f"{desc}-{_observation_label(cube.meta)}"
    # -199 is unverified as a missing code in AIA cutouts
    cmap, missing = (f"irissji{wave}", MISSING_VALUES) if desc.startswith("SJI") else (f"sdoaia{wave}", (-200,))
    if scaling is None:
        return _cube_data(cube, label, cmap=cmap, missing=missing)
    from irispy.utils.constants import DN_UNIT

    cube.meta["scaled"] = True  # the values glue reads are; irispy's unit for the raw values says otherwise
    return _cube_data(cube, label, values=raw, unit=DN_UNIT["SJI"], cmap=cmap, missing=missing, scaling=scaling)


def last_directory():
    """The folder the user browsed last time (home directory if never)."""
    return str(QSettings(*_SETTINGS).value(_LAST_DIR, str(Path.home())))


def image_data(path):
    """
    Load an SJI or AIA-cutout file through irispy.

    Data stored as int16, as Level 2 files store them, stay in the file and are scaled where glue reads them
    (`LAZY`); a ``.fits.gz`` file is decompressed once, and its data held in memory as int16.

    Returns
    -------
    `~glue.core.data.Data`
    """
    from irispy.io import read_files  # with the first file rather than at glue's launch
    from irispy.io.sji import read_sji_lvl2

    with open(path, "rb") as file:
        gzipped = file.read(2) == b"\x1f\x8b"
    if gzipped:  # into memory once: astropy and irispy would each decompress it again, about four times in all
        with gzip.open(path) as file:
            content = file.read()
        with fits.open(io.BytesIO(content), do_not_scale_image_data=True) as hdulist:
            hdu = hdulist[0]
            scaling = _raw_scaling(hdu.header)
            # the raw int16 where they lie in the decompressed bytes, rather than a copy
            raw = np.ndarray(hdu.shape, ">i2", content, hdu.fileinfo()["datLoc"]) if scaling else None
    else:
        with fits.open(path, memmap=True, do_not_scale_image_data=True) as hdulist:
            scaling = _raw_scaling(hdulist[0].header)
            raw = hdulist[0].data if scaling else None
    if scaling:
        allow_open_files()
    if gzipped:
        cube = read_sji_lvl2(io.BytesIO(content), memmap=bool(scaling), uncertainty=False)
    else:
        cube = read_files(path, memmap=bool(scaling), uncertainty=False)
    return _image_cube_data(cube, path, raw, scaling)


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
        with a leading ``Scan`` axis. Scan 0 supplies the nominal spatial WCS and exact
        acquisition times are stored in the ``Time`` component. A window containing one scan
        loads normally as a 3D dataset.

    Returns
    -------
    list of `~glue.core.data.Data`
        One per scan and window, or one per window when ``stack`` is set. Windows stored as int16, as Level 2
        files store them, stay in their files and are scaled where glue reads them (`LAZY`), if every file stores
        them alike.
    """
    return [data for datasets in _raster_windows_data(files, windows, stack).values() for data in datasets]


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
            scans.setdefault(window, []).extend(sequence)
        if step is not None:
            step()
    return {window: _raster_collection_data({window: cubes}, stack=stack, scaling=scaling)
            for window, cubes in scans.items()}


def link_hpc(data_collection):
    """
    Links pairing the helioprojective longitude and latitude of every IRIS dataset with those of the first one.

    Datasets are matched by world axis physical type, not by component name. Only datasets whose coordinates are
    a glue-solar IRIS WCS take part, since those are all in arcsec; a sunpy map WCS is in degrees and
    `~glue.core.link_helpers.LinkSame` does not convert. No link involves time, so a slit-jaw image frame is
    placed with its own pointing. Pairs that are already linked, either way round, are skipped, so calling this
    again after loading more data is safe. The caller adds the links::

        data_collection.add_link(link_hpc(data_collection))

    Every dataset links to the first, not to every other: glue rediscovers all links at each change, which
    takes 0.3 s for the 70 links of 36 datasets but 4 s for the 1260 links of every pair. Removing the first
    dataset drops the links of all the others; `keep_hpc_linked` links them again.

    Returns
    -------
    list of `~glue.core.link_helpers.LinkSame`
    """
    linked = {frozenset((link.get_to_id(), *link.get_from_ids())) for link in data_collection.links}
    anchors, links = {}, []
    for data in data_collection:
        if not isinstance(data.coords, _GlueWCS):
            continue
        # glue's world components are in numpy order, the reverse of the WCS world axes
        for physical_type, cid in zip(data.coords.world_axis_physical_types[::-1], data.world_component_ids):
            if physical_type and physical_type.startswith("custom:pos.helioprojective."):
                anchor = anchors.setdefault(physical_type, cid)
                if anchor is not cid and frozenset((anchor, cid)) not in linked:
                    links.append(LinkSame(anchor, cid))
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


def _failing_file(observation, kind, name, windows):
    """
    The name of the file of a browser entry that failed to load: for a raster window, the first raster file that fails
    on its own, as the error does not name it.
    """
    if kind != "raster":
        return (observation.sji[name] if kind == "sji" else observation.sdo[name]).name
    for path in observation.rasters:
        try:
            _raster_windows_data([path], windows)
        except Exception:  # noqa: BLE001 - whatever the read of every file raised
            return path.name
    return f"{len(observation.rasters)} raster files"  # each loads on its own, but not together


def _fmt(value):
    return "" if value is None else f"{round(value, 1) + 0.0:.1f}"  # + 0.0 turns -0.0 into 0.0


class QtIRISImporter(QtWidgets.QDialog):
    """
    Browse a folder of IRIS Level 2 files by observation and load a selection.

    After ``exec()`` returns ``Accepted``, ``datasets`` holds the loaded
    `~glue.core.data.Data` objects and ``first_image`` the first SJI/AIA cube
    (the natural thing to open in an image viewer). ``loaded`` records what each
    ticked entry gave, as ``(observation, kind, name, datasets)``.
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
        self.loaded = []
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
        skipped = []
        self.observations = scan_directory(directory, recursive=self.recursive.isChecked(), skipped=skipped)
        self.progress.setFormat(f"Skipped {len(skipped)} raster file(s) that are not Level 2" if skipped else "%p%")
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
        self.datasets, self.first_image, self.loaded = [], None, []
        windows, rasters = {}, {}  # each observation's ticked raster windows, read at once to map each file once
        for i, kind, name in picks:
            if kind == "raster":
                windows.setdefault(i, []).append(name)
        for n, (i, kind, name) in enumerate(picks):
            self.progress.setValue(int(100 * n / len(picks)))
            get_qapp().processEvents()
            obs = self.observations[i]
            try:
                if kind == "raster":
                    if i not in rasters:
                        rasters[i] = _raster_windows_data(obs.rasters, windows[i], stack=self.stack.isChecked())
                    datasets = rasters[i][name]
                else:
                    datasets = load_entry(obs, kind, name)
            except Exception as error:  # noqa: BLE001 - third-party reader errors must stay inside the dialog
                self.progress.setFormat(f"Loading {name} from {_failing_file(obs, kind, name, windows.get(i))} "
                                        f"failed: {error}")
                return
            self.loaded.append((obs, kind, name, datasets))
            self.datasets.extend(datasets)
            if kind != "raster":
                self.first_image = self.first_image or datasets[0]
        self.progress.setValue(100)
        self.accept()
