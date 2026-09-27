"""Regenerate IRIS_CRISPEX_FEATURES.md from the plan and the review data.

Run from the glue-solar root in a micromamba env:
    ~/mamba/envs/iris-plan/bin/python IRIS_PLAN_PROTOTYPES/review_20260927/gen_features_map.py IRIS_CRISPEX_FEATURES.md
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

S = Path(__file__).parent
plan = S.parent.parent / "IRIS_GLUE_GAP_PLAN.md"
feat = json.load(open(S / "features.json"))
work = json.load(open(S / "work.json"))
drafts = json.load(open(S / "restructure-drafts" / "result3.json"))

box = re.compile(r"^- \[ \] \*\*(M\d)\*\* `([^`]+)`", re.M)
fidmap = {}
full = plan.read_text()
sections = re.split(r"^### (WP\d+):", full, flags=re.M)
for wp, text in zip(sections[1::2], sections[2::2]):
    text = text.split("\n## ", 1)[0]
    starts = [(m.start(), m.group(1), m.group(2)) for m in box.finditer(text)]
    for i, (pos, ms, key) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        chunk = text[pos:end]
        fm = re.search(r"Features:\s*([^\n]*?)(?:\.\s*(?:Findings|Depends)|\n|$)", chunk)
        if not fm:
            continue
        for fid in re.findall(r"F\d{3}", fm.group(1)):
            fidmap.setdefault(fid, []).append((wp, ms, key))

done = {d["fid"]: d["how"] for d in work["done"]}
for w in drafts:
    for m in w["final"]["fid_map"]:
        if m["key"] == "already-done" and m["fid"] not in done:
            done[m["fid"]] = m["note"]

STALE = {
    "wp9-temporal-docs": "wp9-m0-viewer-tools-docs",
    "wp9-browser-export-overlay-docs": "wp9-m0-browsing-recipes",
    "wp9-m0-inspection-scripting-docs": "wp9-m0-scripting-recipe",
    "wp9-display-window-basics": "wp9-m0-viewer-tools-docs",
    "wp9-m0-existing-workflow-recipes": "wp9-m0-workflow-recipes",
    "wp11-iris-display-defaults": "wp11-raster-cmap",
    "wp12-m3-path-extras": "wp12-path-overlays-slopes",
}
for fid, how in list(done.items()):
    if fid == "F124":
        how = how.replace("wp9-browser-export-overlay-docs", "wp9-m0-mask-overlays")
    for old, new in STALE.items():
        how = how.replace(old, new)
    done[fid] = how

# Verified note corrections (review issues 47-51); they win over any row's note.
NOTE_OVERRIDES = {
    "F177": "The Preferences dialog (colours, theme, font) loads plugin panes from the "
            "preference_panes registry (glue_qt/config.py:218@0.4.2). IRIS display defaults are "
            "per dataset (wp11-raster-cmap). Browser search settings persist in QSettings beside "
            "iris/last_dir (wp8-search-ui, wp8-browser-conveniences, M3). No Preferences pane is planned.",
    "F085": "Image-viewer slice sliders (Profile sliders arrive with Qt #70) have "
            "first/prev/back/stop/forward/next/last buttons driven by a QTimer "
            "(glue_qt/viewers/common/data_slice_widget.py:81-83,146-193 at glue-qt 0.4.2). The interval "
            "is round(500/|n|) ms, speeding up with repeated presses, and playback wraps. A focused "
            "slider steps with the arrow keys. Playback docs are in wp9-m0-browsing-recipes; the "
            "Tab/Backspace limits are in wp9-m0-viewer-tools-docs. CRISPEX-style frame shortcuts belong "
            "to the WP11 keyboard item (F197).",
    "F121": "The browser lists each observation's SJI channels as checkboxes (loaders/iris.py:240,262-267), "
            "and loaded channels open from the data collection. wp4-sji-panels makes the preset open every "
            "selected channel. Thumbnails are deliberately not built, per the plan's 'No IDL clone' non-goal.",
    "F144": "The default raster view is the wavelength × slit spectrogram, and the step slider (with "
            "playback) moves through each raster position's panel. A per-position panel grid falls under "
            "the plan's 'No IDL clone' non-goal; wp9-m0-workflow-recipes explains that iris_xraster's "
            "'Spectroheliogram' is the per-position spectrogram.",
    "F180": "In any viewer, use toolbar Save → 'Save plot to file' (mpl:save → matplotlib save_figure, "
            "glue_qt/viewers/matplotlib/toolbar.py:66-75@0.4.2). A probe in the iris-plan env found these "
            "Agg file types: avif, eps, gif, jpeg, jpg, pdf, pgf, png, ps, raw, rgba, svg, svgz, tif, tiff, "
            "webp. Docs item wp9-m0-browsing-recipes documents this; the plan's 'No IDL clone' non-goal "
            "excludes only the IDL PostScript-device workflow.",
    "F092": "Load a raster (default view wavelength × slit, the spectrogram) and press play on its "
            "step/exposure slider (data_slice_widget.py playback). Documented in wp9-m0-browsing-recipes "
            "(playback) and wp9-m0-workflow-recipes (spectrogram axes); movie export is the WP12 movie "
            "item (F178/F179).",
    "F032": "Data collection → 'Arithmetic attributes' (ArithmeticEditorWidget, "
            "glue_qt/app/application.py:423,487@0.4.2) defines a scaled derived component, e.g. "
            "`<window> * 2.5`. Documented in wp9-m0-browsing-recipes ('Arithmetic scaling').",
    "F105": "The IRIS browser lists every SJI (keyed by TDESC1) and aligned AIA cutout of an observation, "
            "with no channel limit (glue_solar/sources/loaders/scan.py:164-165,174-175; "
            "loaders/iris.py:121-125,240-242 at 236f0a8). Each loads as a Data with an irissji/sdoaia "
            "colormap and can be opened from the data collection. Multi-SJI coordination is wp4-sji-panels "
            "and wp4-time-sync; docs are in wp9-m0-browsing-recipes.",
    "F128": "Each viewer's layer style editor sets colour, alpha and linewidth per layer. Preferences sets "
            "foreground and background, the default data colour and alpha, and the font size (glue-qt "
            "app/preferences.py). Docs item: wp9-m0-browsing-recipes (style editor and Preferences bullet).",
    "F070": "Separate Image viewers of one raster keep independent wavelength sliders. For the lock, Profile "
            "Options → Navigate moves the wavelength slice of every open Image viewer showing that dataset "
            "together (glue_qt/viewers/profile/profile_tools.py:140-161 @ glue-qt 0.4.2, iris-plan env). "
            "Caveat: on 0.4.2, Navigate lands on the wrong slice when the display unit is not the native one "
            "('slice 28, expected 20' in review_20260927/feas.json, spectral-marker entry). WP1's native Å "
            "or Qt #70 fixes this. Documented by wp9-m0-workflow-recipes.",
    "F031": "SPECTFILE: the mean-spectrum reference is a full-dataset Profile with function Mean "
            "(glue's default is Maximum)",
}

rows = defaultdict(list)
problems = []
for f in feat:
    fid = f["fid"]
    if f["scope"] == "excluded":
        where, ms = "Excluded", "—"
        note = f["scope_note"]
    elif fid in fidmap:
        entries = fidmap[fid]
        if len(entries) > 1:
            problems.append(f"{fid} in several checkboxes: {entries}")
        ms = min(e[1] for e in entries)
        where = "; ".join(f"`{key}` ({wp}, {m})" for wp, m, key in entries)
        note = f["scope_note"] if f["scope"] == "covered_by_equivalent" else ""
    elif fid in done:
        where, ms = "Available today", "—"
        note = done[fid]
    else:
        where, ms, note = "UNMAPPED", "—", ""
        problems.append(f"{fid} unmapped")
    note = NOTE_OVERRIDES.get(fid, note)
    rows[f["category"]].append((fid, f["name"], "yes" if f["iris_relevant"] else "no",
                                f["priority"], ms, where, note))

esc = lambda s: " ".join(str(s).replace("|", "\\|").split())
out = [
    "# CRISPEX and IRIS-SolarSoft feature map",
    "",
    "Companion to [IRIS_GLUE_GAP_PLAN.md](IRIS_GLUE_GAP_PLAN.md), generated on 2026-09-27 from the",
    "plan's checkboxes and the verified review in",
    "[IRIS_PLAN_PROTOTYPES/review_20260927/](IRIS_PLAN_PROTOTYPES/review_20260927/README.md).",
    "Each of the 203 features from CRISPEX and the IRIS SolarSoft quicklook tools maps to one or more plan",
    "checkboxes, to 'Available today' (with how to do it in Glue), or to an exclusion. The source",
    "citations and Glue evidence for every row are in `review_20260927/features.json`. Regenerate",
    "this file when checkbox keys or feature lists change; the plan is authoritative.",
    "",
    "Columns: IRIS = relevant to IRIS data; Priority = review priority for an IRIS-first CRISPEX",
    "quicklook (must/should/could/wont); Milestone and Where = the owning checkbox.",
    "",
]
counts = defaultdict(int)
for cat, rs in rows.items():
    out += [f"## {cat}", "", "| ID | Feature | IRIS | Priority | Milestone | Where | Note |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rs:
        out.append("| " + " | ".join(esc(x) for x in r) + " |")
        counts[r[4] if r[4] != "—" else r[5].split()[0]] += 1
    out.append("")
summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
out.insert(13, f"Summary: {summary}.")
out.insert(14, "")
Path(sys.argv[1]).write_text("\n".join(out) + "\n")
print(summary)
print("\n".join(problems) or "no problems")
