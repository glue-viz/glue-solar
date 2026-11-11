# Speed up discover_links with many linked datasets

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-discover-links`, commit db1c379e (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`discover_links` starts again from the first link after each component it finds, so its time grows as the number of derived components times the number of links. `LinkManager` calls it for every dataset at every link change. With 99 small datasets, each linked to the first on its pixel and world components, one update derives 38,808 components and takes 11 to 13 s.

It now goes through all the links in each pass and keeps every new component or shorter path it finds, until a pass finds none. The number of passes is set by the depth of the links, not by the number of components. The same update takes 0.25 to 0.27 s.

The components found and their depths are the same. Where two paths are equally short, the link used can be another one than before. That choice already depended on the order of a set of links, so it was not stable before either.

`test_discover_links_passes` counts how often the links are gone through for 10 datasets linked to one of them: 10 times on main, at most 3 here. `test_discover_links_fewest_links` checks the components and their depths for the links in two orders; it passes on main too.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text is the drafted body (`prs/glue-perf-discover-links.md`), cut from 44 lines to these, without its table, its DKIST figure and its tie-break example.
- The tracker's order is after `perf-g3-batch-link-removal` (the same file). The two merge cleanly, and so does the rebuilt `stable-link-order`.
- The drafted notes suggested the labels `performance` and `linking`, which put it under Other Changes; `enhancement` puts it under New Features. Your call.
