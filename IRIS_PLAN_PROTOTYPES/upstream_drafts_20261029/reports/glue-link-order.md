# glue-core #83: equally short link paths taken in no stable order

- **Where:** a new issue on glue-viz/glue (bug template). No existing issue or PR found (`gh search` for
  "discover_links", "link order", "shortest link"). A PR is ready too if you prefer one (below).
- **Review row:** glue-core #83 (UPSTREAM_REVIEW, REPORT, "design open").
- **Reproducer:** `scripts/glue_link_order.py`, run by `run.sh rel|main glue_link_order.py`; outputs
  `out/glue_link_order_{rel,main,branch}.txt`.
- **Tried fix:** clone `clones/glue`, local branch `stable-link-order`, commit `55b169995dc819e90ef29cdf3efc0a7b01cc5c88`
  (on main 3683f07c, the v1.28.0 tag): the link manager keeps its links in insertion order (dicts, not sets), with a
  test `test_equal_depth_links_use_the_first_added`. The test fails on main (`assert np.float64(2.0) == 1`) and passes on
  the branch; `glue/core glue/plugins glue/viewers` pass on the branch (1487 passed, 17 skipped, 6 xfailed, 1 xpassed,
  -n 4); ruff (glue's config) is clean. glue's CHANGES.md is generated from PR titles, so the branch adds no entry.

## Title

Of two equally short link paths, glue uses either one, varying from run to run

## Body (paste)

**Describe the bug**

When a component can be derived through two links of the same depth, glue picks one in an order that changes between
runs, not in the order the links were added. `LinkManager.update_externally_derivable_components` passes
`self._links | self._inverse_links` to `discover_links` (`link_manager.py:250`), and both are sets (`:268-288`). So
their order follows the links' hashes, that is, their ids. `discover_links` keeps the first accessible link to each
component and skips an equally short one later (`cost >= depth[to_]`, `:85`). The same session can thus give a
component other values after a restart or a session restore.

We met this with a mosaic of DKIST tiles, each linked by WCS to a center tile and by index links to a mosaic image: a
tile's frame index came through another tile, and after a session restore its x and y could be 2 pixels off.

**To Reproduce**

```python
import numpy as np

import glue
from glue.core import Data, DataCollection
from glue.core.component_link import ComponentLink

print("glue", glue.__version__, "from", glue.__file__)
for order in ("x link added first", "y link added first"):
    used = {"via x": 0, "via y": 0}
    for _ in range(40):  # new objects each time, as after a restart or a session restore
        d = Data(x=np.zeros(3), y=np.zeros(3), label="d")
        c = Data(c=np.zeros(3), label="c")
        dc = DataCollection([d, c])
        via_x = ComponentLink([d.id["x"]], c.id["c"], using=lambda x: x + 100)
        via_y = ComponentLink([d.id["y"]], c.id["c"], using=lambda y: y + 200)
        dc.add_link([via_x, via_y] if order.startswith("x") else [via_y, via_x])
        used["via x" if d[c.id["c"]][0] == 100 else "via y"] += 1
    print(f"{order}: d's c is computed {used['via x']} times via x and {used['via y']} times via y in 40 runs")
```

Output on glue-core 1.28.0, paths shortened. main is the v1.28.0 tag commit (3683f07c), so this is main too:

```
glue 1.28.0 from .../site-packages/glue/__init__.py
x link added first: d's c is computed 12 times via x and 28 times via y in 40 runs
y link added first: d's c is computed 26 times via x and 14 times via y in 40 runs
```

Another run of the script gave 21 and 19 via x and y, then 20 and 20.

**Expected behavior**

The same links, added in the same order, always give the same path. A simple rule: of equally short paths, take the
link added first, with each dataset's own links (its coordinate and derived links) ahead of external ones.

Keeping the link manager's links in dicts instead of sets does this, as `discover_links` already takes the first link
it finds:

```diff
     @property
     def _links(self):
+        # A dict, not a set, so that links keep a stable order: each dataset's
+        # own links first, then the external links in the order they were
+        # added. discover_links takes the first of several equally short paths.

         if self.data_collection is None:
-            data_links = set()
+            links = {}
         else:
-            data_links = set(link for data in self.data_collection for link in getattr(data, 'links', []))
-
-        external_links = set()
+            links = dict.fromkeys(link for data in self.data_collection for link in getattr(data, 'links', []))

         for link in self._external_links:
             if isinstance(link, LinkCollection):
-                for sublink in link:
-                    external_links.add(sublink)
+                links.update(dict.fromkeys(link))
             else:
-                external_links.add(link)
+                links[link] = None

-        return data_links | external_links
+        return links

     @property
     def _inverse_links(self):
-        return set(link.inverse for link in self._links if link.inverse is not None)
+        return dict.fromkeys(link.inverse for link in self._links if link.inverse is not None)
```

With it, the script gives 40 of 40 via x when x's link is added first, and 40 of 40 via y the other way, and glue's
`core`, `plugins` and `viewers` tests pass. I can open it as a PR, with a test.

**Details:**

- Operating System: Fedora Linux 44
- Python version (``python --version``): Python 3.13.16
- Glue version (``glue --version``): glue-core 1.28.0 (main is at its tag, 3683f07c)
- How you installed glue: pip

## Notes for the user (not to paste)

- Branch output (`out/glue_link_order_branch.txt`): "x link added first: ... 40 times via x and 0 times via y";
  "y link added first: ... 0 times via x and 40 times via y".
- Whether the branch alone retires `_mosaic_links`' index links (`sources/dkist.py:912`) depends on the mosaic's links
  being ahead of the competing path in this order. That was not tried with glue-solar or DKIST data here. Say so in the
  glue-solar PR that drops them, and keep the tests that pin the frame index.
- As a PR instead: push `stable-link-order` to your fork; its commit message is "Use the first-added of equally short
  link paths", and the issue's body works as the PR's description.
