"""
Re-verification probes for glue-solar's glue-qt items (D89). Each check prints FAULT (the problem is there), OK (not
there) or SKIP, with the key number. ``--src DIR`` puts a glue-qt tree first on sys.path (the main clone or a fork
branch export); without it the installed glue-qt is probed.

Run: HOME=<scratch home> QT_QPA_PLATFORM=offscreen MPLBACKEND=agg python -I probe_qt.py [--src DIR] [check ...]
"""
import argparse
import gc
import inspect
import os
import subprocess
import sys
import time
import traceback
import weakref
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument("--src")
parser.add_argument("checks", nargs="*")
args = parser.parse_args()
if args.src:
    sys.path.insert(0, args.src)

# keep glue-solar's plugin (installed in the env) from patching what is probed
cfg_dir = os.path.join(os.environ["HOME"], ".glue")
os.makedirs(cfg_dir, exist_ok=True)
with open(os.path.join(cfg_dir, "plugins.cfg"), "w") as f:
    f.write("[plugins]\nglue_solar = 0\n")

import numpy as np  # noqa: E402
import glue_qt  # noqa: E402
from glue.core import Data, DataCollection  # noqa: E402
from qtpy import QtCore, QtGui, QtWidgets  # noqa: E402
from qtpy.QtCore import Qt  # noqa: E402

print("glue_qt from", os.path.dirname(glue_qt.__file__))

from glue_qt.utils import get_qapp, process_events  # noqa: E402

qapp = get_qapp()

CHECKS = {}


def check(f):
    CHECKS[f.__name__] = f
    return f


_app = None


def app():
    global _app
    if _app is None:
        from glue_qt.app.application import GlueApplication
        _app = GlueApplication()
        _app.resize(1200, 800)
        _app.show()
        process_events()
        assert "glue_solar" not in sys.modules, "glue_solar got loaded"
    return _app


def cube(shape=(4, 5, 6), label="cube"):
    return Data(label=label, x=np.arange(int(np.prod(shape)), dtype=float).reshape(shape))


def profile_tools(viewer):
    return viewer.toolbar.tools["profile-analysis"]._profile_tools


def close_all(a):
    for tab in list(a.viewers):
        for v in list(tab):
            v.close(warn=False)
    process_events()
    for d in list(a.data_collection):
        a.data_collection.remove(d)
    process_events()


# ---------------------------------------------------------------- Fit tab and fitters

@check
def fitter_new_per_fit():
    """A new fitter for Settings and for each fit, so Settings never reach the fit (fork branch fitter-settings)."""
    from glue.core.fitters import BaseFitter1D
    from glue.core.simpleforms import IntOption
    from glue_qt.viewers.profile import ProfileViewer
    from glue_qt.viewers.profile.profile_tools import ProfileTools
    src = inspect.getsource(ProfileTools._on_fit) + inspect.getsource(ProfileTools._on_settings)
    a = app()
    d = cube()
    a.data_collection.append(d)
    v = a.new_data_viewer(ProfileViewer, data=d)
    process_events()
    tools = profile_tools(v)

    class Probe(BaseFitter1D):
        label = "probe"
        degree = IntOption(1, 10, 1)

        def fit(self, x, y, dy, constraints, **options):
            return options

        def predict(self, fit_result, x):
            return np.zeros_like(x)

    seen = []
    from glue.config import fit_plugin
    fit_plugin.add(Probe)
    type(tools).fit_function.set_choices(tools, list(fit_plugin))
    tools.fit_function = Probe
    settings = tools._get_fitter() if hasattr(tools, "_get_fitter") else None
    # Settings as the dialog applies them: set degree on the fitter it was given
    from glue_qt.viewers.profile import profile_tools as pt
    given = []
    pt.FitSettingsWidget = lambda fitter: given.append(fitter) or SimpleNamespace(exec_=lambda: setattr(fitter, "degree", 7))
    tools._on_settings()
    orig_fit = ProfileTools._fit
    ProfileTools._fit = lambda self, fitter, xlim=None: seen.append(fitter) or ({}, np.zeros(1), np.zeros(1))
    try:
        tools.rng_mode.state.x_min, tools.rng_mode.state.x_max = 0, 3
        tools._on_fit()
        tools.wait_for_fit()
        process_events()
    finally:
        ProfileTools._fit = orig_fit
    close_all(a)
    same = seen and given and seen[0] is given[0]
    deg = getattr(seen[0], "degree", None) if seen else None
    return ("OK" if same else "FAULT") + f": fit used the Settings fitter={bool(same)}, degree at fit={deg}; " \
        f"source has 'self.fit_function()' {src.count('self.fit_function()')}x"


@check
def fit_settings_checkbox():
    """FitSettingsWidget reads each widget's value(); a QCheckBox (BoolOption) has none (fork branch fitter-settings)."""
    from glue.core.fitters import BaseFitter1D
    from glue.core.simpleforms import BoolOption
    from glue_qt.core.fitters import FitSettingsWidget

    class Probe(BaseFitter1D):
        label = "probe"
        flag = BoolOption(default=False)

        def fit(self, *a, **k):
            return None

        def predict(self, *a, **k):
            return None

    fitter = Probe()
    w = FitSettingsWidget(fitter)
    try:
        w.update_fitter_from_settings()
    except AttributeError as e:
        return f"FAULT: {e}"
    return "OK: check box option read"


@check
def fit_artists():
    """_plot_fit keeps only the first artist a fitter's plot returns (fork branch fit-artists)."""
    from glue_qt.viewers.profile.profile_tools import ProfileTools

    class Layer:
        state = SimpleNamespace(alpha=1, linewidth=1, color="k")

    tools = SimpleNamespace(_fit_artists=[], _clear_fit=lambda: None, axes=None,
                            canvas=SimpleNamespace(draw_idle=lambda: None))
    ProfileTools._plot_fit(tools, SimpleNamespace(plot=lambda *a, **k: ["first", "second"]), {Layer: None},
                           None, None, {})
    return ("OK" if tools._fit_artists == ["first", "second"] else "FAULT") + f": kept {tools._fit_artists}"


@check
def fitter_settings_widget():
    """_on_settings ignores a fitter's own settings_widget (fork branch fitter-settings-widget)."""
    from glue_qt.viewers.profile import profile_tools as pt
    opened, default = [], pt.FitSettingsWidget
    fitter = SimpleNamespace(settings_widget=lambda f: SimpleNamespace(exec_=lambda: opened.append(f)))
    pt.FitSettingsWidget = lambda f: SimpleNamespace(exec_=lambda: None)
    try:
        pt.ProfileTools._on_settings(SimpleNamespace(fit_function=lambda: fitter, _get_fitter=lambda: fitter,
                                                     _fitters={}))
    finally:
        pt.FitSettingsWidget = default
    return ("OK" if opened == [fitter] else "FAULT") + f": own settings_widget opened={opened == [fitter]}"


@check
def fitter_summarize_args():
    """summarize gets neither the layer nor the viewer; the Fit tab has no hook for a fitter's own actions (source)."""
    from glue_qt.viewers.profile.profile_tools import ProfileTools
    src = inspect.getsource(ProfileTools._on_fit)
    line = next(l.strip() for l in src.splitlines() if "summarize(" in l)
    enable = inspect.getsource(ProfileTools.enable)
    hook = any(w in enable for w in ("fit_actions", "extra_actions", "fitter.actions"))
    return f"FAULT: {line!r}; hook for fitter actions in enable(): {hook}"


# ---------------------------------------------------------------- layer actions, icons, tables

@check
def layer_action_applies():
    """Layer actions take no applies (fork branch layer-action-applies)."""
    from glue_qt.config import LayerActionRegistry
    try:
        LayerActionRegistry()("probe", applies=bool)
    except TypeError as e:
        return f"FAULT: {e}"
    return "OK: applies accepted"


@check
def cmap_icon_cache():
    """QColormapCombo draws every icon per combo and per resize; R17 numbers (fork branch perf-q3)."""
    from echo.qt.connect import UserDataWrapper
    from glue_qt.utils import colors
    from matplotlib.colors import ListedColormap
    from glue.config import colormaps
    drawn, draw = [], colors.cmap2pixmap
    colors.cmap2pixmap = lambda *a, **k: drawn.append(a) or draw(*a, **k)
    combo_class = type("ProbeCombo", (colors.QColormapCombo,), {"__init__": QtWidgets.QComboBox.__init__})
    cmap = ListedColormap(["black", "white"])
    try:
        for _ in range(2):
            combo = combo_class()
            combo.addItem("probe", userData=UserDataWrapper(cmap))
            colors.QColormapCombo._update_icons(combo)
    finally:
        colors.cmap2pixmap = draw
    redrawn = sum(a[0] is cmap for a in drawn) > 1
    # timing with 102 colormaps registered, as glue-solar registers
    from matplotlib import colormaps as mpl_maps
    base = len(colormaps.members)
    for i in range(102 - base):
        colormaps.add(f"probe{i}", mpl_maps["viridis"])
    t = []
    for _ in range(5):
        t0 = time.perf_counter()
        c = colors.QColormapCombo()
        t.append(time.perf_counter() - t0)
    t1 = time.perf_counter()
    c.resize(c.width() + 10, c.height())
    c.resizeEvent(None)
    t_resize = time.perf_counter() - t1
    return ("FAULT" if redrawn else "OK") + f": second combo redraws={redrawn}; {len(colormaps.members)} colormaps: " \
        f"combo build median {np.median(t) * 1e3:.1f} ms, resize {t_resize * 1e3:.1f} ms"


@check
def layer_icon_loads():
    """R15: the data tree reloads tinted icons from disk per dataset added (fork branch perf-q4)."""
    from glue_qt.icons import helpers
    from glue_qt.core import data_collection_model as dcm
    a = app()
    close_all(a)
    calls, loads, rebuilds = [], [], []
    orig = helpers.layer_icon
    helpers.layer_icon = dcm.layer_icon = lambda layer: calls.append(1) or orig(layer)
    orig_path = helpers.icon_path
    helpers.icon_path = lambda name: loads.append(1) or orig_path(name)
    orig_inv = dcm.DataCollectionModel.invalidate
    dcm.DataCollectionModel.invalidate = lambda self, *a: rebuilds.append(1) or orig_inv(self, *a)
    try:
        datasets = [cube((2, 2, 2), label=f"d{i}") for i in range(30)]
        t0 = time.perf_counter()
        a.add_datasets(datasets)
        process_events()
        dt = time.perf_counter() - t0
    finally:
        helpers.layer_icon = dcm.layer_icon = orig
        helpers.icon_path = orig_path
        dcm.DataCollectionModel.invalidate = orig_inv
    close_all(a)
    return ("FAULT" if len(loads) > 60 else "OK") + f": 30 datasets: {len(calls)} layer_icon calls, " \
        f"{len(loads)} icon file loads, {len(rebuilds)} model rebuilds ({dt:.2f} s)"


@check
def table_time_filter():
    """A Table viewer's search refuses a datetime column (glue-solar get_filter_mask)."""
    from glue.viewers.common.state import LayerState
    from glue.viewers.table.state import TableViewerState
    from glue_qt.viewers.table.data_viewer import DataTableModel
    d = Data(t=np.zeros(1, "datetime64[ns]"), label="probe")
    state = TableViewerState(layers=[LayerState(layer=d)], filter="")
    try:
        DataTableModel.get_filter_mask(DataTableModel(SimpleNamespace(data=d, state=state, layers=[])))
    except TypeError as e:
        return f"FAULT: {e}"
    return "OK"


@check
def table_new_rows():
    """A Table viewer keeps the row count its dataset had when shown (glue-solar SlopeTool resets it)."""
    from glue_qt.viewers.table.data_viewer import TableViewer
    a = app()
    d = Data(label="rows", a=np.arange(3.0))
    a.data_collection.append(d)
    v = a.new_data_viewer(TableViewer, data=d)
    process_events()
    more = Data(label="rows", a=np.arange(5.0))
    d.update_values_from_data(more)
    process_events()
    rows = v.model.rowCount()
    try:
        v.model.sort(0, Qt.AscendingOrder)
        process_events()
        v.model.data(v.model.index(4, 0), Qt.DisplayRole)
        sorted_rows = v.model.rowCount()
        err = None
    except Exception as e:
        sorted_rows, err = None, repr(e)
    close_all(a)
    return ("FAULT" if rows != 5 or err else "OK") + f": rows shown {rows} of 5; after sort {sorted_rows} err={err}"


# ---------------------------------------------------------------- sliders and playback

@check
def play_timer_outlives_viewer():
    """Slider playback keeps stepping a closed viewer (glue-solar close_event)."""
    from glue_qt.viewers.common.data_slice_widget import SliceWidget
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = cube((6, 5, 5))
    a.data_collection.append(d)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    slider = v.options_widget().findChildren(SliceWidget)[0]
    slider._adjust_play("forw")
    ref = weakref.ref(v)
    v.close(warn=False)
    process_events()
    active = slider._play_timer.isActive()
    before = slider.state.slice_center
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(1200, loop.quit)
    loop.exec_()
    after = slider.state.slice_center
    slider._adjust_play("stop")
    close_all(a)
    gc.collect()
    return ("FAULT" if active else "OK") + f": timer active after close={active}, slider stepped {before}->{after}, " \
        f"viewer alive={ref() is not None}"


@check
def play_timer_survives_rebuild():
    """Slider playback survives a slider rebuild (x_att change), on an orphaned widget."""
    from glue_qt.viewers.common.data_slice_widget import SliceWidget
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = cube((6, 5, 5))
    a.data_collection.append(d)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    old = v.options_widget().findChildren(SliceWidget)[0]
    old._adjust_play("forw")
    v.state.x_att = d.pixel_component_ids[0]  # rebuilds the sliders
    process_events()
    new = v.options_widget().slice_helper._sliders
    active = old._play_timer.isActive()
    old._adjust_play("stop")
    close_all(a)
    return ("FAULT" if active else "OK") + f": old slider's timer active after rebuild={active}; old in new={old in new}"


@check
def sync_state_rewrites_aggregate():
    """A slider move rewrites every slice, turning a Collapse AggregateSlice into an int (wp0-qt-aggregate-slice)."""
    from glue.viewers.image.state import AggregateSlice
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = cube((3, 4, 5, 6))
    a.data_collection.append(d)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    slices = list(v.state.slices)
    slices[0] = AggregateSlice(slice(0, 3), 1, np.mean)
    v.state.slices = tuple(slices)
    process_events()
    sliders = v.options_widget().slice_helper._sliders
    sliders[1].state.slice_center = 2
    process_events()
    kind = type(v.state.slices[0]).__name__
    close_all(a)
    return ("FAULT" if kind != "AggregateSlice" else "OK") + f": slices[0] is {kind} after moving slider 1"


@check
def collapse_drops_last_sample():
    """Profile Collapse makes slice(imin, imax) with imax the range's last index, so that sample is dropped."""
    from glue_qt.viewers.image import ImageViewer
    from glue_qt.viewers.profile import ProfileViewer
    a = app()
    d = cube((8, 5, 5))
    a.data_collection.append(d)
    iv = a.new_data_viewer(ImageViewer, data=d)
    pv = a.new_data_viewer(ProfileViewer, data=d)
    process_events()
    pv.state.x_att = d.pixel_component_ids[0]
    tools = profile_tools(pv)
    tools.rng_mode.state.x_min, tools.rng_mode.state.x_max = 2, 5
    tools._on_collapse()
    process_events()
    agg = iv.state.slices[0]
    close_all(a)
    return ("FAULT" if agg.slice == slice(2, 5) else "OK") + f": range 2..5 collapsed as {agg.slice}"


@check
def navigate_display_unit():
    """Navigate/Collapse find the nearest index comparing display-unit x with native values (draft #70 fixes)."""
    from astropy.wcs import WCS
    from glue_qt.viewers.profile import ProfileViewer
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = ["WAVE", "SLIT", "STEP"]
    wcs.wcs.cunit = ["Angstrom", "arcsec", "arcsec"]
    wcs.wcs.crval = [1400.0, 0, 0]
    wcs.wcs.cdelt = [1.0, 1, 1]
    wcs.wcs.crpix = [1, 1, 1]
    d = Data(label="spec", x=np.zeros((5, 5, 10)), coords=wcs)
    a = app()
    a.data_collection.append(d)
    pv = a.new_data_viewer(ProfileViewer, data=d)
    process_events()
    pv.state.x_att = d.world_component_ids[2]
    try:
        pv.state.x_display_unit = "nm"
    except Exception as e:
        close_all(a)
        return f"SKIP: no x_display_unit ({e})"
    tools = profile_tools(pv)
    axis, idx = tools._get_axis_and_pixel_slice(d, 140.5)  # 1405 Angstrom = 140.5 nm -> index 5
    close_all(a)
    return ("FAULT" if idx != 5 else "OK") + f": 140.5 nm gave axis {axis} index {idx} (expected 5)"


# ---------------------------------------------------------------- edit subset, focus, dashboard

@check
def edit_subset_from_selection():
    """Selecting a dataset in the data collection empties the edit subset (#288)."""
    a = app()
    d = cube()
    a.data_collection.append(d)
    g = a.data_collection.new_subset_group("pt")
    mode = a.session.edit_subset_mode
    mode.edit_subset = [g]
    tree = a._layer_widget
    tree.ui.layerTree.set_selected_layers([d])
    process_events()
    edit = list(mode.edit_subset)
    close_all(a)
    return ("FAULT" if edit == [] else "OK") + f": edit subset after selecting data: {edit}"


@check
def default_mode_click_empties():
    """With no tool on, the default mouse mode's click off any ROI empties the edit subset (#244, #300)."""
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = cube((3, 5, 5))
    a.data_collection.append(d)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    g = a.data_collection.new_subset_group("pt")
    mode = a.session.edit_subset_mode
    mode.edit_subset = [g]
    v.toolbar.active_tool = None
    ev = SimpleNamespace(xdata=1.0, ydata=1.0, x=10, y=10, button=1, inaxes=v.axes, dblclick=False)
    v.toolbar._default_mouse_mode.press(ev)
    edit = list(mode.edit_subset)
    close_all(a)
    return ("FAULT" if edit == [] else "OK") + f": edit subset after click: {edit}"


@check
def focus_turns_tool_off():
    """Activating another window turns the previous viewer's mouse mode off (#244 set_focus)."""
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = cube((3, 5, 5))
    a.data_collection.append(d)
    v1 = a.new_data_viewer(ImageViewer, data=d)
    v2 = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    a.current_tab.setActiveSubWindow(v1.parent())
    process_events()
    v1.toolbar.active_tool = "image:point_selection"
    a.current_tab.setActiveSubWindow(v2.parent())
    process_events()
    tool = v1.toolbar.active_tool
    close_all(a)
    return ("FAULT" if tool is None else "OK") + f": v1 tool after focus change: {tool}"


@check
def dashboard_keeps_data():
    """A dataset an Image viewer showed stays alive after removal and the viewer's close (#312 review)."""
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = cube((3, 5, 5), label="gone")
    a.data_collection.append(d)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    ref = weakref.ref(d)
    a.data_collection.remove(d)
    process_events()
    v.close(warn=False)
    process_events()
    del v, d
    gc.collect()
    alive = ref() is not None
    who = []
    if alive:
        for r in gc.get_referrers(ref()):
            if isinstance(r, dict):
                for o in gc.get_referrers(r):
                    if not isinstance(o, dict):
                        who.append(type(o).__name__)
            else:
                who.append(type(r).__name__)
    # the next viewer: does the stale options widget still hold it?
    return ("FAULT" if alive else "OK") + f": data alive={alive}; referrers {sorted(set(who))[:8]}"


# ---------------------------------------------------------------- keys

@check
def keys_exact_class():
    """Keyboard shortcuts are looked up by the viewer's exact class, so a subclass gets none."""
    from glue_qt.config import keyboard_shortcut
    from glue_qt.viewers.image import ImageViewer

    class Sub(ImageViewer):
        pass

    a = app()
    d = cube((3, 5, 5))
    a.data_collection.append(d)
    v = a.new_data_viewer(Sub, data=d)
    process_events()
    a.current_tab.setActiveSubWindow(v.parent())
    hit = []
    keyboard_shortcut.add([ImageViewer], Qt.Key_F7, lambda session: hit.append(1))
    ev = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_F7, Qt.NoModifier)
    a.keyPressEvent(ev)
    close_all(a)
    return ("FAULT" if not hit else "OK") + f": ImageViewer key reached subclass viewer: {bool(hit)}"


@check
def tab_never_cycles():
    """Tab is taken by Qt's focus chain before the application's key handler, so Tab never cycles windows."""
    from qtpy.QtTest import QTest
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = cube((3, 5, 5))
    a.data_collection.append(d)
    v1 = a.new_data_viewer(ImageViewer, data=d)
    v2 = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    a.current_tab.setActiveSubWindow(v1.parent())
    v1.figure.canvas.setFocus()
    process_events()
    calls = []
    orig = a.current_tab.activateNextSubWindow
    a.current_tab.activateNextSubWindow = lambda: calls.append(1) or orig()
    QTest.keyClick(v1.figure.canvas, Qt.Key_Tab)
    process_events()
    QTest.keyClick(a, Qt.Key_Tab)
    process_events()
    close_all(a)
    return ("FAULT" if not calls else "OK") + f": activateNextSubWindow called {len(calls)}x for 2 Tab presses"


@check
def table_keys_on_model():
    """glue-qt registers the Table viewer's keys on DataTableModel, which is never the active window's class."""
    from glue_qt.config import keyboard_shortcut
    from glue_qt.viewers.table.data_viewer import DataTableModel, TableViewer
    import glue_qt.app.keyboard_shortcuts  # noqa: F401
    m = keyboard_shortcut.members
    return ("FAULT" if DataTableModel in m and TableViewer not in m else "OK") + \
        f": DataTableModel registered={DataTableModel in m}, TableViewer registered={TableViewer in m}"


@check
def canvas_mpl_keys():
    """MplCanvas keeps matplotlib's key handler (f, s, g, l, k, L, p, o); g over WCSAxes raises."""
    from astropy.visualization.wcsaxes import WCSAxes
    from astropy.wcs import WCS
    from matplotlib.backend_bases import KeyEvent, key_press_handler
    from glue_qt.viewers.matplotlib.widget import MplCanvas
    c = MplCanvas()
    connected = any(key_press_handler is getattr(f, "__func__", f) or getattr(f, "func", None) is key_press_handler
                    for f in c.callbacks.callbacks.get("key_press_event", {}).values()) \
        or getattr(c.manager, "key_press_handler_id", None) is not None
    ax = WCSAxes(c.fig, [0.1, 0.1, 0.8, 0.8], wcs=WCS(naxis=2))
    c.fig.add_axes(ax)
    errors = {}
    for key in ("g", "G"):
        ev = KeyEvent("key_press_event", c, key, 10, 10)
        ev.inaxes = ax
        try:
            key_press_handler(ev)
        except Exception as e:
            errors[key] = type(e).__name__
    return ("FAULT" if connected else "OK") + f": matplotlib key handler connected={connected}; over WCSAxes {errors}"


# ---------------------------------------------------------------- tooltips, status, icon

@check
def profile_tool_tooltip():
    from glue_qt.viewers.image.profile_viewer_tool import ProfileViewerTool
    return ("FAULT" if ProfileViewerTool.tool_tip is None else "OK") + f": tool_tip={ProfileViewerTool.tool_tip!r}"


@check
def menu_button_tooltip():
    """A dropdown tool's QToolButton has no tooltip and its menu hides entry tooltips (#222)."""
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = cube((3, 5, 5))
    a.data_collection.append(d)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    tb = v.toolbar
    action = tb.actions["save"]
    button = tb.widgetForAction(action)
    tip, visible = button.toolTip(), button.menu().toolTipsVisible()
    close_all(a)
    return ("FAULT" if not tip or not visible else "OK") + f": save button tooltip={tip!r}, menu tooltips visible={visible}"


@check
def app_icon_hook():
    """GlueApplication sets glue's app_icon with no hook or parameter for another (glue-solar wraps __init__)."""
    from glue_qt.app.application import GlueApplication
    src = inspect.getsource(GlueApplication.__init__)
    sig = inspect.signature(GlueApplication.__init__)
    return f"FAULT: get_icon('app_icon') in __init__={'app_icon' in src}; parameters={list(sig.parameters)}"


@check
def cursor_status():
    from glue_qt.viewers.image import ImageViewer
    return ("OK" if hasattr(ImageViewer, "cursor_status") else "FAULT") + \
        f": ImageViewer.cursor_status exists={hasattr(ImageViewer, 'cursor_status')} (draft glue-qt#74)"


# ---------------------------------------------------------------- large data, -x script

@check
def large_data_cancel():
    """Cancelling 'Add large data set?' on a new viewer: what is left behind (wp0-qt-large-data-cancel)."""
    from glue_qt.core import dialogs
    from glue_qt.viewers.common import data_viewer as dv
    from glue_qt.viewers.image import ImageViewer
    from glue_qt.viewers.profile import ProfileViewer
    a = app()
    close_all(a)
    d = cube((4, 5, 5), label="big")
    a.data_collection.append(d)
    old = ProfileViewer.large_data_size
    ProfileViewer.large_data_size = 10
    orig = dv.warn
    dv.warn = lambda *args, **kw: False  # Cancel
    problems = []
    try:
        v = a.new_data_viewer(ProfileViewer, data=d)
        process_events()
        problems.append(f"new_data_viewer returned {v!r}")
        problems.append(f"viewers left in tab: {len(a.current_tab.subWindowList())}")
        problems.append(f"_viewer_in_focus: {type(a._viewer_in_focus).__name__}")
        # later viewers
        try:
            v2 = a.new_data_viewer(ImageViewer, data=d)
            process_events()
            a.current_tab.setActiveSubWindow(v2.parent())
            process_events()
            problems.append(f"later Image viewer ok, focus={type(a._viewer_in_focus).__name__}")
            v2.close(warn=False)
        except Exception as e:
            problems.append(f"later viewer failed: {e!r}")
    finally:
        dv.warn = orig
        ProfileViewer.large_data_size = old
    close_all(a)
    bad = any("failed" in p for p in problems)
    return ("FAULT" if bad else "OK (no break seen)") + ": " + "; ".join(problems)


@check
def x_script():
    """glue -x script.py: the script runs under exec() in a function scope, so its functions see no module names."""
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "x_script_probe.py")
    code = ("import sys\n" + (f"sys.path.insert(0, {args.src!r})\n" if args.src else "") +
            f"from glue_qt.main import main\nmain(['glue', '-x', {script!r}])\n")
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120,
                       env=dict(os.environ))
    out = (r.stdout + r.stderr).strip().splitlines()
    tail = " | ".join(out[-3:])
    ok = r.returncode == 0 and "X-SCRIPT-RAN" in r.stdout
    return ("OK" if ok else "FAULT") + f": rc={r.returncode}; {tail[:300]}"


@check
def terminal_imports():
    """R22: importing glue_qt.app.application imports IPython/qtconsole (fork branch perf-q5)."""
    code = ("import sys\n" + (f"sys.path.insert(0, {args.src!r})\n" if args.src else "") +
            "import time; t=time.perf_counter(); import glue_qt.app.application\n"
            "print('IPython' in sys.modules, 'qtconsole' in sys.modules, 'QtQuick' in str(sorted(m for m in sys.modules if 'QtQuick' in m)), round(time.perf_counter()-t,2))")
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120)
    out = r.stdout.strip()
    return ("FAULT" if out.startswith("True") else "OK") + f": (IPython, qtconsole, QtQuick, s) = {out} {r.stderr.strip()[-200:]}"


@check
def startup_sources():
    """R29/R30 source facts: splash after import glue; QtQuick import; QFont('Courier')."""
    import glue_qt.main as m
    import glue_qt.utils.app as ua
    from glue_qt.viewers.profile import profile_tools as pt
    msrc = inspect.getsource(m)
    splash_line = next(i for i, l in enumerate(msrc.splitlines()) if "get_splash()" in l and "splash =" in l)
    import_line = next(i for i, l in enumerate(msrc.splitlines()) if l.strip() == "import glue")
    quick = "import" in inspect.getsource(ua).splitlines()[2] and "QtQuick" in inspect.getsource(ua).splitlines()[2]
    courier = "QFont(\"Courier\")" in inspect.getsource(pt) or "QFont('Courier')" in inspect.getsource(pt)
    return f"FAULT: splash created at main.py line {splash_line + 1}, 'import glue' at line {import_line + 1}; " \
        f"QtQuick imported at module level={quick}; QFont('Courier')={courier}"


# ---------------------------------------------------------------- perf: worker, hidden canvases, slider sync

@check
def worker_latency():
    """R3: ComputeWorker round trip for a trivial job (polling at 25 Hz) (fork branch perf-q1)."""
    from glue_qt.viewers.matplotlib.compute_worker import ComputeWorker
    done = []
    w = ComputeWorker(lambda reset=False: None)
    w.compute_end.connect(lambda: done.append(time.perf_counter()))
    w.start()
    time.sleep(0.2)
    times = []
    for _ in range(10):
        done.clear()
        t0 = time.perf_counter()
        w.work_queue.put(False)
        loop = QtCore.QEventLoop()
        timer = QtCore.QTimer()
        timer.setInterval(5)
        timer.timeout.connect(lambda: loop.quit() if done else None)
        timer.start()
        QtCore.QTimer.singleShot(2000, loop.quit)
        loop.exec_()
        times.append((done[0] - t0) * 1e3 if done else float("nan"))
    w.work_queue.put("stop")
    w.wait()
    med = float(np.nanmedian(times))
    return ("FAULT" if med > 25 else "OK") + f": median round trip {med:.1f} ms (min {np.nanmin(times):.1f})"


@check
def profile_thread_by_parent_size():
    """R3(c): a one-pixel SliceSubsetState profile is threaded because Subset.size is the parent's (perf-q2)."""
    from glue_qt.viewers.profile.layer_artist import QThreadedProfileLayerArtist
    src = inspect.getsource(QThreadedProfileLayerArtist._calculate_profile)
    by_parent = "self.state.layer.size > 1e7" in src
    return ("FAULT" if by_parent else "OK") + f": threads by layer.size={by_parent}"


@check
def hidden_canvas_draws():
    """R9: a canvas in a hidden tab still does full draws on draw_idle."""
    from glue_qt.viewers.matplotlib.widget import MplCanvas
    tabs = QtWidgets.QTabWidget()
    shown, hidden = MplCanvas(), MplCanvas()
    tabs.addTab(shown, "shown")
    tabs.addTab(hidden, "hidden")
    tabs.resize(400, 300)
    tabs.show()
    process_events()
    hidden._draw_count = shown._draw_count = 0
    for _ in range(5):
        hidden.draw_idle()
        shown.draw_idle()
        process_events()
    return ("FAULT" if hidden._draw_count else "OK") + f": hidden canvas draws={hidden._draw_count}, shown={shown._draw_count}, hidden visible={hidden.isVisible()}"


@check
def slider_sync_per_position():
    """R16: every slider position applies to viewer_state.slices synchronously, through the full slice tick."""
    from glue_qt.viewers.image import ImageViewer
    a = app()
    d = Data(label="big", x=np.zeros((60, 300, 300), dtype=np.float32))
    a.data_collection.append(d)
    v = a.new_data_viewer(ImageViewer, data=d)
    process_events()
    slider = v.options_widget().slice_helper._sliders[0]
    seen = []
    v.state.add_callback("slices", lambda *a: seen.append(time.perf_counter()))
    t0 = time.perf_counter()
    for i in range(1, 41):
        slider.value_slice_center.setValue(i)  # as tracking delivers each dragged position
    dt = time.perf_counter() - t0
    tracking = slider.value_slice_center.hasTracking()
    close_all(a)
    return ("FAULT" if len(seen) >= 40 else "OK") + f": {len(seen)} slice changes for 40 positions in {dt * 1e3:.0f} ms " \
        f"({dt / 40 * 1e3:.1f} ms each, synchronous), tracking={tracking}"


# ---------------------------------------------------------------- run

def _watchdog():
    for w in qapp.topLevelWidgets():
        if isinstance(w, QtWidgets.QDialog) and w.isVisible():
            print(f"  (watchdog rejected dialog {w.windowTitle()!r}: {getattr(w, 'text', lambda: '')()!r})")
            w.reject()


_wd = QtCore.QTimer()
_wd.setInterval(1500)
_wd.timeout.connect(_watchdog)
_wd.start()

import signal  # noqa: E402


def _alarm(*_):
    raise TimeoutError("check took over 120 s")


signal.signal(signal.SIGALRM, _alarm)

names = args.checks or list(CHECKS)
for name in names:
    signal.alarm(120)
    try:
        print(f"[{name}] {CHECKS[name]()}")
    except Exception:
        print(f"[{name}] ERROR {traceback.format_exc().strip().splitlines()[-1]}")
        traceback.print_exc()
    sys.stdout.flush()
if _app is not None:
    _app.close()
    process_events()
