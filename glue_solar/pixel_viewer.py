from glue.utils import decorate_all_methods, defer_draw
from glue.viewers.profile.qt.data_viewer import ProfileViewer

from glue_solar.options_widget import PixelToolOptionsWidget

__all__ = ["PixelInfoViewer"]


@decorate_all_methods(defer_draw)
class PixelInfoViewer(ProfileViewer):
    """
    A subclass of `glue.viewers.profile.qt.data_viewer.qt.ProfileViewer`.
    """

    LABEL = "Pixel Profile"
    _options_cls = PixelToolOptionsWidget
    allow_duplicate_data = False

    def __init__(self, session, parent=None, state=None):
        super().__init__(session=session, parent=parent, state=state)

    def setup_callbacks(self):
        super().setup_callbacks()
        self.state.add_callback("subtract profile", self._update_axes)
        self.state.add_callback("smooth profile", self._update_axes)

    def _update_axes(self, *args):
        super()._update_axes(*args)
