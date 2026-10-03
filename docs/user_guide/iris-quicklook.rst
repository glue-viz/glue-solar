.. _glue_solar_users_guide_iris_quicklook:

=============
The quicklook
=============

The quicklook is a CRISPEX-style set of viewers for one observation, in a new tab. Open it

- from the observation browser, with "Open quicklook" ticked (the default): each observation you
  load opens in its own quicklook, showing the raster window you ticked if you ticked one;
- for data already loaded, with "IRIS: quicklook…" in the "Plugins" menu, which asks which
  observation when several are loaded;
- from the command line, with ``glue --startup=iris_quicklook`` followed by the files. Files given
  this way load one by one, so each raster file keeps its raster number in its label
  (``…-r00003``) and the quicklook shows the first; to stack the scans, use the browser;
- from glue's Terminal, with ``glue_solar.quicklook.quicklook(application, datasets)``.

For those used to CRISPEX:

.. list-table::
   :header-rows: 1

   * - CRISPEX or iris_xcontrol
     - In glue-solar
   * - ``crispex, raster, sjicube=sji`` (one call per observation)
     - Tick the observation in the browser, or ``glue --startup=iris_quicklook raster.fits sji.fits``
   * - several ``sjicube`` files
     - Tick every slit-jaw channel; each gets its own viewer
   * - iris_xcontrol's raster, sit-and-stare and multi-raster modes
     - Chosen from the observation: map, slit against time, or a stack's map with its scan slider
   * - ``spcube`` (transposed cube)
     - Not needed: the wavelength panel shows wavelength against step, exposure or scan
   * - ``dt`` and non-equidistant timing
     - "Regrid on time" (see `Regridding on time`_)

It shows one spectral window: Mg II k 2796 when loaded, otherwise the first (pass
``window="Si IV 1403"`` to choose). The raster opens as three panels, plus one viewer per slit-jaw
channel and a spectrum panel:

- a raster: the map (step against slit), the spectrogram (wavelength against slit) and wavelength
  against step;
- a sit-and-stare raster: slit against time, the spectrogram and wavelength against time;
- a stack of raster scans: the map of the current scan, the spectrogram and wavelength against scan.

A sit-and-stare raster's exposure axis, in the quicklook or any Image viewer, is labelled
"Exposure (acquisition order)" with the UTC range of its exposures on a second line, and its ticks
are exposure numbers: it is an index axis, so exposures are evenly spaced whatever their cadence
(`Regridding on time`_ places them in time). The other axis shows only its own coordinate, and so
does the mouse-over readout, followed by the time and exposure of the exposure under the mouse,
rather than where the slit was then. The label and ticks come back whenever glue resets the axes,
after an axis change or, on the wavelength panel, a slit move; a label typed in the viewer's axes
options is kept until that reset, as glue's own labels are.

In every Image viewer, each world coordinate's ticks are labelled with that coordinate's name.
WCSAxes can put a coordinate's ticks on another side than the axis it belongs to: latitude can run
along the bottom of a slit-jaw image rolled by more than 45°. The label then stays with the ticks,
and an x or y axis label typed in the axes options names the coordinate of that axis, wherever its
ticks are; glue-core 1.27.0 alone labels the bottom and left ticks after the x and y axes, whichever
coordinate they show.

On an image that shows another coordinate, such as wavelength or time, beside longitude and
latitude, an angle that changes by less than 5 % of the other across the image has no tick labels,
also after glue resets the axes: the latitude along a raster's steps on the wavelength-against-step
panel, or the longitude along the slit on the spectrogram. WCSAxes would label it wherever pointing
jitter takes it across a tick value, one label over another or off the panel. An image of the two
angles alone, such as the map, a slit-jaw image or any other celestial map, keeps both.

The map shows the wavelength nearest the window's reference wavelength, and the panels use
99.5 % limits. A point, the edit subset "Point", starts at the centre of the map with the Pixel
tool active: drag it on the map, and the spectrum panel shows its spectrum. The point is a detector
pixel (a step or exposure, and a slit position) at every wavelength, and the other panels follow
it: the spectrogram moves to its step and the wavelength panel to its slit. Its crosshair shows
only on the map; the spectrogram and the wavelength panel highlight its row instead. Clicking the
spectrogram or the wavelength panel moves the point there and the map to the clicked wavelength;
no other wavelength slider moves. Moving a step, exposure or scan slider moves the point, so on a
stack the point stays on the map's scan. A Profile's collapse of an axis is left in place. After
"Clear point" the panels stop following each other until the next click, except in time: the
slit-jaw viewers keep following the exposure slider of a sit-and-stare raster and the scan slider of
a stack's map, on a scanning raster the time stays at the last point's raster step, and a slit-jaw
time master (see below) still moves the others. A click on a slit-jaw viewer moves the point to the
raster there (see below). The raster panels have no region selection tools, because a region drawn on a
raster map is recomputed on every slit-jaw viewer for each screen pixel at every frame (see
:ref:`Linking <glue_solar_users_guide_iris_linking>`). Each quicklook has its own point,
shown only in its own panels, edited while its tab is
shown and moved only by that tab's sliders. Where a point does not show, it is not in the viewer's
layer list either, since glue would still redraw a hidden layer at every move: drag the subset onto
a viewer outside its quicklook to show it there. In its own quicklook, each move adds the point
back to the image panels of the dataset it is on and removes it from the others. Another Image viewer of the same data follows the point. When a slit-jaw channel is loaded both plain and deconvolved,
the plain one is shown and the status bar names the other. The spectrum panel does not ask "Add
large data set?", and the status bar gives the size of the data it shows.

The panels also follow one time. The raster is the time master: the slit-jaw viewers show the frame
nearest the time of the point's exposure or raster step (mid-raster before there is a point). Choose
"Time master" in the "Coordinate" menu of a slit-jaw viewer to make it the master instead; the
raster then moves to the exposure, or on a stack the scan, nearest each frame, keeping the slit and
the raster step. The master rules: while there is a point, moving the raster's exposure or scan
slider by hand, or clicking another exposure or scan, snaps the raster back to the one matching
the master's frame (after "Clear point" it keeps a hand-moved exposure or scan, as below), while a
slit-jaw follower moved by hand keeps its frame until the panels next follow the time, on a click, a
move of the point or of the master, or when its tab is shown again. A dataset with nothing within
half its own time step of the master's time (for a
scanning raster, one that does not cover it) keeps its frame and is greyed. The "Frame time" readout
says which dataset is the time master, how far each matched dataset's time is from the master's
(Δt) and "NO MATCH" with that offset for the others. Wavelength and slit sliders are never moved.

Each slit-jaw viewer is titled with its channel ("SJI 1400", "SJI 2796 (deconvolved)") and opens on
the raster's field of view with a margin. Every slit-jaw viewer, in a quicklook or not, draws the
displayed frame's slit as a dashed line (from the frame's slit position in the file) and the raster
point as a red cross, placed with that frame's own pointing. The cross is hidden, and the "Frame
time" readout says "outside SJI FOV", when the point is off the image; neither is drawn while the
viewer shows the frame axis. A slit-jaw frame taken a raster step earlier or later than the point
shows the slit a step away from the cross.

A click with the Pixel tool on a slit-jaw viewer of the quicklook moves the point to the raster
pixel there, placed with the displayed frame's own pointing (``sji_to_raster``, see
:ref:`Scripting with IRIS data <glue_solar_users_guide_scripting_iris_data>`): on a scanning raster
the nearest step and slit position, on a stack also the scan nearest the frame's time at that step,
and on a sit-and-stare raster the exposure nearest the frame's time and the slit position level with
the click, however far beside the slit: the slit, 0.33″ or about two slit-jaw pixels wide, is about
a screen pixel wide at the quicklook's zoom. The other panels and the spectrum follow, as after a
map click, and the red cross marks the point. The viewer keeps the frame clicked, also after a click
outside the raster (below), until the point moves again, with its offset from the raster's time, NO
MATCH and greyed when the raster took that place more than half a frame interval away, as it often
did on a scanning raster; under a slit-jaw time master the master rules, and the exposure or scan
and the viewer clicked follow its frame. One Undo ("Edit" menu, Ctrl+Z, Cmd+Z on macOS) takes the
point back. Redo repeats the click in the frame the viewer shows then, so after the frame has moved
it can land on another exposure or scan than the first time. A click outside the raster, past its first or last step or either end of its slit, or on
a sit-and-stare raster in a frame with no exposure within half its cadence, leaves the point where
it was, and the viewer's "Frame time" readout says "outside raster FOV" until the point moves; it
still adds an Undo step, which changes nothing. A click on a slit-jaw viewer showing its frame axis,
which is no place on the Sun, is marked only there, and the spectrum panel is empty until the next
raster click.

Below the panels, which keep their size (scroll the tab down on a small screen), the read-only
"Point" window gives the point in each dataset the quicklook shows, one row each, as the readouts
give it:

- Pixel: the point's indices in the dataset: step (exposure on a sit-and-stare raster, scan and step
  on a stack), slit and wavelength pixel (λ, the one the map shows) on the raster; frame, y and x
  on a slit-jaw image, where the point is placed in the displayed frame, as its red cross is;
- Position: the helioprojective longitude and latitude of that pixel, and on the raster its
  wavelength, in arcsec to 0.01″ and Å to 0.001 Å, as the mouse-over readout gives them;
- Time and Exposure: that pixel's ``Time`` in UTC, to the millisecond, and its ``Exposure time``;
- Value: the value there of the component the dataset's panel shows;
- Time sync: what its "Frame time" readout says: "time master" (with the timing raster step), the
  offset Δt of its time from the master's, such as each slit-jaw frame's from the point's raster
  step or exposure, or "NO MATCH".

A point clicked on a slit-jaw viewer showing its frame axis fills its own row only, as the raster
panels do not follow it; a point off a slit-jaw image gives "outside SJI FOV" there, and a dataset
of another observation "no match". After "Clear point" only the time sync is left. The window refreshes once for each
click, slider step, time sync or change to a panel's layers, such as the component it shows, and
only while its tab is shown. Move or resize it like a panel; closing the tab closes it, and one
closed by hand stays closed.

Regridding on time
------------------

Every axis of glue's viewers is an index axis, so a sit-and-stare raster's exposures, a slit-jaw
image's frames and a stack's scans show evenly spaced whatever their timing: the cadence of OBSID
4000255147's Si IV varies from 2.71 to 3.29 s, and an observation can have gaps. To see them in
time, select one such dataset in the data collection and choose "Regrid on time" from its
right-click menu. This adds ``<label> regridded``, resampled at the median step between their times:
each pixel along that axis is one step after the previous one, from the first time up to the first
pixel at or past the last, and holds the exposure, frame or scan nearest its time within 0.75 steps
(the earlier of two as near), so one exposure can fill two pixels. A pixel with none, in a gap, is
NaN, with ``Time`` NaT, ``Exposure time`` NaN and the missing-data mask 1. The 1600 exposures of
4000255147's Si IV, 4750 s at a median step of 2.89 s, give 1645 pixels, none of them empty.

- A stack is regridded scan by scan, each scan timed by its middle raster step: its steps are
  places on the Sun, so each pixel keeps a whole scan, and the scan slider stays its time, as in
  the quicklook.
- A scanning raster is refused with a message saying why: its steps are places on the Sun, not
  times. Stack its scans in the observation browser and regrid the stack instead.
- The new dataset has the original's other axes, units, colormap, ``<label> DN/s`` and metadata,
  ``meta['time_step']`` adding the step in seconds, and its coordinates: along the regridded axis,
  those at each pixel's time, so that a slit-jaw image's time coordinate is regular, and those of
  the last time for a last pixel past it. Its helioprojective coordinates are linked with the other
  IRIS datasets, no viewer opens, and data read from their files as they are viewed (see
  :ref:`Memory and open files <glue_solar_users_guide_iris_memory_and_open_files>`) stay there.
- In an Image viewer, a regridded sit-and-stare raster's time axis is labelled "Time (2.89 s per
  pixel)", with the UTC range of its exposures on a second line, and its ticks are pixel numbers. It
  follows and leads the time sync as its original does (see `The quicklook`_): a pixel in a gap has
  no time, so its "Frame time" readout is empty, the other datasets keep their frames and show "NO
  MATCH", and a slit-jaw time master never moves it into a gap. "IRIS: quicklook…" shows the
  original; for a quicklook of the regridded raster, type
  ``from glue_solar.quicklook import quicklook`` in glue's terminal, then
  ``quicklook(application, [dc["<raster label> regridded"], dc["<slit-jaw label>"]])`` with the
  labels the data collection shows. ``glue_solar.regrid.regrid_on_time(data)`` regrids a dataset
  there too.
