.. _glue_solar_user_guide_1dprofile_viewer_for_iris_data:

=============================================================================
A guide to using ``glue``'s 1D profile viewer to probe IRIS Level 2 data sets
=============================================================================

Loading and stacking multi-scan IRIS Level 2 raster cubes
---------------------------------------------------------

Use the observation browser for this task because it groups raster scans by observing-program
execution and lets you select spectral windows before loading their arrays. Open
"Plugins -> IRIS: browse observations…" and point it at a directory containing the IRIS
Level 2 files or their downloaded archives. If an archive is still packed, tick its
"Extract ..." entry and press "Load selected" first; the browser refreshes and shows its contents.
Then tick the raster spectral windows to load (``C II 1336`` and ``Mg II k 2796`` here) and tick
"Stack sequential raster scans" to place two or more scans of each selected window into one 4D
cube without resampling their detector values. A window with only one scan loads as its normal 3D
dataset.

.. image:: images/choosing-iris-level-2-data-cubes-and-stacking-raster-cubes.png
   :width: 800
   :alt: Selecting two raster spectral windows of a multi-scan observation and ticking the stacking option

The browser uses ``irispy`` to read the selected files and returns the datasets to Glue.
Once loaded, the data sets show up in the "Data Collection" window in the upper left of the GUI.
A stacked window is labelled ``<window>-<OBSID>-<STARTOBS>-stack``, while unstacked scans are
labelled ``<window>-<OBSID>-<STARTOBS>-scan-<n>``. Including ``STARTOBS`` keeps repeated executions
of the same observing program distinct.

The stacked cube has a leading ``Scan`` coordinate rather than pretending that a complete raster
was acquired at one instant. Its separate ``Time`` component records the exact acquisition time
of every pixel. Scan 0 supplies the nominal helioprojective WCS for the whole stack; subsequent
scans keep their original raster and detector indices, not their distinct absolute pointings.
Load the original per-scan datasets when those per-scan absolute coordinates are required.

Using ``glue``'s 2D image viewer to pick a pixel
------------------------------------------------

Drag the stacked ``Mg_II_k_2796`` dataset from the "Data Collection" area onto the large plotting
window to the right and choose "2D Image". The viewer shows one slice of the 4D cube, whose axes
Glue lists as ``Scan``, ``Helioprojective Longitude`` (raster position),
``Helioprojective Latitude`` (slit position) and ``Wavelength``. By default the x-axis is
``Wavelength`` and the y-axis is ``Helioprojective Latitude``, so you are looking at the spectrum
along the slit, with sliders for ``Scan`` and ``Helioprojective Longitude``.

The raw min/max limits can make the slice look flat. Change the limits to "99%" and pick a more
nuanced colormap so the emission lines stand out.

To turn the slice into a map with celestial axes, change the x-axis to
``Helioprojective Longitude`` while keeping the y-axis as ``Helioprojective Latitude``.
The sliders are then ``Scan`` and ``Wavelength``. Set the aspect to "Automatic" so the narrow
raster field fills the plot, or press "Physical aspect" in the toolbar to see it in its
proportions on the sky, then move the ``Wavelength`` slider onto the line core until structure
appears in the map.

Now activate the "Pixel" tool in the viewer toolbar ("Select a single pixel based on mouse
location") and click a point of interest. This creates a subset, ``Subset 1``, containing that
pixel at every wavelength in the scan shown by the ``Scan`` slider; it appears under "Subsets" in
the Data Collection and is drawn on top of the image.
Click and drag to move it interactively.

Using Glue's 1D Profile viewer to plot the spectrum and scan evolution
----------------------------------------------------------------------

Drag ``Mg_II_k_2796`` onto the plotting window again and choose "1D Profile". The profile viewer
collapses the cube over every axis except the one chosen as the x-axis, using its function, which
starts as "Maximum". Pick ``Wavelength`` as the x-axis and "Mean" as the function. The
``Mg_II_k_2796`` layer is then the mean spectrum of the whole cube, the equivalent of CRISPEX's
average spectrum. The ``Subset 1`` layer is the spectrum at the selected pixel in the scan it was
selected in: the subset holds one sample per wavelength, so Mean returns that sample unchanged.

The values are floating point, with NaN in place of the -200 and -199 fill of the files. The profile
functions skip NaN samples, so the fill is left out.

No glue release has a profile function that plots the profile through one position without
collapsing, so use a one-pixel subset with Mean as above.

.. image:: images/spectrum-at-the-selected-pixel.png
   :width: 800
   :alt: The 1D Profile viewer showing the spectrum at the selected pixel

Switching the x-axis to ``Scan`` makes the ``Mg_II_k_2796`` layer the mean intensity of each scan,
by raster number; the ``Subset 1`` layer then has only the scan it was selected in. The ``Time``
component supplies the exact acquisition timestamp for individual pixels, but it depends on both
scan number and raster position and is therefore not a single Glue profile axis. The ``Subset 1``
profile updates as you move the pixel selection in the image viewer.

Recipes
-------

:ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`
sets up most of these views. The recipes below build them by hand with glue's own viewers, for any
raster. Glue names a raster's axes after its world coordinates, so by role they are:

.. list-table::
   :header-rows: 1

   * - Role
     - Glue's name for the axis
   * - Raster step
     - ``Helioprojective Longitude``
   * - Exposure of a sit-and-stare raster, in acquisition order
     - ``Helioprojective Longitude``
   * - Position along the slit
     - ``Helioprojective Latitude``
   * - Wavelength
     - ``Wavelength``
   * - Scan of a stack
     - ``Scan``
   * - Slit-jaw frame
     - ``Time (Utc)``

The ``Time`` component gives the time of each raster step or exposure.

**Views.** Drag the raster onto the canvas, choose "2D Image" and set the "x axis" and "y axis" in
the viewer's options:

- spectrogram: wavelength against slit (x ``Wavelength``, y ``Helioprojective Latitude``), glue's
  default for a raster, with a slider for the raster step or exposure;
- raster map: step against slit (x ``Helioprojective Longitude``, y ``Helioprojective Latitude``),
  with a ``Wavelength`` slider;
- time–wavelength: wavelength against exposure (x ``Wavelength``, y ``Helioprojective Longitude``)
  for a sit-and-stare raster, or against scan (y ``Scan``) for a stack. On a scanning raster the
  same axes give wavelength against raster step.

**Four panels.** Open a raster map, a spectrogram, a slit-jaw image and a 1D Profile of the raster
with ``Wavelength`` as its x axis, then choose "Canvas -> Gather Windows" (Ctrl+G) to place them side
by side. The 1D Profile viewer asks "Add large data set?" for datasets of 1e8 samples or more, with
Cancel as the default button.

**Pixel.** "Pixel" in an Image viewer of a raster selects a detector pixel, one step (and scan) and
slit position at every wavelength, and the Profile shows its spectrum. Click to select, or drag to
move the point; it stays where you release the button. Pixel replaces the selected subset and
switches glue's selection mode to replace.

**Navigate.** "Options" in the Profile viewer's toolbar opens glue's
`profile tools <http://docs.glueviz.org/en/stable/gui_guide/spectrum.html>`__. On their "Navigate"
tab, click the profile or drag its line to move the wavelength slider of every Image viewer of the
same raster to the nearest wavelength.

**Band maps.** On the "Collapse" tab, drag a wavelength range on the profile, pick a function (Mean,
Median, Minimum, Maximum, Sum, Moment 1 or Moment 2) and press "Collapse": the Image viewers of the
raster show the data combined over the range, each until you move any of its sliders. glue-qt 0.4.2
leaves out the sample at the upper end of the range, so the range must cover at least two samples.

In glue-qt 0.4.2, Navigate and Collapse pick the wrong wavelengths when the Profile's "x unit" is not
the data's own (``Angstrom`` for IRIS wavelengths), so leave it unchanged for them.

**Slice Extraction.** In an Image viewer of a raster or slit-jaw cube, "Slice Extraction" (P) takes a
path drawn on the image and, on Enter, shows the data along the path against the slider's axis in a
new window, for example along a path across a slit-jaw frame against time. The window is not a
dataset, and the tool is not offered for stacks; see glue's
`slice extraction <http://docs.glueviz.org/en/stable/gui_guide/slice.html>`__. glue-solar's "Path
diagram" (L) makes datasets of the data along a path instead, the spectra along a path across a
raster map too, and takes stacks (see :ref:`glue_solar_users_guide_viewer_tools_and_windows`).
