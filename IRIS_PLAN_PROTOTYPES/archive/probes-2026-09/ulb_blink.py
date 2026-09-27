from glue.config import settings, viewer_tool; settings._save_to_disk = False
import numpy as np
from qtpy import QtCore
from glue.core import Data, DataCollection
from glue.viewers.common.tool import CheckableTool
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
P = lambda *a: print(*a, flush=True)

@viewer_tool
class BlinkTool(CheckableTool):
    tool_id = 'image:blink'; icon = 'glue_move'; action_text = 'Blink'; tool_tip = 'Blink layers'
    def __init__(self, viewer):
        super().__init__(viewer); self._t = QtCore.QTimer(); self._t.setInterval(500); self._t.timeout.connect(self._step); self._i = 0
    def _layers(self): return [l for l in self.viewer.layers if l.enabled]
    def _step(self):
        ls = self._layers(); self._i = (self._i + 1) % len(ls)
        for k, l in enumerate(ls): l.state.visible = (k == self._i)
    def activate(self): self._step(); self._t.start()
    def deactivate(self):
        self._t.stop()
        for l in self._layers(): l.state.visible = True

ImageViewer.tools = list(ImageViewer.tools) + ['image:blink']
d1 = Data(label='a', x=np.random.random((20, 20))); d2 = Data(label='b', x=np.random.random((20, 20)))
app = GlueApplication(DataCollection([d1, d2]))
v = app.new_data_viewer(ImageViewer, data=d1); v.add_data(d2)
P("tools:", ImageViewer.tools, "| toolbar has blink:", 'image:blink' in v.toolbar.tools)
t = v.toolbar.tools['image:blink']; t.activate()
P("after activate visible:", [l.state.visible for l in v.layers])
t._step(); P("after step visible:", [l.state.visible for l in v.layers])
t.deactivate(); P("after deactivate visible:", [l.state.visible for l in v.layers])
v.layers[1].state.alpha = 0.5; v.axes.figure.canvas.draw()
comp = v.axes._composite
P("composite alphas:", [comp.layers[k]['alpha'] for k in comp.layers], "| color_mode choices:", type(v.state).color_mode.get_choices(v.state))
P("DONE")
