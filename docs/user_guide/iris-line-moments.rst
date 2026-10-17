.. _glue_solar_users_guide_iris_line_moments:

=========
Line maps
=========

To map a spectral line, select a raster window, of one scan or a stack of its scans, in the data
collection and choose "IRIS: line maps…" from its right-click menu. The rest wavelength, in Å,
starts at the window's :ref:`rest wavelength <glue_solar_users_guide_iris_rest_wavelength>`, such as
2796.352 for Mg II k, or blank for a window without one; type another to change it. Tick the maps to
make:

- "Line moments", ticked at first: the intensity, centroid, width and velocity of the line within
  its velocity range, with optional continuum windows and error maps, grayed out unless it is ticked
  (see below);
- "Doppler image": the red wing less the blue wing at 10, 20, 30, 40 and 50 km / s;
- "Red-blue asymmetry": irispy's, of the wavelengths within 1 Å of the rest wavelength, the wings 30
  to 55 km / s from the peak.

A blank rest wavelength, or no map ticked, adds nothing. Glue checks every map ticked first, and
should it refuse one, says why and adds none (see `What is refused`_). It then computes them in turn
on a worker thread, while its status bar says "Computing line maps of <label>…", and adds each as a
dataset on the window's raster steps and slit pixels, linked to the window's, with their
helioprojective coordinates in arcsec linked with the other IRIS datasets, and opens each in an
Image viewer in the current tab: its first map, longitude along x as on a quicklook's map, and, in a
quicklook's tab, the point's crosshair; pick another map as its attribute. A stack's maps are one
dataset on its scans, raster steps and slit pixels, each scan's as that scan alone gives them, at
its own coordinates and exposure times; the scan slider picks the scan. The functions named below
take other settings in glue's terminal.

Line moments
------------

The velocity range, the Doppler velocities of the wavelengths taken, from and to, in km / s from the
rest wavelength, is -107 to 107 km / s unless changed, ±0.5 Å at Si IV 1402.77 and ±1.0 Å at Mg II
k; it is the line moments' alone. The velocities stop at the window's first and last wavelengths
about a rest wavelength within them, the one the dialog starts at, or one typed once its editing
finishes, or on OK: -726.906 to 692.126 km / s about Si IV 1402.77 in 4000255147's window, 1399.369
to 1406.009 Å, rounded outwards to the thousandth of a km / s, so irispy still takes every
wavelength of the window. Continuum windows are optional: line-free wavelength ranges outside the
velocity range, such as ``1401.6-1402.1, 1403.5-1404.3``, to which irispy's ``subtract_background``
fits the background of each spectrum, a constant to one window or a straight line to more, and
subtracts it; left blank, nothing is subtracted, and any continuum within the velocity range adds to
every map. irispy's ``calculate_moments`` computes the maps from the wavelengths within the velocity
range alone, and glue adds them as ``<label> moments <rest>``.

To take the velocity range from a Profile, drag a range over the line on the "Collapse" or "Fit"
tab of the "Options" of a Profile viewer of the window against its wavelength, such as a
quicklook's spectrum panel (see :ref:`the Profile guide
<glue_solar_user_guide_1dprofile_viewer_for_iris_data>`). While the range shows, the dialog shows it
too, and a rest wavelength within it, the one the dialog starts at or one typed, sets the
velocities to its ends, whatever the Profile's "x unit"; they can still be changed afterwards. A
range reaching past the window is cut to it, and the dialog says so, such as "1390.000 to 1415.000
Å, cut to the window: 1399.369 to 1406.009 Å"; one wholly outside it says "outside the window" and
sets nothing.

The maps are:

- ``intensity``, the sum of the samples, in irispy's ``DN_IRIS_FUV / s`` or ``DN_IRIS_NUV / s``, the
  window's DN / s by its detector: those of the window's ``<label> DN / s``, its DN over each raster
  step's exposure time (NaN at a step whose exposure time is 0 s), or of the window's own values, in
  their unit, for data without one;
- ``centroid``, the line's intensity-weighted mean wavelength, in Angstrom;
- ``width``, its standard deviation about the centroid, in Angstrom, not its full width at half maximum:
  for a Gaussian line within the velocity range, the FWHM is 2√(2 ln 2) ≈ 2.355 times the width,
  and a range that cuts the line off gives a smaller width;
- ``velocity`` and ``velocity_width``, the centroid's Doppler velocity from the rest wavelength and
  the width as a velocity, in km / s.

Velocities are relative to the uncorrected Level 2 wavelength scale, which can be off by about 5-10
km / s; for a FUV window, a rest wavelength shifted by a fitted O I 1355.5977 Å makes them relative
to a line at rest, and for a NUV window, one shifted by a fitted Ni I 2799.474 Å (see "Rest
wavelength from a measured line" in :ref:`the Profile guide
<glue_solar_user_guide_1dprofile_viewer_for_iris_data>`). Mg II h and k and C II are optically
thick: their profiles, often with two peaks about a central reversal, form over a range of heights,
so their centroid and width are proxies for the motions and broadening of the plasma, not
measurements of them.

A pixel whose every sample within the velocity range is missing (NaN or -Inf), or with too few
samples in the continuum windows to fit its background, is NaN in every map; irispy counts other
missing and negative samples, after any background is subtracted, as 0. A pixel with a saturated
sample within the velocity range, +Inf, as glue-solar reads 16182 DN, the Level 2 ceiling
saturated samples are clipped to (a sample merely that bright counts too, as Level 2 cannot tell
them apart), is NaN in every map too, as a background leaves +Inf as it is; the status bar and
``moments_saturated`` in ``meta`` say how many, as irispy counts them, and
:ref:`Was it saturated? <glue_solar_users_guide_iris_saturation>` shows where the samples are. A
pixel saturated across its continuum windows too has no background but keeps its +Inf, so it is
counted: the X1 flare's rasters r00172-r00174 of 3860258481 have 839 saturated Si IV 1402.77
pixels within ±107 km / s, with or without continuum windows 1401.6-1402.1 and 1403.5-1404.3 Å.

The new dataset's ``meta`` holds the observation's ``OBSID`` and ``STARTOBS``, ``moments_center``
and ``moments_velocity_range``, and with a continuum also ``moments_continuum``, the windows, and
``moments_continuum_degree``, the degree of the background; maps made before glue-solar took a
velocity range keep their ``moments_wings``, in Å, in sessions.
``glue_solar.sources.moments.line_moments(data, center, velocity_range, continuum, errors)``
computes the dataset in glue's terminal too, ``velocity_range`` a ``(lower, upper)`` pair in km / s
and ``continuum`` a list of ``(lower, upper)`` wavelengths in Å.

Error maps
----------

Tick "Error maps" in the dialog, unticked at first, to add each map's error, ``<map> error`` in the
map's unit: irispy's standard deviation of it, which ``calculate_moments`` propagates to first order
from that of each sample its reader gives with ``uncertainty=True``, the photon noise of its DN,
through the detector's gain and yield, and the read noise, over the raster step's exposure time for
DN / s. Samples are taken as independent, and a fitted background's own error is left out. An error is
NaN where its map is, and where irispy leaves it undefined: the intensity's where no sample is left,
the centroid's and the velocity's where fewer than two are, and the widths' where the width is 0. The
errors are statistical only, unreliable below a signal-to-noise ratio of about 5, and leave out the
wavelength calibration (see irispy's ``calculate_moments``). irispy takes about 1.7 times as long
with them. On 3610108077's full Si IV 1403 window they are irispy's own, from its reader, to 4e-9 or
better with or without a continuum. A rebinned window's (see :ref:`Rebinning
<glue_solar_users_guide_iris_rebinning>`) are refused: irispy would give each bin the noise of one
sample, not of their mean. A stack's errors are each scan's, as that scan alone gives them, from its
own exposure times.

.. _glue_solar_users_guide_iris_doppler:

Doppler images
--------------

A Doppler image maps a line's red wing less its blue wing, as CRISPEX's Doppler images do. At each
velocity v, each wing is the window's DN / s interpolated linearly at rest × (1 ± v/c), the optical
Doppler shift, between the two samples about it, each scan of a stack at its own wavelengths, and
its map, ``red - blue <v> km / s``, is the red wing less the blue: positive where the red wing is
brighter, as for a redshift. Glue adds them as ``<label> Doppler image <rest>``. A map is NaN where
either sample about a wing is missing, or saturated: +Inf, as glue-solar reads 16182 DN, the Level 2
ceiling saturated samples are clipped to (see :ref:`Was it saturated?
<glue_solar_users_guide_iris_saturation>`). A line symmetric about the rest wavelength gives 0, to
float precision, where the rest wavelength is a sample's or halfway between two; elsewhere the
interpolation leaves a small difference. Velocities are relative to the uncorrected Level 2
wavelength scale, as the line moments' are. The new dataset's ``meta`` holds the observation's
``OBSID`` and ``STARTOBS``, ``doppler_rest``, ``doppler_velocities`` and ``doppler_sign``,
``"red - blue"``. ``glue_solar.sources.doppler.doppler_image(data, rest, velocities, normalized)``
computes the dataset in glue's terminal too, at any positive ``velocities`` in km / s, and with
``normalized`` adds each map over the sum of its wings, ``(red - blue) / (red + blue) <v> km / s``,
NaN where a wing is not positive.

.. _glue_solar_users_guide_iris_red_blue:

Red-blue asymmetry
------------------

Red-blue asymmetry compares the red and blue wings of a line. irispy is given the window's DN / s
within 1 Å of the rest wavelength, so a Mg II k window's h line is left out, a slab of raster steps
of one scan at a time. Its ``calculate_red_blue_asymmetry`` interpolates each profile about its peak
every 5 km / s and divides the mean of its red wing, from 30 to 55 km / s above the peak, less the
mean of its blue wing, as far below it, by the peak: positive for excess red emission. These are the
wing velocities and step of SolarSoft's iris_xfiles (its double Gaussian fit,
``iris_moment__dgf.pro``). Glue adds ``<label> red-blue asymmetry <rest>``, with the maps:

- ``red_blue_asymmetry``, NaN where irispy does not compute it;
- ``quality``, irispy's ``RBAQualityFlag``: 0 computed, 1 no finite sample, 2 the peak at an end of
  the wavelengths taken, 3 too few samples, 4 the interpolation failed, 5 a peak of 0, 6 a wing not
  covered, 8 saturated: a sample taken is +Inf, as glue-solar reads 16182 DN (see :ref:`Was it
  saturated? <glue_solar_users_guide_iris_saturation>`); 7, below a minimum intensity, is never set.

Missing (NaN or -Inf) and negative samples are left out. The wings are measured from the peak,
which for the two peaks of Mg II or C II about their central reversal is the brighter one; the rest
wavelength sets the wavelengths taken and their velocities. The new dataset's ``meta`` holds the
observation's ``OBSID`` and ``STARTOBS``, ``red_blue_rest``, ``red_blue_wavelengths``,
``red_blue_velocities`` and ``red_blue_step``.
``glue_solar.sources.red_blue.red_blue_asymmetry(data, rest, wavelengths, velocities, step)``
computes the dataset in glue's terminal too, with other wavelengths taken, ``(below, above)`` in Å,
wing velocities and step.

What is refused
---------------

The entry is offered only for an IRIS raster window or a stack of its scans. Glue says why, and adds
nothing, for:

- a rest wavelength or continuum window that is not a wavelength, or a list of ranges, in Å;
- a velocity range that does not increase, or with no wavelength of the window within it about the
  rest wavelength, a continuum window with none, or one that overlaps the velocity range;
- a Doppler image's wing outside the window, or red-blue asymmetry with no wavelength of the window
  within 1 Å of the rest wavelength.

.. _glue_solar_users_guide_iris_rest_wavelength:

Rest wavelength
---------------

The rest wavelength of a spectral window, at which the line maps dialog starts, and from which a
Profile viewer gives the :ref:`Doppler velocity <glue_solar_users_guide_iris_velocity>` and the
Image viewer's "Cursor readout" (:ref:`Viewer tools and windows
<glue_solar_users_guide_viewer_tools_and_windows>`) the velocity under the mouse, is:

- the one set with "IRIS: set rest wavelength…" from the window's right-click menu, which lists the main
  IRIS lines within the window and takes a wavelength typed in Å, a blank one removing it. It is
  kept in the dataset's ``meta['rest_wavelength']``, in Å, which a script can set too;
- else the main IRIS line within the window's wavelengths (those the Profile viewer's "IRIS lines"
  button labels, at NIST vacuum wavelengths), or of several, as a Mg II k window holds k, h and the
  triplet, the one nearest the wavelength the window is named for, if within 1 Å: Mg II k
  2796.352 Å in ``Mg II k 2796``, C II 1335.7079 Å in ``C II 1336``, O I 1355.5977 Å in ``O I 1356``;
- else none, as for ``2832`` or ``Cl I 1352``.

The window's reference wavelength, ``TWAVE``, is never taken: it is not the line's (2796.20 Å for
Mg II k). The field's tooltip says where its wavelength comes from, and
``glue_solar.lines.rest_wavelength(data)`` gives it, or None, in glue's terminal. Mg II features
measure k and h from irispy's own rest wavelengths, or, with one set here, k from it and h from
irispy's h as far off (see :ref:`Mg II features <glue_solar_users_guide_iris_mg_features>`), and the
Profile viewer's "Gaussian + constant (IRIS)" fit names the main line nearest its fitted center
itself, as it has no dataset to read.

Line ratios
-----------

To map the electron density or the temperature from the ratio of two lines, such as O IV 1399.77
and 1401.16 Å, compute the line moments of each, select both maps in the data collection (Ctrl- or
⌘-click) and choose "IRIS: line ratio diagnostic…" from the right-click menu. Pick the numerator and
the denominator among the maps' attributes, their ``intensity`` unless changed, a text table of the
theoretical ratio, typed or with Browse…, and the quantity's name, ``log n_e``, ``log T`` or one
typed; a blank table or name adds nothing. The table's first two columns, separated by spaces or
commas, after an optional header line and ``#`` comments, are the quantity, such as log10 of the
electron density in cm⁻³, and the ratio of the numerator's line to the denominator's there,
monotonic in it, such as one computed with CHIANTI. irispy's ``map_ratio_to_quantity`` interpolates
the maps' ratio on it, linearly in the quantity, and glue adds ``<numerator> / <denominator> <name>``
on the maps' grid, with their helioprojective coordinates linked with the other IRIS datasets, in
an Image viewer, as the line maps open. Its maps are ``ratio``, the numerator over the denominator,
NaN where the denominator is 0, and the quantity, NaN where the ratio is missing or outside the
table's. Its ``meta`` holds the numerator's ``OBSID`` and ``STARTOBS``, ``ratio_numerator`` and
``ratio_denominator``, each ``<label>: <attribute>``, and ``ratio_table``, the table's path.
``glue_solar.sources.line_ratio.line_ratio(numerator, denominator, quantity, ratio, name)`` maps two
attributes, such as ``dc["<label>"].id["intensity"]``, on arrays in glue's terminal too.

In place of a table, tick "O IV 1399.8/1401.2 (CHIANTI, fiasco)" to map ``log n_e`` from the ratio
of the O IV 1399.8 Å line, the numerator, to the 1401.2 Å line, the denominator: irispy's
``density_diagnostic`` interpolates it, linearly in the electron density, on CHIANTI's ratio, which
fiasco computes on electron densities 0.1 dex apart, from and to the log cm⁻³ typed below the tick,
8 to 13 unless changed, at temperatures from log T 4.5 to 6, 0.05 apart, between which irispy
interpolates, linearly, at the log T typed, O IV's formation temperature, 5.15, unless changed.
Compute both moments with a narrow velocity range and a continuum (see above): with the default
range and none, the weak 1399.8 Å line's ratio lies above CHIANTI's, 0.17 to 0.42, at nearly every
pixel, which the map leaves NaN. The new dataset is as from a table, with ``ratio_preset`` in its
``meta`` in place of ``ratio_table``, and ``ratio_log_n_e`` and ``ratio_log_t``, the densities and
the temperature, and
``glue_solar.sources.line_ratio.o_iv_density(numerator, denominator, log_densities, log_temperature)``
maps it in glue's terminal too, ``log_densities`` a ``(from, to)`` pair. The preset needs fiasco
from its git main, glue-solar's ``density`` extra (see :ref:`installing <glue-solar-index>`);
without it, it is grayed out, and its tooltip says so.
On its first use fiasco downloads the CHIANTI database, 3.5 GB unpacked, and builds its own 2.2 GB
copy of it, in ``~/.fiasco`` or where ``~/.fiasco/fiascorc`` says, a path without ``em`` or ``ip``
in it, as in a folder named emily or Temp, or the build finds no ions: 3 minutes on a fast
connection, while glue's status bar says so; a later map takes a few seconds, also in the
background. Should glue quit while fiasco builds it, delete the unfinished ``chianti_dbase.h5``
before the next use.

The entry is offered only where the 2-D maps selected hold two attributes or more between them, not
for a subset group or other data. Glue says why, and adds nothing, for maps of different shapes or
coordinates or in different units, a table that cannot be read, has fewer than two columns, or
holds a ratio irispy cannot map from, such as one that is not monotonic, and O IV densities that do
not increase.

.. _glue_solar_users_guide_exporting_derived_data:

Exporting derived data
----------------------

To save a map with its coordinates, such as the line moments, a line ratio, a red-blue asymmetry or
the Mg II features, choose "Export Data/Subsets" in glue's toolbar, or "Export data values" from the
map's right-click menu, and "IRIS FITS (coordinates and Time)". As with glue's "FITS (1
component/HDU)", each attribute is an image named after it, with its unit in ``BUNIT``, and here
also the observation's ``OBSID`` and ``STARTOBS`` and the map's coordinates as a FITS-TAB WCS: the
helioprojective longitude and latitude of every pixel as glue gives them, shifted pointing included,
in degrees, in the ``WCS-TABLE`` extension, with the observer and time of their frame. A ``Time``
attribute is the ``TIME`` image, seconds since its ``DATEREF``, UTC. astropy reads them back, and
with sunpy imported gives positions in the observer's helioprojective frame::

    import astropy.units as u
    import sunpy.coordinates  # noqa: F401
    from astropy.io import fits
    from astropy.time import Time
    from astropy.wcs import WCS

    with fits.open("moments.fits") as hdus:
        wcs = WCS(hdus["INTENSITY"].header, fobj=hdus)
        position = wcs.pixel_to_world(slit, step)  # FITS order: the fastest axis first
        # for a map with a Time attribute
        times = Time(hdus["TIME"].header["DATEREF"], scale="utc") + hdus["TIME"].data * u.s

``glue_solar.sources.iris.export_iris_fits(filename, data)`` writes the file in glue's terminal too.
Only 2-D maps on helioprojective coordinates export so: glue says why for a raster window, a
slit-jaw image or other data, which glue's "FITS (1 component/HDU)" writes without their IRIS
coordinates.

1-D data, such as the light curves at a point (see :ref:`The quicklook
<glue_solar_users_guide_iris_quicklook>`), export with "ECSV (with Time)" as an ECSV table: a
column for each attribute, as glue's "Comma-separated table" writes them, with its unit, a time
such as ``Time`` as UTC times to the nanosecond, which astropy reads back as a
`~astropy.time.Time` (glue's "Comma-separated table" writes nanoseconds since 1970), and the
observation's ``OBSID`` and ``STARTOBS`` in its header::

    from astropy.table import Table

    curve = Table.read("curve.ecsv")
    curve["Time"]  # an astropy Time, UTC
    curve["Value"]  # in the data's unit

``glue_solar.sources.iris.export_ecsv(filename, data)`` writes the file in glue's terminal too, and
glue says why for data that are not 1-D.

The profiles a Profile viewer draws, such as a quicklook's spectrum panel, save with "IRIS: save
profiles as ECSV…" in its save menu, a column for each layer's x, y, time and position, named after
the layer (see :ref:`Saving the profiles <glue_solar_users_guide_iris_save_profiles>`).
