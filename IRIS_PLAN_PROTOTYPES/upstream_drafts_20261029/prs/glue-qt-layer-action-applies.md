# Add an `applies` function to layer actions

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:layer-action-applies` at `c9fbcf1ce5` (pushed 2026-11-12)
- Label: enhancement

## Body

~~~~~markdown
A layer action registered with `layer_action` is shown for a kind of selection: a single dataset, subset group or subset, or any selection. A plugin cannot show an action only for the layers it can handle, such as datasets with three dimensions: the action is there for all of them.

`layer_action` now takes an `applies` function. It is called with the first argument the callback would get (the selected layer if `single` is true, otherwise the list of selected layers), and the action is shown only where it returns true:

```python
@layer_action('Do something', single=True, data=True,
              applies=lambda data: data.ndim == 3)
```

Without `applies` nothing changes. The registry's item gets the new field with a default of `None`, so code that builds items with the eight earlier values still works.

The customization guide documents it. `test_user_action_applies` in `glue_qt/app/tests/test_layer_tree_widget.py` fails without the change.
~~~~~

## Notes for the owner (not to paste)

- Existing fork branch, to force-push. Same tree as the fork's (checked). The subject is now 40 characters (it was 91).
- The commit had no body. I added six lines saying what was missing and what the change does; drop them if you want the subject only.
- Tests on the branch: `test_layer_tree_widget.py`, 23 passed. With the test on main: `TypeError: LayerActionRegistry.__call__() got an unexpected keyword argument 'applies'`, 1 failed, 22 passed.
- ruff: passes. Merges cleanly with `edit-subset-tree-rebuild`, which touches the same test file and `layer_tree_widget.py`.
