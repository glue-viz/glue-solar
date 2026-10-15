# After glue-viz/glue-standalone-apps' hooks (4e35d18), used with the glue team's permission
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

# fiasco's tables, and the metadata of fiasco and of what it needs, which packages read their versions from: fiasco
# comes with glue-solar's density extra, which hook-glue_solar.py's copy_metadata does not follow
datas = collect_data_files("fiasco", excludes=["**/tests/"]) + copy_metadata("fiasco", recursive=True)
