"""Apply the WP3 brief's edits to the throwaway worktree, exactly as the brief states them."""
import re, sys
W = sys.argv[1]
impl = open(sys.argv[2] + "/wp3_impl.py").read().splitlines(keepends=True)
funcs = "".join(impl[27:83])          # lines 28-83: _tab_record, _wcs_record, _wcs_from_record
quantity = "".join(impl[95:104])      # lines 96-104
solar = "".join(impl[106:121])        # lines 107-121
rasters = "".join(impl[123:133]).replace("L.raster_data", "raster_data")  # lines 124-133

p = f"{W}/glue_solar/sources/loaders/iris.py"
src = open(p).read()
src = src.replace("import os\nimport tarfile\n", "import base64\nimport io\nimport os\nimport tarfile\n", 1)
src = src.replace("import numpy as np\nfrom glue.core.component import Component\n",
                  "import asdf\nimport gwcs\nimport numpy as np\nfrom glue.core.component import Component\n", 1)
src = src.replace("from glue.core.data import Data\nfrom glue.core.visual import VisualAttributes\n",
                  "from glue.core.data import Data\nfrom glue.core.data_factories import load_data\nfrom glue.core.state import GlueSerializeError, loader, saver\nfrom glue.core.visual import VisualAttributes\nfrom glue.utils import as_list\nfrom ndcube.wcs.wrappers import CompoundLowLevelWCS\n", 1)
src = src.replace("import astropy.units as u\nfrom astropy.wcs.wcsapi.wrappers import BaseWCSWrapper\n",
                  "import astropy.units as u\nfrom astropy.io import fits\nfrom astropy.wcs import WCS\nfrom astropy.wcs.wcsapi.wrappers import BaseWCSWrapper, SlicedLowLevelWCS\n", 1)
src = src.replace('__all__ = ["QtIRISImporter", "image_data", "iris_data", "last_directory", "raster_data"]',
                  '__all__ = ["QtIRISImporter", "SolarVisualAttributes", "image_data", "iris_data", "last_directory", "raster_data"]', 1)
src = src.replace("class _GlueWCS(BaseWCSWrapper):\n", funcs + "\n\nclass _GlueWCS(BaseWCSWrapper):\n", 1)
methods = '''
    def __gluestate__(self, context):
        return {"wcs": _wcs_record(self._wcs)}

    @classmethod
    def __setgluestate__(cls, rec, context):
        return cls(_wcs_from_record(rec["wcs"]))
'''
src = src.replace("        return self._wcs.world_to_pixel_values(*values)\n\n\ndef _cube_data(",
                  "        return self._wcs.world_to_pixel_values(*values)\n" + methods + "\n\n" + quantity + "\n\n" + solar + "\n\ndef _cube_data(", 1)
src = src.replace("    data.style = VisualAttributes(color=color, preferred_cmap=cmap)\n",
                  "    data.style = SolarVisualAttributes(color=color, preferred_cmap=cmap)\n", 1)
old_loop = '''        self.datasets, self.first_image = [], None
        for n, (i, kind, name) in enumerate(picks):
            self.progress.setValue(int(100 * n / len(picks)))
            get_qapp().processEvents()
            obs = self.observations[i]
            try:
                if kind == "raster":
                    self.datasets.extend(raster_data(obs.rasters, [name], stack=self.stack.isChecked()))
                else:
                    image = image_data(obs.sji[name] if kind == "sji" else obs.sdo[name])
                    self.datasets.append(image)
                    self.first_image = self.first_image or image
            except Exception as error:  # noqa: BLE001 - third-party reader errors must stay inside the dialog
                self.progress.setFormat(f"Loading {name} failed: {error}")
                return
'''
new_loop = '''        from glue_solar.sources.iris import read_iris_file, read_iris_rasters  # sources.iris imports this module

        self.datasets, self.first_image = [], None
        for n, (i, kind, name) in enumerate(picks):
            self.progress.setValue(int(100 * n / len(picks)))
            get_qapp().processEvents()
            obs = self.observations[i]
            try:
                if kind == "raster":
                    files = [str(p) for p in obs.rasters]
                    folder = os.path.dirname(files[0])
                    loaded = load_data(files[0], factory=read_iris_rasters,
                                       files=[os.path.relpath(f, folder) for f in files],
                                       windows=[name], stack=self.stack.isChecked())
                    self.datasets.extend(as_list(loaded))
                else:
                    image = load_data(str(obs.sji[name] if kind == "sji" else obs.sdo[name]), factory=read_iris_file)
                    self.datasets.append(image)
                    self.first_image = self.first_image or image
            except Exception as error:  # noqa: BLE001 - third-party reader errors must stay inside the dialog
                self.progress.setFormat(f"Loading {name} failed: {error}")
                return
'''
assert old_loop in src
src = src.replace(old_loop, new_loop, 1)
open(p, "w").write(src)

p = f"{W}/glue_solar/sources/iris.py"
src = open(p).read()
src = src.replace("from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, last_directory\n\n__all__ = [\"browse_iris\", \"read_iris_file\"]\n",
                  "from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, last_directory, raster_data\n\n__all__ = [\"browse_iris\", \"read_iris_file\", \"read_iris_rasters\"]\n", 1)
src = src.replace("    return iris_data(file_path)\n\n\n", "    return iris_data(file_path)\n\n\n" + rasters + "\n\n", 1)
src = src.replace("from glue.config import data_factory, menubar_plugin\n", "import os\n\nfrom glue.config import data_factory, menubar_plugin\n", 1)
open(p, "w").write(src)

p = f"{W}/glue_solar/sources/maps.py"
src = open(p).read()
assert 'result.style = VisualAttributes(color="#FDB813", preferred_cmap=scan_map.cmap)' in src
src = src.replace('result.style = VisualAttributes(color="#FDB813", preferred_cmap=scan_map.cmap)',
                  'result.style = SolarVisualAttributes(color="#FDB813", preferred_cmap=scan_map.cmap)', 1)
src = src.replace("from glue.core.visual import VisualAttributes\n", "from glue_solar.sources.loaders.iris import SolarVisualAttributes\n", 1)
open(p, "w").write(src)
print("patched")
