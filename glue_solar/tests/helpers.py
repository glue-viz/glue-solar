"""
Helpers that drive glue's viewers the way a user does, and read the expected answers from the data.
"""

from collections import Counter

import numpy as np
import pytest
from matplotlib.backend_bases import MouseEvent
from qtpy import QtWidgets
from qtpy.QtCore import QPoint, Qt
from qtpy.QtTest import QTest


def angles(data):
    """The helioprojective longitude and latitude of ``data`` at its first and last pixels, in arcsec, a row each."""
    from glue_solar.sources.loaders.iris import _HPC

    types = list(data.coords.world_axis_physical_types)
    world = data.coords.pixel_to_world_values(*zip([0] * data.ndim, np.subtract(data.shape[::-1], 1)))
    return np.array([world[types.index(kind)] for kind in _HPC])


def answer(monkeypatch, accept=True, **typed):
    """
    Make each dialog return as if ``typed`` were entered in its boxes of those names, a check box ticked or not, and
    OK, or Cancel, pressed; returns what each dialog's boxes opened with, by name.
    """
    kinds = (QtWidgets.QLineEdit, QtWidgets.QAbstractSpinBox, QtWidgets.QCheckBox)
    opened = []

    def shown(box):
        if isinstance(box, QtWidgets.QCheckBox):
            return box.isChecked()
        return box.text() if isinstance(box, QtWidgets.QLineEdit) else box.value()

    def enter(box, value):
        if isinstance(box, QtWidgets.QCheckBox):
            box.setChecked(value)
        elif isinstance(box, QtWidgets.QLineEdit):
            box.setText(value)
        else:
            box.setValue(value)

    def exec_(dialog):
        boxes = {box.objectName(): box for box in dialog.findChildren(QtWidgets.QWidget) if isinstance(box, kinds)}
        boxes = {name: box for name, box in boxes.items() if name and not name.startswith("qt_")}
        opened.append({name: shown(box) for name, box in boxes.items()})
        for name, value in typed.items():
            enter(boxes[name], value)
        return QtWidgets.QDialog.Accepted if accept else QtWidgets.QDialog.Rejected

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    return opened


def count_tick_work(monkeypatch, axes):
    """
    A Counter of the WCSAxes ``axes``' ``set_xlabel`` and ``set_ylabel`` calls, which place every tick at once,
    and of its ``_update_ticks``, one per coordinate in each tick placement.
    """
    from astropy.visualization.wcsaxes.coordinate_helpers import CoordinateHelper

    calls = Counter()
    for name in ("set_xlabel", "set_ylabel"):
        method = getattr(axes, name)
        monkeypatch.setattr(axes, name, lambda *args, _name=name, _method=method, **kwargs: (
            calls.update([_name]) or _method(*args, **kwargs)
        ))
    update_ticks = CoordinateHelper._update_ticks

    def counted(self):
        calls.update(["_update_ticks"] if self.parent_axes is axes else [])
        return update_ticks(self)

    monkeypatch.setattr(CoordinateHelper, "_update_ticks", counted)
    return calls


def linked_data(data_collection):
    """The datasets of ``data_collection`` that any link between datasets reaches."""
    linked = set()
    for link in data_collection.links:
        parents = {cid.parent for cid in (link.get_to_id(), *link.get_from_ids())}
        if len(parents) > 1:
            linked |= parents
    return linked


def inversions(monkeypatch, data):
    """A list that grows by one at each inversion of ``data``'s coordinates, world to pixel, from now on."""
    calls, inverse = [], data.coords.world_to_pixel_values
    monkeypatch.setattr(data.coords, "world_to_pixel_values", lambda *world: calls.append(1) or inverse(*world))
    return calls


def restore(qtbot, monkeypatch, path, show=False):
    """glue's application restored from the session ``path``, whose errors fail the test rather than open its dialog."""
    from glue_qt.app.application import GlueApplication

    app = GlueApplication.restore_session(str(path), show=show)
    qtbot.addWidget(app)
    monkeypatch.setattr(app, "report_error", lambda message, detail: pytest.fail(detail))
    return app


def run_action(app, qtbot, data, action, status, message="", added=1):
    """
    Trigger glue-qt's layer ``action`` on ``data`` and wait for its thread to end and the ``added`` datasets, glue's
    status bar saying ``status`` meanwhile and ``message`` then; returns the datasets added.
    """
    from glue_solar.sources.loaders.iris import _RUNNING

    collection, tree = app.data_collection, app._layer_widget
    count = len(collection)
    tree.ui.layerTree.set_selected_layers([data])
    tree._actions[action].trigger()
    assert _RUNNING  # on glue-qt's worker
    assert app.statusBar().currentMessage() == status
    # error maps take seconds
    qtbot.waitUntil(lambda: len(collection) == count + added and not _RUNNING, timeout=60_000)
    assert app.statusBar().currentMessage() == message
    return collection[count:]


def scanned(qtbot, dialog):
    """Wait until the observation browser has scanned its folder on its worker thread."""
    from glue_solar.sources.loaders.iris import _RUNNING

    qtbot.waitUntil(lambda: dialog.ok.isEnabled() and not _RUNNING, timeout=60_000)


def load_selected(qtbot, dialog):
    """Press the observation browser's Load selected, and wait until its worker thread is done."""
    from glue_solar.sources.loaders.iris import _RUNNING

    assert dialog.ok.isEnabled()  # not scanning its folder
    dialog.ok.click()
    assert not any(button.isEnabled() for button in (dialog.ok, dialog.change, dialog.recursive))
    assert dialog.cancel.text() == "Stop"
    qtbot.waitUntil(lambda: dialog.ok.isEnabled() and not _RUNNING, timeout=60_000)


def mouse(viewer, name, x, y, button=1):
    """Send the mouse event ``name`` at data position ``x, y`` of the viewer's axes."""
    viewer.figure.canvas.draw()
    px, py = viewer.axes.transData.transform((x, y))
    viewer.figure.canvas.callbacks.process(name, MouseEvent(name, viewer.figure.canvas, px, py, button=button))


def mouse_click(viewer, x, y):
    """
    Click data position ``x, y`` of the viewer with the mouse, whatever its mouse mode: Qt first makes its window the
    active one, as a user's click does, in a main window shown.
    """
    canvas = viewer.figure.canvas
    canvas.draw()
    px, py = viewer.axes.transData.transform((x, y))
    ratio = canvas.device_pixel_ratio
    at = QPoint(round(px / ratio), round((canvas.figure.bbox.height - py) / ratio))
    QTest.mouseClick(canvas, Qt.LeftButton, Qt.NoModifier, at)


def select_point(viewer, x, y):
    """Click pixel ``x, y`` with the Pixel tool."""
    viewer.toolbar.active_tool = "image:point_selection"
    mouse(viewer, "button_press_event", x, y)
    mouse(viewer, "button_release_event", x, y)


def press(viewer, key):
    """Press ``key`` over the viewer's image, as after a click on it, which makes its window the active one."""
    window = viewer.parent()
    window.mdiArea().setActiveSubWindow(window)
    QTest.keyClick(viewer.figure.canvas, key)


def raster_point_on_sji(raster, sji, step, slit, frame=0, scan=0):
    """Raster pixel ``step, slit`` (at a stack's scan ``scan``) in slit-jaw frame ``frame``, from their coordinates."""
    raster_types, types = list(raster.coords.world_axis_physical_types), list(sji.coords.world_axis_physical_types)
    raster_world, world = raster.coords.pixel_to_world_values(0, slit, step, *[scan] * (raster.ndim - 3)), [None] * 3
    for kind in ("custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat"):
        world[types.index(kind)] = raster_world[raster_types.index(kind)]
    world[types.index("time")] = sji.coords.pixel_to_world_values(0, 0, frame)[types.index("time")]
    x, y, _ = sji.coords.world_to_pixel_values(*world)
    return x, y


def resized(qtbot, viewers):
    """
    Wait until ``viewers`` are done resizing, on private timers: glue-qt's canvas ends a resize 250 ms after the last
    one, and mpl-scatter-density draws each image again 0.5 s after it.
    """
    from mpl_scatter_density.base_image_artist import BaseImageArtist

    canvases = [viewer.figure.canvas for viewer in viewers]
    images = [image for viewer in viewers for image in viewer.axes.images if isinstance(image, BaseImageArtist)]
    qtbot.waitUntil(
        lambda: (
            not any(canvas._resize_timer.isActive() for canvas in canvases)
            and all(image._make_image_called and not image._timer._timer.isActive() for image in images)
        )
    )


def refused(action):
    """Run glue-qt's layer ``action``, hidden for the layers selected, on them anyway, as its guard sees it."""
    assert not action.isVisible()
    action._do_action()


def shift(monkeypatch, data, collection, offset):
    """
    Choose 'IRIS: shift pointing…' on ``data`` and type ``offset``, in arcsec; returns the offset its dialog opened
    with.
    """
    from glue_solar.sources.iris import shift_pointing_iris

    opened = []

    def exec_(dialog):
        boxes = [dialog.findChild(QtWidgets.QDoubleSpinBox, name) for name in ("dx", "dy")]
        opened.append(tuple(box.value() for box in boxes))
        for box, value in zip(boxes, offset):
            box.setValue(value)
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtWidgets.QDialog, "exec", exec_)
    shift_pointing_iris(data, collection)
    return opened[0]
