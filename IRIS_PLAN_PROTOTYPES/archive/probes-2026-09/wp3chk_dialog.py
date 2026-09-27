"""Does a failing File -> Save Session show a modal error box in glue-qt, or only the log widget?"""
import os, glob
from qtpy import QtWidgets
from glue_qt.app import GlueApplication
from glue.core import Data
from glue_solar.sources.loaders.iris import image_data
from irispy.data.test import get_test_data_filenames

sji = [f for f in get_test_data_filenames() if "3620258102_SJI_1330" in str(f)][0]
app = GlueApplication()
d = image_data(str(sji))  # stock branch code: _GlueWCS has no saver -> GlueSerializeError
app.data_collection.append(d)
calls = []
app.report_error = lambda msg, detail: calls.append((msg, detail))  # QMessageBox.exec_ would block offscreen
out = os.path.join(os.environ["HOME"], "dialog_test.glu")
app.save_session(out, include_data=False, absolute_paths=False)
print("report_error called:", len(calls))
print("message:", calls[0][0].splitlines()[0] if calls else None, "|", (calls[0][0].splitlines()[1][:80] if calls else None))
print("file written:", os.path.exists(out))
import inspect, glue_qt.app.application as A
src = inspect.getsource(A.GlueApplication.report_error)
print("report_error uses QMessageBox:", "QMessageBox" in src)
