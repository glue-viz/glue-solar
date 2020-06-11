from __future__ import absolute_import, division, print_function

from glue.config import viewer_tool
from glue.core.data_derived import IndexedData
from glue.viewers.matplotlib.toolbar_mode import ToolbarModeBase

__all__ = ['CubeSliderTool']


@viewer_tool

class CubeSliderTool(ToolbarModeBase):
    """
    Slice a data cube to obtain a given 1D profile.

    """
    # icon = "glue_crosshair"
    action_text = 'Cube Slider'
    tool_id = 'solar:cube_slider'
    tool_tip = 'To slice a data cube'
    status_tip = 'CLICK to select a cut, then CLICK and DRAG to slice data cube in real time'

    _pressed = False

    def __init__(self, *args, **kwargs):
        super(CubeSliderTool, self).__init__(*args, **kwargs)

        self._move_callback = self._slice_cube
        self._press_callback = self._on_press
        self._release_callback = self._on_release
        self._sliced = None

        self._line_x = self.viewer.axes.axvline(0, color='#00BFFF')
        self._line_x.set_visible(False)

    # def menu_actions(self):
    #     return []

    def _on_press(self, mode):
        self._pressed = True
        self._slice_cube(mode)

    def _on_release(self, mode):
        self._pressed = False

    def _slice_cube(self, mode):

        if not self._pressed:
            return

        x = self._event_xdata

        if x is None:
            return None

        xi = int(round(x))
        print('xi', xi)
        print('self.viewer.state.x_att.axis', self.viewer.state.x_att.axis)

        slider_indices = [None] * self.viewer.state.reference_data.ndim
        slider_indices[self.viewer.state.x_att.axis] = xi

        self._line_x.set_data([x, x], [0, 1])
        self._line_x.set_visible(True)

        self.viewer.axes.figure.canvas.draw()

        if self._sliced is None:
            self._sliced = IndexedData(self.viewer.state.reference_data, slider_indices)
            self.viewer.session.data_collection.append(self._sliced)
        else:
            try:
                self._sliced.indices = slider_indices
            except TypeError:
                self.viewer.session.data_collection.remove(self._sliced)
                self._sliced = IndexedData(self.viewer.state.reference_data, slider_indices)
                self.viewer.session.data_collection.append(self._sliced)
