import numpy as np
from glue.viewers.matplotlib.state import DeferredDrawCallbackProperty
from glue.viewers.profile.state import ProfileLayerState, ProfileViewerState

__all__ = ["PixelToolViewerState", "PixelInfoLayerState"]


class PixelToolViewerState(ProfileViewerState):
    """
    A state class that includes all the attributes for a Pixel Info viewer.
    """

    smooth = DeferredDrawCallbackProperty(
        False, docstring="Whether to smooth the profile."
    )
    subtract = DeferredDrawCallbackProperty(
        False, docstring="Whether to subtract the reference profile."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_callback("smooth", self._reset_y_limits)
        self.add_callback("subtract", self._reset_y_limits)


class PixelInfoLayerState(ProfileLayerState):
    """
    A state class that includes all the attributes for layers in a PixelInfo plot.
    """

    def __init__(self, layer=None, viewer_state=None, **kwargs):
        super().__init__(layer=layer, viewer_state=viewer_state, **kwargs)

    def subtract_reference(self, values, reference):
        return np.asarray(values) - np.asarray(reference)

    def smooth_values(self, values):
        return (np.asarray(values) - self.v_min) / (self.v_max - self.v_min)
