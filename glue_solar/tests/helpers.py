"""
Helpers that drive glue's viewers the way a user does, and read the expected answers from the data.
"""

from matplotlib.backend_bases import MouseEvent

__all__ = ["mouse", "raster_point_on_sji", "select_point"]


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
    """Raster pixel ``step, slit`` in slit-jaw frame ``frame``, from both datasets' own coordinates."""
    raster_types, types = list(raster.coords.world_axis_physical_types), list(sji.coords.world_axis_physical_types)
    raster_world, world = raster.coords.pixel_to_world_values(0, slit, step), [None] * 3
    for kind in ("custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat"):
        world[types.index(kind)] = raster_world[raster_types.index(kind)]
    world[types.index("time")] = sji.coords.pixel_to_world_values(0, 0, frame)[types.index("time")]
    x, y, _ = sji.coords.world_to_pixel_values(*world)
    return x, y
