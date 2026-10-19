.. _glue_solar_dev_docs_manual_checks:

==============================
Manual checks of the quicklook
==============================

The tests run Qt offscreen and drive glue through its viewer states, Qt actions and matplotlib events
built in Python. This list covers what they cannot see: the screen's scaling, fonts and themes,
native menus, dialogs and settings, window management, and how glue responds at real event rates. Go
through it by hand on each operating system you can after a change to ``glue_solar/quicklook.py``,
``glue_solar/tools.py`` or the loaders, and after a new release of glue-core, glue-qt or Qt. Each
item says what to do and what you should see; report a failure by its number, together with the
record of item 1.

Before you start
----------------

1. Record the operating system and its version, the display scaling (100 %, 150 %, 200 % or a
   Retina display), whether the system appearance is light or dark, and the versions glue runs
   with::

       python -c "import platform, sys, qtpy; from importlib.metadata import version; print(platform.platform(), sys.version.split()[0], qtpy.API_NAME, qtpy.QT_VERSION, *(f'{p} {version(p)}' for p in ('glue-core', 'glue-qt', 'glue-solar', 'irispy-lmsal', 'matplotlib')))"

2. Find irispy's bundled test files with
   ``python -c "import irispy.data.test as t; print(t.ROOTDIR)"``; ``$T`` below stands for that
   folder. ``$T/sns`` holds the sit-and-stare raster of OBSID 3620258102 with its SJI 1330, 1400,
   2796 and 2832 files.

3. Download two files of `LM-SAL/irispy-data <https://github.com/LM-SAL/irispy-data/releases/tag/v1>`__
   into a new, empty folder, ``$D`` below, and leave them packed:
   ``iris_l2_20250328_225628_3400109360_cutout_raster.tar.gz``, a 64-step raster of Mg II k 2796
   with 13 million samples, and ``iris_l2_20130902_182935_4000005156_cutout_raster.tar.gz``, a
   full-size 64-step raster with C II 1336, Si IV 1403 and Mg II k 2796.

4. Go through "Clicks and drags" and "Readouts, labels and themes" once at 100 % scaling and once at
   200 %. Without a HiDPI screen, set the environment variable ``QT_SCALE_FACTOR=2`` before starting
   glue.

Starting glue
-------------

On macOS and Linux, start glue from a terminal as below. On Windows, where ``cmd`` and PowerShell do
not expand ``*`` for ``glue``, name the files one by one or start ``glue`` without files and use the
observation browser (item 6). glue may first suggest links between the loaded datasets in a dialog;
write down whether it does, and close it with either button.

5. Run ``glue --startup=iris_quicklook $T/sns/*.fits``. glue opens a tab with the quicklook of OBSID
   3620258102, its panels side by side without overlapping. SJI 1330, 1400 and 2796 keep their first
   frame under a gray veil, and their "Frame time" readouts are gray and end with "NO MATCH Δt = …".
   The terminal shows no traceback; write down any warning it prints, such as a font alias warning
   on macOS.

6. In a glue started without files, choose "Browse observations…" in the "Plugins" menu, on
   macOS in the menu bar at the top of the screen. The system's folder dialog opens, in your home
   folder the first time. Choose ``$T/sns``, tick OBSID 3620258102 and press "Load selected": the
   quicklook of item 5 opens in a new tab.

7. Quit glue, start it again and open the browser: the folder dialog opens in ``$T/sns``. Qt keeps
   the folder on macOS in ``~/Library/Preferences/com.glue-solar.glue-solar.plist``, on Linux in
   ``~/.config/glue-solar/glue-solar.conf`` and on Windows in the registry under
   ``HKEY_CURRENT_USER\Software\glue-solar\glue-solar``. To forget it on macOS, run
   ``defaults delete com.glue-solar.glue-solar``; deleting the file is not enough while macOS
   caches it.

Clicks and drags
----------------

8. On the map of item 5, click a pixel with the Pixel tool. The crosshair is on the pixel under the
   tip of the mouse pointer, not beside it.

9. Drag across the map, quickly and then slowly, and let go. The crosshair and the spectrum follow
   without a growing lag, and everything settles on the pixel where you let go.

Readouts, labels and themes
---------------------------

10. At the size the quicklook of item 5 gives each panel, its "Frame time" readout, for example
    "00:42:24 · exp … s · Δt +… s", shows in full in the status bar beside the position and
    value under the mouse, neither covering the other. Write down the narrowest panel at which it
    still fits.

11. Press "Hide axes" in the View menu of a panel of item 5. On the map and the wavelength panel, the
    exposure axis's label, "Exposure (acquisition order)" with the UTC range of the exposures on a
    second line, is inside the panel and clear of the tick labels.

12. Switch the system to the other appearance, light or dark (macOS: System Settings, Appearance;
    Windows: Settings, Personalization, Colors; Linux: the desktop's dark theme), start glue again
    and repeat items 5, 10 and 11. The gray veil, the gray NO MATCH text, the exposure label and the
    ticks stay readable in both.

Windows, tabs and shortcuts
---------------------------

13. In the quicklook of item 5, maximize the map with its window's maximize button: it fills the tab.
    Move its wavelength slider and restore it: it returns to its place, and the dashed lines of the
    wavelength and spectrum panels it covered mark the new wavelength. Minimize SJI 2832 and restore
    it. Choose "Gather Windows" in the "Canvas" menu: the viewers are placed side by side, and still
    follow the point.

14. With two screens, move glue's window to the other screen, ideally one with a different scaling,
    and back. The panels redraw sharp at each screen's scaling, and the click of item 8 still lands
    under the pointer.

15. Ctrl+N ("New Data Viewer"), Ctrl+T ("New Tab"), Ctrl+G ("Gather Windows") and Ctrl+R ("Rename
    Tab") work, with Cmd in place of Ctrl on macOS. Click SJI 1400 and press Backspace (⌫ on a Mac
    keyboard): glue asks "Do you want to close this window?", with "Cancel" as the default. Do not
    press Backspace in the data collection, which removes the selected datasets without asking.

Responsiveness
--------------

16. Open the browser on ``$D``, tick the "Extract …" entry of OBSID 3400109360 and press "Load
    selected", then tick the observation and press "Load selected". glue computes the spectrum of its
    13 million samples on a worker thread: click a new point on the map, and while the spectrum is
    computed, menus open and sliders move.

17. Extract OBSID 4000005156 the same way, tick its Mg II k 2796 and Si IV 1403 windows and press
    "Load selected". Drag Si IV 1403 from the data collection onto the map; in the map's "Plot
    Options" choose it as the reference data, set the axes back to the map's, and move the
    ``Wavelength`` slider to about 1402.8 Å. Choose "Set blink partner here" in the "Coordinate"
    menu's "Blink" submenu. Choose Mg II k 2796 again the same way, at about 2796.4 Å, zoom in with
    "Zoom" (Z) and click a point with the Pixel tool. Choose "0.25 s" under "Blink interval", then
    "Blink": the map alternates between the two windows four times a second without skipping or
    lagging, at the same zoom and with the crosshair in place. Choose "Blink" again to stop it.

18. In the quicklook of item 5, choose "Save frames or movie…" in the save menu of SJI 1400
    (the disk icon). Keep the range offered and save as ``sji.mp4`` where ffmpeg is installed, else
    as ``sji.gif``. The file plays every frame at 10 a second in a movie player or web browser.
