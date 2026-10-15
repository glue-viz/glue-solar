# After glue-viz/glue-standalone-apps' hooks (4e35d18), used with the glue team's permission
from PyInstaller.utils.hooks import collect_data_files

# plasmapy's particle data
datas = collect_data_files("plasmapy", excludes=["**/tests/"])
