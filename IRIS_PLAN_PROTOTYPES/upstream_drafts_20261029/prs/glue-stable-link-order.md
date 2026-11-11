# Keep the link manager's links in the order they were added

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:stable-link-order`, commit 36fb1cc0 (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
When a component can be derived through two links of the same depth, the link glue uses changes from run to run. `LinkManager` keeps its links in sets and passes them to `discover_links`, which keeps the first link it finds to each component. A set of links is ordered by their hashes, which are their ids, so the same session can give a component other values after a restart or a session restore.

```python
d = Data(x=np.zeros(3), y=np.zeros(3), label='d')
c = Data(c=np.zeros(3), label='c')
dc = DataCollection([d, c])
via_x = ComponentLink([d.id['x']], c.id['c'], using=lambda x: x + 100)
via_y = ComponentLink([d.id['y']], c.id['c'], using=lambda y: y + 200)
dc.add_link([via_x, via_y])
d[c.id['c']][0]  # 100 or 200
```

Built 40 times in one process on main, this gave 100 in 30 of them and 200 in 10.

This PR keeps the links in dicts, so they have a fixed order: each dataset's own links first, then the external links in the order they were added. The same links added in the same order now always give the same path. For two links that lead straight to the same component, as above, that is the one added first. The PR does not otherwise define which of several equally short paths wins.

`test_equal_depth_links_same_choice_in_every_run` builds the example 20 times with new objects and fails on main.
~~~~~

## Notes for the owner (not to paste)

- Commit retitled, the test renamed from `test_equal_depth_links_use_the_first_added`, and the comment in `link_manager.py` reworded to end "so that discover_links chooses between equally short paths the same way in every run". No other change to the fork branch.
- The body is written from scratch; the drafted one was an issue template. The 30 and 10 are from my run of the example on upstream/main; with the branch it is 40 and 0.
- The tracker puts this after `perf-g3-batch-link-removal` and `perf-discover-links` (the same file). It is one commit on upstream/main and merges cleanly with both, so it does not have to wait for them.
- Tests: `glue/core/tests/test_link_manager.py` 22 passed. On upstream/main, three runs out of three: `assert np.float64(2.0) == 1`. The failure is by chance on main, with odds of about one in a million of passing.
- Lint: one ruff 0.16.1 finding in `link_manager.py`, on upstream's own line and present on upstream/main.
