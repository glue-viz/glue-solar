import numpy as np
from glue.utils import defer_draw
from glue.viewers.profile.layer_artist import ProfileLayerArtist

from glue_solar.pixel_tool.state import PixelInfoLayerState

__all__ = ["PixelLayerArtist"]


class PixelLayerArtist(ProfileLayerArtist):
    # TODO; Work out how to subclass this properly.
    _layer_state_cls = PixelInfoLayerState

    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)

    def _calculate_profile_postthread(self):
        self.notify_end_computation()
        # It's possible for this method to get called but for the state to have
        # been updated in the mean time to have a histogram that raises an
        # exception (for example an IncompatibleAttribute). If any errors happen
        # here, we simply ignore them since _calculate_histogram_error will get
        # called directly.
        try:
            visible_data = self.state.profile
        except Exception:
            return
        self.enable()
        # The following can happen if self.state.visible is None - in this case
        # we just terminate early. If the visible propertx`y is changed, it will
        # trigger the _calculate_profile code to re-run.
        if visible_data is None:
            return
        x, y = visible_data
        # Update the data values.
        if len(x) > 0:
            self.state.update_limits()
            # Normalize profile values to the [0:1] range based on limits
            if self._viewer_state.subtract:
                profile_y = self._viewer_state.layers[0].profile[1]
                if not np.allclose(y, profile_y):
                    y = self.state.subtract_reference(y, profile_y)
            if self._viewer_state.normalize:
                y = self.state.normalize_values(y)
            self.plot_artist.set_data(x, y)
        else:
            # We need to do this otherwise we get issues on Windows when
            # passing an empty list to plot_artist
            self.plot_artist.set_data([0.0], [0.0])
        self.redraw()

    @defer_draw
    def _update_visual_attributes(self):
        super()._update_visual_attributes()
        for mpl_artist in self.mpl_artists:
            if self._viewer_state.smooth:
                mpl_artist.set_drawstyle("default")
            else:
                mpl_artist.set_drawstyle("steps-mid")
        self.redraw()

    def _update_profile(self, force=False, **kwargs):
        if (
            self._viewer_state.x_att is None
            or self.state.attribute is None
            or self.state.layer is None
        ):
            return
        # NOTE: we need to evaluate this even if force=True so that the cache
        # of updated properties is up to date after this method has been called.
        changed = self.pop_changed_properties()
        if force or any(
            prop in changed
            for prop in (
                "layer",
                "x_att",
                "attribute",
                "function",
                "normalize",
                "subtract",
                "v_min",
                "v_max",
                "visible",
            )
        ):
            self._calculate_profile(reset=force)
            force = True
        if force or any(
            prop in changed
            for prop in ("smooth", "alpha", "color", "zorder", "linewidth")
        ):
            self._update_visual_attributes()
