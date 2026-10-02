"""
Helpers that drive glue's viewers the way a user does, and read the expected answers from the data.
"""

from collections import Counter

from matplotlib.backend_bases import MouseEvent

__all__ = ["count_tick_work", "load_selected", "mouse", "raster_point_on_sji", "select_point"]


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


def load_selected(qtbot, dialog):
    """Press the observation browser's Load selected, and wait until its worker thread is done."""
    from glue_solar.sources.loaders.iris import _RUNNING

    dialog.ok.click()
    assert not any(button.isEnabled() for button in (dialog.ok, dialog.change, dialog.recursive))
    assert dialog.cancel.text() == "Stop"
    qtbot.waitUntil(lambda: dialog.ok.isEnabled() and not _RUNNING, timeout=60_000)


def mouse(viewer, name, x, y, button=1):
    """Send the mouse event ``name`` at data position ``x, y`` of the viewer's axes."""
    viewer.figure.canvas.draw()
    px, py = viewer.axes.transData.transform((x, y))
    viewer.figure.canvas.callbacks.process(name, MouseEvent(name, viewer.figure.canvas, px, py, button=button))


def select_point(viewer, x, y):
    """Click pixel ``x, y`` with the Pixel tool."""
    viewer.toolbar.active_tool = "image:point_selection"
    mouse(viewer, "button_press_event", x, y)
    mouse(viewer, "button_release_event", x, y)


def raster_point_on_sji(raster, sji, step, slit, frame=0):
    """Raster pixel ``step, slit`` (at a stack's scan 0) in slit-jaw frame ``frame``, from the datasets' coordinates."""
    raster_types, types = list(raster.coords.world_axis_physical_types), list(sji.coords.world_axis_physical_types)
    raster_world, world = raster.coords.pixel_to_world_values(0, slit, step, *[0] * (raster.ndim - 3)), [None] * 3
    for kind in ("custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat"):
        world[types.index(kind)] = raster_world[raster_types.index(kind)]
    world[types.index("time")] = sji.coords.pixel_to_world_values(0, 0, frame)[types.index("time")]
    x, y, _ = sji.coords.world_to_pixel_values(*world)
    return x, y
