from glue.config import colormaps
from glue_qt.viewers.image import ImageViewer

from sunpy.visualization.colormaps import cmlist

from glue_solar import tools
from glue_solar.sources import iris, maps

from glue_solar.version import version as __version__

__all__ = ["setup", "__version__", "iris", "maps", "tools"]


def setup():
    # Enables sunpy colormaps to be used in glueviz
    for _, ctable in sorted(cmlist.items()):
        colormaps.add(ctable.name, ctable)
    if tools.FrameTimeTool.tool_id not in ImageViewer.tools:
        ImageViewer.tools.append(tools.FrameTimeTool.tool_id)
