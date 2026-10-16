# Adapted from glue-viz/glue-standalone-apps' hooks/hook-glue_qt.py (4e35d18), used with the glue team's permission
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# glue imports its plugins' modules by name, which PyInstaller does not follow
hiddenimports = collect_submodules("glue_qt", filter=lambda name: not {"tests", "conftest"} & {*name.split(".")})
datas = collect_data_files("glue_qt", excludes=["**/tests/"]) + copy_metadata("glue-qt")
