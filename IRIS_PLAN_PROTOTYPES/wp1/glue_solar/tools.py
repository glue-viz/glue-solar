"""
Toolbar tools for glue's viewers.
"""

import numpy as np
from glue.config import viewer_tool
from glue.core.component import DateTimeComponent
from glue.viewers.common.tool import Tool
from qtpy import QtWidgets

__all__ = ["CursorReadoutTool", "FrameTimeTool"]

_WATCHED = ("reference_data", "x_att", "y_att", "slices")


def _time_component(data):
    """The first datetime component of ``data``, or None."""
    return next((cid for cid in data.main_components if isinstance(data.get_component(cid), DateTimeComponent)), None)


@viewer_tool
class FrameTimeTool(Tool):
    """
    Show the acquisition time of the displayed frame in the Image Viewer's status bar.

    The readout follows the sliders and reads the first datetime component of the reference
    data, whichever loader attached it (the IRIS loaders add ``Time``, one per SJI exposure or
    raster step); the toolbar button hides and shows it. A frame spanning several exposures,
    such as a raster shown as step against slit, shows the range.
    """

    icon = "glue_slice"
    tool_id = "solar:frame_time"
    action_text = "Frame time"
    tool_tip = "Show or hide the acquisition time of the displayed frame"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.label = QtWidgets.QLabel()
        self.label.setContentsMargins(0, 0, 12, 0)  # keep clear of the window edge and size grip
        viewer.statusBar().addPermanentWidget(self.label)
        for prop in _WATCHED:
            viewer.state.add_callback(prop, self._refresh)
        self._refresh()

    def activate(self):
        self.label.setHidden(not self.label.isHidden())

    def close(self):
        for prop in _WATCHED:
            self.viewer.state.remove_callback(prop, self._refresh)
        super().close()

    def _refresh(self, *_):
        state = self.viewer.state
        data = state.reference_data
        cid = _time_component(data) if data is not None else None
        if cid is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
            self.label.setText("")
            return
        shown = (state.x_att.axis, state.y_att.axis)
        # an aggregated slider range carries its slice on the AggregateSlice object
        view = tuple(slice(None) if i in shown else getattr(s, "slice", s) for i, s in enumerate(state.slices))
        times = data[cid, view]
        first, last = (np.datetime_as_string(t, unit="ms") for t in (times.min(), times.max()))
        self.label.setText(f"{first} UTC" if first == last else f"{first} – {last} UTC")


@viewer_tool
class CursorReadoutTool(Tool):
    """
    Show the world position and the data value under the mouse in the Image Viewer's status bar.

    The position is whatever the reference data's WCS maps the displayed axes to (helioprojective
    position, wavelength, ...), formatted by the viewer's WCSAxes; the value is the reference
    layer's displayed attribute at that pixel of the current slice. Pressing ``w`` over the image
    switches WCSAxes between world and pixel positions. The toolbar button hides and shows the
    readout.
    """

    icon = "glue_crosshair"
    tool_id = "solar:cursor_readout"
    action_text = "Cursor readout"
    tool_tip = "Show or hide the position and value under the mouse (press W over the image for pixels)"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.shown = True
        self._motion = viewer.axes.figure.canvas.mpl_connect("motion_notify_event", self._on_move)

    def activate(self):
        self.shown = not self.shown
        if not self.shown:
            self.viewer.set_status("")

    def close(self):
        self.viewer.axes.figure.canvas.mpl_disconnect(self._motion)
        super().close()

    def _on_move(self, event):
        if self.shown and event.inaxes is self.viewer.axes:
            self.viewer.set_status(self.describe(event.xdata, event.ydata))

    def describe(self, x, y):
        """The status text for pixel position ``x, y`` of the displayed axes."""
        state = self.viewer.state
        text = self.viewer.axes.format_coord(x, y)
        data = state.reference_data
        layer = next((ls for ls in state.layers if ls.layer is data and ls.visible), None)
        if layer is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
            return text
        ix, iy = int(round(x)), int(round(y))
        if not (0 <= ix < data.shape[state.x_att.axis] and 0 <= iy < data.shape[state.y_att.axis]):
            return text
        # an aggregated slider range carries its middle slice on the AggregateSlice object
        view = tuple(
            ix if i == state.x_att.axis else iy if i == state.y_att.axis else getattr(s, "center", s)
            for i, s in enumerate(state.slices)
        )
        value = data[layer.attribute, view]
        try:
            value = f"{float(value):.6g}"
        except (TypeError, ValueError):  # datetime or string components
            value = str(value)
        # IRIS components are named after their dataset; say 'value' rather than repeat it
        name = "value" if layer.attribute.label == data.label else layer.attribute.label
        return f"{text} | {name} = {value}"
