from glue.config import colormaps, session_patch
from glue_qt.viewers.image import ImageViewer

from sunpy.visualization.colormaps import cmlist

from glue_solar import glue_patches, tools
from glue_solar.sources import iris, maps

from glue_solar.version import version as __version__

__all__ = ["setup", "__version__", "glue_patches", "iris", "maps", "tools"]


def _add_colormap(name):
    """
    List sunpy's colormap ``name``, if sunpy has one, in glue's colormap menus. glue-qt draws every colormap listed
    each time it builds an Image layer's menu, so only those that data ask for are listed.
    """
    ctable = cmlist.get(name)
    if ctable is not None and all(ctable is not cmap for _, cmap in colormaps.members):
        colormaps.add(ctable.name, ctable)


@session_patch()
def _add_session_colormaps(session):
    """List the sunpy colormaps a session names, which glue restores by name, before it restores them."""
    for record in session.values():
        if isinstance(record, dict) and isinstance(record.get("cmap"), str):
            _add_colormap(record["cmap"])


def setup():
    # The IRIS slit-jaw and AIA colormaps, which IRIS data ask for; a sunpy Map adds its own as it loads
    for name in sorted(cmlist):
        if name.startswith(("irissji", "sdoaia")):
            _add_colormap(name)
    wanted = [tools.FrameTimeTool, tools.CoordinateTool, tools.HideAxesTool]
    # glue-qt with its own readout (glue-viz/glue-qt#74, draft) does not need ours
    if not hasattr(ImageViewer, "cursor_status"):
        wanted.append(tools.CursorReadoutTool)
    for tool in wanted:
        if tool.tool_id not in ImageViewer.tools:
            ImageViewer.tools.append(tool.tool_id)
