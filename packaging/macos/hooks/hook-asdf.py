# Adapted from glue-viz/glue-standalone-apps' hooks/hook-asdf.py (4e35d18), used with the glue team's permission
from PyInstaller.utils.hooks import collect_data_files, collect_entry_point

# The extensions and schemas asdf finds by their entry points, its own and those of asdf-astropy, gwcs, ndcube, dkist
# and the schema packages: astropy loads them as it imports asdf-astropy, and sessions save IRIS WCSs in ASDF
datas, hiddenimports = [], []
for group in ("asdf.extensions", "asdf.resource_mappings"):
    group_datas, group_imports = collect_entry_point(group)
    datas += group_datas
    hiddenimports += group_imports
for package in {name.split(".")[0] for name in hiddenimports}:
    datas += collect_data_files(package, excludes=["**/tests/", "data/test/"])
