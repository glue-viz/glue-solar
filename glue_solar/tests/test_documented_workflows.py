"""
Checks that the recipes in the user guides do what they say, on the irispy fixtures.
"""

import re

import numpy as np
from glue.core.subset import RangeSubsetState
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.app.application import GlueApplication
from glue_qt.viewers.image import ImageViewer
from qtpy.QtCore import Qt

import glue_solar
from glue_solar.conftest import find_irispy_test_file
from glue_solar.quicklook import sji_to_raster
from glue_solar.sources.loaders.iris import QtIRISImporter, image_data, link_hpc, raster_data
from glue_solar.tests.helpers import linked_data, load_selected, raster_point_on_sji, scanned, select_point

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

    # link_hpc links the IRIS data, and an AIA cutout only where others names it
    aia = image_data(find_irispy_test_file(irispy_test_files, SNS.format("SJI_1400_t000")))
    aia.meta["INSTRUME"] = "AIA_3"  # read as an aligned cutout is
    data_collection.append(aia)
    data_collection.add_link(link_hpc(data_collection))
    assert linked_data(data_collection) == {raster, sji}
    data_collection.add_link(link_hpc(data_collection, others=[aia]))
    assert linked_data(data_collection) == {raster, sji, aia}


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
