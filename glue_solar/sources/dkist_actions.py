"""
The data actions of DKIST datasets: 'Mosaic…' of DKIST mosaics, 'Frame quality…' and 'Download these frames…'. They are
not in `glue_solar.sources.dkist`, which the quicklook imports, as they import the quicklook.
"""

import os
from functools import partial
from pathlib import Path

import numpy as np
from glue.core.link_helpers import LinkSame
from glue.core.units import UnitConverter
from glue.viewers.image.viewer import MatplotlibImageMixin
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtCore, QtWidgets

import astropy.units as u
from astropy.coordinates import StokesCoord

from glue_solar.glue_patches import _application, layer_action
from glue_solar.quicklook import PERCENTILE, coordinator, nearest
from glue_solar.sources.dkist import (
    _ARRIVING,
    _frame_axis,
    _frame_quality,
    _FrameTimes,
    _mosaic_image,
    _mosaic_links,
    _note_missing,
    _time_axes,
    _transfer,
)
from glue_solar.sources.loaders.iris import keep_hpc_linked
from glue_solar.sources.moments import _accepted, _form, _start, _view

__all__ = ["download_dkist", "frame_quality_dkist", "mosaic_dkist"]


def _check_mosaic(data):
    """Raise why ``data`` has no mosaic: it is no tile of a DKIST mosaic."""
    if len(getattr(data, "_mosaic", ())) < 2:
        raise ValueError(f"{data.label} is no tile of a DKIST mosaic.")


def _slice_shown(tiles, data_collection):
    """
    The indices of the axes but the last two of ``tiles``, a DKIST mosaic's, at which the first Image viewer of one of
    them along those two shows it, such as its frame, or Stokes parameter, repeat and wavelength; else their first.
    """
    app = _application(data_collection)
    for viewer in (viewer for tab in getattr(app, "viewers", ()) for viewer in tab):
        state, tile = viewer.state, viewer.state.reference_data
        if isinstance(viewer, MatplotlibImageMixin) and tile in tiles:
            if (state.y_att, state.x_att) == tuple(tile.pixel_component_ids[-2:]):
                return tuple(int(getattr(s, "center", s)) for s in state.slices[:-2])
    return (0,) * (tiles[0].ndim - 2)


def _add_mosaic(data_collection, tiles, at, image):
    """
    Add ``image``, the mosaic of ``tiles`` at ``at``, linked to them and to other data by 'Link helioprojective
    coordinates', and to each tile's time there (`_mosaic_links`, D108), and open it in an Image viewer at 99.5 %
    limits, as a quicklook's panels, where glue's Min/Max, of a few hot pixels, showed it flat (D109).
    """
    data_collection.append(image)
    data_collection.add_link(_mosaic_links(image, tiles, at))
    keep_hpc_linked(data_collection, others=[*tiles, image])
    viewer = _view(data_collection, image)
    if viewer is not None:  # its window open still
        viewer.state.layers[0].percentile = PERCENTILE


@layer_action(
    "Mosaic…",
    single=True,
    data=True,
    check=_check_mosaic,
    tooltip="Add this DKIST mosaic's tiles stitched into one image at the frame, wavelength and Stokes parameter shown",
)
@messagebox_on_error("Could not make the mosaic")
def mosaic_dkist(data, data_collection):
    """
    Add the loaded tiles of the DKIST mosaic of ``data`` reprojected into one image in the background (`_mosaic_image`,
    D108), at the frame, Stokes parameter, repeat and wavelength an Image viewer shows them at (`_slice_shown`), linked
    to them and to other data by 'Link helioprojective coordinates', and open it in an Image viewer.
    """
    _check_mosaic(data)
    tiles = [tile for tile in data._mosaic if tile in data_collection]
    at = _slice_shown(tiles, data_collection)
    text = f"Reprojecting the tiles of {data.label.rsplit(' (', 1)[0]}…"
    add = partial(_add_mosaic, data_collection, tiles, at)
    _start(data_collection, text, "Could not make the mosaic", _mosaic_image, tiles, at, add=add)


def _check_frames(data):
    """Raise why ``data`` has no frame quality: it is no DKIST dataset with its frames' quality in its headers."""
    if not getattr(data, "_quality", None):
        raise ValueError(f"{data.label} is no DKIST dataset with its frames' seeing or exposure in its headers.")


class _FrameCurves(QtCore.QObject):
    """
    Keep ``frames``, the frame quality of DKIST dataset ``data`` (`_frame_quality`), in Profile viewer ``profile`` and
    the time sliders of the Image viewers of ``data``, or of a tile of its mosaic, following each other by time (D110):
    a line at the row nearest the frame the last moved shows; a click on the curves, with no toolbar mode on, moves each
    to its frame nearest that row's time, at its own Stokes parameter; the frames whose AO was not locked shaded and
    the y axis named by the attribute shown. Not saved in sessions.
    """

    def __init__(self, profile, frames, data):
        super().__init__(profile)
        self.profile, self.frames, self.times = profile, frames, frames[frames.id["Time"]]
        self.datasets, self.viewer = list(getattr(data, "_mosaic", ())) or [data], None
        # in glue's crosshair color
        self.line = profile.axes.axvline(0, color="#d32d26", lw=1, zorder=99, visible=False, gid="solar:frame")
        self.unlocked = None
        profile.figure.canvas.mpl_connect("button_press_event", self._clicked)
        for prop in ("reference_data", "x_att", "x_display_unit", "y_display_unit", "normalize", "layers"):
            profile.state.add_callback(prop, self.refresh)
        self.moves = {}  # each Image viewer watched -> its slices callback (`_watch`)
        watched = coordinator(profile.session.data_collection)
        watched.watch_viewers(self._watch)
        self.destroyed.connect(partial(self._detach, watched, self._watch, self.moves))  # with its Profile viewer
        self.refresh()

    @staticmethod
    def _detach(watched, watch, moves):
        """Stop ``watch`` and ``moves``, its callbacks, following the Image viewers, which may stay open."""
        watched.unwatch_viewers(watch)
        for viewer in list(moves):
            _FrameCurves._leave(moves, viewer)

    @staticmethod
    def _leave(moves, viewer):
        """Take the callback in ``moves`` off ``viewer``: echo would keep it, and so the viewer and curves, for good."""
        if viewer in moves:
            viewer.state.remove_callback("slices", moves.pop(viewer))

    def _watch(self, viewer):
        if viewer not in self.moves:  # once, though a quicklook panel turned on again registers again
            self.moves[viewer] = partial(self._moved, viewer)
            viewer.state.add_callback("slices", self.moves[viewer])
            viewer.destroyed.connect(partial(self._leave, self.moves, viewer))  # closed
        self._moved(viewer)

    def _index(self, viewer):
        """
        The frame ``viewer`` shows, its index over the frame axes of its data, the dataset or a tile of its mosaic;
        None for other data, a frame axis shown, or a closed viewer.
        """
        state, data = viewer.state, viewer.state.reference_data
        if viewer._closed or data not in self.datasets or data._frames is None or None in (state.x_att, state.y_att):
            return None
        lead = data._frames[0].ndim
        if min(state.x_att.axis, state.y_att.axis) < lead or len(state.slices) != data.ndim:
            return None
        return tuple(int(getattr(s, "center", s)) for s in state.slices[:lead])

    def _rows(self):
        """The rows' x in the Profile viewer's unit, or None while it shows other data."""
        state = self.profile.state
        if self.profile._closed or state.reference_data is not self.frames or state.x_att is None:
            return None
        return UnitConverter().to_unit(self.frames, state.x_att, self.frames[state.x_att], state.x_display_unit)

    def _moved(self, viewer, *_):
        index = self._index(viewer)
        rows = self._rows()
        if index is None or rows is None:
            return
        self.viewer = viewer
        [row], _ = nearest([viewer.state.reference_data._frames[0][index]], self.times)
        self.line.set_xdata([rows[row]] * 2)
        self.line.set_visible(True)
        self.profile.figure.canvas.draw_idle()

    def refresh(self, *_):
        """Place the line, shading and y axis name again, as for another x attribute or unit."""
        rows, state = self._rows(), self.profile.state
        if self.unlocked is not None:
            self.unlocked.remove()
            self.unlocked = None
        self.line.set_visible(False)
        if rows is None:
            return
        lock = self.frames.find_component_id("AO_LOCK")
        if lock is not None:
            self.unlocked = self.profile.axes.fill_between(
                rows,
                0,
                1,
                where=self.frames[lock] == 0,
                step="mid",
                transform=self.profile.axes.get_xaxis_transform(),
                color="0.5",
                alpha=0.25,
                lw=0,
                gid="solar:ao_unlocked",
            )
        layer = next((layer for layer in state.layers if layer.layer is self.frames and layer.visible), None)
        if layer is not None and layer.attribute is not None and not state.normalize:
            unit = state.y_display_unit or self.frames.get_component(layer.attribute).units
            state.y_axislabel = f"{layer.attribute.label} [{unit}]" if unit else layer.attribute.label
        if self.viewer is not None:
            self._moved(self.viewer)
        self.profile.figure.canvas.draw_idle()

    def _clicked(self, event):
        rows = self._rows()
        if rows is None or event.button != 1 or event.inaxes is not self.profile.axes:
            return
        if self.profile.toolbar.active_tool is not None:  # a selection, zoom or pan
            return
        when = self.times[np.argmin(abs(rows - event.xdata))]
        viewers = (viewer for tab in self.profile.session.application.viewers for viewer in tab)
        for viewer in (viewer for viewer in viewers if isinstance(viewer, MatplotlibImageMixin)):
            index = self._index(viewer)
            if index is None:
                continue
            data = viewer.state.reference_data
            times = data._frames[0]
            axes = sorted(_time_axes(data) & set(range(times.ndim)))  # its frame axes of time, not of Stokes
            along = times[tuple(slice(None) if axis in axes else at for axis, at in enumerate(index))]
            [frame], _ = nearest([when], along.ravel())
            slices = list(viewer.state.slices)
            for axis, at in zip(axes, np.unravel_index(frame, along.shape)):
                slices[axis] = int(at)
            viewer.state.slices = tuple(slices)


@layer_action(
    "Frame quality…",
    single=True,
    data=True,
    check=_check_frames,
    tooltip="Plot the seeing, AO lock, exposure, light level and elevation of this DKIST dataset's frames against time",
)
@messagebox_on_error("Could not show the frame quality")
def frame_quality_dkist(data, data_collection):
    """
    Add the frame quality of ``data``, a DKIST dataset or a tile of a mosaic, from its headers (`_frame_quality`,
    D110), linked to it by ``Time``, or take the one added before, and open it in a Profile viewer that follows the time
    sliders of its Image viewers and moves them (`_FrameCurves`): the seeing, ``ATMOS_R0``, else the light level,
    ``LIGHTLVL``, the frames whose AO was not locked shaded; the others are the layer's attributes.
    """
    _check_frames(data)
    # the one added before, as a session restores it without its curves' line and clicks
    label = f"{data.label} frame quality"
    frames = next((d for d in data_collection if d.label == label and isinstance(d.coords, _FrameTimes)), None)
    if frames is None:
        frames = _frame_quality(data)
        data_collection.append(frames)
        time = data.find_component_id("Time")
        if time is not None:
            data_collection.add_link(LinkSame(frames.id["Time"], time))
    profile = _application(data_collection).new_data_viewer(ProfileViewer, data=frames)
    _FrameCurves(profile, frames, data)


# How often, in ms, 'Download these frames…' looks for its files (`_watch_download`)
DOWNLOAD_POLL = 5000


def _check_download(data):
    """Raise why ``data`` has no frames to download: it is no DKIST dataset from an ASDF file, or has all its files."""
    if getattr(data, "_dataset", None) is None:
        raise ValueError(f"{data.label} is no DKIST dataset opened from its ASDF file.")
    data._look()  # the files that arrived since by another transfer are not offered
    if all(tile._present.all() for tile in data._mosaic):
        raise ValueError(f"Every FITS file of {data.label} is in {data._dataset.files.basepath}.")


def _shown_at(tiles, data_collection):
    """
    The slider indices, one per array axis, of the first Image viewer of one of ``tiles``, a DKIST dataset or a
    mosaic's tiles, such as its Stokes parameter and repeat; else their first.
    """
    app = _application(data_collection)
    for viewer in (viewer for tab in getattr(app, "viewers", ()) for viewer in tab):
        if isinstance(viewer, MatplotlibImageMixin) and viewer.state.reference_data in tiles:
            return tuple(int(getattr(s, "center", s)) for s in viewer.state.slices)
    return (0,) * tiles[0].ndim


def _wanted(tile, index):
    """
    Whether each FITS file of ``tile``, a DKIST dataset, is at ``index`` along its files' axes and missing, not on its
    way in a download started before (`_ARRIVING`).
    """
    wanted = np.zeros(tile._present.shape, bool)
    wanted[index] = True
    if _ARRIVING:
        files = tile._dataset.files
        arriving = np.vectorize(lambda name: str(Path(files.basepath) / name) in _ARRIVING, otypes=[bool])
        wanted &= ~arriving(files.fileuri_array).reshape(wanted.shape)
    return wanted & ~tile._present


def _download_summary(tiles, index):
    """
    How many FITS files of ``tiles`` at ``index`` are missing (`_wanted`), their size, from their dataset's mean, as its
    ASDF file gives no file's own (8 % low for TXIPCV's Stokes I, of larger files than Q, U and V's), and times, and how
    many are there already.
    """
    wanted = [_wanted(tile, index) for tile in tiles]
    count, there = sum(int(w.sum()) for w in wanted), sum(int(np.sum(tile._present[index])) for tile in tiles)
    text = f"{count} file{'' if count == 1 else 's'} to download"
    inventory = tiles[0]._dataset.meta["inventory"]
    if inventory.get("datasetSize") and inventory.get("frameCount"):  # in GiB, as dkist reads it
        size = (inventory["datasetSize"] * u.GiB * count / inventory["frameCount"]).to(u.MB)
        text += f", about {size.to(u.GB) if size >= 1 * u.GB else size:.1f}"
    times = [tile._frames[0][w] for tile, w in zip(tiles, wanted) if tile._frames is not None]
    times = np.concatenate(times) if times else []
    if len(times):
        start, end = (np.datetime_as_string(time, "s") for time in (times.min(), times.max()))
        text += f", {start}" + (f" to {end}" if end != start else "")
    return text + (f" ({there} more already there)" if there else "")


def _ask_download(tiles, at):
    """
    The index along the FITS files' axes of ``tiles``, a DKIST dataset or a mosaic's loaded tiles, of those to
    download, asked in a dialog (D110): along each axis ``at``, its viewer's slider, such as its Stokes parameter and
    repeat, or all of it where ticked; along its steps or frames the range typed, all at first. It says how many files
    are missing and their size (`_download_summary`) as they change; None for Cancel.
    """
    data = tiles[0]
    dialog, form = _form(f"Download frames of {data.label.rsplit(' (', 1)[0]}")
    frame, wcs, boxes, summary = _frame_axis(data), data.coords, {}, QtWidgets.QLabel(objectName="summary")

    def index():
        return tuple(
            slice(boxes[axis][0].value(), boxes[axis][1].value() + 1)
            if axis == frame
            else (slice(None) if boxes[axis].isChecked() else at[axis])
            for axis in boxes
        )

    def update():
        summary.setText(_download_summary(tiles, index()))

    for axis, size in enumerate(data._present.shape):
        name, k = wcs._names[data.ndim - 1 - axis], wcs.world_n_dim - 1 - axis  # glue's world axis (`DKISTWCS`)
        if axis == frame:
            boxes[axis] = QtWidgets.QSpinBox(objectName="first"), QtWidgets.QSpinBox(objectName="last")
            row = QtWidgets.QHBoxLayout()
            for box, value in zip(boxes[axis], (0, size - 1)):
                box.setMaximum(size - 1)
                box.setValue(value)
                box.valueChanged.connect(update)
                row.addWidget(box)
            form.addRow(f"{name} ({size}):", row)
            continue
        value = str(at[axis])
        if wcs.world_axis_physical_types[k] == "phys.polarization.stokes":
            pixel = [at[axis] if p == data.ndim - 1 - axis else 0 for p in range(data.ndim)]
            value = str(StokesCoord(wcs.pixel_to_world_values(*pixel)[k]).symbol)
        boxes[axis] = QtWidgets.QCheckBox(f"all {size}", objectName=name)
        boxes[axis].toggled.connect(update)
        form.addRow(f"{name} {value}:", boxes[axis])
    form.addRow("Into:", QtWidgets.QLabel(str(data._dataset.files.basepath)))
    form.addRow(summary)
    update()
    return index() if _accepted(dialog, form) else None


def _watch_download(data_collection, label, pending):
    """
    Look every `DOWNLOAD_POLL` ms until all of ``pending``, FITS files of DKIST datasets by path, each a dataset and the
    file's index, are in their folder, glue's status bar saying how many are (D110): a file of the same size and time
    at two looks is whole, as Globus may write it in place; until then it reads as missing (`_ARRIVING`). Each whole
    file is marked present (``_present``), and its frame drawn, the color limits of its dataset, a mosaic's tiles all,
    taken again from the frames present, in every viewer; once all are, glue's Error Console says how many of the
    dataset's files are still missing, if any.
    """
    # ponytail: a transfer stalled one look mid-file reads as whole; Globus's task status if that happens
    app, total, seen = _application(data_collection), len(pending), {}
    if app is None:  # its window closed while the transfer started: its files read as they are, as a session's (D110)
        return
    datasets, folder = next(iter(pending.values()))[0]._mosaic, Path(next(iter(pending))).parent
    _ARRIVING.update(pending)
    timer = QtCore.QTimer(app)  # gone with glue's window, its files then read as they are, as a session restores them
    timer.destroyed.connect(lambda *_: _ARRIVING.difference_update(pending))

    def look():
        arrived = set()
        for path, (tile, index) in list(pending.items()):
            try:
                stat = os.stat(path)
            except OSError:  # not yet there
                continue
            if seen.get(path) == (stat.st_size, stat.st_mtime_ns):
                tile._present[index] = True
                _ARRIVING.discard(path)
                arrived.add(tile)
                del pending[path]
            seen[path] = stat.st_size, stat.st_mtime_ns
        if not arrived:
            return
        for tile in arrived:
            tile._samples.clear()  # its color limits' sample, a mosaic's tiles' too
            tile.__dict__.pop("_noise_cached", None)  # its Stokes parameters' noise (D107)
        for viewer in (viewer for tab in app.viewers for viewer in tab):
            for artist in viewer.layers:
                if artist.layer.data in datasets:  # a tile, or a subset of one: the sample is its mosaic's (D102)
                    limits = getattr(artist.state, "attribute_lim_helper", None)  # an Image layer's
                    if limits is not None:
                        limits.update_values(force=True)  # but limits typed (glue's 'Custom')
                if artist.layer.data in arrived:
                    artist.update()  # glue's NumericalDataChangedMessage would reset the viewer's sliders
        app.statusBar().showMessage(f"{label}: {total - len(pending)} of {total} files downloaded")
        if not pending:
            timer.stop()
            _note_missing(datasets, label, folder)

    timer.timeout.connect(look)
    timer.start(DOWNLOAD_POLL)
    app.statusBar().showMessage(f"{label}: 0 of {total} files downloaded")


@layer_action(
    "Download these frames…",
    single=True,
    data=True,
    check=_check_download,
    tooltip="Download by Globus this DKIST dataset's FITS files at the Stokes parameter and repeat shown, steps or "
    "frames chosen",
)
@messagebox_on_error("Could not start the download")
def download_dkist(data, data_collection):
    """
    Start a Globus transfer in the background of the missing FITS files of ``data``, a DKIST dataset, or of its
    mosaic's loaded tiles, chosen in a dialog (`_ask_download`) at the Stokes parameter, repeat and measurement of its
    first Image viewer (`_shown_at`), into its ASDF file's folder; those files alone, not dkist's ASDF file, movie and
    quality report (`_transfer`, D110). Their frames fill in as they arrive (`_watch_download`).
    """
    _check_download(data)
    tiles = [tile for tile in data._mosaic if tile in data_collection]
    label, folder = data.label.rsplit(" (", 1)[0], Path(data._dataset.files.basepath)
    if not any(_wanted(tile, ()).any() for tile in tiles):  # those missing of tiles removed from glue, or on their way
        raise ValueError(f"Every FITS file of {label} in glue is in {folder} or on its way.")
    index = _ask_download(tiles, _shown_at(tiles, data_collection))
    if index is None:
        return
    pending, parts = {}, []
    for tile in tiles:
        names = np.asarray(tile._dataset.files.fileuri_array).reshape(tile._present.shape)
        missing = [tuple(int(i) for i in at) for at in np.argwhere(_wanted(tile, index))]
        pending.update({str(folder / names[at]): (tile, at) for at in missing})
        if missing:  # dkist's dataset sliced to them, for its own download if need be (`_transfer`)
            parts.append((tile._dataset[index] if index else tile._dataset, [str(names[at]) for at in missing]))
    if not pending:  # a range of no step, or of files all there
        raise ValueError(f"No FITS file of {label} to download at this choice: each is in {folder} or on its way.")

    def send():
        _transfer(parts, folder)
        return pending

    add = partial(_watch_download, data_collection, label)
    text = f"{label}: starting the Globus transfer of {len(pending)} files…"
    _start(data_collection, text, "Could not start the download", send, add=add)
