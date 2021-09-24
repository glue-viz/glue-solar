from __future__ import absolute_import, division, print_function
from glue.config import viewer_tool
from glue.core.data_derived import IndexedData
from glue.viewers.matplotlib.toolbar_mode import ToolbarModeBase
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.core.command import ApplySubsetState


@viewer_tool
class PixelInfoTool(ToolbarModeBase):
    """
    Create a "dervied dataset" corresponding to the selected pixel.

    The goal of this plugin is to:
    1. Show the pixel value at mouse location.
    2. Pick multiple pixels to allow a comparision at several locations.
        a. Allow numerical comparison of pixels, substract for example
    3. Open this automatically with an image viewer.

    Future goals would be allow this to interact with the slit tool in some mananer.
    """
    icon = "pencil"
    tool_id = 'solar:pixel_info'
    action_text = 'Pixel Info'
    tool_tip = 'Extract data for a pixel based on mouse location'
    status_tip = 'CLICK to select a point'
    _pressed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._move_callback = self._extract_pixel
        self._press_callback = self._on_press
        self._release_callback = self._on_release
        self._derived = None

    def _on_press(self, mode):
        self._pressed = True
        self._extract_pixel(mode)

    def _on_release(self, mode):
        self._pressed = False

    def _extract_pixel(self, mode):
        if not self._pressed:
            return
        x, y = self._event_xdata, self._event_ydata
        if x is None or y is None:
            return None

        xi = int(round(x))
        yi = int(round(y))
        indices = [None] * self.viewer.state.reference_data.ndim
        indices[self.viewer.state.x_att.axis] = xi
        indices[self.viewer.state.y_att.axis] = yi

        slices = [slice(None)] * self.viewer.state.reference_data.ndim
        slices[self.viewer.state.x_att.axis] = slice(x, x + 1)
        slices[self.viewer.state.y_att.axis] = slice(y, y + 1)

        if self._derived is None:
            self._derived = IndexedData(self.viewer.state.reference_data, indices)
            self.viewer.session.data_collection.append(self._derived)
        else:
            try:
                self._derived.indices = indices
            except TypeError:
                self.viewer.session.data_collection.remove(self._derived)
                self._derived = IndexedData(self.viewer.state.reference_data, indices)
                self.viewer.session.data_collection.append(self._derived)

        subset_state = PixelSubsetState(self.viewer.state.reference_data, slices)

        cmd = ApplySubsetState(data_collection=self.viewer._data,
                               subset_state=subset_state,
                               override_mode=None)
        self.viewer._session.command_stack.do(cmd)
