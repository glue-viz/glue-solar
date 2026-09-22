"""
Toolbar tools for glue's viewers.
"""

import numpy as np
from glue.config import viewer_tool
from glue.viewers.common.tool import Tool
from qtpy import QtWidgets

__all__ = ["FrameTimeTool"]

_WATCHED = ("reference_data", "x_att", "y_att", "slices")


@viewer_tool
class FrameTimeTool(Tool):
    """
    Show the acquisition time of the displayed frame in the Image Viewer's status bar.

    The readout follows the sliders and reads the ``Time`` component the IRIS loaders attach
    (one time per SJI exposure or raster step); the toolbar button hides and shows it. A frame
    spanning several exposures, such as a raster shown as step against slit, shows the range.
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
        cid = data.find_component_id("Time") if data is not None else None
        if cid is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
            self.label.setText("")
            return
        shown = (state.x_att.axis, state.y_att.axis)
        # an aggregated slider range carries its slice on the AggregateSlice object
        view = tuple(slice(None) if i in shown else getattr(s, "slice", s) for i, s in enumerate(state.slices))
        times = data[cid, view]
        first, last = (np.datetime_as_string(t, unit="ms") for t in (times.min(), times.max()))
        self.label.setText(f"{first} UTC" if first == last else f"{first} – {last} UTC")
