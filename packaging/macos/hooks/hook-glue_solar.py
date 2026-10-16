# After glue-viz/glue-standalone-apps' hooks/hook-glue.py (4e35d18), used with the glue team's permission
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# glue imports its plugins' modules by name, which PyInstaller does not follow
hiddenimports = collect_submodules("glue_solar", filter=lambda name: not {"tests", "conftest"} & {*name.split(".")})
# The metadata of glue-solar and of what it needs, which copy_metadata does not follow: glue finds its plugins by their
# entry points, and packages read their versions
datas = collect_data_files("glue_solar", excludes=["**/tests/"]) + copy_metadata("glue-solar", recursive=True)
# reproject's too, which sunpy.map looks for as it imports, warning without it (sessions import it, through sunpy's
# asdf converters): reproject comes with sunpy's map extra, and the recursion follows no extras
datas += copy_metadata("reproject")
