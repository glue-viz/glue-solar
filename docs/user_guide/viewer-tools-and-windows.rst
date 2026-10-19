.. _glue_solar_users_guide_viewer_tools_and_windows:

============
Viewer tools
============

glue's `getting started guide <http://docs.glueviz.org/en/stable/getting_started/index.html>`__
describes its viewers and tools, such as "Home" (:kbd:`H`), "Pan" (:kbd:`M`), "Zoom" (:kbd:`Z`) and
the region tools "Rectangular ROI" (:kbd:`R`), "X range" (:kbd:`X`), "Y range" (:kbd:`Y`), "Circular
ROI" (:kbd:`C`) and "Polygonal ROI" (:kbd:`G`). A button's tooltip gives its key.

glue-solar adds a button and three menus to each Image viewer's toolbar, after "Zoom": "Follow/lock",
the pencil (mouse modes), the link icon (the Coordinate menu) and the gear (the View menu). A menu
shows only the entries that can act on the viewer's data, with a check by those that are on. A narrow
viewer moves the last buttons behind the toolbar's » button.

Image viewer
------------

.. list-table::
   :header-rows: 1
   :widths: 30 60 10

   * - Entry
     - What it does
     - Key
   * - "Pixel", glue's
     - Click or drag to move the point (see :ref:`Quicklook <glue_solar_users_guide_iris_quicklook>`).
     -
   * - "Follow/lock"
     - The point follows the mouse, as CRISPEX's cursor does; a left click locks it, a right click
       unlocks it.
     - Esc
   * - Pencil → "Measure"
     - Drag a line: the status bar gives its length in pixels, arcsec and km, in the plane of the sky.
     - U
   * - Pencil → "Path diagram"
     - Click a path and press Enter for the data along it (see `Path diagrams`_).
     - L
   * - Pencil → "Show position on original path"
     - In a diagram's viewer, drag to mark the path under the mouse and move the original viewer's
       sliders there.
     -
   * - Pencil → "Slope"
     - In a diagram of frames or exposures against the path, click points along a track and press
       Enter: the speed in km / s, and the acceleration from three times, as a row of the diagram's
       table.
     - Enter, Esc
   * - Pencil → "Save path as ECSV…", "Open path from ECSV…", "Path on other data…"
     - Save, reopen and reuse a path (see `Path diagrams`_).
     -
   * - Coordinate → "Lead the time"
     - Make this dataset's time the one the others follow.
     -
   * - Coordinate → "Go to UTC…"
     - Move the dataset that leads the time to its frame nearest a typed time.
     -
   * - Coordinate → "Loop…"
     - Play a range of the first slider, every Nth index, or back and forth.
     -
   * - Coordinate → Point → "Clear point"
     - Remove the point until the next click.
     -
   * - Coordinate → Point → "Light curves at the point", "Row at the point", "Column at the point"
     - Plot the data through the point (see :ref:`Quicklook <glue_solar_users_guide_iris_quicklook>`).
     -
   * - Coordinate → Blink → "Set blink partner here", "Blink", "Blink interval"
     - Alternate the viewer between two positions.
     -
   * - View → "Frame time"
     - Show the time of day of the frame shown under the image, and its offset from the leading
       dataset's time.
     -
   * - View → "Hide axes"
     - Hide or show the axes; on a quicklook panel, on all its panels.
     -
   * - View → "Per-frame limits"
     - Take the color limits from each slice shown rather than the whole cube.
     -
   * - View → "Wavelength band…"
     - Map the mean of 5, 9 or 15 wavelength pixels about the slider's wavelength. The band follows
       the slider.
     -
   * - View → "Physical aspect"
     - Show the image in its proportions on the sky: a raster with 2″ steps shows each 12 times as
       wide as its 0.17″ slit pixels.
     -
   * - View → "Color bar"
     - Show a color bar right of the image.
     -
   * - View → "Raster overlays"
     - Draw the raster's slit positions on the slit-jaw images, and the step at the synced time on the
       maps.
     -
   * - View → "Cursor readout"
     - Show the position, time, exposure time and value under the mouse in the status bar, with the
       Doppler velocity on a window with a rest wavelength.
     - W
   * - The spectrum icon
     - Open a Profile viewer of the image's data.
     -
   * - Save → "Save frames or movie…"
     - Save the image at each index of a slider as PNG files or a movie (see :ref:`Saving frames or a
       movie <glue_solar_users_guide_iris_save_frames>`).
     -
   * - Layer stretch → "Gamma 0.4", "Gamma 0.75", "Gamma 1.5", "Gamma 2.2"
     - Raise the values between the limits to that power: below 1 brightens faint emission.
     -

Profile viewer
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Entry
     - What it does
   * - "IRIS lines"
     - Mark the main IRIS lines in the plotted wavelength range.
   * - "Lines in this range…"
     - List the lines of irispy's line catalog in the Fit or Collapse range, else in the plotted
       range, strongest first for the quiet Sun, an active region or a flare at coronal or
       photospheric abundances, and those with no predicted strength last. Clicking one marks it
       beside the main lines.
   * - "Velocity axis"
     - Add a top axis of :ref:`Doppler velocity <glue_solar_users_guide_iris_velocity>` from the
       window's rest wavelength.
   * - "Show this window's panels"
     - In a quicklook, on another window's spectrum panel: make it the main window.
   * - Save → "Save profiles as ECSV…"
     - Write the profiles shown to one table (see :ref:`Saving the profiles
       <glue_solar_users_guide_iris_save_profiles>`).

Path diagrams
-------------

Choose "Path diagram" (:kbd:`L`), glue-solar's path tool in place of glue's "Slice Extraction", click
the path's vertices on the image and press :kbd:`Enter`; :kbd:`Esc` clears the path. Each dataset
shown gets a new dataset of its values along the path, each sample the value of the nearest pixel,
and the image's opens in a new viewer with the path along x:

- a slit-jaw image gives its frames against the path, a distance-time diagram;
- a raster window gives its wavelengths against the path;
- a stack gives its wavelengths against the path, with a scan slider.

Other datasets shown, such as a raster window over a slit-jaw image, are sampled at the same places
on the Sun, and their diagrams go to the data collection. Closing the viewer the path was drawn in
closes its diagrams.

- **Save path as ECSV…** writes a diagram's path, a row a sample: the pixels, the longitude and
  latitude in arcsec, and the distance along the path in arcsec and km. **Open path from ECSV…** makes
  the same diagrams from it.
- **Path on other data…** places the path, by its longitude and latitude, on the datasets you tick,
  such as the other windows and the slit-jaw images.

Windows and keys
----------------

Each viewer is a window in the tab. The "Canvas" menu has "New Data Viewer" (Ctrl+N), "New Tab"
(Ctrl+T), "Gather Windows" (Ctrl+G), which places the tab's viewers side by side, and "Rename Tab"
(Ctrl+R); on macOS these use Cmd. Backspace closes the active Image, Scatter or Histogram viewer
after asking. In the data collection, Backspace deletes the selected datasets and subsets at once,
without undo, and Ctrl+I (Cmd+I on macOS) shows the selected dataset's FITS header (see
:ref:`glue_solar_users_guide_iris_fits_header`).

D, F, A, S and Space act on the viewer last clicked, unless you are typing in a box or the data
collection has the keyboard. The others act in the image, toolbar or browser last clicked.

.. list-table:: Keys
   :header-rows: 1
   :widths: 15 85

   * - Key
     - Action
   * - :kbd:`D`, :kbd:`F`
     - A frame, exposure, step or scan back and on, round from the last to the first. On IRIS data
       whose time a dataset leads, they move that dataset, whichever viewer of its observation you
       press them in; otherwise the viewer's slider of the data's first axis.
   * - :kbd:`A`, :kbd:`S`
     - A wavelength back and on: the viewer's own wavelength slider, and in a quicklook the map's.
   * - :kbd:`Space`
     - Plays the time, as the leading dataset's slider does, along its loop if "Loop…" gave it one;
       pressed again, pauses. With no dataset leading, plays the viewer's slider of the data's first
       axis.
   * - :kbd:`U`, :kbd:`L`
     - "Measure" and "Path diagram", while the toolbar has the keyboard: click the toolbar first,
       such as its handle at the left end.
   * - :kbd:`Enter`, :kbd:`Return`
     - In "Path diagram", makes the diagrams of the path drawn; in "Slope", adds the speed to the
       diagram's table. In the observation browser, presses "Load selected", but in a text field.
   * - :kbd:`Esc`
     - In "Path diagram", clears the path; in "Slope", the points; in "Follow/lock", unlocks the
       point.
   * - :kbd:`W`
     - With the mouse over the image, switches the cursor readout between world and pixel positions.

glue-solar turns off matplotlib's keys that clash with glue's, such as F, S, G, L, P and O. A Profile
viewer keeps G and Shift+G: with the mouse over the plot, they step its grid lines.
