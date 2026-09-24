"""WP5 (b): blink tool for the glue-qt Image viewer. Final form: CheckableTool + QTimer + interval spinbox on the toolbar."""
from glue.config import viewer_tool
import numpy as np
from qtpy import QtCore, QtWidgets
from glue.core import BaseData, Data, DataCollection
from glue.viewers.common.tool import CheckableTool
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
P = lambda *a: print(*a, flush=True)


# ---------------------------------------------------------------- the code that ships (glue_solar/viewers.py)
@viewer_tool
class BlinkTool(CheckableTool):
    """Show the visible image layers one at a time in turn; the spinbox next to the button sets the interval."""

    tool_id = "image:blink"
    icon = "glue_replace"
    action_text = "Blink layers"
    tool_tip = "Blink: show the visible image layers one at a time in turn"

    def __init__(self, viewer):
        super().__init__(viewer)
        self._timer = QtCore.QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._step)
        self._layers = []
        self._index = 0
        # ponytail: Tool.menu_actions() is never attached for a CheckableTool (glue_qt toolbar.py:106-136 only
        # calls setMenu for DropdownTool), so the interval knob is a plain toolbar widget instead.
        self._interval = QtWidgets.QSpinBox()
        self._interval.setRange(50, 5000)
        self._interval.setSingleStep(50)
        self._interval.setSuffix(" ms")
        self._interval.setValue(self._timer.interval())
        self._interval.setToolTip("Blink interval")
        self._interval.valueChanged.connect(self._timer.setInterval)
        viewer.toolbar.addWidget(self._interval)

    def _step(self):
        if not self._layers:
            return
        self._index = (self._index + 1) % len(self._layers)
        for i, layer in enumerate(self._layers):
            layer.state.visible = i == self._index

    def activate(self):
        # ponytail: the set of blinked layers is frozen at activation; toggle the tool to pick up new layers
        self._layers = [layer for layer in self.viewer.layers
                        if layer.enabled and layer.state.visible and isinstance(layer.layer, BaseData)]
        self._index = 0
        self._step()
        self._timer.start()

    def deactivate(self):
        self._timer.stop()
        for layer in self._layers:
            layer.state.visible = True
        self._layers = []

    def close(self):
        self.deactivate()
        super().close()


# setup(): ImageViewer.tools is a plain list on the class (glue_qt/viewers/image/data_viewer.py:42-45)
if "image:blink" not in ImageViewer.tools:
    ImageViewer.tools = [*ImageViewer.tools, "image:blink"]
# ---------------------------------------------------------------- end of shipping code


def main():
    d1 = Data(label="a", x=np.random.random((20, 20)))
    d2 = Data(label="b", x=np.random.random((20, 20)))
    d3 = Data(label="c", x=np.random.random((20, 20)))
    from glue.core.link_helpers import LinkSame
    dc = DataCollection([d1, d2, d3])
    for other in (d2, d3):  # pixel-align the synthetic images; real SJI/AIA pairs are linked by WCS/link_hpc
        for i in range(2):
            dc.add_link(LinkSame(d1.pixel_component_ids[i], other.pixel_component_ids[i]))
    app = GlueApplication(dc)
    v = app.new_data_viewer(ImageViewer, data=d1)
    v.add_data(d2); v.add_data(d3)
    v.layers[2].state.visible = False  # user hid 'c' on purpose: it must stay hidden and be left alone
    tool = v.toolbar.tools["image:blink"]
    P("toolbar has blink:", "image:blink" in v.toolbar.tools, "| spinbox in toolbar:", tool._interval.parent() is not None, "| interval:", tool._timer.interval())
    vis = lambda: [(l.layer.label, l.enabled, l.state.visible) for l in v.layers]
    v.toolbar.active_tool = "image:blink"
    P("activate  -> visible:", vis(), "| timer active:", tool._timer.isActive(), "| blinked:", [l.layer.label for l in tool._layers])
    tool._step(); P("step      -> visible:", vis())
    tool._step(); P("step      -> visible:", vis())
    tool._interval.setValue(200); P("spinbox 200 -> timer interval:", tool._timer.interval())
    # let the real timer fire a few times
    from glue_qt.utils import process_events
    import time
    t0 = time.monotonic(); snaps = []
    while time.monotonic() - t0 < 0.75:
        process_events(); snaps.append(tuple(vis())); time.sleep(0.05)
    P("timer-driven states seen:", sorted(set(snaps)))
    v.toolbar.active_tool = None
    P("deactivate -> visible:", vis(), "| timer active:", tool._timer.isActive())
    v.layers[1].state.alpha = 0.5; v.axes.figure.canvas.draw()
    comp = v.axes._composite
    P("mix already exists: composite alphas", [comp.layers[k]["alpha"] for k in comp.layers], "| color_mode choices:", type(v.state).color_mode.get_choices(v.state))
    # subset layer must not be blinked
    from glue.core.roi import RectangularROI
    v.apply_roi(RectangularROI(2, 8, 2, 8))
    v.toolbar.active_tool = "image:blink"
    P("with a subset layer: layers", [type(l).__name__ for l in v.layers], "| blinked:", [l.layer.label for l in tool._layers])
    v.toolbar.active_tool = None
    v.close(warn=False); P("viewer closed; timer active:", tool._timer.isActive(), "| tool.viewer:", tool.viewer)
    P("DONE")


if __name__ == "__main__":
    main()
