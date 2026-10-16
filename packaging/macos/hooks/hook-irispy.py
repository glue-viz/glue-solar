# After glue-viz/glue-standalone-apps' hooks (4e35d18), used with the glue team's permission
from PyInstaller.utils.hooks import collect_data_files

# irispy's response files, which its radiometric calibration reads, without its test files
datas = collect_data_files("irispy", excludes=["**/tests/", "data/test/"])
