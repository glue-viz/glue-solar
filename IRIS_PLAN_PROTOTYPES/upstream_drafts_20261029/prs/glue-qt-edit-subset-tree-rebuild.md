# Keep the edit subset when a dataset or another subset group is removed

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:edit-subset-tree-rebuild` at `bae00851e1` (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
Removing a subset group or a dataset empties the edit subset, even when the edit subset is another group. With subset A selected in the data collection, removing subset B, or any dataset, leaves no edit subset, so the next selection makes a new subset instead of changing A.

`DataCollectionModel.invalidate` rebuilds the tree on `SubsetDeleteMessage` and `DataCollectionDeleteMessage`. The rebuild leaves the tree's selection empty, and `LayerTreeWidget._update_edit_subset` then sets the edit subset to it.

The fix has two parts:
- `invalidate` emits `layoutAboutToBeChanged` first, and makes the old persistent indexes invalid before `layoutChanged`, as Qt asks of a layout change. The tree's items look up their group or dataset by row in a collection that has already changed, so old indexes cannot be mapped to new ones.
- `LayerTreeWidget` leaves the edit subset alone while the tree is rebuilt. It then selects the edit subset's groups that are still in the collection, and sets the edit subset from that selection once. Listeners get one `EditSubsetMessage` with the groups kept, not an empty one first.

As before, removing the edit subset itself empties it, and a group one of whose subsets was deleted on its own (`Subset.delete()`) is dropped from it.

`test_edit_subset_kept_as_other_layers_are_removed` in `glue_qt/app/tests/test_layer_tree_widget.py` fails without the change. The edit subset is kept without the two persistent-index lines; one assertion of the test pins them, `assert not old_index.isValid()`.
~~~~~

## Notes for the owner (not to paste)

- Existing fork branch, to force-push. Same tree as the fork's (checked with `git diff`); only the message changed: the new subject, and a last paragraph naming the one assertion that pins the persistent-index lines.
- Checked: with the two lines (`old = self.persistentIndexList()` and `self.changePersistentIndexList(...)`) removed, the test fails only at `assert not old_index.isValid()` (`assert not True`); with that assertion removed as well, all 23 tests of the file pass.
- The body is the drafted one (`prs/glue-qt-edit-subset-tree-rebuild.md`), shortened, with that sentence added.
- Tests on the branch: `test_layer_tree_widget.py` and `glue_qt/core/tests/test_data_collection_model.py`, 38 passed. With the test on main: `assert [] == [<glue.core.subset_group.SubsetGroup ...>]`, 1 failed, 22 passed.
- ruff: passes.
