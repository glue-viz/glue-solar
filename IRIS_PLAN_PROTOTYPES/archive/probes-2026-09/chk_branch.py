import os, sys, platform
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from Foundation import NSBundle
b = NSBundle.mainBundle()
info = b.localizedInfoDictionary() or b.infoDictionary()
print('bundle', b.bundlePath()); print('CFBundleName before', info.get('CFBundleName'), type(info).__name__)
from glue.config import settings
print('settings.FONT_SIZE before', settings.FONT_SIZE, 'CFG_DIR', __import__('glue.config').config.CFG_DIR)
from glue_qt.utils import app
print('app module', app.__file__)
q = app.get_qapp()
print('CFBundleName after', info.get('CFBundleName'))
print('applicationName', q.applicationName(), '| displayName', q.applicationDisplayName(), '| argv', q.arguments())
print('style', q.style().objectName(), 'PM_ToolBarIconSize', q.style().pixelMetric(app.QtWidgets.QStyle.PM_ToolBarIconSize))
print('default_font_size', app.default_font_size(), 'qapp font pt', q.font().pointSize())
print('settings.FONT_SIZE after', settings.FONT_SIZE)
