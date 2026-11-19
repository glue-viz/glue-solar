"""
What every analysis action shares: the check that data is an IRIS raster window (`check`), the wavelength pixels of a
range and the unit of its values (`window`, `unit`), the reader of its values a slab at a time (`read`, `slab_rows`,
`slabs`) and irispy's cube of them (`cube`), the dataset its maps go in (`dataset`), its dialog (`form`, `accepted`),
and the worker that computes it in the background, adds its result and opens its maps (`start`, `view`).
"""

import gc
import itertools
from functools import partial

import numpy as np
from glue.core.data import Data
from glue.core.link_helpers import LinkSame
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.utils.threading import Worker
from glue_qt.viewers.image import ImageViewer
from qtpy import QtWidgets

import astropy.units as u
from astropy.nddata import StdDevUncertainty
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS

from glue_solar import describe
from glue_solar.glue_patches import _application, refresh_layer_actions
from glue_solar.quicklook import _show, coordinator
from glue_solar.sources.loaders.iris import (
    _AXIS_NAMES,
    _HPC,
    _RUNNING,
    WCS_LOCK,
    _GlueWCS,
    keep_hpc_linked,
    per_second,
)
from glue_solar.sources.loaders.lazy import at_ceiling

# Samples per irispy call, which copies its input about seven times as float64, and per read of a mean spectrum
SLAB = 2**21
# irispy picks the wavelengths within the velocity range again, rounding its own way: a crop wider by this many
# Angstrom keeps every one it picks
HAIR = 1e-6


def check(data):
    """
    Raise why ``data`` is not an IRIS raster window of one scan, (raster step, slit, wavelength), or a stack of its
    scans, (scan, raster step, slit, wavelength).
    """
    if describe.role(data) != "raster" or data.ndim not in (3, 4) or describe.spectral_axes(data) != {data.ndim - 1}:
        raise ValueError(f"{data.label} is not an IRIS raster window.")


def window(data, ends, lines, continuum=None):
    """
    The wavelength pixels of ``data`` from the first to the last within ``ends``, a ``(lower, upper)`` pair in Angstrom
    ``lines`` says in words, or a ``continuum`` window, `HAIR` wider, and the unit of the values irispy is given
    (`read`); raises why for data that has none within ``ends``, or a continuum window that overlaps them or has none.
    """
    check(data)
    wavelengths, _ = describe.wavelengths(data)
    span = f"{data.label} ({wavelengths[0]:.2f} to {wavelengths[-1]:.2f} Å)"

    def within(low, high):
        return np.flatnonzero((wavelengths >= low - HAIR) & (wavelengths <= high + HAIR))

    inside = within(*ends)
    if not inside.size:
        raise ValueError(f"No wavelength of {span} lies within {lines}.")
    taken = [inside[0], inside[-1]]
    for low, high in continuum or ():
        if low <= ends[1] and high >= ends[0]:
            raise ValueError(f"The continuum window {low}-{high} Å overlaps {lines}.")
        window = within(low, high)
        if not window.size:
            raise ValueError(f"No wavelength of {span} lies within the continuum window {low}-{high} Å.")
        taken += [window[0], window[-1]]
    return slice(min(taken), max(taken) + 1), unit(data)


def unit(data, rate=None):
    """The unit of the values of ``data`` that irispy is given, per second with ``rate``, as `read` takes it."""
    from irispy.utils.constants import DN_UNIT  # with the first use rather than at glue's launch

    cid = data.main_components[0]
    with u.add_enabled_units(DN_UNIT.values()):  # astropy's registry, global: on the calling thread
        unit = u.Unit(data.get_component(cid).units)
    if rate is None:
        rate = data.find_component_id(f"{cid.label} DN / s") is not None
    return unit / u.s if rate else unit


def read(data, rows, wavelengths, rate=None):
    """
    The values of ``data`` at ``rows``, the scan of a stack, raster steps and slit pixels, and ``wavelengths`` that
    irispy is given, each step's exposure time in s, and which are saturated, as the window's mask marks them from the
    DN (`at_ceiling`, D85):
    with ``rate``, None for whether the window has the loader's ``<label> DN / s``, its DN over each step's exposure
    time (D4), from the DN read here, in float64, else its scaled float32 and None; NaN where missing, on any thread.
    """
    cid = data.main_components[0]
    values = data[cid, (*rows, wavelengths)]  # scaled float32 of these steps and wavelengths only
    if rate is None:
        rate = data.find_component_id(f"{cid.label} DN / s") is not None
    if not rate:
        return values, None, at_ceiling(values)
    # glue's derived component reads them again
    seconds = data["Exposure time", (*rows[:-1], slice(0, 1), slice(0, 1))].astype(np.float32)
    return per_second(values.astype(float), seconds), seconds, at_ceiling(values)


def cube(data, values, rows, wavelengths, unit, saturated, sigma=None, shift=0):
    """
    irispy's cube of ``values`` in ``unit``, of ``data`` at ``rows`` and ``wavelengths``, NaN, -Inf and ``saturated``
    masked, and ``saturated`` in ``meta['saturated']`` too, where irispy finds saturation (#239); with ``sigma``, each
    value's standard deviation (`_sigma`), and with ``shift``, each wavelength that of the pixel ``shift`` pixels
    further along.
    """
    from irispy.spectrograph import SpectrogramCube
    from ndcube.wcs.wrappers import ResampledLowLevelWCS

    view = SlicedLowLevelWCS(data.coords._wcs, (*rows, wavelengths))
    if shift:  # the wavelength is the first pixel axis
        view = ResampledLowLevelWCS(view, 1, (shift, 0, 0))
    uncertainty = None if sigma is None else StdDevUncertainty(sigma)
    mask = np.isnan(values) | np.isneginf(values) | saturated
    return SpectrogramCube(values, view, uncertainty, unit, mask=mask, meta={"saturated": saturated})


def slab_rows(data, crop, factor=1, scans=False):
    """
    The ``rows`` of each slab of ``data`` at ``crop``: raster steps of one scan, about `SLAB` / ``factor`` samples; with
    ``scans``, the whole scans of a stack that fit in one slab together, each still at its own coordinates.
    """
    steps = max(1, SLAB // (data.shape[-2] * (crop.stop - crop.start) * factor))
    together = steps // data.shape[-3] if scans and data.ndim == 4 else 0
    if together > 1:
        scans = range(0, data.shape[0], together)
        return [(slice(scan, min(scan + together, data.shape[0])), slice(None), slice(None)) for scan in scans]
    # each scan of a stack, as its own WCS and exposure times give it
    starts = itertools.product(np.ndindex(data.shape[:-3]), range(0, data.shape[-3], steps))
    return [(*scan, slice(start, start + steps), slice(None)) for scan, start in starts]


def slabs(data, crop, factor=1):
    """``(rows, values, seconds, saturated)``, `read` at ``crop``, for each of `slab_rows`; on any thread."""
    for rows in slab_rows(data, crop, factor):
        yield rows, *read(data, rows, crop)
        # ndcube's cubes are reference cycles, and irispy's hold the slab's values: else every slab's stay until
        # Python's collector runs
        gc.collect(0)


def dataset(data, label):
    """
    A new dataset ``label`` on the scans of a stack, raster steps and slit pixels of ``data``, following its pointing
    offset, with its observation's meta.
    """
    maps = Data(label=label)
    with WCS_LOCK:
        # the raster's own steps and slit pixels, each scan's: its wavelength does not move them
        maps.coords = _GlueWCS(SlicedLowLevelWCS(data.coords._wcs, (..., 0)))
    maps.coords.follow(data)
    # the observation's, for the quicklook's grouping and transparent NaN, without INSTRUME, which makes a raster
    maps.meta = {key: data.meta[key] for key in ("OBSID", "STARTOBS") if key in data.meta}
    return maps


def accepted(dialog, form):
    """Add OK and Cancel to ``form``, run ``dialog`` and say whether OK was pressed."""
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    accepted = dialog.exec() == QtWidgets.QDialog.Accepted
    dialog.deleteLater()  # else each run keeps a hidden dialog under the main window
    return accepted


def form(title):
    """A dialog ``title`` on glue's window and its form, for `accepted`."""
    dialog = QtWidgets.QDialog(QtWidgets.QApplication.activeWindow())
    dialog.setWindowTitle(title)
    return dialog, QtWidgets.QFormLayout(dialog)


def view(data_collection, result):
    """
    Open each map of ``result``, a dataset or a list, in a glue Image viewer in the current tab, at its first component
    and with its subsets, of the quicklooks' Points the followed one alone, longitude along x as on a quicklook's map;
    a table, such as the burst events, opens none (D83). Its pixels are linked to those of the dataset it is made from: through the
    helioprojective links alone, glue inverts the WCS for the Point, 5 exposures off and 0.2 s more a step on
    4000255147's sit-and-stare. Return the last viewer opened, or None.
    """
    app, viewer = _application(data_collection), None
    if app is None:  # its window closed meanwhile
        return
    coord = coordinator(data_collection)
    for data in result if isinstance(result, list) else [result]:
        if data.ndim < 2:
            continue
        made_from = getattr(data.coords, "follows", ())[:1]  # none for a line ratio of maps without coordinates
        source = next((other for other in data_collection if other.uuid in made_from), None)
        if source is not None:  # its leading axes are the map's
            pairs = zip(source.pixel_component_ids, data.pixel_component_ids)
            data_collection.add_link([LinkSame(*pair) for pair in pairs])
        viewer = app.new_data_viewer(ImageViewer, data=data)
        # glue-qt's default mouse mode empties the edit subset, the Point, at a click with no tool on (#244)
        viewer.toolbar._default_mouse_mode.deactivate()
        viewer.toolbar._default_mouse_mode = None
        for group in coord._owners:  # the followed Point alone, as on the quicklook's panels (D19)
            if group is not coord.group:
                _show(viewer, group, False)
        state = viewer.state
        for cid in data.world_component_ids:
            if cid.label == _AXIS_NAMES[_HPC[0]]:  # glue puts a raster's slit along x
                state.x_att_world = cid
    return viewer


def _add(data_collection, said, add, to_view, result):
    if result is None:  # a run canceled
        return
    if add is None:
        data_collection.append(result)  # a list too
        keep_hpc_linked(data_collection)
    else:
        add(result)
    if to_view:
        view(data_collection, result)
    message = said(result) if said else None
    status = status_bar(data_collection)  # none once its window closed meanwhile
    if message and status is not None:  # in place of what it says while it is computed
        status.showMessage(message)


def status_bar(data_collection):
    """The status bar of the glue window of ``data_collection``, or None."""
    app = _application(data_collection)
    return None if app is None else app.statusBar()


def clear(data_collection, text):
    status = status_bar(data_collection)  # none once its window closed meanwhile
    if status is not None and status.currentMessage() == text:  # unless something else has said more since
        status.clearMessage()


def reraise(exc_info):
    raise exc_info[1]


def start(data_collection, text, title, function, *args, said=None, add=None, view=False):
    """
    Compute ``function(*args)`` on glue-qt's `Worker`, while glue's status bar says ``text``, and add it, a dataset or
    a list, to ``data_collection``, or give it to ``add``, on the main thread, with ``view``, an analysis's, opening its
    maps (`view`), the status bar then saying ``said(result)``, if anything; or show its error in glue-qt's error box
    ``title``; then refresh the right-click entries (`refresh_layer_actions`).
    """
    worker = Worker(function, *args)
    status = status_bar(data_collection)
    worker.result.connect(partial(_add, data_collection, said, add, view))
    # glue-qt's decorator, as its GLUE_TESTING bypass is in it alone
    worker.error.connect(messagebox_on_error(title)(reraise))
    if status is not None:  # until the dataset is added or the error shown (D46)
        status.showMessage(text)
        worker.finished.connect(partial(clear, data_collection, text))
    _RUNNING.add(worker)

    def finished():  # queued: the message cleared, the result added by then
        _RUNNING.discard(worker)
        refresh_layer_actions(data_collection)  # the entries its result or error changes

    # one slot, the last: one queued after the discard could run once the worker is collected, its slots freed (segfault)
    worker.finished.connect(finished)
    worker.start()
