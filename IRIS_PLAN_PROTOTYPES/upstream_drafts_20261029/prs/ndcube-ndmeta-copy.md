# Fix copy.copy of an NDMeta sharing its axes, comments and data shape

- Upstream: sunpy/ndcube (branch is one commit on main 23465f9)
- Fork branch: `nabobalis:ndmeta-copy` at `4dcbb35bd172fffda9688249480eddafb0169bb9` (new branch)
- Changelog fragment to rename: `changelog/PLACEHOLDER.bugfix.rst` to `<PR number>.bugfix.rst`

## Body

~~~~~markdown
## PR Description

`copy.copy` of an `NDMeta` shared the original's `axes` and `key_comments` dicts and its `data_shape` array, so `add` and `del` on the copy changed the original:

```python
import copy

import numpy as np

from ndcube import NDMeta

meta = NDMeta({"a": 1}, data_shape=(4, 0))
meta_copy = copy.copy(meta)
meta_copy.add("b", np.arange(5), axes=1)
print(dict(meta.axes), meta.data_shape)  # main: {'b': array([1])} [4 5]; this PR: {} [4 0]
```

This PR gives `NDMeta` a `__copy__` that still shares the values, as a shallow copy does, and copies those three. `copy.deepcopy` is unchanged, and ndcube itself calls `copy.copy` on a meta nowhere. The new `test_copy` fails on main.

## AI Assistance Disclosure

AI tools were used for:
- [x] Code generation (e.g., when writing an implementation or fixing a bug)
- [x] Test/benchmark generation
- [x] Documentation (including examples)
- [x] Research and understanding
- [ ] No AI tools were used

> Regardless of AI use, the human contributor remains fully responsible for correctness, design choices, licensing compatibility, and long-term maintainability.
~~~~~

## Notes for the owner (not to paste)

- Do not paste this body as written. sunpy's AI policy, which ndcube's PR template links, lists "Pasting AI generated text in the description of issues, PRs or in comments" as inappropriate use. Rewrite the description in your own words; the policy does allow AI to help reword a summary you have written.
- The policy also says a PR that removes the AI Assistance Disclosure checklist may be closed without review, and one that leaves it incomplete is marked draft and not reviewed. Keep the checklist and the quoted line under it.
- The four ticked boxes are facts about how the work was made (code, test, the changelog fragment, and the research); confirm them before posting.
- ndcube's template asks for an issue before a PR; none exists for this one.
- ndcube's template asks for commit subjects of 72 characters or less; this one is 68.
- This is the old `ndmeta-slice-shallow-copy` branch's first commit, with the tracker's subject and a body that also says what the change does: `NDMeta.__copy__`, `test_copy`, and the bugfix fragment.
- `ndmeta-slice-shallow-copy` (row 6) is stacked on this branch, so open this one first.
- Run: `ndcube/tests/test_meta.py`, 19 passed. With upstream's `meta.py`: 1 failed, 18 passed: `test_copy`, `assert_metas_equal(meta, expected)` fails at `assert np.allclose(test_input.data_shape, expected_output.data_shape)` with `AssertionError`.
- Run: the body's snippet prints `{'b': array([1])} [4 5]` on main and `{} [4 0]` on the branch.
- Lint: ruff 0.16.1 check passes; upstream pins v0.17.4, which was not available.
- Not run: the whole suite, the docs build, towncrier, the other pre-commit hooks.
