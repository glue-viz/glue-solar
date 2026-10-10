"""
The entry point of the macOS app: glue's own ``glue`` command, on PyQt6.
"""

import os
import runpy
import sys
from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()  # a process that multiprocessing starts runs its task, not glue
    os.environ["QT_API"] = "pyqt6"  # before anything imports qtpy
    if "GLUE_SOLAR_APP_CHECK" in os.environ:  # a script that checks the app, smoke.py; glue's own -x fails
        runpy.run_path(os.environ["GLUE_SOLAR_APP_CHECK"], run_name="__main__")
    else:
        from glue_qt.main import main

        sys.exit(main(sys.argv))
