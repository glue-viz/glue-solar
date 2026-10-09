.. _glue_solar_dev_docs_manual_checks:

==============================
Manual checks of the quicklook
==============================

The tests run Qt offscreen and drive glue through its viewer states, Qt actions and matplotlib events
built in Python, so they cannot see what a person at a real screen sees: the mouse and keys at real
event rates, timers, native menus and dialogs, fonts, themes, window management and how responsive
the window stays. This list covers those. Go through it by hand on each operating system you can
after a change to ``glue_solar/quicklook.py``, ``glue_solar/tools.py`` or the loaders, and after a
new release of glue-core, glue-qt or Qt. Each item says what to do and what you should see; report a
failure by its number, together with the record of item 1.

Before you start
----------------

1. Record the operating system and its version, the display scaling (100 %, 150 %, 200 % or a
   Retina display), whether the system appearance is light or dark, and the versions glue runs
   with::

       python -c "import platform, sys, qtpy; from importlib.metadata import version; print(platform.platform(), sys.version.split()[0], qtpy.API_NAME, qtpy.QT_VERSION, *(f'{p} {version(p)}' for p in ('glue-core', 'glue-qt', 'glue-solar', 'irispy-lmsal', 'matplotlib')))"

2. Find irispy's bundled test files with
   ``python -c "import irispy.data.test as t; print(t.ROOTDIR)"``; ``$T`` below stands for that
   folder. ``$T/sns`` holds the sit-and-stare raster of OBSID 3620258102 with its SJI 1330, 1400,
   2796 and 2832 files, and ``$T/raster/iris_l2_20140329_140938_3860258481_raster`` holds 3 scans
   of the 8-step raster of OBSID 3860258481, without slit-jaw images.

3. Download two files of `LM-SAL/irispy-data <https://github.com/LM-SAL/irispy-data/releases/tag/v1>`__
   into a new, empty folder, ``$D`` below, and leave the archive packed:
   ``iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz``, a 64-step raster with a negative
   raster step (Mg II k 2796 only, 13 million samples), and
   ``iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz``, 50 full-size SJI 1400 frames.

4. Go through "Clicks and drags" and "Readouts, labels and themes" once at 100 % scaling and once at
   200 %. Without a HiDPI screen, set the environment variable ``QT_SCALE_FACTOR=2`` before starting
   glue.

Starting glue
-------------

On macOS and Linux, start glue from a terminal as below. On Windows, where ``cmd`` and PowerShell do
not expand ``*`` for ``glue``, name the files one by one or start ``glue`` without files and use the
observation browser (item 9). glue may first suggest links between the loaded datasets in a dialog;
write down whether it does, and close it with either button.

5. Run ``glue --startup=iris_quicklook $T/sns/*.fits``. glue opens a tab with the quicklook of OBSID
   3620258102: the map (slit against time), the spectrogram and wavelength against time in the top
   row, and the SJI 1330, 1400, 2796 and 2832 viewers and the spectrum panel in the bottom row, side
   by side without overlapping. The Pixel tool is active on the map, the point is at its centre and
   the spectrum panel shows its spectrum. The fixture's slit-jaw frames are minutes apart, and SJI
   1330, 1400 and 2796 have none within half their cadence of the centre exposure: these three keep
   their first frame under a grey veil, and their "Frame time" readouts are grey and end with
   "NO MATCH Δt = …"; SJI 2832 shows its nearest frame. The terminal shows no traceback; write down
   any warning it prints, such as a font alias warning on macOS.

6. Run ``glue --startup=iris_quicklook $T/raster/iris_l2_20140329_140938_3860258481_raster/*.fits``.
   The 3 files load one by one and the quicklook shows the first scan: the map (step against slit),
   the spectrogram, wavelength against step and the spectrum panel, with no slit-jaw viewer. The
   status bar ends with "Only the first raster file is shown: stacks of scans need Plugins → IRIS:
   browse observations…".

7. Run ``glue`` without files. The "Plugins" menu, on macOS in the menu bar at the top of the screen,
   has "IRIS: browse observations…", "IRIS: link helioprojective coordinates" and "IRIS:
   quicklook…". "IRIS: quicklook…" says "No IRIS observation is loaded."

8. Run ``glue $T/sns/*.fits $T/raster/iris_l2_20140329_140938_3860258481_raster/*_r00000_test.fits``
   and choose "IRIS: quicklook…" in the "Plugins" menu. A dialog asks for the "Observation:" and
   lists both OBSIDs with their start times. "Cancel" opens nothing; "OK" opens the chosen
   observation's quicklook in a new tab. Choose OBSID 3620258102 twice, for two quicklook tabs of it.

Observation browser and dialogs
-------------------------------

9. In a glue started without files, choose "IRIS: browse observations…" in the "Plugins" menu. The
   system's folder dialog opens, in your home folder the first time. Choose ``$T/sns``. The browser
   lists OBSID 3620258102 with 5 files; expanded, it shows ``SJI_1330``, ``SJI_1400``, ``SJI_2796``
   and ``SJI_2832`` and one entry per raster window. Tick the observation and press "Load selected":
   a progress bar runs, and the quicklook of item 5 opens in a new tab.

10. Quit glue, start it again and open the browser: the folder dialog opens in ``$T/sns``. Qt keeps
    the folder on macOS in ``~/Library/Preferences/com.glue-solar.glue-solar.plist``, on Linux in
    ``~/.config/glue-solar/glue-solar.conf`` and on Windows in the registry under
    ``HKEY_CURRENT_USER\Software\glue-solar\glue-solar``. To forget it on macOS, run
    ``defaults delete com.glue-solar.glue-solar``; deleting the file is not enough while macOS
    caches it.

11. Open the browser on ``$D``. The "Files" column of the row of OBSID 3400109360 reads "0 — Extract
    iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz (9 MB, next to the archive)". Tick that
    row and press "Load selected": the progress bar ends with "Extracted 1 archive(s) — now tick
    what to load", the row now reads "1 — Mg II k 2796 — 1 raster file(s)", nothing is loaded and the
    archive is still in ``$D``. Tick the row and press "Load selected": its quicklook opens.

12. Open the browser on ``$T/raster/iris_l2_20140329_140938_3860258481_raster``, tick one raster
    window of OBSID 3860258481, tick "Stack sequential raster scans" and press "Load selected". The
    quicklook shows the stack: the map of the current scan, with a ``Scan`` slider, the spectrogram
    and wavelength against scan.

Clicks and drags
----------------

13. On the map of item 6, click a pixel with the Pixel tool. The crosshair is on the pixel under the
    tip of the mouse pointer, not beside it. The spectrum panel shows that pixel's spectrum, and the
    spectrogram and the wavelength panel move to it and highlight its row.

14. Drag across the map, quickly and then slowly, and let go. The crosshair and the spectrum follow
    without a growing lag, and everything settles on the pixel where you let go.

15. Choose the Pixel tool of the spectrogram and click it, then do the same on the wavelength panel.
    The point moves to the clicked pixel and the map to the clicked wavelength; no other wavelength
    slider moves.

16. In the quicklook of item 5, choose the Pixel tool of SJI 1400 and click its image. The point is
    marked only there, and the spectrum panel is empty until the next click on a raster panel.

Sliders and playback
--------------------

The sliders of the active viewer are in "Plot Options" on the left of glue's window, below the data
collection and the plot layers.

17. Run ``glue --startup=iris_quicklook $D/iris_l2_20130902_163935_4000255147_SJI_1400_t000_f050.fits.gz``
    and drag the ``Time (Utc)`` slider quickly back and forth over the 50 frames. The image changes
    at most about ten times a second while you drag, rather than at every frame, and shows the
    slider's frame once you let go. Do the same with the ``Wavelength`` slider of the map of item 11.

18. Click a slider's handle and press the left and right arrow keys: each press steps one slice and
    the image follows at once. Click the slider's track beside the handle: the handle moves towards
    the click and the image follows at once.

19. In the quicklook of item 5, click the map with its Pixel tool, then make the spectrogram active
    and press "Play forwards" under its exposure slider. The exposures advance about twice a second;
    each slit-jaw viewer follows to its frame nearest the exposure's time, its "Frame time" readout
    gives the offset (Δt) or NO MATCH, and its dashed slit and red cross move with the frame. Press
    "Play forwards" again: playback runs twice as fast. Press "Stop the playback".

20. Choose "Time master" in the "Coordinate" menu of SJI 1330 and play its ``Time (Utc)`` slider.
    The spectrogram's exposure follows each frame, and the other slit-jaw viewers follow or grey out
    with NO MATCH. While it plays, close the SJI 1330 viewer with its window's close button, and
    confirm if asked. Playback stops and the terminal shows no traceback. Click the map: the raster
    is the time master again, and the raster panels' "Frame time" readouts say "time master".

Coordinate menu and mouse mode
------------------------------

21. On the map of item 6, with the Pixel tool active, click the toolbar button labelled "Coordinate"
    and choose "Time master", then click it again and choose "Clear point". The menu opens under the
    button as soon as you press it, and closes after the choice. After each entry the Pixel button
    is still pressed, and the next click on the map moves the point without choosing Pixel again.
    "Clear point" removes the crosshair and empties the spectrum panel.

22. On the same map, with the Pixel tool active, press "Hide axes", "Frame time" and "Cursor
    readout", each twice, and click the map after each. The Pixel button stays pressed and each click
    moves the point, although glue-qt switches the mouse mode off for any plain toolbar button.

Readouts, labels and themes
---------------------------

23. In the quicklook of item 5, move the spectrogram's exposure slider to 1, then the ``Time (Utc)``
    slider of SJI 1400 to 40. SJI 1400 is covered by a grey veil, and its "Frame time" readout, in
    grey, ends with "NO MATCH Δt = …". Click the map near its left edge (an exposure below 20): SJI
    1400 moves to a matching frame and the veil goes. A click on one of the few exposures with no SJI
    1400 frame within half its cadence, such as the map's centre, leaves it greyed with NO MATCH.

24. At the size the quicklook gives each panel, its "Frame time" readout, for example
    "2021-09-05T… UTC · exp … s · Δt +… s", shows in full in the status bar beside the position and
    value under the mouse, neither covering the other. Write down the narrowest panel at which it
    still fits.

25. On the map and the wavelength panel of item 5, the exposure axis is labelled "Exposure
    (acquisition order)", with the UTC range of the exposures on a second line, and its ticks are
    whole exposure numbers. Both lines are inside the panel and clear of the tick labels.

26. Switch the system to the other appearance, light or dark (macOS: System Settings, Appearance;
    Windows: Settings, Personalization, Colors; Linux: the desktop's dark theme), start glue again
    and repeat items 23 and 25. The grey veil, the grey NO MATCH text, the exposure label and the
    ticks stay readable in both.

27. Press "Hide axes" on the map of item 5. The ticks, tick labels, axis labels and frame disappear,
    and the Pixel tool stays on. Move the mouse over the image: the status bar gives the same world
    position and value as with the axes shown. Zoom with "Zoom" (Z) and resize the panel, then move
    the mouse again: the first readout after each is already in world coordinates. Press "Hide
    axes" again: the axes come back, with the exposure label.

28. Press "Physical aspect" on the map of item 11, whose 1″ raster steps are three times as wide as
    its 0.33″ slit pixels. The map narrows to its field's proportions on the sky, and the Pixel tool
    stays on. With a screenshot tool, measure the distance between two longitude ticks 10″ apart and
    between two latitude ticks 10″ apart: they agree within 5 %. Resize the panel and zoom with "Zoom"
    (Z), and measure again. Press "Physical aspect" again: the map fills the panel again.

Windows, tabs and shortcuts
---------------------------

29. In the quicklook of item 5 no panel overlaps another or reaches past the tab. Maximise the map
    with its window's maximise button: it fills the tab; restore it: it returns to its place.
    Minimise SJI 2832 and restore it. Choose "Gather Windows" in the "Canvas" menu: the viewers are
    placed side by side, and still follow the point.

30. With two screens, move glue's window to the other screen, ideally one with a different scaling,
    and back. The panels redraw sharp at each screen's scaling, and the click of item 13 still lands
    under the pointer.

31. In the two quicklook tabs of item 8, click the map of the second tab: only that tab's panels
    move. Click the first tab's label to show it, and click its map: its own point moves, and the
    second tab's point is still where you left it.

32. Ctrl+N ("New Data Viewer"), Ctrl+T ("New Tab"), Ctrl+G ("Gather Windows") and Ctrl+R ("Rename
    Tab") work, with Cmd in place of Ctrl on macOS. Click SJI 1400 and press Backspace (⌫ on a Mac
    keyboard): glue asks "Do you want to close this window?", with "Cancel" as the default; so does
    Backspace on the map, the spectrogram or the wavelength panel. Do not press Backspace in the data
    collection, which removes the selected datasets without asking. Click the map and press F, then D:
    the raster's exposure, the point and the slit-jaw viewers move as with the spectrogram's exposure
    slider, and no empty window appears. Click SJI 2832 and press S, then A: only the map's wavelength
    moves, and no save dialog opens. Press Space: the exposures play; press it again: they stop.

33. Close a quicklook tab with its tab's close button. glue asks "Are you sure you want to close this
    tab?", with "Cancel" as the default. "Cancel" keeps the tab; "OK" closes it without a traceback,
    and the quicklook in the other tab still follows its point.

Responsiveness
--------------

34. In the quicklook of item 11, whose raster has 13 million samples, glue computes the spectrum on a
    worker thread. Once the first spectrum is computed, the spectrum panel shows it, scaled to fit.
    Click a new point on the map: while the spectrum is computed, menus open and sliders move.

35. Download ``iris_l2_20130902_182935_4000005156_cutout_raster.tar.gz`` from the release of item 3
    into ``$D``: a full-size 64-step raster with C II 1336, Si IV 1403 and Mg II k 2796. Open the
    browser on ``$D``, extract it as in item 11, tick its Mg II k 2796 and Si IV 1403 windows and
    press "Load selected". Drag Si IV 1403 from the data collection onto the map; in the map's "Plot
    Options" choose it as the reference data, set the axes back to the map's, and move the
    ``Wavelength`` slider to about 1402.8 Å. Choose "Set blink partner here" in the "Coordinate"
    menu. Choose Mg II k 2796 again the same way, at about 2796.4 Å, zoom in with "Zoom" (Z) and
    click a point with the Pixel tool. Choose "0.25 s" under "Blink interval", then "Blink": the map
    alternates between the two windows four times a second without skipping or lagging, at the same
    zoom and with the crosshair in place; the other panels' sliders and the Pixel button stay, and
    "Blink" shows a check mark. Choose "Blink" again: the blink stops and both windows are ticked in
    the layer list. Start it again and close the map while it blinks: the terminal shows no
    traceback.

36. In the quicklook of item 5, make SJI 1400 the time master and choose "Save frames or movie…" in
    its save menu (the floppy-disk button). Keep the whole range offered and save as ``sji.mp4``
    where ffmpeg is installed, else as ``sji.gif``. A progress dialog counts the frames while the
    image, its slit and red cross and the spectrogram step through them; the file plays every frame
    at 10 a second in a movie player or web browser. Save again as ``sji.png`` and press "Cancel"
    halfway: the dialog closes within a frame, the folder holds the PNG frames saved until then, and
    the viewer is back on the frame it showed.

37. In the quicklook of item 5, drag SJI 2796 from the data collection onto the SJI 1400 viewer; in
    its "Plot Options" choose SJI 2796 as the reference data, set the axes back to the image's and
    choose "Set blink partner here", then choose SJI 1400 again the same way and "Frame time" in the
    View menu. Choose "Blink", then press Space: while the raster plays, the viewer alternates
    between the two channels without skipping, each keeping its own colour limits, the "Frame time"
    readout gives each a time within 139 s (half its cadence) of the raster's or NO MATCH, and the
    red cross stays on the same feature in both. Press Space and choose "Blink" again: playback and
    the blink stop, and both channels are ticked in the layer list.
