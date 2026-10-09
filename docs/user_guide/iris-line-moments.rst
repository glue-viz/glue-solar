.. _glue_solar_users_guide_iris_line_moments:

============
Line moments
============

To map a spectral line, select a raster window of one scan in the data collection and choose "IRIS:
line moments…" from its right-click menu. Type the line centre in Å, the rest wavelength of the
velocities (the window's reference wavelength is never assumed), and the wings, the wavelengths
taken below and above it, ±0.5 Å unless changed; a blank centre adds nothing. Continuum windows are
optional: line-free wavelength ranges outside the wings, such as ``1401.6-1402.1, 1403.5-1404.3``,
to which irispy's ``subtract_background`` fits the background of each spectrum, a constant to one
window or a straight line to more, and subtracts it; left blank, nothing is subtracted, and any
continuum within the wings adds to every map. irispy's ``calculate_moments`` computes the maps on a
worker thread from the wavelengths within the wings alone, while glue's status bar says "Computing
line moments of <label>…", and adds ``<label> moments <centre>`` on the window's raster steps and
slit pixels, with their helioprojective coordinates in arcsec linked with the other IRIS datasets.
No viewer opens: drag it onto an Image viewer and pick a map as its attribute.

The maps
--------

- ``intensity``, the sum of the samples, in DN/s: those of the window's ``<label> DN/s``, its DN over
  each raster step's exposure time (NaN at a step whose exposure time is 0 s), or of the window's
  own values, in their unit, for data without one;
- ``centroid``, the line's intensity-weighted mean wavelength, in Å;
- ``width``, its standard deviation about the centroid, in Å, not its full width at half maximum:
  for a Gaussian line within the wings, the FWHM is 2√(2 ln 2) ≈ 2.355 times the width, and wings
  that cut the line off give a smaller width;
- ``velocity`` and ``velocity_width``, the centroid's Doppler velocity from the centre and the width
  as a velocity, in km/s.

Velocities are relative to the uncorrected Level 2 wavelength scale, which can be off by about
5-10 km/s; for a FUV window, a centre shifted by a fitted O I 1355.5977 Å makes them relative to a
line at rest, and for a NUV window, one shifted by a fitted Ni I 2799.474 Å (see "Rest wavelength
from a measured line" in
:ref:`the Profile guide <glue_solar_user_guide_1dprofile_viewer_for_iris_data>`). Mg II h and k and
C II are optically thick: their profiles, often with two peaks about a central reversal, form over
a range of heights, so their centroid and width are proxies for the motions and broadening of the
plasma, not measurements of them.

A pixel whose every sample within the wings is missing (NaN or -Inf), or with too few samples in the
continuum windows to fit its background, is NaN in every map; irispy counts other missing and
negative samples, after any background is subtracted, as 0. A pixel with a sample within the wings
at 16182 DN, the Level 2 ceiling saturated samples are clipped to (a sample merely that bright
counts too, as Level 2 cannot tell them apart), is NaN in every map too; the status bar and
``moments_saturated`` in ``meta`` say how many, and
:ref:`Was it saturated? <glue_solar_users_guide_iris_saturation>` shows where the samples are.

The new dataset's ``meta`` holds the observation's ``OBSID`` and ``STARTOBS``, ``moments_centre``
and ``moments_wings``, and with a continuum also ``moments_continuum``, the windows, and
``moments_continuum_degree``, the degree of the background.
``glue_solar.sources.moments.line_moments(data, centre, wings, continuum, errors)`` computes the
dataset in glue's terminal too, ``continuum`` a list of ``(lower, upper)`` wavelengths in Å.

Error maps
----------

Tick "Error maps" in the dialog, unticked at first, to add each map's error, ``<map> error`` in the
map's unit: irispy's standard deviation of it, which ``calculate_moments`` propagates to first order
from that of each sample its reader gives with ``uncertainty=True``, the photon noise of its DN,
through the detector's gain and yield, and the read noise, over the raster step's exposure time for
DN/s. Samples are taken as independent, and a fitted background's own error is left out. An error is
NaN where its map is, and where irispy leaves it undefined: the intensity's where no sample is left,
the centroid's and the velocity's where fewer than two are, and the widths' where the width is 0. The
errors are statistical only, unreliable below a signal-to-noise ratio of about 5, and leave out the
wavelength calibration (see irispy's ``calculate_moments``). irispy takes about 1.7 times as long
with them. On 3610108077's full Si IV 1403 window they are irispy's own, from its reader, to 4e-9 or
better with or without a continuum. A rebinned window's (see :ref:`Rebinning
<glue_solar_users_guide_iris_rebinning>`) are refused: irispy would give each bin the noise of one
sample, not of their mean.

What is refused
---------------

Glue says why, and adds nothing, for:

- a stack of scans: its scans load one by one without "Stack sequential raster scans" in the
  observation browser;
- a slit-jaw image or any other data than an IRIS raster window;
- a centre or continuum window that is not a wavelength, or a list of ranges, in Å;
- a centre with no wavelength of the window within the wings, a continuum window with none, or one
  that overlaps the wings.

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
on the maps' grid, with their helioprojective coordinates linked with the other IRIS datasets, and
no viewer. Its maps are ``ratio``, the numerator over the denominator, NaN where the denominator is
0, and the quantity, NaN where the ratio is missing or outside the table's. Its ``meta`` holds the
numerator's ``OBSID`` and ``STARTOBS``, ``ratio_numerator`` and ``ratio_denominator``, each
``<label>: <attribute>``, and ``ratio_table``, the table's path.
``glue_solar.sources.line_ratio.line_ratio(numerator, denominator, quantity, ratio, name)`` maps two
attributes, such as ``dc["<label>"].id["intensity"]``, on arrays in glue's terminal too.

In place of a table, tick "O IV 1399.8/1401.2 (CHIANTI, fiasco)" to map ``log n_e`` from the ratio
of the O IV 1399.8 Å line, the numerator, to the 1401.2 Å line, the denominator: irispy's
``density_diagnostic`` interpolates it, linearly in the electron density, on CHIANTI's ratio, which
fiasco computes for 10⁸ to 10¹³ cm⁻³ at O IV's formation temperature, log T 5.15. Compute both
moments with narrow wings and a continuum (see above): with the default wings and none, the weak
1399.8 Å line's ratio lies above CHIANTI's, 0.17 to 0.42, at nearly every pixel, which the map
leaves NaN. The new dataset is as from a table, with ``ratio_preset`` in its ``meta`` in place of
``ratio_table``, and ``glue_solar.sources.line_ratio.o_iv_density(numerator, denominator)`` maps it
in glue's terminal too. The preset needs fiasco from its git main, glue-solar's ``density`` extra
(see :ref:`installing <glue-solar-index>`); without it, it is greyed out, and its tooltip says so.
On its first use fiasco downloads the CHIANTI database, 3.5 GB unpacked, and builds its own 2.2 GB
copy of it, in ``~/.fiasco`` or where ``~/.fiasco/fiascorc`` says, a path without ``em`` or ``ip``
in it, as in a folder named emily or Temp, or the build finds no ions: 3 minutes on a fast
connection, while glue's status bar says so; a later map takes a few seconds, also in the
background. Should glue quit while fiasco builds it, delete the unfinished ``chianti_dbase.h5``
before the next use.

Glue says why, and adds nothing, for fewer than two attributes of 2-D maps selected, maps of
different shapes or coordinates or in different units, and a table that cannot be read, has fewer
than two columns, or holds a ratio irispy cannot map from, such as one that is not monotonic.
