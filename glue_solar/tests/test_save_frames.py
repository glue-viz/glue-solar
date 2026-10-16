"""'IRIS: save frames or movie…' on an Image viewer: each frame the image at its index, and how a save ends."""

import numpy as np
import pytest
from glue.viewers.image.frb_artist import FRBArtist
from glue_qt.viewers.image import ImageViewer
from matplotlib import animation, rcParams
from matplotlib.image import imread
from PIL import Image
from qtpy import QtWidgets
from qtpy.QtCore import QTimer

from glue_solar.conftest import find_irispy_test_file
from glue_solar.sources.loaders.iris import image_data
from glue_solar.tests.helpers import resized
from glue_solar.tests.test_lazy import SJI
from glue_solar.tests.test_quicklook import refusals, saved, type_in_dialog


@pytest.fixture
def viewer(app, qtbot, monkeypatch, tmp_path, irispy_test_files):
    """An Image viewer of 3620258102's SJI 1400 at frame 20, shown, saving into ``tmp_path``."""
    sji = image_data(find_irispy_test_file(irispy_test_files, SJI))
    app.data_collection.append(sji)
    viewer = app.new_data_viewer(ImageViewer, data=sji)
    viewer.state.slices = (20, 0, 0)
    app.resize(1200, 800)
    app.show()  # for resizes to reach the canvas
    resized(qtbot, [viewer])
    monkeypatch.setitem(rcParams, "savefig.directory", str(tmp_path))
    return viewer


def save(monkeypatch, viewer, path, typed="0 4"):
    """Save the indices ``typed`` to ``path``, as typed in the dialogs; the entry returns once the first is saved."""
    type_in_dialog(monkeypatch, typed)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *args: (str(path), ""))
    button = viewer.toolbar.widgetForAction(viewer.toolbar.actions["save"])
    next(action for action in button.menu().actions() if action.text() == "IRIS: save frames or movie…").trigger()


def test_each_frame_is_the_image_at_its_index_just_after_a_resize(viewer, qtbot, monkeypatch, tmp_path):
    # mpl-scatter-density draws an image's last array for 0.5 s after its canvas is resized: frame 20's here
    viewer.viewer_size = (500, 350)
    QtWidgets.QApplication.processEvents()
    assert [image._pressed for image in viewer.axes.images if isinstance(image, FRBArtist)] == [True]
    save(monkeypatch, viewer, tmp_path / "sji.png")
    qtbot.waitUntil(saved)
    resized(qtbot, [viewer])
    for frame in range(5):
        viewer.state.slices = (frame, 0, 0)
        viewer.figure.savefig(tmp_path / "plot.png")
        np.testing.assert_array_equal(imread(tmp_path / f"sji_{frame:04d}.png"), imread(tmp_path / "plot.png"))


def test_a_resize_ends_the_save(viewer, qtbot, monkeypatch, tmp_path):
    canvas = viewer.figure.canvas
    before, frame = (canvas.width(), canvas.height()), canvas.get_width_height(physical=True)

    def gather(slices):  # glue's Gather Windows, from the main window, while frame 2 is saved
        if slices[0] == 2:
            QTimer.singleShot(0, viewer.session.application.gather_current_tab)

    viewer.state.add_callback("slices", gather)
    save(monkeypatch, viewer, tmp_path / "sji.gif")
    qtbot.waitUntil(saved)
    with Image.open(tmp_path / "sji.gif") as gif:
        assert (gif.n_frames, gif.size) == (2, frame)  # frame 2, being saved, is not
    assert viewer.state.slices == (20, 0, 0)
    # the figure the canvas' new size, not the start's
    assert (canvas.width(), canvas.height()) != before
    shown = np.array([canvas.width(), canvas.height()]) * canvas.device_pixel_ratio
    np.testing.assert_allclose(viewer.figure.bbox.max, shown)


def test_cancel_between_frames_keeps_those_saved(viewer, qtbot, monkeypatch, tmp_path):
    save(monkeypatch, viewer, tmp_path / "sji.png")  # frame 0 saved, frame 1 at the next turn of the event loop
    [progress] = viewer.session.application.findChildren(QtWidgets.QProgressDialog)
    progress.cancel()
    qtbot.waitUntil(saved)
    assert [path.name for path in tmp_path.glob("sji_*.png")] == ["sji_0000.png"]
    assert viewer.state.slices == (20, 0, 0)


def test_a_movie_writer_that_cannot_start_ends_the_save(viewer, qtbot, monkeypatch, tmp_path):
    shown = refusals(monkeypatch)
    missing = tmp_path / "ffmpeg"
    monkeypatch.setitem(rcParams, "animation.ffmpeg_path", str(missing))  # an MP4 typed where ffmpeg is not
    save(monkeypatch, viewer, tmp_path / "sji.mp4")
    assert shown == [f"Could not save the frames or movie\n[Errno 2] No such file or directory: '{missing}'"]
    held = viewer.parent(), viewer.options_widget(), viewer.layer_view()
    assert (saved(), viewer.state.slices, *(widget.isEnabled() for widget in held)) == (True, (20, 0, 0), *[True] * 3)
    assert viewer.figure.canvas.manager is not None
    save(monkeypatch, viewer, tmp_path / "sji.png", "0 1")  # not refused
    qtbot.waitUntil(saved)
    assert (len(list(tmp_path.glob("sji_*.png"))), len(shown)) == (2, 1)


def test_a_movie_that_cannot_be_finished_says_why(viewer, qtbot, monkeypatch, tmp_path):
    shown = refusals(monkeypatch)

    def finish(writer):  # on glue-qt's Worker
        raise OSError("No space left on device")

    monkeypatch.setattr(animation.PillowWriter, "finish", finish)
    save(monkeypatch, viewer, tmp_path / "sji.gif", "0 1")
    qtbot.waitUntil(saved)
    assert shown == ["Could not save the frames or movie\nNo space left on device"]
