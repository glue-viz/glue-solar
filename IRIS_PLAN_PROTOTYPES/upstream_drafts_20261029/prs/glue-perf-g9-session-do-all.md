# Serialize each object only once when saving a session

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g9-session-do-all`, commit 549472f3 (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`GlueSerializer.do_all` repeats a full pass over all registered objects until a pass registers no new ones, and serializes every object again on each pass. Saving a data collection with subset groups, or an application with viewers, takes three or more passes, so each data array is saved with `np.save` and base64-encoded two or more times.

Each object is now serialized once, in the first pass that sees it. The output is the same: serializing an object again gives the same record, because the names of the objects it refers to are fixed when they are first registered.

Saving a glue-qt application with an image viewer on four 300x200x200 float32 cubes goes from 136 to 70 serializer calls and from 8 to 4 array encodings, and takes 0.65 s instead of 0.90 s. The 256 MB session string is byte-identical.

`test_serialize_each_object_once` counts the calls.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text is the commit message, shortened. The review marks the branch ready as it is.
- It touches `glue/core/state.py` and its tests, like `fix-session-style-meta` and `session-quantity-saver`. Both rebuilt branches merge cleanly with it.
