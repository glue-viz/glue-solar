import os
from collections import Counter
from pathlib import Path

import numpy as np
from glue.config import viewer_tool
from glue.core import Data
from glue.icons import icon_path
from glue.plugins.tools.path_slicer.matplotlib_mode import BasePathSlicerCrosshairMode, BasePathSlicerMode
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer

import glue_solar

# glue-solar's tools with an icon of glue-solar's own
OWN = ("solar:path", "solar:velocity", "solar:band", "solar:color_bar", "solar:slope")
# glue's icons on glue-solar's tools: the path crosshair's is glue's own tool's, the others borrowed
FROM_GLUE = {
    "solar:path_crosshair",
    "solar:follow_lock",
    "solar:frame_time",
    "solar:lines",
    "solar:per_frame_limits",
    "solar:save_sequence",
    "solar:save_profile",
}
# glue-solar's tools sharing an icon: the Modes menu and its Measure, and the save entries of two viewers
REPEATED = {"solar:measure", "solar:modes", "solar:save_sequence", "solar:save_profile"}


def _icon_file(icon):
    """The file of a tool's ``icon``, as glue-qt's toolbar finds it; icon_path raises for a missing one."""
    return icon if os.path.exists(icon) else icon_path(icon)


def test_icons_are_glue_solars_own(app):
    cube = Data(label="cube", x=np.zeros((3, 4, 5)))
    app.data_collection.append(cube)
    viewers = [app.new_data_viewer(viewer, data=cube) for viewer in (ImageViewer, ProfileViewer)]
    # every tool registered and every toolbar's, its menus' entries too
    tools = dict(viewer_tool.members) | {tid: type(t) for v in viewers for tid, t in v.toolbar.tools.items()}
    actions = {tid: action for v in viewers for tid, action in v.toolbar.actions.items()}
    files = {tid: _icon_file(tool.icon) for tid, tool in tools.items() if tool.icon is not None}
    content = {tid: Path(file).read_bytes() for tid, file in files.items()}
    ours = {tid for tid in files if tid.startswith("solar:")}
    # and glue-core's path slicer modes, which glue-solar's subclass and glue does not register
    glue = {content[tid] for tid in files.keys() - ours}
    glue |= {Path(icon_path(tool.icon)).read_bytes() for tool in (BasePathSlicerMode, BasePathSlicerCrosshairMode)}
    for tid in OWN:
        assert os.path.dirname(files[tid]) == os.path.join(os.path.dirname(glue_solar.__file__), "icons")
        assert not actions[tid].icon().isNull()  # in the toolbar or its menu
    assert {tid for tid in ours if content[tid] in glue} == FROM_GLUE
    repeats = Counter(content[tid] for tid in ours)
    assert {tid for tid in ours if repeats[content[tid]] > 1} == REPEATED
    assert tools["solar:path_crosshair"].icon == BasePathSlicerCrosshairMode.icon  # glue's path icon on its own tool
