# filelock: the fork-safety audit hook slows every deepcopy (perf360 c1)

- **Where:** a new issue on tox-dev/filelock (the repo has no issue template). No existing issue or PR found
  (`gh search` for "audit hook", "audit", "addaudithook", "deepcopy slow", "performance", "overhead", "slow"). Related:
  the hook came with #652 (3.30.0); #701 with #703 fixed it at interpreter shutdown; #747 (4.0.3) skips it on CPython
  3.10 and 3.11. An issue, not a PR: where the hook goes is the maintainers' call, and the sketch was not run.
- **Review row:** perf360 REPORT (c) c1. irispy's side is a4 (import filelock inside `_extract_tarfile`).
- **Reproducer:** `scripts/perf360_filelock.py` (numpy and astropy; each case in a fresh interpreter, since an audit
  hook cannot be removed); output `out/perf360_filelock_rel.txt`. Release: filelock 4.2.4 in iris-plan-latest-1028,
  `python -I -B`, 24G cap; peaks 115, 114 and 115 MB.
- **Main (715a8de) not run:** the session's permission classifier refused to run the clone's code ("Code from
  External"). From the source: `_audit_fork_safety` and `_register_fork_hooks` are the same as in 4.2.4 (main's
  `_api.py:1978`), so main installs the same hook at import. The body says so.

## Title

`import filelock` slows every `copy.deepcopy`: the fork-safety audit hook runs at each `id()` call

## Body (paste)

Since 3.30.0 (#652), importing filelock installs `_audit_fork_safety` with `sys.addaudithook` (`_register_fork_hooks`,
`src/filelock/_api.py:1978` on main). An audit hook cannot be removed, and CPython calls every Python hook for every
audit event. Some events fire very often: `id()` raises `builtins.id`, and `copy.deepcopy` calls `id()` for each object
it visits. So a program that imports filelock, even one that never makes a lock, runs a Python function for each
object of every deep copy.

The script below times `copy.deepcopy` of a nested dict and of an astropy compound model, each case in a fresh
interpreter: no hook, `import filelock`, and a do-nothing Python hook in place of filelock's.

```python
"""copy.deepcopy with and without `import filelock`.

filelock installs a Python audit hook at import (sys.addaudithook(_audit_fork_safety)). CPython then calls it for every
audit event, and copy.deepcopy raises one (builtins.id) for each object it visits. An audit hook cannot be removed, so
each case runs in its own interpreter: no hook, `import filelock`, and a do-nothing Python hook in its place.
"""

import collections
import copy
import json
import resource
import subprocess
import sys
import timeit

import numpy as np

import astropy
import astropy.units as u
from astropy.modeling import models


def nested():
    """A nested structure of dicts, lists and tuples: 10 windows of 40 keys and 20 steps."""
    return {
        f"window {i}": {
            "shape": [8, 1093, 548],
            "keys": {f"KEY{j:03d}": float(j) for j in range(40)},
            "steps": [(j, f"step {j}", [j, j + 1]) for j in range(20)],
        }
        for i in range(10)
    }


def compound_model():
    """A 4-D compound model of the kind a raster gWCS uses (spectral, celestial, time and an identity)."""
    spectral = models.Linear1D(slope=0.0025 * u.nm / u.pix, intercept=133 * u.nm, name="wavelength")
    celestial = (
        (models.Shift(-274) & models.Shift(-546))
        | (models.Scale(0.35) & models.Scale(0.1667))
        | models.AffineTransformation2D(matrix=[[0.99, -0.01], [0.01, 0.99]])
        | models.Pix2Sky_TAN()
        | models.RotateNative2Celestial(0.05, -0.02, 180)
    )
    time = models.Tabular1D(points=np.arange(400), lookup_table=np.linspace(0, 3000, 400), name="time")
    sky_time = models.Mapping((0, 1, 1)) | (celestial & time)
    return spectral & sky_time & models.Identity(1)


def per_call(fn, number):
    return min(timeit.repeat(fn, number=number, repeat=7)) / number


CASES = {
    "none": "no audit hook",
    "filelock": "import filelock",
    "noop": "a do-nothing Python hook instead",
}
TIMED = ("deepcopy of the nested structure", "deepcopy of the compound model", "1000 id() calls")


def child(case):
    if case == "filelock":
        import filelock

        print(f"filelock {filelock.__version__} from {filelock.__file__}", file=sys.stderr)
    elif case == "noop":
        sys.addaudithook(lambda event, args: None)
    data, model = nested(), compound_model()
    times = [
        per_call(lambda: copy.deepcopy(data), 200),
        per_call(lambda: copy.deepcopy(model), 200),
        per_call(lambda: [id(x) for x in range(1000)], 2000),
    ]
    counts = collections.Counter()
    sys.addaudithook(lambda event, args: counts.update((event,)))
    events = []
    for obj in (data, model):
        counts.clear()
        copy.deepcopy(obj)
        events.append(dict(counts))
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(json.dumps({"times": times, "events": events, "peak": peak}))


if len(sys.argv) > 1:
    child(sys.argv[1])
    sys.exit()

flags = [f for f, on in (("-I", sys.flags.isolated), ("-P", sys.flags.safe_path), ("-s", sys.flags.no_user_site)) if on]
print(f"Python {sys.version.split()[0]}, numpy {np.__version__}, astropy {astropy.__version__}")
results = {}
for case in CASES:
    run = subprocess.run([sys.executable, *flags, "-B", __file__, case], capture_output=True, text=True, check=True)
    sys.stdout.write(run.stderr)
    results[case] = json.loads(run.stdout)
for i, name in enumerate(TIMED):
    base = results["none"]["times"][i]
    cells = [f"{CASES[c]} {r['times'][i] * 1e3:.3f} ms ({r['times'][i] / base:.2f} x)" for c, r in results.items()]
    print(f"{name}: " + "; ".join(cells))
for i, name in enumerate(("nested structure", "compound model")):
    print(f"audit events in one deepcopy of the {name}: {results['none']['events'][i]}")
extra = results["filelock"]["times"][0] - results["none"]["times"][0]
print(f"filelock's hook adds {extra / sum(results['none']['events'][0].values()) * 1e9:.0f} ns per event (nested)")
print("peak RSS of each run (MB):", ", ".join(f"{r['peak']:.0f}" for r in results.values()))
```

Output with filelock 4.2.4 (main, 715a8de, installs the same hook in the same way), paths shortened:

```
Python 3.13.16, numpy 2.5.4, astropy 8.0.2
filelock 4.2.4 from .../site-packages/filelock/__init__.py
deepcopy of the nested structure: no audit hook 0.322 ms (1.00 x); import filelock 0.566 ms (1.76 x); a do-nothing Python hook instead 0.464 ms (1.44 x)
deepcopy of the compound model: no audit hook 0.722 ms (1.00 x); import filelock 1.197 ms (1.66 x); a do-nothing Python hook instead 1.001 ms (1.39 x)
1000 id() calls: no audit hook 0.017 ms (1.00 x); import filelock 0.088 ms (5.26 x); a do-nothing Python hook instead 0.059 ms (3.54 x)
audit events in one deepcopy of the nested structure: {'builtins.id': 2994}
audit events in one deepcopy of the compound model: {'builtins.id': 5095}
filelock's hook adds 81 ns per event (nested)
peak RSS of each run (MB): 115, 114, 115
```

filelock's hook makes these deep copies 1.7-1.8 times slower, about 80 ns per audit event. Most of that is the cost of
having a Python hook at all: a hook that does nothing makes them 1.4 times slower.

We found this while profiling irispy, which imports filelock at module level for one tar-extraction helper. Reading an
IRIS observation builds many gWCS objects, and gwcs and astropy.modeling deep-copy models. In py-spy,
`_audit_fork_safety` took 15% of a 160 s load, with about 85,000 calls for each file read. Importing filelock only in
that helper cut the read from 76.3 to 67.8 ms per file.

I understand what the hook guards. It turns a fork, or a subprocess, started from inside a thread's own lock-state
transition (from a signal handler, say) into an immediate `RuntimeError`. Since #747 it is skipped on CPython 3.10 and
3.11, where the at-fork callbacks still pin the lock state, and a child forked at the SQLite boundary exits with status
70 (the how-to, "Use shared read / exclusive write locks").

**Suggestion:** install the hook with the first lock instead of at import. As far as I can tell, there is no lock
state to guard before a lock is constructed: the only transitions before then are filelock's own registrations, at
import or when a lock class is defined. A program that imports filelock and never locks would pay nothing. One that
locks keeps the guard, from its first lock on. The lock constructors look like the place: the three lock metaclasses,
next to their `_ensure_current_process()` call, and `AsyncReadWriteLock.__init__`, which registers itself and enters a
transition before it builds its `ReadWriteLock`. A sketch against main (not run;
`test_import_adds_audit_hook_only_where_settrace_survives_it` asserts that `import filelock` adds the hook, so it
would need to make a lock first):

```diff
--- a/src/filelock/_api.py
+++ b/src/filelock/_api.py
@@ -374,6 +374,7 @@
     ) -> _T:
         _ensure_current_process()
         _resolve_lazy_imports_before_shutdown()
+        _install_fork_audit_hook()
         lifetime = _resolve_lifetime(lifetime, cls, stacklevel=cls._constructor_lifetime_warning_stacklevel)
         poll_interval = _resolve_poll_interval(poll_interval)
         # Validate before building the instance: a raise inside __init__ would leave a half-constructed object whose
@@ -1971,11 +1972,24 @@
                     getattr(module, attribute)
 
 
+_FORK_AUDIT_HOOK: Final[list[bool]] = []
+_FORK_AUDIT_HOOK_LOCK: Final = RLock()
+
+
+def _install_fork_audit_hook() -> None:
+    # With the first lock, not at import: an audit hook cannot be removed, and CPython calls it for every audit event,
+    # such as the builtins.id event of each id() call, which copy.deepcopy makes for each object it copies.
+    if _FORK_AUDIT_HOOK or _REGISTER_AT_FORK is None or not _SETTRACE_SURVIVES_AUDIT_HOOKS:
+        return
+    with _FORK_AUDIT_HOOK_LOCK:
+        if not _FORK_AUDIT_HOOK:
+            sys.addaudithook(_audit_fork_safety)
+            _FORK_AUDIT_HOOK.append(True)
+
+
 def _register_fork_hooks() -> None:
     if _REGISTER_AT_FORK is None:
         return  # pragma: lacks fork
-    if _SETTRACE_SURVIVES_AUDIT_HOOKS:  # pragma: needs fork  # pragma: needs settrace-safe-audit-hooks
-        sys.addaudithook(_audit_fork_safety)
     _REGISTER_AT_FORK(  # pragma: needs fork
         before=_pin_fork_objects,
         after_in_parent=_resume_parent_after_fork,
@@ -2256,6 +2270,7 @@
     "_ensure_current_process",
     "_fork_transition",
     "_grouped_errors",
+    "_install_fork_audit_hook",
     "_raise_body_and_release",
     "_raise_chained_errors",
     "_raise_cleanup_errors",
--- a/src/filelock/_async_read_write.py
+++ b/src/filelock/_async_read_write.py
@@ -18,6 +18,7 @@
     _append_exception_context,
     _ensure_current_process,
     _fork_transition,
+    _install_fork_audit_hook,
     _register_fork_object,
 )
 from filelock._async import (
@@ -79,6 +80,7 @@
         loop: asyncio.AbstractEventLoop | None = None,
         executor: futures.Executor | None = None,
     ) -> None:
+        _install_fork_audit_hook()
         creator_pid = os.getpid()
         self._creator_pid = creator_pid
         self._fork_invalidated = False
--- a/src/filelock/_read_write.py
+++ b/src/filelock/_read_write.py
@@ -35,6 +35,7 @@
     _canonical,
     _ensure_current_process,
     _fork_transition,
+    _install_fork_audit_hook,
     _raise_chained_errors,
     _register_fork_class,
     _register_fork_object,
@@ -394,6 +395,7 @@
     ) -> ReadWriteLock:
         _ensure_current_process()
         _resolve_lazy_imports_before_shutdown()
+        _install_fork_audit_hook()
         timeout = _seconds("timeout", timeout)
         if cls._instances_pid != _GETPID():
             cls._reset_class_after_fork()
--- a/src/filelock/_soft_rw/_sync.py
+++ b/src/filelock/_soft_rw/_sync.py
@@ -26,6 +26,7 @@
     _canonical,
     _check_timeout_max,
     _ensure_current_process,
+    _install_fork_audit_hook,
     _register_fork_class,
     _register_fork_object,
     _resolve_read_write_timeout,
@@ -64,6 +65,7 @@
         on_compromise: Callable[[LeaseCompromise], None] | None = None,
     ) -> SoftReadWriteLock:
         _ensure_current_process()
+        _install_fork_audit_hook()
         timeout = _seconds("timeout", timeout)
         # Passed through only when set, so a subclass that declares its own constructor without it keeps working.
         extra = {} if on_compromise is None else {"on_compromise": on_compromise}
```

If that does not fit, two other ways: an opt-out, such as an environment variable that skips the hook, or a hook
written in C (`PySys_AddAuditHook`), which costs much less per event but needs a compiled extension.

Python 3.13.16 (conda-forge) on Fedora Linux 44, filelock 4.2.4 from pip, numpy 2.5.4, astropy 8.0.2.

## Notes for the user (not to paste)

- The irispy figures are the perf360 REPORT's (py-spy: 15.1% of stock #360's load phase, overlapping other rows;
  85,000 hook calls per file and 76.3 → 67.8 ms per file from a4). They were not re-run here. The report says
  "160 s" for that load (160.8 s median).
- "No lock state to guard before a lock is constructed" is my reading of `_api.py`. The hook also raises on
  `os.fork` while another thread's fork is pinning (`fork_owner_depths`), which does not need a lock to exist, but
  there is nothing of filelock's to protect then. Drop the "As far as I can tell" sentence if you prefer not to make
  that claim.
- The sketch covers `FileLockMeta.__call__` (the async locks go through it), `_ReadWriteLockMeta.__call__`,
  `_SoftRWMeta.__call__` (`AsyncSoftReadWriteLock` builds its `SoftReadWriteLock` before anything else) and
  `AsyncReadWriteLock.__init__`: a plain class that calls `_register_fork_object(self)` and enters `_fork_transition()`
  before it builds its `ReadWriteLock` (`_async_read_write.py:89-91`). ruff 0.16.1 with filelock's config passes on
  the four edited files. filelock's tests were not run on it (the same refusal as main). From the source:
  `test_import_adds_audit_hook_only_where_settrace_survives_it` (`tests/test_fork_coordination.py:346`) asserts that
  `import filelock` adds a hook on CPython 3.12+ and PyPy, so it fails with the sketch until it makes a lock first.
  `test_audit_hook_survives_interpreter_shutdown` (`:362`) makes no lock, so it would pass without a hook to test. The
  tests that add a rejecting hook before the import make a lock, so they still take the rejection path.
