"""
IRIS Level 2 support: a file reader for File → Open Data Set, the observation browser, the 'Quicklook…' data action, of
IRIS data, SST cubes and other spectral cubes, 'IRIS: shift pointing…', an exporter
of derived maps with their coordinates, and one of 1-D data, such as light curves, with their times.
"""

import re
from pathlib import Path

import numpy as np
from glue.config import data_exporter, data_factory, layer_artist_maker, menubar_plugin, startup_action
from glue.core import Subset
from glue.core.data_exporters.astropy_table import data_to_astropy_table
from glue.core.message import ExternallyDerivableComponentsChangedMessage
from glue.viewers.image.viewer import MatplotlibImageMixin
from glue_qt.utils.decorators import messagebox_on_error
from qtpy import QtCore, QtGui, QtWidgets

import astropy.units as u
from astropy.io import fits
from astropy.time import Time
from astropy.wcs.utils import celestial_frame_to_wcs
from astropy.wcs.wcsapi import HighLevelWCSWrapper

from glue_solar.glue_patches import _application, export_fits, layer_action
from glue_solar.quicklook import (
    _cube_axes,
    _pick_sjis,
    _pick_windows,
    _role,
    _same_file,
    _time_axis,
    coordinator,
    observation_key,
    quicklook,
)
from glue_solar.sources.bursts import _shift_events
from glue_solar.sources.loaders.iris import (
    _HPC,
    QtIRISImporter,
    _GlueWCS,
    iris_data,
    keep_hpc_linked,
    last_directory,
)
from glue_solar.sources.loaders.scan import _is_supported_file, _primary_header, strip_pooch
from glue_solar.sources.moments import _accepted

__all__ = [
    "browse_iris",
    "export_ecsv",
    "export_iris_fits",
    "help_iris",
    "iris_image_layer",
    "iris_quicklook",
    "link_iris",
    "quicklook_cube",
    "read_iris_file",
    "shift_pointing_iris",
]


def is_iris_fits(filename, **_kwargs):
    """
    An IRIS file, or an aligned AIA cutout, whose TELESCOP is blank, or Hinode/SOT cube, as the observation browser
    takes it.
    """
    try:
        header = _primary_header(filename)
    except (OSError, ValueError, EOFError):  # not a FITS file
        return False
    return header.get("TELESCOP") == "IRIS" or _is_supported_file(strip_pooch(Path(filename).name), header)


@data_factory("IRIS Level 2 FITS", is_iris_fits, priority=200)  # glue's own "FITS file" is 100
def read_iris_file(file_path):
    """
    Read one IRIS Level 2 file: an SJI cube, an aligned AIA cutout or Hinode/SOT cube, or every spectral window of a
    raster file.
    """
    return iris_data(file_path)


@layer_artist_maker("IRIS: transparent NaN pixels")
def iris_image_layer(viewer, data):
    """
    Give image layers of IRIS datasets transparent NaN pixels, as matplotlib draws them.

    glue's default paints NaN opaque in the colormap's "bad" color, black for the IRIS
    colormaps, so gaps and off-detector areas look like dark data.
    """
    if not isinstance(viewer, MatplotlibImageMixin) or "OBSID" not in getattr(data, "meta", {}):
        return None  # not an image viewer, a subset, or not an IRIS dataset: glue's default artist
    artist = viewer.get_data_layer_artist(data)
    if hasattr(artist.state, "cmap_bad"):  # a 1-D dataset's scatter layer has none
        artist.state.cmap_bad = (0, 0, 0, 0)
    return artist


@menubar_plugin("IRIS: browse observations…")
def browse_iris(session, data_collection):
    """
    Browse a folder by observation, load the selection and link the helioprojective coordinates of its IRIS data.

    With "Open quicklook" ticked, each loaded observation opens as a quicklook of its ticked raster
    windows: the browser's "Main window" if ticked, else Mg II k 2796 if ticked, else the first, with
    the others beside it, and each SST cube in an SST quicklook of its own; otherwise, or with no raster,
    slit-jaw image or SST cube loaded, the first image opens in an Image Viewer.
    """
    app = session.application
    directory = QtWidgets.QFileDialog.getExistingDirectory(
        app, "Select a folder containing IRIS Level 2 files", last_directory()
    )
    if not directory:
        return
    dialog = QtIRISImporter(directory, parent=app, shown=_shown)
    if dialog.exec() != QtWidgets.QDialog.Accepted or not dialog.datasets:
        return
    # not app.add_datasets: its autolinker would ask about WCS links in a dialog before the quicklook
    # opens (with glue-viz/glue#2595), and keep_hpc_linked links IRIS datasets
    data_collection.extend(dialog.datasets)
    keep_hpc_linked(data_collection)
    quicklooks = _quicklooks(dialog.loaded) if dialog.quicklook.isChecked() else []
    for datasets, window in quicklooks:
        quicklook(app, datasets, window=window, main=dialog.main_window.currentText() or None)
    if not quicklooks and dialog.first_image is not None:
        from glue_qt.viewers.image import ImageViewer

        app.new_data_viewer(ImageViewer, data=dialog.first_image)


def _quicklooks(loaded):
    """
    The ``(datasets, window)`` of each quicklook `browse_iris` opens of the observation browser's ``loaded``, an SST
    cube's after the IRIS observations'.
    """
    observations, cubes = {}, []  # observation -> (its datasets, its ticked raster windows); each SST cube's
    for observation, kind, name, datasets in loaded:
        if kind == "sst":
            cubes.append((datasets, None))
            continue
        got, windows = observations.get(id(observation), ([], []))
        observations[id(observation)] = (got + datasets, windows + [name] * (kind == "raster"))
    shown = [(datasets, windows or None) for datasets, windows in observations.values() if _has_quicklook(datasets)]
    return shown + cubes


def _has_quicklook(datasets):
    """Whether ``datasets`` hold a raster or slit-jaw image, which a quicklook shows, and not only AIA or SOT cubes."""
    return any(_role(data) in ("raster", "sji") for data in datasets)


def _shown(loaded, quicklooks, main=None):
    """
    The datasets of the observation browser's ``loaded`` that the first viewers `browse_iris` opens show: the raster,
    ``main`` where ticked, the other windows with a wavelength panel and the slit-jaw images of each quicklook, with
    ``quicklooks`` on, else the first image.
    """
    quicklooks = _quicklooks(loaded) if quicklooks else []
    if not quicklooks:
        return [datasets[0] for _, kind, _, datasets in loaded if kind != "raster"][:1]
    shown = []
    for datasets, window in quicklooks:
        rasters = [data for data in datasets if _role(data) == "raster"]
        if rasters:
            raster, others = _pick_windows(rasters, window, main)
            shown += [raster] + [data for data in others if _time_axis(data) is not None]
        shown += _pick_sjis([data for data in datasets if _role(data) == "sji"])[0]
    return shown


@menubar_plugin("IRIS: link helioprojective coordinates")
def link_iris(session, data_collection):
    """
    Link the helioprojective longitude and latitude of every loaded dataset that has them, IRIS data, AIA cutouts, SOT
    cubes, sunpy maps and FITS files such as SST cubes alike, and the scans of each stack and SST cube to the other
    IRIS data by time.

    Selections then carry over between them through their world coordinates. The observation browser, a quicklook and
    the analyses link IRIS rasters and slit-jaw images, and data made from them, only, and the links are kept when a
    dataset is removed.
    """
    keep_hpc_linked(data_collection, others=data_collection)


def _ask_offset(data, chosen):
    """The pointing offset typed for ``data``, in arcsec, from its current one, asked on ``chosen``; or None for Cancel."""
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(f"Shift pointing of {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    if chosen is not data:
        form.addRow(QtWidgets.QLabel(f"{chosen.label} is made from it and moves with it.", objectName="source"))
    boxes = []
    for name, label, value in zip(("dx", "dy"), ("Δx (longitude):", "Δy (latitude):"), data.coords.pointing_offset):
        box = QtWidgets.QDoubleSpinBox(objectName=name, decimals=2, minimum=-1000, maximum=1000, singleStep=0.1)
        box.setSuffix("″")
        box.setValue(value)
        form.addRow(label, box)
        boxes.append(box)
    return tuple(box.value() for box in boxes) if _accepted(dialog, form) else None


def _source(data, data_collection):
    """The furthest dataset ``data`` is made from (`_GlueWCS.follows`) still in ``data_collection``, else ``data``."""
    loaded = {other.uuid: other for other in data_collection}
    return next((loaded[uuid] for uuid in reversed(data.coords.follows) if uuid in loaded), data)


def _check_iris(data):
    """Raise why ``data`` has no IRIS coordinates to shift."""
    if not isinstance(data.coords, _GlueWCS):
        raise ValueError(f"{data.label} has no IRIS coordinates to shift: shift the IRIS data against it instead.")


@layer_action(
    "IRIS: shift pointing…",
    single=True,
    data=True,
    check=_check_iris,
    tooltip=(
        "Offset the helioprojective longitude and latitude of this IRIS dataset, or of the dataset it was made from, "
        "by a typed number of arcsec"
    ),
)
@messagebox_on_error("Could not shift the pointing")
def shift_pointing_iris(data, data_collection):
    """
    Add a typed offset, in arcsec, to the helioprojective longitude and latitude of ``data``, or of the furthest
    dataset it is made from still loaded (`_source`), which the dialog names, of the other windows of its raster file
    and of the data made from any of them that follow it (`_GlueWCS.follow`), a burst events table's coordinates too,
    in place of any before (0, 0 removes it), and place everything in every viewer, the readouts, links and a
    quicklook's point and raster overlays again; offered only for data with IRIS coordinates.
    """
    _check_iris(data)
    chosen, data = data, _source(data, data_collection)
    offset = _ask_offset(data, chosen)
    if offset is None:
        return
    shifted = {other.uuid for other in data_collection if _same_file(data, other)}  # one slit, one pointing
    for other in data_collection:
        coords = other.coords if isinstance(other.coords, _GlueWCS) else None
        follows = other.meta.get("pointing_follows", ()) if coords is None else coords.follows
        if other.uuid in shifted or shifted.intersection(follows):
            if coords is None:
                _shift_events(other, offset)
            else:
                coords.pointing_offset = offset
    for other in data_collection:  # as glue does after a change of links: its layers place their images again
        data_collection.hub.broadcast(ExternallyDerivableComponentsChangedMessage(other))
    coordinator(data_collection).place_again()


@data_exporter("IRIS FITS (coordinates and Time)", extension=["fits", "fit"])
@messagebox_on_error("Could not export the data")
def export_iris_fits(filename, data, components=None):
    """
    Write ``data``, a 2-D map on helioprojective coordinates, such as line moments, or a subset of one, as glue's
    "FITS (1 component/HDU)" does, each image with the map's coordinates as a FITS-TAB WCS: every pixel's longitude
    and latitude as glue gives them, in degrees, in a ``WCS-TABLE`` extension, and the frame's observer and time. A
    ``Time`` component is a ``TIME`` image of the same pixels, every pixel of a subset too, in seconds since its
    ``DATEREF``, UTC, NaN where missing; ``OBSID`` and ``STARTOBS`` go in every component's header. glue shows why for
    other data.
    """
    maps = data.data if isinstance(data, Subset) else data
    coords = maps.coords
    types = list(getattr(coords, "world_axis_physical_types", ()))
    if maps.ndim != 2 or set(types) != set(_HPC):
        raise ValueError(
            f"{maps.label} is not a 2-D map on helioprojective coordinates: glue's 'FITS (1 component/HDU)' "
            "exports it without them."
        )
    y, x = np.indices(maps.shape)
    world, axes = coords.pixel_to_world_values(x, y), [types.index(kind) for kind in _HPC]  # longitude, latitude
    lonlat = np.stack([u.Unit(coords.world_axis_units[i]).to(u.deg, world[i]) for i in axes], -1)
    table = fits.BinTableHDU(np.array([(lonlat,)], dtype=[("COORDS", float, lonlat.shape)]), name="WCS-TABLE")
    header = fits.Header({key: str(maps.meta[key]) for key in ("OBSID", "STARTOBS") if key in maps.meta})
    frame = HighLevelWCSWrapper(coords).pixel_to_world(0, 0).frame
    header.update(celestial_frame_to_wcs(frame, projection="TAB").to_header())
    for i in (1, 2):  # world axis i is element i of COORDS, whose axis i pixel axis i indexes directly
        header.update({f"CUNIT{i}": "deg", f"CRPIX{i}": 1, f"CRVAL{i}": 1, f"CDELT{i}": 1})
        header.update({f"PS{i}_0": table.name, f"PS{i}_1": "COORDS", f"PV{i}_3": i})
    extensions = [table]
    time = maps.find_component_id("Time")
    if time is not None and maps.get_kind(time) == "datetime" and (components is None or time in components):
        times = maps[time]
        start = np.nanmin(times)
        seconds = fits.ImageHDU((times - start) / np.timedelta64(1, "s"), name="TIME")
        seconds.header.update(BUNIT="s", TIMESYS="UTC", DATEREF=np.datetime_as_string(start))
        extensions.insert(0, seconds)
    export_fits(filename, data, components, header, extensions)


@data_exporter("ECSV (with Time)", extension=["ecsv"])
@messagebox_on_error("Could not export the data")
def export_ecsv(filename, data, components=None):
    """
    Write ``data``, 1-D data such as the light curves at a point, or a subset of it, as an ECSV table: glue's table of
    its attributes, as glue's "Comma-separated table" writes it, with each attribute's unit, a datetime attribute such
    as ``Time`` as UTC times to the nanosecond, which astropy reads back as `~astropy.time.Time`, and ``OBSID`` and
    ``STARTOBS`` in its meta. glue shows why for other data.
    """
    whole = data.data if isinstance(data, Subset) else data
    if whole.ndim != 1:
        raise ValueError(f"{whole.label} is not 1-D: glue's 'Comma-separated table' exports it.")
    table = data_to_astropy_table(data, components)
    for cid in whole.main_components + whole.derived_components:
        if cid.label in table.colnames and whole.get_component(cid).units:
            table[cid.label].unit = whole.get_component(cid).units
    _write_ecsv(filename, table, whole.meta)


def _write_ecsv(filename, table, meta):
    """
    Write the astropy ``table`` as ECSV, its datetime64 columns as UTC times to the nanosecond, which astropy reads back
    as `~astropy.time.Time`, with ``OBSID`` and ``STARTOBS`` of ``meta`` in its meta.
    """
    for name in table.colnames:
        if table[name].dtype.kind == "M":
            table[name] = Time(table[name], scale="utc")  # a masked one stays masked
    table.meta.update({key: str(meta[key]) for key in ("OBSID", "STARTOBS") if key in meta})
    table.write(filename, format="ascii.ecsv", overwrite=True)


def _observations(data_collection):
    """The datasets of ``data_collection`` by IRIS observation with a quicklook, in the collection's order."""
    observations = {}
    for data in data_collection:
        key = observation_key(data)
        if key is not None:
            observations.setdefault(key, []).append(data)
    return {key: datasets for key, datasets in observations.items() if _has_quicklook(datasets)}


def _check_quicklook(data):
    """Raise why ``data`` has no quicklook: it is no IRIS raster or slit-jaw image, SST cube or other spectral cube."""
    role = _role(data)
    if role not in ("raster", "sji", "sst") and (role is not None or _cube_axes(data) is None):
        raise ValueError(
            f"{data.label} is no IRIS raster or slit-jaw image, SST cube or cube of one wavelength and two spatial axes."
        )


@layer_action(
    "Quicklook…",
    single=True,
    data=True,
    check=_check_quicklook,
    tooltip="Open the quicklook of this IRIS observation, SST cube or spectral cube",
)
@messagebox_on_error("Could not open the quicklook")
def quicklook_cube(data, data_collection):
    """
    Open the quicklook (`~glue_solar.quicklook.quicklook`) of ``data``: of an IRIS raster or slit-jaw image, its
    observation's loaded datasets; of an SST or other spectral cube, the cube alone (D83).
    """
    _check_quicklook(data)
    datasets = [data]
    if _role(data) in ("raster", "sji"):
        datasets = _observations(data_collection).get(observation_key(data), datasets)
    quicklook(_application(data_collection), datasets)


@menubar_plugin("IRIS: user guide and issues")
def help_iris(session, data_collection):
    """
    Open glue-solar's user guide and its issues on GitHub, to report a problem, in the web browser.
    """
    for url in (
        "https://glue-solar.readthedocs.io/en/latest/user_guide/index.html",
        "https://github.com/glue-viz/glue-solar/issues",
    ):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))


@startup_action("iris_quicklook")
def iris_quicklook(session, data_collection):
    """
    ``glue --startup=iris_quicklook <files>``: a quicklook of each IRIS observation and each SST cube among the files.

    Files given on the command line load one by one and cannot be stacked, so each observation
    opens on its first raster file (the lowest ``rNNNNN``); stacks of scans need the observation
    browser. With no raster, slit-jaw image or SST cube, only AIA cutouts or SOT cubes, the first
    opens in an Image Viewer instead, as the observation browser opens it.
    """
    app = session.application
    several = False
    observations = _observations(data_collection)
    for datasets in observations.values():
        numbers = sorted({_raster_number(data) for data in datasets} - {None})
        several |= len(numbers) > 1
        first = numbers[0] if numbers else None
        quicklook(app, [data for data in datasets if _raster_number(data) in (None, first)])
    cubes = [data for data in data_collection if _role(data) == "sst"]
    for cube in cubes:
        quicklook(app, [cube])
    image = next((data for data in data_collection if observation_key(data) is not None), None)
    if not observations and not cubes and image is not None:
        from glue_qt.viewers.image import ImageViewer

        app.new_data_viewer(ImageViewer, data=image)
    if several:
        note = "Only the first raster file is shown: stacks of scans need Plugins → IRIS: browse observations…"
        app.statusBar().showMessage(f"{app.statusBar().currentMessage()} {note}".strip())


def _raster_number(data):
    """The raster number of a raster window loaded from one file (`_label`), else None."""
    match = re.search(r" scan (\d+)$", data.label)
    return int(match.group(1)) if match else None
