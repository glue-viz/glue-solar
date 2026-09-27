Two session-save crashes:

- Any `Data` whose `style.preferred_cmap` is a `Colormap` object (the setter turns even a string into one) fails with `TypeError: Object of type ListedColormap is not JSON serializable`. `_save_style` now stores the colormap name; `_load_style` already discards the key.
- A `Quantity` value in `data.meta` reaches `@saver(np.ndarray)` and fails inside `np.save`; `_save_data_5` only caught `GlueSerializeError`. It now skips any meta value that fails to serialize.

Tests: `test_save_style_colormap_object`, `test_save_meta_quantity`.

Label: bug.
