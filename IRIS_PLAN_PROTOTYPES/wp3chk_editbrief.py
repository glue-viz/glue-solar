p = "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad/briefs/wp3-sessions.md"
s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) >= 1, old[:80]
    s = s.replace(old, new, count)

# a. Save-failure UI claim (wrong in brief and in the audit verifier)
rep("""Docs: `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:61-66` says sessions "cannot currently be restored reliably". Understated: saving itself raises, nothing is written (glue-core `application_base.py:101-131` dumps first and only then opens the output file, so no partial `.glu` is left). glue-qt `_choose_save_session` (`glue_qt/app/application.py:1032-1062`) has no `@messagebox_on_error`; the traceback lands in the log widget (console button turns red), not a dialog.""",
"""Docs: `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:61-66` says sessions "cannot currently be restored reliably". Understated: saving itself raises, nothing is written (glue-core `application_base.py:101-131` dumps first and only then opens the output file, so no partial `.glu` is left). What the user sees (checker correction; the audit verifier and the first draft of this brief had it wrong): `Application.save_session` is wrapped in `@catch_error("Failed to save session")` (glue-core `application_base.py:100`, decorator at `:18-30`), which calls `GlueApplication.report_error` (`glue_qt/app/application.py:1303-1315`), a modal `QMessageBox.Critical` titled "Error" with the text "Failed to save session" plus the exception message and the traceback under "Show Details". glue-qt `_choose_save_session` (`glue_qt/app/application.py:1032-1062`) itself has no `@messagebox_on_error`, but it does not need one. Verified today (`wp3chk_dialog.py`, "Verified code" 9): `report_error called: 1`, message `Failed to save session | Don't know how to serialize <_GlueWCS ...>`, `file written: False`.""")

rep("""14. glue-qt's `_choose_save_session` has no error dialog; a save failure only reddens the console button. After WP3 nothing in glue-solar raises, but a foreign coords type would raise `GlueSerializeError("Cannot save a X in a session")` from `_wcs_record` into that log.""",
"""14. A save failure IS reported in a modal error box ("Failed to save session", `application_base.py:100` `@catch_error` -> `GlueApplication.report_error`, verified today), not only in the log widget; the earlier claim that only the console button reddens was wrong. After WP3 nothing in glue-solar raises, but a foreign coords type would raise `GlueSerializeError("Cannot save a X in a session")` from `_wcs_record` into that box, and no file is written.""")

# c. helpers.py unpack line numbers
rep("`load_data` unpacks a 1-element list to a bare `Data` (`helpers.py:296-298`), hence `as_list`.",
    "`load_data` unpacks a 1-element list to a bare `Data` (`helpers.py:314-316`), hence `as_list`.")
rep("12. `load_data` unpacks a 1-element result to a bare `Data` (`helpers.py:296-298`); use `glue.utils.as_list` in `finalize`.",
    "12. `load_data` unpacks a 1-element result to a bare `Data` (`helpers.py:314-316`); use `glue.utils.as_list` in `finalize`.")
# d. state.py:1030 -> 1033
rep("`_save_data_5` `except GlueSerializeError` -> `except Exception` (`state.py:1030`)",
    "`_save_data_5` `except GlueSerializeError` -> `except Exception` (`state.py:1033`)")
# e. 1058-1059 -> 1059-1060
rep("(glue-core behaviour, `state.py:1058-1059` does `result.meta.update(...)`)",
    "(glue-core behaviour, `state.py:1059-1060` does `result.meta.update(...)`)")
# f. application_base 156-163 -> 157-163
rep("glue chdirs to the session folder for save and restore (`application_base.py:120-127, 156-163`)",
    "glue chdirs to the session folder for save and restore (`application_base.py:120-127, 157-163`)")
# g. irispy 57-111 -> 56-111
rep("exactly irispy's construction (`irispy/io/spectrograph.py:57-111`:",
    "exactly irispy's construction (site-packages `irispy/io/spectrograph.py:56-111`, `_create_tabular_wcs`:")
# h. VersionedDict line
rep("`VersionedDict` cannot re-register version 1 (`state.py:222`)",
    "`VersionedDict` cannot re-register version 1 (`state.py:235-237`, `KeyError: Cannot overwrite version`)")

# i. wp3_roundtrip.py trailing crash annotation
rep("""("coords _GlueWCS(WCS)" for the SJI is `gwcs.wcs._wcs.WCS`, the class name collides with astropy's.) Records seen in the JSON:""",
"""("coords _GlueWCS(WCS)" for the SJI is `gwcs.wcs._wcs.WCS`, the class name collides with astropy's.) Checker note: re-run today reproduces every line above verbatim; after them the script's trailing "sunpy Map" section dies on its own print statement (`AttributeError: 'WCS' object has no attribute '_wcs'`, the report line assumes a `_GlueWCS` wrapper), which is a script bug, not an implementation failure. The sunpy Map round trip is covered by `wp3_map.py` (section 4) and by `test_sunpy_map_session_saves_and_keeps_colormap` (section 9). Records seen in the JSON:""")

# j. step 6 "not run" -> run in worktree
rep("""`load_data` only sets a label when the factory left it empty, so existing label assertions keep passing. This edit was not run (repo is read-only); every call it makes was run in `wp3_loadlog.py`.""",
"""`load_data` only sets a label when the factory left it empty (`helpers.py:293-294`), so existing label assertions keep passing. Checker: this exact edit (plus steps 1-5 and the test file of step 7) was applied to a throwaway worktree of `d3a2bd3` (`wp3chk_patch.py`) and the whole suite passed: 33 tests (27 existing + 6 new), see "Verified code" 9. The browser session of one SJI plus a 3-scan stack is 56 KB with relative paths.""")

# k/l. step 7 and imports ordering
rep("""7. Add `glue_solar/tests/test_sessions.py` (below). Run `.venv/bin/python -m pytest glue_solar -o addopts='' -q` with `QT_QPA_PLATFORM=offscreen`. `pytest.ini` has `filterwarnings = error`; the verified code emits no warnings on save or load (the "caught []" column in "Verified code" 3).""",
"""7. Add `glue_solar/tests/test_sessions.py` (below). Run `QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python -m pytest glue_solar -o addopts='' -q`. `pytest.ini` has `filterwarnings = error`; the verified code emits no warnings on save or load (the "caught []" column in "Verified code" 3; 33 passed today with that setting).
8. Run `pre-commit run --all-files` (ruff v0.16.1 with the isort rule `I` enabled in `.ruff.toml:17`; `ruff` is not installed in `.venv`, so the checker could not lint). Expect it to reorder the new imports; in `maps.py` drop the now-unused `from glue.core.visual import VisualAttributes` (F401).""")
rep("8. Update docs and changelog fragments (Docs section). Reword the two planning docs.",
    "9. Update docs and changelog fragments (Docs section). Reword the two planning docs.")

# Files to touch: sources/iris.py needs os + raster_data import; maps.py drop VisualAttributes import
rep("""- `glue_solar/sources/iris.py`: add `read_iris_rasters` next to `read_iris_file` (plain function, in `__all__`). `finalize` imports it lazily (`sources/iris.py` imports `loaders/iris.py`, so a module-level import would be circular).""",
"""- `glue_solar/sources/iris.py`: `import os`; extend the loaders import to `from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, last_directory, raster_data`; add `read_iris_rasters` next to `read_iris_file` (plain function, no decorator, in `__all__`; body = "Verified code" 2 with `L.raster_data` -> `raster_data`). `finalize` imports it lazily (`sources/iris.py` imports `loaders/iris.py`, so a module-level import would be circular).""")
rep("""- `glue_solar/sources/maps.py:30`: `from glue_solar.sources.loaders.iris import SolarVisualAttributes`; `result.style = SolarVisualAttributes(color="#FDB813", preferred_cmap=scan_map.cmap)`.""",
"""- `glue_solar/sources/maps.py:30`: `from glue_solar.sources.loaders.iris import SolarVisualAttributes` (replace the `from glue.core.visual import VisualAttributes` import at `maps.py:6`, otherwise unused); `result.style = SolarVisualAttributes(color="#FDB813", preferred_cmap=scan_map.cmap)`. No circular import: `glue_solar/__init__.py` imports `sources.iris` (which loads `loaders.iris`) before `sources.maps` (verified, suite passes).""")

# m. verified code 5 note on the 9-window case
rep("""raster file, all 9 windows: 9 dataset(s) | relative-paths session 249 KB (data embedded: 4455 KB) | biggest records [('_GlueWCS', 130787), ('Data', 97291)]
3 scans of C II 1336, stacked:""",
"""raster file, all 9 windows: 9 dataset(s) | relative-paths session 249 KB (data embedded: 4455 KB) | biggest records [('_GlueWCS', 130787), ('Data', 97291)]
   LoadLog record: {'factory': {'_type': 'types.FunctionType', 'function': 'wp3_impl.read_iris_rasters'}, 'kwargs': [[]], 'path': 'data/iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits'}
3 scans of C II 1336, stacked:""")

# n. scripts list
rep("""Scripts live in `/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad/` (`wp3_impl.py`, `wp3_stock.py`, `wp3_roundtrip.py`, `wp3_loadlog.py`, `wp3_style_trap.py`, `wp3_meta.py`, `wp3_map.py`, `wp3_stackdbg.py`). The repo was not modified (`git status`: only the two untracked planning docs).""",
"""Scripts live in `/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad/` (`wp3_impl.py`, `wp3_stock.py`, `wp3_roundtrip.py`, `wp3_loadlog.py`, `wp3_style_trap.py`, `wp3_meta.py`, `wp3_map.py`, `wp3_stackdbg.py`; checker additions `wp3chk_dialog.py`, `wp3chk_patch.py`, `wp3chk_editbrief.py`). The repo was not modified (`git status`: only the two untracked planning docs); the checker's full-suite run used a detached throwaway worktree of `d3a2bd3` under the scratchpad, removed afterwards. Sections 1-8 were re-run by the checker on 2026-09-02 and match the pasted output line for line (except the `wp3_roundtrip.py` tail, see the note in section 3).""")

# o. Add verified code 9
rep("""## Tests to add
""",
"""### 9. Checker run: the brief applied end to end in a throwaway worktree (`wp3chk_patch.py`, `wp3chk_dialog.py`)

`git -C /Users/nabil/Git/glue-solar worktree add --detach <scratch>/wt-wp3chk d3a2bd3`, then `wp3chk_patch.py` pasted "Verified code" 2 into `loaders/iris.py` / `sources/iris.py` / `maps.py` exactly as steps 1-6 say (including the `finalize` rewrite) and wrote `glue_solar/tests/test_sessions.py` as specified below. `git diff --stat`: `sources/iris.py +18 -1`, `loaders/iris.py +120 -9`, `maps.py +4 -2`.

```
$ cd <scratch>/wt-wp3chk && HOME=<scratch>/home-wp3chk QT_QPA_PLATFORM=offscreen MPLBACKEND=agg \\
    /Users/nabil/Git/glue-solar/.venv/bin/python -m pytest glue_solar -o addopts='' -q -p no:cacheprovider
.................................                                        [100%]
33 passed in 3.54s
```
(27 existing + 6 new; `filterwarnings = error` from `pytest.ini` active. First attempt failed only because the browser test ticked the raster observation's top-level row, which loads all 9 windows -> 10 datasets; tick the "C II 1336" child instead, as the test spec below now says.)

Browser dialog on a folder holding `..._3620258102_SJI_1400_t000.fits` plus the three `3860258481` `r00000..r00002` raster files, SJI row and the "C II 1336" child ticked, `stack` checked, `finalize()`, cwd = that folder:
```
datasets: ['SJI_1400-3620258102-2021-09-05T00:18:33', 'C_II_1336-3860258481-2014-03-29T14:09:38-stack'] | load_log: [True, True] | first_image: SJI_1400-3620258102-2021-09-05T00:18:33
relative-paths session: 56 KB
  LoadLog: iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits [[]] glue_solar.sources.iris.read_iris_file
  LoadLog: iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits [[['files', ['iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits', 'iris_l2_20140329_140938_3860258481_raster_t000_r00001.fits', 'iris_l2_20140329_140938_3860258481_raster_t000_r00002.fits']], ['windows', ['C II 1336']], ['stack', True]]] glue_solar.sources.iris.read_iris_rasters
reloaded: ['SJI_1400-3620258102-2021-09-05T00:18:33', 'C_II_1336-3860258481-2014-03-29T14:09:38-stack']
```

Save-failure UI on the unpatched branch (`wp3chk_dialog.py`: `GlueApplication()`, `image_data(SJI_1330)` appended, `app.report_error` stubbed, `app.save_session(path, include_data=False, absolute_paths=False)`):
```
report_error called: 1
message: Failed to save session | Don't know how to serialize <glue_solar.sources.loaders.iris._GlueWCS object at
file written: False
report_error uses QMessageBox: True
```

## Tests to add
""")

# k. test spec precision
rep("""def _assert_same_coords(original, restored):""",
"""def _real(files, name):
    return next(path for path in files if path.name == name)  # same helper as test_importer.py:28

def _style_record(s, label):
    # the style dict is inline in the Data record; find the Data record by label
    return next(rec for rec in json.loads(s).values() if isinstance(rec, dict) and rec.get("label") == label)["style"]

def _assert_same_coords(original, restored):""")
rep("""`assert restored.coords._wcs.wcs.ctype[1:] == ("HPLT-TAB", "HPLN-TAB")` (check the actual tuple form on astropy 8: it is a `list`-like, compare `list(...)`)""",
    """`assert list(restored.coords._wcs.wcs.ctype)[1:] == ["HPLT-TAB", "HPLN-TAB"]` (passes as written today)""")
rep("""`assert json.loads(s)` Data record's `style["_type"] == "glue_solar.sources.loaders.iris.SolarVisualAttributes"` and `"_protocol" not in style`.""",
    """`style = _style_record(s, original.label)`; `assert style["_type"] == "glue_solar.sources.loaders.iris.SolarVisualAttributes"` and `"_protocol" not in style`.""")
rep("""- `test_browser_datasets_reference_their_files(qtbot, tmp_path, irispy_test_files, monkeypatch)`: copy `iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits` and the three `3860258481` raster files `r00000..r00002` into `tmp_path`; `QtIRISImporter(tmp_path)`; tick both rows, `dialog.stack.setChecked(True)`, `dialog.finalize()`; `assert all(hasattr(d, "_load_log") for d in dialog.datasets)`; `monkeypatch.chdir(tmp_path)`; `s = GlueSerializer(DataCollection(dialog.datasets), include_data=False, absolute_paths=False).dumps()`; `assert len(s) < 200_000` (measured 22 KB + 32 KB); the LoadLog record for the stack has `kwargs == [[["files", [three basenames]], ["windows", ["C II 1336"]], ["stack", True]]]` and `path` without a directory component (relative to `tmp_path`); reload with `GlueUnSerializer.loads(s)` and compare the stack's science component and coords to the originals.""",
"""- `test_browser_datasets_reference_their_files(qtbot, tmp_path, irispy_test_files, monkeypatch)`: copy `iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits` and the three `3860258481` raster files `r00000..r00002` into `tmp_path`; `dialog = QtIRISImporter(tmp_path)`, `qtbot.addWidget(dialog)`. Two top-level rows appear (order not guaranteed): the SJI-only observation (`childCount() == 0`, tick the row itself) and the raster observation (tick ONLY the child whose `text(0).startswith("C II 1336")`; ticking the raster row loads all 9 windows and gives 10 datasets). `dialog.stack.setChecked(True)`, `dialog.finalize()`; `assert len(dialog.datasets) == 2`; `assert all(hasattr(d, "_load_log") for d in dialog.datasets)`; `monkeypatch.chdir(tmp_path)`; `s = GlueSerializer(DataCollection(dialog.datasets), include_data=False, absolute_paths=False).dumps()`; `assert len(s) < 200_000` (measured 56 KB); LoadLog records are the JSON values whose `_type` ends with `LoadLog`; the one with non-empty `kwargs` has `kwargs == [[["files", [three basenames]], ["windows", ["C II 1336"]], ["stack", True]]]`; every LoadLog `path` has no `/` (relative to `tmp_path`); reload with `GlueUnSerializer.loads(s).object("__main__")`, pick the dataset whose label ends with `-stack` on both sides, `np.array_equal(..., equal_nan=True)` on the science component and `_assert_same_coords`. Passed today as written.""")

# acceptance
rep("- [ ] Existing tests (27) still pass; `test_load_selected_real_sji`, `test_duplicate_real_raster_is_listed_and_loaded_once`, `test_reader_failure_stays_in_dialog` unchanged.",
    "- [ ] Existing tests (27) still pass; `test_load_selected_real_sji`, `test_duplicate_real_raster_is_listed_and_loaded_once`, `test_reader_failure_stays_in_dialog` unchanged (checker: 33 passed in the worktree with the brief applied verbatim).\n- [ ] `pre-commit run --all-files` clean (ruff isort ordering of the new imports, unused `VisualAttributes` import removed from `maps.py`).")

open(p, "w").write(s)
print("brief edited")
