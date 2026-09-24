import inspect, glue, pytestqt.qtbot as qb
from glue_qt.utils import Worker
from qtpy.QtCore import QThread
from qtpy import QT_VERSION, API_NAME
print("from glue_qt.utils import Worker ->", Worker, "| glue", glue.__version__)
print("waitUntil", inspect.signature(qb.QtBot.waitUntil))
print(API_NAME, QT_VERSION)
print('requestInterruption' in dir(QThread), 'isInterruptionRequested' in dir(Worker))
