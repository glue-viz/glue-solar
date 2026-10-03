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
- "Contrast/Bias": drag on the image, left and right for the bias, up and down for the contrast.
  The "Reset" button next to the layer's contrast/bias sliders undoes it.
- "Slice Extraction" (P): draw a path and press Enter to see the data along it in a new window.
  It is offered for 3D data only, so not for stacks.
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
- A button with a spectrum icon and no tooltip, which opens a 1D Profile viewer of the image's data.
- The save menu, with "Save plot to file" and "Save Python script to reproduce plot", and the
  window menu, with "Move to another tab" and "Change viewer title".

Each viewer is a window in the current tab, with its own minimise, maximise and close buttons. The
"Canvas" menu has "New Data Viewer" (Ctrl+N), "New Tab" (Ctrl+T), "Gather Windows" (Ctrl+G), which
places the tab's viewers side by side, and "Rename Tab" (Ctrl+R); on macOS these use Cmd. Backspace
closes the active viewer after asking "Do you want to close this window?" if it is one of glue's own
Image, Scatter or Histogram viewers. It does nothing in a Profile or Table viewer, or in the
quicklook's map, spectrogram and wavelength panels. In the data collection, though, Backspace is
"Delete Layer": it removes the selected datasets and subsets at once, without asking and without
undo.

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
