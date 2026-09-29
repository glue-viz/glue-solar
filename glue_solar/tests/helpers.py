"""
Helpers that drive glue's viewers the way a user does.
"""

from matplotlib.backend_bases import MouseEvent

__all__ = ["mouse", "select_point"]


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
