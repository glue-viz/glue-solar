import os
import tempfile
from copy import deepcopy
from functools import partialmethod

import glue.config
import qtpy
from glue.config import fit_plugin, menubar_plugin, session_patch, stretches, unit_converter
from glue.core.state import GlueSerializer
from glue.logger import logger
from glue_qt.config import keyboard_shortcut, layer_action
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.image.profile_viewer_tool import ProfileViewerTool
from glue_qt.viewers.profile import ProfileViewer
from qtpy import QtWidgets

from astropy.visualization import PowerStretch

from sunpy.visualization.colormaps import cmlist

# Before anything of glue-solar registers with glue
if not qtpy.QT6:
    message = (
        f"glue-solar needs Qt 6 (PyQt6), not {qtpy.API_NAME} on Qt {qtpy.QT_VERSION}: install PyQt6, and set "
        "QT_API=pyqt6 where PyQt5 is installed too, as qtpy takes it first"
    )
    logger.error(message)  # glue logs a plugin that fails to load only at info level, which it does not show
    raise RuntimeError(message)

from glue_solar import glue_patches, lines, regrid, tools
from glue_solar.quicklook import QuicklookImageViewer
from glue_solar.sources import bursts, calibration, doppler, iris, line_ratio, maps, mg_features, moments, red_blue
from glue_solar.sources.maps import _add_colormap

from glue_solar.version import version as __version__

# glue-solar's data actions as the data collection's right-click menu lists them, after any others, by data kind: the
# spectral analyses, the image actions, then the coordinates; glue lists them as they register, in import order
_DATA_ACTIONS = (
    lines.rest_wavelength_iris,
    calibration.radiometric_calibration_iris,
    moments.mean_spectrum_iris,
    moments.moments_iris,
    doppler.doppler_iris,
    red_blue.red_blue_iris,
    mg_features.mg_features_iris,
    bursts.bursts_iris,
    line_ratio.line_ratio_iris,
    calibration.remove_dust_iris,
    regrid.north_up_iris,
    regrid.regrid_iris,
    regrid.rebin_iris,
    iris.shift_pointing_iris,
)
layer_action.members.sort(key=lambda item: _DATA_ACTIONS.index(item.callback) if item.callback in _DATA_ACTIONS else -1)

__all__ = [
    "setup",
    "__version__",
    "bursts",
    "calibration",
    "doppler",
    "glue_patches",
    "iris",
    "line_ratio",
    "lines",
    "maps",
    "mg_features",
    "moments",
    "red_blue",
    "regrid",
    "restore_last_session",
    "tools",
]


@session_patch()
def _add_session_colormaps(session):
    """
    List the sunpy colormaps a session names before glue restores them: glue saves a colormap's own name, which is its
    sunpy key only for rhessi, std_gamma_2 and the SUIT maps, and restores it by that name (`maps._add_colormap`).
    """
    for record in session.values():
        if isinstance(record, dict) and isinstance(record.get("cmap"), str):
            _add_colormap(record["cmap"])


def _last_session():
    """Where glue-solar keeps the last session, in glue's settings folder (``~/.glue``)."""
    return os.path.join(glue.config.CFG_DIR, "glue-solar-last-session.glu")


def _save_last_session(app):
    """
    Keep the session of ``app``, a shown glue application with data, as the last session, as glue's Export Session
    writes it with absolute paths to the files; one over 1 MB or that glue cannot save leaves the last session as it
    was, and the log says why.
    """
    if not app.isVisible() or not len(app.data_collection):
        return
    try:
        held = sum(  # the values glue would save, not their files: less than the session, measured before encoding
            component.data.nbytes
            for data in app.data_collection
            for component in map(data.get_component, data.main_components)
            if not hasattr(component, "_load_log")
        )
        if held > 1e6:
            raise ValueError(f"its data hold {held / 1e6:.1f} MB of values, over 1 MB")
        state = GlueSerializer(app, absolute_paths=True).dumps(indent=2)
        if len(state) > 1e6:  # data saved with their values, not their files
            raise ValueError(f"the session is {len(state) / 1e6:.1f} MB, over 1 MB")
        os.makedirs(glue.config.CFG_DIR, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=glue.config.CFG_DIR, suffix=".glu", delete_on_close=False) as file:
            file.write(state)
            file.close()
            os.replace(file.name, _last_session())  # whole or not at all
    except Exception as error:  # glue closes whatever happens
        logger.warning(f"glue-solar kept no last session: {error}")


_glue_close_event = None  # glue-qt's ``GlueApplication.closeEvent``, once `setup` wraps it


def _close_event(self, event):
    """glue-qt's ``GlueApplication.closeEvent``, keeping the session first, while its viewers are open."""
    _save_last_session(self)
    _glue_close_event(self, event)


@menubar_plugin("IRIS: restore last session")
def restore_last_session(session, data_collection):
    """
    Open the session glue-solar kept as glue's window last closed with data, as File → Open Session opens one.
    """
    app = session.application
    if not os.path.exists(_last_session()):
        QtWidgets.QMessageBox.information(
            app, "Restore last session", "No session kept yet: glue-solar keeps one as glue's window closes with data."
        )
        return
    app.restore_session_and_close(_last_session())


def _add_keys(viewer, keys):
    """Give glue-qt's ``viewer`` class those of ``keys``, {Qt key: function of the session}, it has no function for."""
    for key, function in keys.items():
        if key not in keyboard_shortcut.members.get(viewer, {}):
            keyboard_shortcut.add([viewer], key, function)


def setup():
    global _glue_close_event
    # Every sunpy colormap, under its own name; glue-qt draws each one's icon once (`glue_patches.update_icons`)
    for name in sorted(cmlist):
        _add_colormap(name)
    # Gamma stretches, value ** gamma between the limits; glue creates a stretch from its class with no arguments
    for gamma in (0.4, 0.75, 1.5, 2.2):
        if f"gamma_{gamma}" not in stretches.members:
            stretch = type("GammaStretch", (PowerStretch,), {"__init__": partialmethod(PowerStretch.__init__, gamma)})
            stretches.add(f"gamma_{gamma}", stretch, display=f"Gamma {gamma}")
    # The mouse modes and the display tools in menus of their own, to keep the toolbar short
    menus = {
        tools.ModesTool: [tools.MeasureTool, tools.PathTool, tools.PathCrosshairTool, tools.SlopeTool],
        tools.ViewTool: [
            tools.FrameTimeTool,
            tools.HideAxesTool,
            tools.PerFrameLimitsTool,
            tools.BandTool,
            tools.PhysicalAspectTool,
            tools.ZoomOneToOneTool,
            tools.ColourBarTool,
        ],
    }
    # glue-qt with its own readout (glue-viz/glue-qt#74, draft) does not need ours
    if not hasattr(ImageViewer, "cursor_status"):
        menus[tools.ViewTool].append(tools.CursorReadoutTool)
    # Right after glue's Home, Pan and Zoom, so that a narrow viewer moves glue's region tools, Pixel, Contrast/Bias,
    # the Profile viewer button and Slice Extraction behind the toolbar's » button first
    ours = [tool.tool_id for tool in (tools.FollowLockTool, tools.ModesTool, tools.CoordinateTool, tools.ViewTool)]
    ImageViewer.tools[:] = ours + [tool for tool in ImageViewer.tools if tool not in ours]
    # glue-qt 0.4.2's Profile viewer button has neither text nor tooltip
    if ProfileViewerTool.tool_tip is None:
        ProfileViewerTool.tool_tip = "Open a Profile viewer of this viewer's data along a slider's axis"
    from glue.plugins.tools import python_export  # noqa: F401, registers glue's "save:python", as its plugin does

    for viewer, tool in ((ImageViewer, tools.SaveSequenceTool), (ProfileViewer, tools.SaveProfileTool)):
        if tool.tool_id not in viewer.subtools["save"]:
            # a copy, as glue makes for its own entry: the Matplotlib viewers share the list
            viewer.subtools = deepcopy(viewer.subtools)
            # after glue's own, its Python script too, which glue's plugin adds after ours where it loads later, and
            # glue-qt then lists once
            save = viewer.subtools["save"]
            save += [tool_id for tool_id in ("save:python", tool.tool_id) if tool_id not in save]
    for menu, entries in menus.items():
        ImageViewer.subtools[menu.tool_id] = [tool.tool_id for tool in entries]
    for tool in (lines.LineTool, lines.VelocityTool):
        if tool.tool_id not in ProfileViewer.tools:
            ProfileViewer.tools.append(tool.tool_id)
    # km / s for the wavelength of data with a rest wavelength, in glue's own converter; a setting naming another
    # converter would be saved, and glue reads its settings before loading plugins
    unit_converter.members["default"] = lines.DopplerConverter
    # The Gaussian + constant fitter, which glue loads with the first Profile viewer, leaving astropy.modeling to it
    fit_plugin.lazy_add("glue_solar.fitters")
    # Keys for the viewer of the active window (`tools.KEYS`). glue-qt finds a viewer's keys by its exact class, so the
    # quicklook's raster panels take every key of the Image viewer, glue-qt's own Tab and Backspace too, which its
    # application module registers: glue loads plugins before it
    from glue_qt.app import keyboard_shortcuts  # noqa: F401

    for viewer in (ImageViewer, ProfileViewer):
        _add_keys(viewer, tools.KEYS)
    _add_keys(QuicklookImageViewer, keyboard_shortcut.members[ImageViewer])
    # The last session, kept as glue's window closes: on quit, and when another session replaces it
    from glue_qt.app.application import GlueApplication

    if GlueApplication.closeEvent is not _close_event:
        _glue_close_event, GlueApplication.closeEvent = GlueApplication.closeEvent, _close_event
