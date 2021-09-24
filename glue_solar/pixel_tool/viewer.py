from glue.utils import decorate_all_methods, defer_draw
from glue.viewers.profile.qt.data_viewer import ProfileViewer

from glue_solar.pixel_tool.qt.layer_artist import QThreadedPixelLayerArtist
from glue_solar.pixel_tool.qt.options_widget import PixelToolOptionsWidget
from glue_solar.pixel_tool.state import PixelToolViewerState

__all__ = ["PixelInfoViewer"]


@decorate_all_methods(defer_draw)
class PixelInfoViewer(ProfileViewer):
    """
    A subclass of `glue.viewers.profile.qt.data_viewer.qt.ProfileViewer`.
    """

    _data_artist_cls = QThreadedPixelLayerArtist
    _options_cls = PixelToolOptionsWidget
    _state_cls = PixelToolViewerState
    _subset_artist_cls = QThreadedPixelLayerArtist
    allow_duplicate_data = False
    LABEL = "Pixel Profile"

    def __init__(self, session, parent=None, state=None):
        super().__init__(session=session, parent=parent, state=state)
