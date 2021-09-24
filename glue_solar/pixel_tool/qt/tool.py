from __future__ import absolute_import, division, print_function
from glue.config import viewer_tool
from glue.core.component_id import PixelComponentID
from glue.core.qt.dialogs import info, warn
from glue.viewers.image.qt.profile_viewer_tool import ProfileViewerTool

from glue_solar.pixel_tool.viewer import PixelInfoViewer


@viewer_tool
class PixelInfoTool(ProfileViewerTool):
    """
    Create a "dervied dataset" corresponding to the selected pixel.

    The goal of this plugin is to:
    1. Show the pixel value at mouse location.
    2. Pick multiple pixels to allow a comparision at several locations.
        a. Allow numerical comparison of pixels, subtract for example
    3. Open this automatically with an image viewer.

    Future goals would be allow this to interact with the slit tool in some manner.
    """

    icon = "pencil"
    tool_id = "solar:pixel_info"
    action_text = "Pixel Info"
    tool_tip = "Extract data for a pixel based on mouse location"
    status_tip = "CLICK to select a point"
    _pressed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def pixelinfo_viewers_exist(self):
        for tab in self.viewer.session.application.viewers:
            for viewer in tab:
                if isinstance(viewer, PixelInfoViewer):
                    return True
        return False

    def activate(self):
        if self.profile_viewers_exist:
            proceed = warn(
                "A profile viewer was already created",
                "Do you really want to create a new one?",
                default="Cancel",
                setting="show_warn_profile_duplicate",
            )
            if not proceed:
                return
        else:
            proceed = info(
                "Creating a profile viewer",
                "Note: profiles are "
                "computed from datasets and subsets collapsed along all but one "
                "dimension. To view the profile of part of the data, once you "
                "click OK you can draw and update a subset in the current "
                "image viewer and the profile will update accordingly.",
                setting="show_info_profile_open",
            )
            if not proceed:
                return
        profile_viewer = self.viewer.session.application.new_data_viewer(
            PixelInfoViewer
        )
        profile_viewer.state.function = "median"
        any_added = False
        for data in self.viewer.session.data_collection:
            if data in self.viewer._layer_artist_container:
                result = profile_viewer.add_data(data)
                any_added = any_added or result
        if not any_added:
            profile_viewer.close()
            return
        # If the reference data for the current image viewer is in the profile
        # viewer, we make sure that it is used as the reference data there too
        if self.viewer.state.reference_data in profile_viewer._layer_artist_container:
            profile_viewer.state.reference_data = self.viewer.state.reference_data
            # We now pick an attribute in the profile viewer that is one of the ones
            # with a slider in the image viewer. Note that the attribute viewer may
            # be a pixel attribute or world attribute depending on what information
            # is available in the coordinates, so we need to be careful about that.
            reference_data = self.viewer.state.reference_data
            if isinstance(profile_viewer.state.x_att, PixelComponentID):
                for att in reference_data.pixel_component_ids:
                    if (
                        att is not self.viewer.state.x_att
                        and att is not self.viewer.state.y_att
                    ):
                        if att is not profile_viewer.state.x_att:
                            profile_viewer.state.x_att = att
            else:
                for att in reference_data.world_component_ids:
                    if (
                        att is not self.viewer.state.x_att_world
                        and att is not self.viewer.state.y_att_world
                    ):
                        if att is not profile_viewer.state.x_att:
                            profile_viewer.state.x_att = att
