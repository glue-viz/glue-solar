.. _glue_solar_users_guide_loading_sst_cubes:

===================================
Opening SST CRISP and CHROMIS cubes
===================================

What loads
----------

File → Open Data Set opens a CRISP or CHROMIS cube from the SST data archive, one of the SOLARNET FITS
files its SSTRED pipeline exports (``nb_6563_…_im.fits`` and the like), as one dataset. glue-solar's
reader, "SST CRISP or CHROMIS cube (SOLARNET FITS)", takes these files ahead of glue's "FITS file",
which gave each cube 32 more datasets: its cavity map, and an empty one for each of its tables. In
glue's terminal, ``sst_data`` loads one the same way::

    from glue_solar.sources.sst import sst_data

    data_collection.append(sst_data("nb_8542_2023-09-19T10:43:01_mosaic_…_im.fits"))

The dataset's axes are the file's, in numpy order: scan, Stokes, tuning, y and x, but a cube of
intensities, such as CHROMIS's, leaves out its Stokes axis of length 1: scan, tuning, y and x. Its
values stay in the file, memory-mapped: opening a cube reads only its headers and tables, about 0.3 MB
in 0.03 to 0.05 s, and a viewer reads the planes it shows. A viewer's colour limits come from evenly
spaced rows and columns of 16 evenly spaced planes, about 10,000 values, as many as glue samples at
random, each on another page of the file, which read 0.7 GB the first time.

Its coordinates are the file's tabulated WCS: the helioprojective longitude and latitude of each scan,
which move from scan to scan in a mosaic, the nominal wavelength of each tuning, in nm, and the time
of each tuning of each scan, in seconds since the file's ``DATEREF``. ``Time`` gives that time in UTC
at every pixel, as the file's ``DATE-AVG`` table does. A scan's tunings span from 2 s, the 11
H-alpha tunings of the archive's obs 171, to 26 s, the 21 Ca II 8542 tunings of its obs 492; glue's
own reader gave every tuning the time of the first. A file whose header has no ``SPECSYS``, as the
archive's 2020 exports have none, is given ``TOPOCENT``, without which no viewer showed it. The file's
other tables (``VAR-EXT-…``), such as the exposure times (``XPOSURE``) and the seeing (``ATMOS_R0``),
are kept in the dataset's metadata, not as components: ``meta['VAR-EXT']`` gives each column by name,
on the cube's axes, 1 long along those it does not change on, such as ``XPOSURE``'s value per scan and
tuning, or at the table's own times, such as the seeing's (``TIME-ATMOS_R0``, in seconds since
``DATEREF``).

Line core
---------

The cube's line core is the tuning nearest its line: of the lines of the archive's cubes (Ca II K and
H, H-beta, Fe I 617.33, 630.15 and 630.25 nm, H-alpha and Ca II 854.21 nm, at their NIST air
wavelengths, redshifted 0.636 km/s by the Sun's gravity as the Sun shows them), the one within the
cube's tunings nearest the header's ``WAVELNTH``, which is the prefilter's, not the line's; with none
within them, the tuning nearest ``WAVELNTH``. Counting from 0, it is tuning 10 of 21 (854.2121 nm) on
obs 492 Ca II 8542, the middle one, tuning 5 of 11 (630.2483 nm) on its Fe I 6302, the middle one too,
and tuning 7 of 55 (393.3675 nm, Ca II K) on obs 495 Ca II H & K, whose ``WAVELNTH``, 395.0 nm, lies
between Ca II K and H, nearer K, and whose middle tuning is in Ca II H. The quicklook opens its map
there, the time sync and the links to IRIS data time each scan there, and a linked IRIS dataset,
which has no wavelength, reaches the cube there (see `Linking to IRIS data`_).

Cavity error
------------

``Cavity error`` is the shift of each pixel's wavelength from the nominal one at each scan, in nm,
from the cavity map of the Fabry–Pérot that SSTRED stores in the file (``WCSDVARR``): up to
0.006 nm on obs 171, 2.8 km/s at H-alpha. The wavelength axis keeps the nominal wavelengths. To
correct one, or a line position measured on them, add the cavity error, with glue's arithmetic
attribute editor for example: ``{Wavelength} + {Cavity error}``, or as a velocity at 656.28 nm,
``{Cavity error} / 656.28 * 299792.458`` in km/s. A CHROMIS Ca II H & K cube has a map for each
prefilter, each applied to its own tunings, and none for its continuum tuning, where the cavity error
is 0, so that the corrected wavelength there is the nominal one. The maps too stay in the file until
they are viewed.

Linking to IRIS data
--------------------

An SST cube is linked to IRIS data only on request, with "IRIS: link helioprojective coordinates" in
the "Plugins" menu (see :ref:`glue_solar_users_guide_iris_linking`). Once it is linked, a region drawn
on the cube selects, in each slit-jaw frame and each raster exposure or step, the IRIS pixels at its
place on the Sun in the cube's scan nearest that frame's time, timed at its line core, at that scan's
own pointing. A Pixel point on the cube, which takes the scan and any Stokes parameter of the viewer
clicked and is placed at the cube's first tuning, reaches the raster pixel at its place, and in the
slit-jaw frame nearest that scan, the pixel there. The cube then also shares the time of the IRIS
observation whose times come nearest its middle scan (see `The SST quicklook`_). The cube's
coordinates have a lock of their own, as its viewers draw them while its spectra are computed on other
threads; only once linked are its links to IRIS data made behind the lock glue-solar keeps IRIS data's
behind, so until then its viewers never wait for IRIS data's spectrum threads.

The SST quicklook
-----------------

A CRISP or CHROMIS cube opens in a quicklook of its own, in a new tab named after its line, such as
"SST Ca II 8542", one cube to a tab:

- from the observation browser, which lists the SST archive's cubes (see
  :ref:`glue_solar_users_guide_loading_iris_level_2_raster_and_sji_files`), with "Open quicklook"
  ticked;
- for a cube already loaded, with "IRIS: quicklook…" in the "Plugins" menu, which asks which when
  several cubes or IRIS observations are loaded;
- from the command line, with ``glue --startup=iris_quicklook`` followed by the cubes' files;
- from glue's Terminal, with ``glue_solar.quicklook.quicklook(application, [cube])``.

Its panels are laid out in three rows, maps on top:

- the map, at the line core (see `Line core`_), with sliders for the scan, the Stokes parameter, if
  any, and the wavelength; a second map, at the first tuning, the line's blue wing; and the virtual
  slit, wavelength against y at the point's x;
- the spectrum at the point of Stokes I, Q, U and V side by side, or the one spectrum of a cube of
  intensities such as CHROMIS's;
- wavelength against scan at the point ("λ–time"), and the light curve at the point: the cube's value
  at each scan, against the scan index, at the map's wavelength, or the mean over its band, a Collapse
  or a "Wavelength band…" (see :ref:`Viewer tools and windows
  <glue_solar_users_guide_viewer_tools_and_windows>`).

The point, the edit subset "Point", starts at the map's centre in the first scan and Stokes I, with
the Pixel tool on the map, and is a pixel at every wavelength, as in the IRIS quicklook (see
:ref:`The quicklook <glue_solar_users_guide_iris_quicklook>`). A click on either map moves it, the
virtual slit to its x and wavelength against scan to its y and x; a click on the virtual slit or on
wavelength against scan moves it there and the map, not the second map, to the wavelength clicked. The
scan and Stokes sliders of either map move the point and the other panels; a wavelength slider moves
its own map only, and :kbd:`A` and :kbd:`S` step every map's but the second's, unless pressed on it.
The spectra keep their Stokes parameter and follow the point and the scan; the light curve follows the
point, any Stokes parameter and the map's wavelength or band. Each is a subset group, "<line> Stokes I
at the point" or "<line> light curve", glue's selection of those pixels by their indices, so no panel
reads the whole cube, as the cube's own profile would (see `A Profile viewer of a cube`_). As in the
IRIS quicklook, the virtual slit and wavelength against scan have a thin red line at the point,
wavelength against scan dashed white lines at both maps' wavelengths and a dotted one at the scan
nearest the time master's time, and the Stokes I spectrum dashed grey lines at the maps' wavelengths;
a zoom on its x axis gives wavelength against scan the same wavelength range. The "Point" window
gives the point's scan, any Stokes parameter, wavelength (λ, the map's), y and x, its position, the
time of that tuning and the value there, and the "Panels" list beside it turns each panel off and on.
As in the IRIS quicklook, the maps, the virtual slit and wavelength against scan open without their
axes, and "Axes", at the top of the Panels list, shows or hides them on all four; the spectra and the
light curve keep theirs. On obs 498 CHROMIS 4846 a scan step and a move of the point take 0.19 s with
or without axes, as they wait for the spectrum and the light curve, which glue computes on a worker
thread; the panels' own redraws are faster without axes.

Each scan of a mosaic, such as the archive's obs 492 and 495, is another pointing: the point is a
pixel, which stays put from scan to scan, so the light curve and wavelength against scan follow that
pixel, not a place on the Sun. The maps take 99.5 % colour limits over the whole cube, Stokes I, Q, U
and V together, so the Q, U and V maps show flat at first: "Per-frame limits" in a map's "View" menu
scales each frame on its own. The spectra fit their own ranges.

The cubes of a day share one time, a scan timed at its line core, and the quicklook shown leads
it: its cube is the time master, unless one is chosen with "Time master" in the "Coordinate" menu.
Showing another cube's quicklook moves that cube to its scan nearest the time the last one was left
at, unless it is within half the longer of the two cubes' times between scans already, and a new
quicklook starts there; a quicklook not shown keeps its time until it is shown. Once linked to IRIS
data, the cube shares the time of that IRIS observation instead: the IRIS quicklook, shown, moves its
raster to the exposure nearest the cube's scan in the same way, and the cube moves to the scan nearest
the IRIS time when its quicklook is shown again.

A saved session opens the quicklook again with its point and its time master, the spectra and the
light curve following the point again; as in the IRIS quicklook, the Point window, the Panels list,
the lines and the panels turned off are not restored.

On obs 492 Ca II 8542, 9.9 GB with four Stokes parameters, the quicklook opens in 2.4 s from a cold
disk, reading 0.2 GB, and in 2.0 s once read. A scan or Stokes step takes 0.6 s cold, as the virtual
slit reads a pixel of each row at each tuning, and 0.2 s warm; a wavelength step 0.16 s, a click 0.2
to 0.3 s and each move of a Pixel drag 0.25 to 0.3 s. On obs 495 Ca II H & K, 3.3 GB with no Stokes
axis and 55 tunings, it opens in 2.0 s cold and 1.2 s warm, and a scan step takes 0.8 and 0.2 s.
After each, every panel equals numpy's reading of the file at the point, the scan, the Stokes
parameter and the wavelengths shown, and a saved session of either opens again in about a second.

A Profile viewer of a cube
--------------------------

glue's Profile button, or a cube dragged onto a 1D Profile viewer, adds the cube hidden once glue's
"Add large data set?" is answered OK, as it adds any dataset of 1e8 values or more that the IRIS
reader did not open: glue would compute the cube's own profile on the main thread first, which reads
the whole file, 30 s, 20 s of them frozen, and 11 GB on obs 492 Ca II 8542, and again after each
change of links, such as a Path diagram's. The viewer's status bar says so. A subset drawn on the
cube, such as a rectangle, shows its profile, and the viewer fits its range to the first subset
profile computed: the rectangle, or the point's spectra when the cube's quicklook is open; Home fits
the range to all. Ticking the cube in the viewer's layer list shows its own profile, at that cost.
On obs 492 Ca II 8542 the button then opens in 0.2 s, reading nothing, a 200 by 200 pixel
rectangle's profile takes 1.7 s from a cold disk, reading 0.9 GB, and 0.6 s once read, and a Path
diagram settles 0.3 s after Enter rather than 4 to 5 s.

Saving sessions
---------------

A session refers to the cube's file, as it does to IRIS data's (see "Saving sessions" in
:ref:`Viewer tools and windows <glue_solar_users_guide_viewer_tools_and_windows>`), and reads it again
as it opens; "IRIS: restore last session" opens the one glue-solar keeps as glue closes.

What is not supported
---------------------

The Level 3 files of the IRIS–SST coordinated observations, made for CRISPEX
(``iris_l3_…_im.fits``), are not SSTRED exports: glue's own "FITS file" reader opens them, without
these coordinates, times and cavity maps.

A cube whose table gives the pointing at more points than the field's four corners, which SSTRED does
not write, takes wcslib's own inverse of its coordinates, so once linked a region drawn on it selects
no IRIS pixels.

Opening a map, or other data with sky coordinates and a different number of axes, after an SST cube
shows glue's "Could not load data … Cannot slice WCS" from its autolinker, though the map loads; open
the map first to avoid it.
