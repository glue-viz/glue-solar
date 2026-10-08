.. _glue_solar_users_guide_viewer_tools_and_windows:

========================
Viewer tools and windows
========================

glue's `getting started guide <http://docs.glueviz.org/en/stable/getting_started/index.html>`__
describes its viewers and tools; this section names those IRIS work uses most, as glue-qt 0.4.2
labels them. A toolbar button's tooltip gives the tool's single-key shortcut if it has one, for
example "Zoom to rectangle [shortcut: Z]".

Besides glue's "Home" (H), "Pan" (M), "Zoom" (Z) and region selection tools, the Image Viewer
toolbar has:

- "Pixel" ("Select a single pixel based on mouse location"): click or drag to select one pixel.
  On IRIS data this is the point the other viewers follow
  (see :ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`).
- "Follow/lock", from glue-solar ("Move the point with the mouse; click to lock it there, right-click
  or press Esc to unlock it"): the point follows the mouse over the image, as CRISPEX's cursor does,
  moving as a Pixel click there would move it, at most once every 50 ms and with no Undo step. A left
  click moves it there and locks it, in one Undo step, which also unlocks it; a right click, or Esc
  once a click has given the image the keyboard, unlocks it. A locked point stays as the mouse moves
  over any viewer, and stays locked as sliders or Pixel clicks move it or "Clear point" empties it.
  The mouse alone never moves a region picked to edit, which a click replaces, as with Pixel. As
  with every mouse mode, it stays on only in the viewer last clicked: choose it in the viewer the
  mouse will move over.
- "Measure", from glue-solar ("Drag a line to measure its length in pixels, arcsec and km"): drag a
  line on the image, and the status bar gives its length in data pixels, on the sky in arcsec, the
  great-circle angle between the world coordinates at its ends, and in km, that angle at the
  observer's distance from the Sun's centre, the data's ``DSUN_OBS``. The km are a length in the
  plane of the sky through the Sun's centre, 713 to 737 km per arcsec through the year, with no
  correction for foreshortening on the disk. For example, a 100-pixel line on a slit-jaw image of
  OBSID 4000255147 reads ``Length 100.0 px · 16.64" · 12,172 km``. On axes other than a longitude
  and a latitude alone, such as a spectrogram, a slit-jaw image's x against time or a sit-and-stare
  raster's exposures against its slit, it gives pixels only; data without ``DSUN_OBS``, such as
  line-moment maps, get no km. The line and its length stay until the next drag, or until other
  axes or another dataset are shown, which they would not describe; another mouse mode hides them
  while it is on, and glue-solar's buttons keep them.
- "Contrast/Bias": drag on the image, left and right for the bias, up and down for the contrast.
  The "Reset" button next to the layer's contrast/bias sliders undoes it.
- "Slice Extraction" (P): draw a path and press Enter to see the data along it in a new window.
  It is offered for 3D data only, so not for stacks.
- "Path diagram" (L), from glue-solar ("Draw a path, then press Enter for the data along it"):
  glue's path slicer for 3D and 4D data. Click the path's vertices on the image and press Enter (Esc
  clears the path): each dataset shown gets a dataset of its values along the path, in the data
  collection and in a new Image viewer, with the path along x and the dataset's other axes kept: a
  slit-jaw image gives its frames against the path (400 rows on OBSID 4000255147's SJI 1400), a
  raster window its wavelengths against the path, a stack its wavelengths against the path with a
  scan slider. The path is sampled once a pixel of the image, each sample taking the value of the
  pixel it lies in, and NaN where the path leaves the data. Other datasets shown, such as a raster
  window added to a slit-jaw image's viewer, are sampled at the same places on the Sun through
  glue's links ("IRIS: link helioprojective coordinates"), with the pointing of the frame shown, so
  a viewer that follows the time master samples them at its exposure; a stack is placed with its
  first scan's coordinates. A sit-and-stare raster placed this way gives each place the exposure in
  which its slit lay there, as its coordinates say, not the frame's. A dataset glue cannot place
  from the image, such as a slit-jaw image added to a raster's viewer, gets no diagram. Each Enter
  makes a new set in a new viewer and keeps its path drawn on the image; closing the viewer it was
  drawn in closes them. In the diagram's viewer, "Show position on original path" marks the point
  of the path under the mouse while you drag, and moves the viewer it was drawn in to the frame,
  wavelength or scan the diagram's y axis shows there, only that slider. Sessions do not save the
  diagrams yet.
- "Cursor readout", from glue-solar: the world position under the mouse, the ``Time`` (UTC, to the
  millisecond) and ``Exposure time`` of that pixel, and its value, in the status bar, for example
  ``65.13" 109.32" (world) · 2013-09-02T18:31:07.229 UTC · exp 2 s | value = -3`` on a raster map,
  where the time is that of the step under the mouse; on a slit-jaw image or a sit-and-stare
  raster it is that of the frame or exposure. Helioprojective angles are in arcsec to 0.01″ and
  IRIS wavelengths in Å to 0.001 Å, a tenth of an IRIS pixel or finer, whatever the zoom; other
  coordinates, such as a stack's scan or a Carrington longitude, are as on their ticks. Press W
  over the image to switch between world and pixel positions; the button hides and shows the
  readout, and the mouse mode, such as Pixel, stays on.
- "Frame time" and the "Coordinate" menu, from glue-solar,
  :ref:`described above <glue_solar_users_guide_loading_iris_level_2_raster_and_sji_files>`; the "Frame time" button
  hides and shows its readout of the displayed frame, not the mouse-over one, and the mouse mode
  stays on.
- "Hide axes", from glue-solar: hides the viewer's axes (ticks, tick labels, axis labels and frame),
  and shows them again; the mouse mode, such as Pixel, stays on. Without them each slice step and
  redraw is faster, since no ticks are placed; the image, subsets, links, the slit and point of
  slit-jaw viewers and the readouts work as before, and the mouse-over position stays in world
  coordinates. A saved session keeps each viewer's choice. To open every new Image viewer,
  quicklook panels included, without axes, add ``solar_show_axes = false`` to the ``[main]`` section
  of glue's settings file, ``~/.glue/settings.cfg``, or type
  ``from glue.config import settings; settings.SOLAR_SHOW_AXES = False`` in glue's terminal for the
  rest of the session ("OK" in glue's Preferences then saves it to that file).
- "Per-frame limits", from glue-solar: takes the colour limits of the displayed dataset from the
  displayed slice, at the layer's percentile (99.5 % on the quicklook panels), so each slice step,
  such as a wavelength step of a raster map, gets that slice's limits; press it again for the whole
  cube's limits. Layers of other datasets keep theirs, and choosing another reference data in the
  viewer's options gives the previous one the whole cube's limits again. The mouse mode, such as
  Pixel, stays on. The button does not stay pressed: the limits in the layer's style editor change
  with each step while it is on. A session saved with it on does not open (see `Saving sessions`_).
- "Physical aspect", from glue-solar: shows the image in its proportions on the sky, an arcsecond
  as long on screen along x as along y, and pressed again, with the aspect it had; the mouse mode
  stays on. It sets the aspect in the viewer's options to "Square Pixels", scaled by the ratio of
  the arcseconds a pixel spans along y and along x, on average across the image through the centre
  of the view, so that a raster map of 2″ steps along a slit of 0.17″ pixels shows each step 12
  times as wide as a slit pixel is tall, wherever the view is. Resizing, zooming, panning and the
  sliders keep the proportions, and choosing other x or y axes shows the new image whole, in its
  own proportions. Axes other than a longitude and a latitude alone show square pixels: a
  spectrogram, a sit-and-stare raster's exposures against its slit, or a slit-jaw image's x
  against time. Choosing "Automatic" in the viewer's options switches it off too. Pressed again on
  a quicklook raster panel, whose aspect is "Automatic", the image fills the panel again, keeping a
  zoom. A saved session restores the viewer with "Square Pixels".
- "Zoom 1:1", from glue-solar: zooms about the centre of the view so that one pixel of the displayed
  dataset spans one pixel of the screen, along whichever axes are shown, wavelength included; the
  mouse mode stays on, and "Home" (H) shows the whole image again. A screen pixel is a physical
  one, so on a HiDPI (Retina) screen the image shows at half the size it would in the screen's
  points. With "Physical aspect" on, x is at 1:1 and y keeps the proportions on the sky: on a map
  of 2″ steps along a slit of 0.17″ pixels, 12 slit pixels share each screen pixel. glue draws an
  image through a buffer of 72 dots per inch, so at 1:1 it shows only some of the rows and columns,
  72 of every 100 at matplotlib's 100 dots per inch and 36 on a HiDPI screen.
- "Colour bar", from glue-solar: shows a colour bar right of the image, from one colour limit of the
  displayed dataset (the viewer's reference data) to the other, with value ticks, and pressed again
  hides it; the mouse mode stays on. Its colours are glue's own for that dataset's layer, so it
  follows the limits, "Per-frame limits" included, the stretch, the contrast and bias, the colormap,
  or the colour in "One color per layer" mode, and the sliders. The image narrows to make room for
  it, keeping "Square Pixels" and "Physical aspect", and "Save plot to file" saves the bar with the
  image. "Save Python script to reproduce plot" and saved sessions leave it out. The bar and its
  ticks stay when "Hide axes" is on.
- A button with a spectrum icon and no tooltip, which opens a 1D Profile viewer of the image's data.
- The save menu, with "Save plot to file", glue-solar's "Save frames or movie…" and "Save Python
  script to reproduce plot", and the window menu, with "Move to another tab" and "Change viewer
  title". "Save frames or movie…" saves the image at each index of a slider, from a first to a last,
  as "Save plot to file" would save it there: as PNG files named after the file chosen with the index
  added (``sji.png`` gives ``sji_0000.png``, ``sji_0001.png``, …), or as a movie at 10 frames per
  second, an MP4 where ffmpeg is installed or else a GIF. A GIF is kept in memory until it is
  written, about 1.4 MB a frame of 800 × 600 pixels, so save long sequences as an MP4 or as PNG
  files. Of several sliders it asks which, offering first that of the data's first axis (a slit-jaw
  image's frames, a sit-and-stare raster's exposures, a scanning raster's steps or a stack's scans),
  then for the first and last index, as "Loop…" does, starting from the slider's loop or else its
  whole range. Playback of the slider, or of the time master, stops; the slider moves as when it
  plays, so the other viewers follow, and the slit, the point and the raster overlays are drawn as
  they then show. Every frame has the same colour limits:
  with "Per-frame limits" on, the whole cube's. "Cancel" in its progress dialog keeps the frames
  saved so far, a movie of them too, and the viewer goes back to its slice and limits.

A Profile viewer, the quicklook's spectrum panels included, gets an "IRIS lines" button: where its x
axis is the wavelength of IRIS data, a thin marker and a label mark each main IRIS line in the
plotted range (Mg II k, h and the triplet, C II, Si IV, O I, Fe XII and Fe XXI, at NIST vacuum
wavelengths), in the axis's unit, with lines too close to tell apart sharing a label. They start on,
and the button hides or shows them.

Each viewer is a window in the current tab, with its own minimise, maximise and close buttons. The
"Canvas" menu has "New Data Viewer" (Ctrl+N), "New Tab" (Ctrl+T), "Gather Windows" (Ctrl+G), which
places the tab's viewers side by side, and "Rename Tab" (Ctrl+R); on macOS these use Cmd. Backspace
closes the active viewer after asking "Do you want to close this window?" if it is an Image viewer,
quicklook panels included, or one of glue's Scatter or Histogram viewers. It does nothing in a
Profile or Table viewer. In the data collection, though, Backspace is "Delete Layer": it removes the
selected datasets and subsets at once, without asking and without undo. glue-qt also gives those
viewers Tab, to go to the tab's next window, but Qt takes Tab first to move the keyboard focus, so it
never does.

glue-solar gives Image and Profile viewers, quicklook panels included, these keys. A key acts on the
active viewer, the one last clicked, unless you are typing in a box or the data collection has the
keyboard focus; glue-qt ignores Shift and Ctrl with them.

- D and F go a frame, exposure, step or scan back and on, round from the last to the first and back.
  On IRIS data with a time master (see :ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`),
  they move the time master, as "Go to UTC…" does, whichever viewer of its observation you press them
  in, and the others follow. Otherwise they move the viewer's own slider of the data's first axis.
- A and S go a wavelength back and on, round from either end: the viewer's own wavelength slider, and
  in a quicklook's tab, pressed on any of its viewers, the map's. Nothing else moves.
- Space plays the time forwards, as the play button of the time master's frame, exposure, step or
  scan slider does, round its loop if "Loop…" gave it one, and pressed again pauses it. Without a time
  master it plays the viewer's own slider of the data's first axis.

glue-qt's viewers also have matplotlib's own keys, such as G for a Profile viewer's grid with the
mouse over its plot; with glue-solar, F and S no longer show an empty window full screen or open
matplotlib's save dialog. The save menu saves the plot.

The stretch menu in the Image Viewer's layer options lists glue-solar's "Gamma 0.4", "Gamma 0.75",
"Gamma 1.5" and "Gamma 2.2" after Glue's own stretches. Each raises the values between the limits to
that power: a gamma below 1 brightens faint emission, one above 1 darkens it, and "Square Root" is a
gamma of 0.5.

Saving sessions
---------------

Saving a session that contains IRIS data can fail before any file is written. The irispy
metadata and WCS objects, including SJI gWCS and raster lookup tables, need dedicated serializers,
and data read from their files as they are viewed cannot be saved in a session yet; save derived
products separately rather than relying on a Glue session as their only copy. With glue-core 1.27.0
a session saved while an Image viewer has "Per-frame limits" on, whatever its data, does not open:
glue reports "'NoneType' object has no attribute 'add_callback'". Turn them off before saving.
