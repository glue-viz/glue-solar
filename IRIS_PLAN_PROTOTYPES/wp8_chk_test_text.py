import time
import pytest
from glue_solar.conftest import OBS_A, OBS_C, OBS_S, iris_tree  # noqa: F401
import wp8_scan
from wp8_proto import ProtoImporter
from wp8_chk_proto_fix import ProtoImporterFixed


@pytest.fixture
def slow_headers(monkeypatch):
    real = wp8_scan.fits.getheader
    calls = []

    def slow(path, *args, **kwargs):
        calls.append(path)
        time.sleep(0.2)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(wp8_scan.fits, "getheader", slow)
    return calls


@pytest.mark.parametrize("cls", [ProtoImporter, ProtoImporterFixed])
def test_stop_message_is_visible_after_an_earlier_load(qtbot, iris_tree, slow_headers, cls):
    dlg = cls(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: not dlg.scanning)
    dlg.progress.setValue(50)  # what finalize() leaves behind after a failed/partial load
    dlg.recursive.setChecked(False)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)
    dlg.stop_scan.click()
    qtbot.waitUntil(lambda: not dlg.scanning)
    assert dlg.progress.format() == "Scan stopped"
    assert dlg.progress.text() == "Scan stopped"  # what the user actually sees
