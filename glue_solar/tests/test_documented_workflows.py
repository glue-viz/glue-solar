"""
Checks that the recipes in the user guides and the examples in the developer guide do what they say, on the irispy
fixtures.
"""

import inspect
import re

import numpy as np
import pytest
from glue.config import viewer_tool
from glue.core.subset import RangeSubsetState
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.app.application import GlueApplication
from glue_qt.config import layer_action as glue_layer_action
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from qtpy.QtCore import Qt

import glue_solar
from glue_solar import glue_patches
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import sji_to_raster
from glue_solar.sources.loaders.iris import QtIRISImporter, image_data, keep_hpc_linked, link_hpc, raster_data
from glue_solar.tests.helpers import (
    linked_data,
    load_selected,
    raster_point_on_sji,
    refused,
    run_action,
    scanned,
    select_point,
)

SNS = "iris_l2_20210905_001833_3620258102_{}.fits"


def arcsec(text):
    """The two angles of a WCSAxes readout such as '12" -34" (world)', in arcsec."""
    return [float(value.replace("−", "-")) for value in re.findall(r"(−?-?[\d.]+)\"", text)]


def test_scripting_recipe(qtbot, irispy_test_files):
    # docs/user_guide/scripting-iris-data.rst
    glue_solar.setup()
    rasters = raster_data([find_irispy_test_file(irispy_test_files, SNS.format("raster_t000_r00000"))], ["Si IV 1403"])
    sji = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    app = GlueApplication()
    qtbot.addWidget(app)
    data_collection = app.data_collection
    data_collection.extend([*rasters, sji])
    raster = rasters[0]
    step, slit, pixel = 90, 20, 14
    _, latitude, _ = raster.coords.pixel_to_world_values(pixel, slit, step)

    # the coordinates are what the readout shows at a Pixel point on the raster map
    viewer = app.new_data_viewer(ImageViewer, data=raster)
    viewer.state.x_att, viewer.state.y_att = raster.pixel_component_ids[0], raster.pixel_component_ids[1]
    select_point(viewer, step, slit)
    point = data_collection.subset_groups[-1].subset_state
    assert isinstance(point, PixelSubsetState)
    assert [s.start for s in point.slices[:2]] == [step, slit]
    viewer.figure.canvas.draw()
    readout = viewer.axes.format_coord(step, slit)
    # a sit-and-stare raster, whose steps are exposures: the latitude along the slit, and the exposure's time
    assert arcsec(readout) == [round(latitude, 2)]
    assert f" · {np.datetime_as_string(raster['Time'][step, 0, 0], unit='ms')} UTC" in readout

    # on this sit-and-stare raster the exposure nearest the frame's time, and the slit row level with the pixel: back
    # in the frame, within half a pixel of it (the fixture's raster and slit-jaw pixels are both 1.66")
    frame, x, y = 30, 18.5, 20.0
    index = sji_to_raster(sji, frame, x, y, raster)
    assert index[0] == np.argmin(np.abs(raster["Time"][:, 0, 0] - sji["Time"][frame, 0, 0]))
    assert abs(raster_point_on_sji(raster, sji, *index, frame)[1] - y) <= 0.5

    # link_hpc links the IRIS data and their observation's AIA cutout, and another's only where others names it
    aia, other = (image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000"))) for _ in range(2))
    aia.meta["INSTRUME"] = other.meta["INSTRUME"] = "AIA_3"  # read as an aligned cutout is
    other.meta["STARTOBS"] = "2021-09-06T00:18:33.640"
    data_collection.extend([aia, other])
    data_collection.add_link(link_hpc(data_collection))
    assert linked_data(data_collection) == {raster, sji, aia}
    data_collection.add_link(link_hpc(data_collection, others=[other]))
    assert linked_data(data_collection) == {raster, sji, aia, other}


def test_browser_stacks_scans_into_4d_data_with_per_pixel_time(qtbot, irispy_test_files):
    # docs/user_guide/loading-data.rst: "Stack sequential raster scans"
    scans = [path for path in irispy_test_files if "3860258481_raster_t000_r" in path.name]
    dialog = QtIRISImporter(scans[0].parent)
    qtbot.addWidget(dialog)
    scanned(qtbot, dialog)
    tree = dialog.obs_tree
    observation = next(
        item for item in map(tree.topLevelItem, range(tree.topLevelItemCount())) if item.text(1) == "3860258481"
    )
    entries = [observation.child(i) for i in range(observation.childCount())]
    next(entry for entry in entries if entry.text(0).startswith("C II 1336")).setCheckState(0, Qt.Checked)
    load_selected(qtbot, dialog)
    assert [data.ndim for data in dialog.datasets] == [3] * len(scans)

    dialog.stack.setChecked(True)
    load_selected(qtbot, dialog)
    [stack] = dialog.datasets
    assert stack.ndim == 4
    # docs/user_guide/iris-quicklook.rst: the terminal's mean over scans is the Profile's
    # Mean of an X range over them
    cid = stack.main_components[0]
    np.testing.assert_array_equal(
        stack.compute_statistic("mean", cid, axis=(0, 1, 2), view=(slice(1, 3),)),
        stack.compute_statistic(
            "mean", cid, axis=(0, 1, 2), subset_state=RangeSubsetState(0.5, 2.5, stack.world_component_ids[0])
        ),
    )
    assert stack.world_component_ids[0].label == "Scan"
    times = stack["Time"]
    assert times.shape == stack.shape
    assert times.dtype.kind == "M"
    # one time per scan and raster step, the same at every slit position and wavelength
    np.testing.assert_array_equal(times, np.broadcast_to(times[:, :, :1, :1], stack.shape))
    assert len(np.unique(times[:, :, 0, 0])) == len(scans) * stack.shape[1]


@pytest.fixture
def registries(monkeypatch):
    """
    glue-solar set up, and what an example of the developer guide registers gone once its test ends: glue's data
    actions and viewer tools, and the Profile viewer's buttons, are copies until then.
    """
    glue_solar.setup()
    monkeypatch.setattr(glue_layer_action, "_members", list(glue_layer_action.members))
    monkeypatch.setattr(glue_patches, "_APPLIES", dict(glue_patches._APPLIES))  # each data action's guard
    monkeypatch.setattr(viewer_tool, "_members", dict(viewer_tool.members))
    monkeypatch.setattr(ProfileViewer, "tools", list(ProfileViewer.tools))


def test_adding_a_data_action(qtbot, registries, sns):
    # docs/dev_guide/adding-features.rst, "A data action": its example, then the entry in glue's window
    import numpy as np
    from glue_qt.utils.decorators import messagebox_on_error

    from glue_solar import describe
    from glue_solar.glue_patches import layer_action
    from glue_solar.sources import analysis

    def _check(data):
        """Raise why ``data`` is not an IRIS slit-jaw image."""
        if describe.role(data) != "sji":
            raise ValueError(f"{data.label} is not an IRIS slit-jaw image.")

    @layer_action(
        "IRIS: cadence",
        single=True,
        data=True,
        check=_check,
        tooltip="Show the median time between the frames of this slit-jaw image",
    )
    @messagebox_on_error("Could not show the cadence")
    def cadence_iris(data, data_collection):
        """Say the median time between the frames of ``data`` in glue's status bar."""
        _check(data)
        seconds = describe.cadence(data["Time"][:, 0, 0]) / np.timedelta64(1, "s")
        analysis.status_bar(data_collection).showMessage(f"{data.label}: {seconds:.2f} s between frames")

    app = GlueApplication()  # after the example: glue-qt makes the entries as its window opens
    qtbot.addWidget(app)
    sji, raster = sns
    app.data_collection.extend([sji, raster])
    tree = app._layer_widget
    action = tree._actions["IRIS: cadence"]
    assert action.toolTip() == "Show the median time between the frames of this slit-jaw image"
    tree.ui.layerTree.set_selected_layers([raster])
    with pytest.raises(ValueError, match=re.escape(f"{raster.label} is not an IRIS slit-jaw image.")):
        refused(action)  # hidden for a raster, and its guard says why
    tree.ui.layerTree.set_selected_layers([sji])
    assert action.isVisible()
    action.trigger()
    seconds = np.median(np.diff(sji["Time"][:, 0, 0])) / np.timedelta64(1, "s")
    assert seconds > 0
    assert app.statusBar().currentMessage() == f"{sji.label}: {seconds:.2f} s between frames"


def test_adding_a_viewer_tool(qtbot, registries, sns):
    # docs/dev_guide/adding-features.rst, "A viewer tool": its example, then the button in a Profile viewer
    from glue.config import viewer_tool
    from glue.viewers.common.tool import Tool

    @viewer_tool
    class LogScaleTool(Tool):
        """The 'Log scale' button of a Profile viewer."""

        icon = "glue_spectrum"
        tool_id = "solar:log_scale"
        action_text = "Log scale"
        tool_tip = "Plot the profiles on a logarithmic or a linear y axis"

        def activate(self):
            self.viewer.state.y_log = not self.viewer.state.y_log

    if LogScaleTool.tool_id not in ProfileViewer.tools:
        ProfileViewer.tools.append(LogScaleTool.tool_id)

    app = GlueApplication()
    qtbot.addWidget(app)
    _, raster = sns
    app.data_collection.append(raster)
    viewer = app.new_data_viewer(ProfileViewer, data=raster)
    button = viewer.toolbar.actions["solar:log_scale"]
    assert viewer.toolbar.widgetForAction(button) is not None  # a button of the toolbar
    assert button.isVisible()
    assert (button.text(), button.toolTip()) == ("Log scale", "Plot the profiles on a logarithmic or a linear y axis")
    assert not button.icon().isNull()
    assert viewer.axes.get_yscale() == "linear"
    button.trigger()
    assert viewer.axes.get_yscale() == "log"
    button.trigger()
    assert viewer.axes.get_yscale() == "linear"


def test_adding_an_analysis(qtbot, registries, sns):
    # docs/dev_guide/adding-features.rst, "An analysis": its example, then the entry's dataset
    import numpy as np
    from glue.core.component import Component
    from glue_qt.utils.decorators import messagebox_on_error

    from glue_solar.glue_patches import layer_action
    from glue_solar.sources import analysis

    def peak(data):
        """The largest value of each spectrum of ``data``, an IRIS raster window or a stack of its scans."""
        analysis.check(data)
        cid = data.main_components[0]
        values = np.fmax.reduce(data[cid], axis=-1)  # NaN where every sample is missing
        maps = analysis.dataset(data, f"{data.label} peak")
        maps.add_component(Component(values, units=data.get_component(cid).units), "peak")
        return maps

    @layer_action(
        "IRIS: peak map",
        single=True,
        data=True,
        check=analysis.check,
        tooltip="Add the largest value of each spectrum of this raster window or stack",
    )
    @messagebox_on_error("Could not compute the peak map")
    def peak_iris(data, data_collection):
        """Add the `peak` of ``data``, computed in the background."""
        text, title = f"Computing the peak map of {data.label}…", "Could not compute the peak map"
        analysis.start(data_collection, text, title, peak, data, view=True)

    app = GlueApplication()
    qtbot.addWidget(app)
    sji, raster = sns
    collection, tree = app.data_collection, app._layer_widget
    collection.extend([sji, raster])
    keep_hpc_linked(collection)
    action = tree._actions["IRIS: peak map"]
    tree.ui.layerTree.set_selected_layers([sji])
    assert not action.isVisible()
    tree.ui.layerTree.set_selected_layers([raster])
    assert action.isVisible()
    # on glue-qt's worker, glue's status bar saying so meanwhile
    [maps] = run_action(app, qtbot, raster, "IRIS: peak map", f"Computing the peak map of {raster.label}…")
    cid = raster.main_components[0]
    assert maps.label == f"{raster.label} peak"
    assert maps.shape == raster.shape[:2]
    assert maps.get_component("peak").units == raster.get_component(cid).units
    values = np.nan_to_num(raster[cid], nan=-np.inf).max(axis=-1)  # -inf where every sample is missing
    assert 0 < np.isinf(values).sum() < values.size
    np.testing.assert_array_equal(maps["peak"], np.where(np.isinf(values), np.nan, values))
    # its helioprojective coordinates linked with the others', and its pixels with the raster's, in an Image viewer
    assert link_hpc(collection) == []
    assert {raster, sji, maps} <= linked_data(collection)
    linked = {cid for link in collection.links for cid in (link.get_to_id(), *link.get_from_ids())}
    assert {*maps.world_component_ids, *maps.pixel_component_ids, *raster.pixel_component_ids[:2]} <= linked
    [[viewer]] = app.viewers
    assert isinstance(viewer, ImageViewer)
    assert viewer.state.reference_data is maps


def test_the_developer_guides_examples_are_the_lines_tested(request):
    # docs/dev_guide/adding-features.rst: each section's example is, line for line, what starts its test
    page = request.config.rootpath / "docs" / "dev_guide" / "adding-features.rst"
    if not page.exists():
        pytest.skip("the package is installed without its docs")
    sections = re.split(r"\n(?=[^\n]+\n-+\n)", page.read_text(encoding="utf-8"))
    tests = {
        "A data action": test_adding_a_data_action,
        "A viewer tool": test_adding_a_viewer_tool,
        "An analysis": test_adding_an_analysis,
    }
    for title, test in tests.items():
        [section] = [section for section in sections if section.startswith(f"{title}\n")]
        # the section's literal blocks, and the test after its ``def`` and comment, without the blank lines
        example = [line[4:] for line in section.splitlines() if line.startswith("    ")]
        tested = [line[4:] for line in inspect.getsource(test).splitlines()[2:] if line.strip()]
        assert example
        assert tested[: len(example)] == example
