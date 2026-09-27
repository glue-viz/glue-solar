### Description

Saving a session fails with a `TypeError` for two kinds of otherwise ordinary `Data` objects.

1. Any `Data` whose `style.preferred_cmap` is set. `VisualAttributes.preferred_cmap` always holds a `Colormap` object (its setter converts names to objects, `glue/core/visual.py`), so as soon as a plugin or data loader sets it the session can no longer be saved:

   ```python
   from matplotlib import cm
   from glue.core import Data, DataCollection
   from glue.core.state import GlueSerializer

   d = Data(x=[1, 2, 3], label='d')
   d.style.preferred_cmap = cm.viridis      # the string 'viridis' gives the same result
   GlueSerializer(DataCollection([d])).dumps()
   # TypeError: Object of type ListedColormap is not JSON serializable
   ```

   `_load_style` removes `preferred_cmap` from the attributes it restores, so nothing is lost by storing the colormap's name instead of the object.

2. Any `Data` whose `meta` holds a value that is not serializable but does not raise `GlueSerializeError`, e.g. an astropy `Quantity` (it reaches the `np.ndarray` saver and fails inside `np.save`):

   ```python
   import astropy.units as u

   d = Data(x=[1, 2, 3], label='d')
   d.meta['exposure time'] = 4 * u.s
   GlueSerializer(DataCollection([d])).dumps()
   # TypeError: no implementation found for 'numpy.save' on types that implement __array_function__: [<class 'astropy.units.quantity.Quantity'>]
   ```

   `_save_data_5` already filters meta entries that cannot be serialized, but only catches `GlueSerializeError`: a plain `object()` value is silently dropped while a `Quantity` aborts the whole save.

### Changes

- `_save_style` stores `preferred_cmap` by name (`getattr(cmap, 'name', cmap)`; `None` and strings pass through unchanged).
- `_save_data_5` catches any `Exception` while probing a meta key/value and skips the entry, as it already did for `GlueSerializeError`.
- Tests: `test_save_style_colormap_object` and `test_save_meta_quantity` in `glue/core/tests/test_state.py`; both fail on `main` with the errors above.

Checks: ruff v0.15.20 (the pre-commit pin) clean on the changed files; `pytest glue/core/tests/test_state.py glue/core/tests/test_component_link.py glue/core/tests/test_coordinate_links.py glue/core/tests/test_coordinates.py glue/core/tests/test_data_region.py glue/utils/tests/test_matplotlib.py glue/utils/tests/test_array.py`: 250 passed, 1 skipped (python 3.14.7, numpy 2.5.2, matplotlib 3.11.1, astropy 8.0.1).

Found while loading IRIS data in glue-solar (irispy metadata carries `Quantity` values and the loader sets a preferred colormap); glue-solar works around both until this is released.

Label: bug
