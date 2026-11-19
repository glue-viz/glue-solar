"""glue_patches' probes: one that raises, as on a glue change it did not foresee, installs its patch (D82)."""

import inspect
import re
import sys

import pytest
from glue_qt.app.application import GlueLogger
from glue_qt.utils.threading import Worker
from qtpy import QtWidgets
from qtpy.QtCore import QThread

from glue_solar import glue_patches


def test_a_probe_that_raises_installs_its_patch(caplog):
    def probe():
        raise AttributeError("a glue internal the probe drives is gone")

    assert glue_patches._needs(probe) is True
    # with a warning that names the probe and its error, not without a word
    [record] = caplog.records
    assert record.levelname == "WARNING"
    assert "probe probe raised AttributeError('a glue internal the probe drives is gone')" in record.getMessage()
    assert glue_patches._needs(lambda: False) is False
    # every patch asks its probe through `_needs`
    assert not re.findall(r"(?<!def )\bneeds_\w+_workaround\(\)", inspect.getsource(glue_patches))


def test_no_probe_raises_on_the_installed_versions(qapp):
    # one that did would install its patch whatever glue, glue-qt and astropy now do
    raised = {}
    for name in re.findall(r"^def (needs_\w+)\(", inspect.getsource(glue_patches), re.MULTILINE):
        try:
            getattr(glue_patches, name)()
        except Exception as error:  # noqa: BLE001 - each probe's, named below
            raised[name] = error
    assert not raised


def test_the_register_and_glue_patches_name_the_same_probes(request):
    # docs/dev_guide/workarounds.rst: each probe is the switch of an entry, and no entry names a probe that is gone
    register = request.config.rootpath / "docs" / "dev_guide" / "workarounds.rst"
    if not register.exists():
        pytest.skip("the package is installed without its docs")
    probes = re.findall(r"^def (needs_\w+)\(", inspect.getsource(glue_patches), re.MULTILINE)
    assert set(re.findall(r"\bneeds_\w+", register.read_text())) == set(probes)


def test_a_write_to_glue_qt_s_log_off_the_gui_thread_is_made_on_it(qtbot, monkeypatch):
    # the log is sys.stderr, where irispy warns as the observation browser reads on a worker thread: glue-qt 0.4.2
    # edits the log's QTextEdit on the thread that writes, and Qt allows that on the GUI thread only
    gui, button, edits = QThread.currentThread(), QtWidgets.QToolButton(), []
    log = GlueLogger(button_console=button)  # sys.stderr from here until it closes, with the test
    qtbot.addWidget(log)
    monkeypatch.setattr(log._text, "insertPlainText", lambda message: edits.append((message, QThread.currentThread())))
    worker = Worker(sys.stderr.write, "from a worker")  # glue-qt's, as the browser's
    worker.start()
    qtbot.waitUntil(lambda: bool(edits))
    worker.wait()
    sys.stderr.write("from the GUI thread")  # at once
    assert edits == [("from a worker", gui), ("from the GUI thread", gui)]


def test_the_slider_patch_installs_where_glue_qt_reads_an_array_axis_for_a_world_axis(qapp):
    assert glue_patches.needs_slider_world_workaround()  # glue-qt 0.4.2's own method
    assert not glue_patches.needs_slider_world_workaround(glue_patches.sync_sliders_from_state)
