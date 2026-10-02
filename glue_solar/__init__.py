from functools import partialmethod

from glue.config import session_patch, stretches
from glue_qt.viewers.image import ImageViewer

from astropy.visualization import PowerStretch

from sunpy.visualization.colormaps import cmlist

from glue_solar import glue_patches, tools
from glue_solar.sources import iris, maps
from glue_solar.sources.maps import _add_colormap

from glue_solar.version import version as __version__

__all__ = ["setup", "__version__", "glue_patches", "iris", "maps", "tools"]


@session_patch()
def _add_session_colormaps(session):
    """
    List the sunpy colormaps a session names by sunpy key, the name glue restores a colormap by, before it restores
    them. glue saves a colormap's own name, which is its key only for rhessi, std_gamma_2 and the SUIT maps.
    """
    for record in session.values():
        if isinstance(record, dict) and isinstance(record.get("cmap"), str):
            _add_colormap(record["cmap"])


def setup():
    # The IRIS slit-jaw and AIA colormaps, which IRIS data ask for; a sunpy Map adds its own as it loads
    for name in sorted(cmlist):
        if name.startswith(("irissji", "sdoaia")):
            _add_colormap(name)
    # Gamma stretches, value ** gamma between the limits; glue creates a stretch from its class with no arguments
    for gamma in (0.4, 0.75, 1.5, 2.2):
        if f"gamma_{gamma}" not in stretches.members:
            stretch = type("GammaStretch", (PowerStretch,), {"__init__": partialmethod(PowerStretch.__init__, gamma)})
            stretches.add(f"gamma_{gamma}", stretch, display=f"Gamma {gamma}")
    wanted = [tools.FrameTimeTool, tools.CoordinateTool, tools.HideAxesTool, tools.PerFrameLimitsTool]
    # glue-qt with its own readout (glue-viz/glue-qt#74, draft) does not need ours
    if not hasattr(ImageViewer, "cursor_status"):
        wanted.append(tools.CursorReadoutTool)
    for tool in wanted:
        if tool.tool_id not in ImageViewer.tools:
            ImageViewer.tools.append(tool.tool_id)
