import os, sys, tempfile, pathlib
from fiasco.util.util import get_chianti_catalog
import fiasco
print("fiasco", fiasco.__version__)
for name in ("plain", "emily"):
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / name / "chianti"
        (root / "fe" / "fe_12").mkdir(parents=True)
        (root / "fe" / "fe_12" / "fe_12.elvlc").write_text("x")
        cat = get_chianti_catalog(root)
        print(name, "ion_files:", cat["ion_files"])
