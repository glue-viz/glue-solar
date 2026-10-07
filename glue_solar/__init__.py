from functools import partialmethod

from glue.config import session_patch, stretches
from glue_qt.config import keyboard_shortcut
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer

from astropy.visualization import PowerStretch

from sunpy.visualization.colormaps import cmlist

from glue_solar import glue_patches, lines, regrid, tools
from glue_solar.quicklook import QuicklookImageViewer
from glue_solar.sources import iris, maps, moments
from glue_solar.sources.maps import _add_colormap

from glue_solar.version import version as __version__

__all__ = ["setup", "__version__", "glue_patches", "iris", "lines", "maps", "moments", "regrid", "tools"]


@session_patch()
def _add_session_colormaps(session):
    """
    List the sunpy colormaps a session names before glue restores them: glue saves a colormap's own name, which is its
    sunpy key only for rhessi, std_gamma_2 and the SUIT maps, and restores it by that name (`maps._add_colormap`).
    """
    for record in session.values():
        if isinstance(record, dict) and isinstance(record.get("cmap"), str):
            _add_colormap(record["cmap"])


def _add_keys(viewer, keys):
    """Give glue-qt's ``viewer`` class those of ``keys``, {Qt key: function of the session}, it has no function for."""
    for key, function in keys.items():
        if key not in keyboard_shortcut.members.get(viewer, {}):
            keyboard_shortcut.add([viewer], key, function)


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
    wanted = [
        tools.FollowLockTool,
        tools.FrameTimeTool,
        tools.CoordinateTool,
        tools.HideAxesTool,
        tools.PerFrameLimitsTool,
        tools.PhysicalAspectTool,
    ]
    # glue-qt with its own readout (glue-viz/glue-qt#74, draft) does not need ours
    if not hasattr(ImageViewer, "cursor_status"):
        wanted.append(tools.CursorReadoutTool)
    for tool in wanted:
        if tool.tool_id not in ImageViewer.tools:
            ImageViewer.tools.append(tool.tool_id)
    if lines.LineTool.tool_id not in ProfileViewer.tools:
        ProfileViewer.tools.append(lines.LineTool.tool_id)
    # Keys for the viewer of the active window (`tools.KEYS`). glue-qt finds a viewer's keys by its exact class, so the
    # quicklook's raster panels take every key of the Image viewer, glue-qt's own Tab and Backspace too, which its
    # application module registers: glue loads plugins before it
    from glue_qt.app import keyboard_shortcuts  # noqa: F401

    for viewer in (ImageViewer, ProfileViewer):
        _add_keys(viewer, tools.KEYS)
    _add_keys(QuicklookImageViewer, keyboard_shortcut.members[ImageViewer])
