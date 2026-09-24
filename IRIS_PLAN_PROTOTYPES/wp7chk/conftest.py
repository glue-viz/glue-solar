import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from glue_solar.conftest import iris_tree, irispy_test_files  # noqa: E402, F401
