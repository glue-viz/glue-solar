# Avoid importing IPython when importing the common viewer module

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g6-lazy-ipython`, commit 2f8689ff (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`glue.viewers.common.viewer` imports `get_ipython` from IPython at module level, only to look up the running shell in `Viewer.cleanup`. Every viewer imports this module, so any script or application that uses a glue viewer pays for the IPython import even when no IPython shell is running.

A shell can exist only if IPython was already imported, so `cleanup` now takes IPython from `sys.modules`. Importing the viewer module after `glue.core` goes from about 110 ms to about 5 ms (`python -X importtime`, Python 3.13, IPython 8.37).

A Qt session does not gain from this PR alone, because glue-qt imports IPython itself at startup for its terminal. It gains once glue-qt imports its terminal only when it is first opened, which is a separate PR there. Scripts and other front ends gain now.

`test_viewer_does_not_import_ipython` imports the module in a subprocess and checks `sys.modules`. The line added to `.ruff.toml` allows that subprocess call (S603) in the test file, as for `test_python_export.py`.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text is the commit message, plus the review's point that a Qt session gains only with glue-qt's half (`perf-q5-lazy-terminal`, glue-qt row 11). Add that PR's number to the third paragraph once it is open.
- The review marks the branch ready as it is.
