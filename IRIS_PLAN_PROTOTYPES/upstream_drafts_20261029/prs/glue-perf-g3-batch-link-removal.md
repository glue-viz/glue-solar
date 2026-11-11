# Remove the links of a removed dataset or component in one update

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g3-batch-link-removal`, commit 7986425d (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`LinkManager._data_removed` and `_component_removed` call `remove_link` once for each affected link. Each call runs `update_externally_derivable_components`, which discovers the links again and rebuilds the derivable components and the pixel-aligned data of every dataset in the collection. Removing a dataset that is linked to many others therefore runs one full update per link.

They now pass the list of links to `remove_link`, which removes them all and then updates once. The derivable components and pixel-aligned data that result are the same. The datasets no longer pass through the states in between, so listeners get fewer `ExternallyDerivableComponentsChangedMessage` and `PixelAlignedDataChangedMessage` broadcasts.

Removing the dataset that 29 others are linked to through their pixel axes (58 links) goes from 58 updates and about 760 ms to 1 update and 4 ms, and from 870 and 434 broadcasts of the two messages to 29 of each.

`test_remove_links_updates_once` counts the updates.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text is the commit message, shortened. The review marks the branch ready as it is.
- First of the three link manager PRs (then `perf-discover-links`, then `stable-link-order`). The rebuilt `stable-link-order` merges cleanly with it.
