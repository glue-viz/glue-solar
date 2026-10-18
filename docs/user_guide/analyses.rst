.. _glue_solar_users_guide_analyses:

========
Analyses
========

Each analysis is in the right-click menu of a dataset in the data collection. It runs in the
background while glue's status bar says so, adds its result as a new dataset, linked with the other
IRIS data, and opens it in an Image viewer in the current tab, with the quicklook's point. A stack's
result has a scan slider, each scan's as that scan alone gives it. The result's ``meta`` holds the
observation's ``OBSID`` and ``STARTOBS`` and the settings used. To save a map with its coordinates,
see :ref:`Exporting derived data <glue_solar_users_guide_exporting_derived_data>`.

Should an analysis refuse its data or settings, glue says why and adds nothing.

.. _glue_solar_users_guide_iris_line_moments:

Line maps
---------

1. Select a raster window, or a stack of its scans, and choose "IRIS: line maps…".
2. Check the rest wavelength, in Å: it starts at the window's (see `Rest wavelength`_), such as
   2796.352 for Mg II k.
3. Tick the maps to make: "Line moments", ticked at first, "Doppler image" and "Red-blue asymmetry".
4. For the line moments, set the velocities, from and to, in km / s from the rest wavelength:
   -107 to 107 km / s unless changed, ±0.5 Å at Si IV 1402.77. Optionally, type continuum windows,
   line-free ranges outside the velocities such as ``1401.6-1402.1, 1403.5-1404.3``, and tick
   "Error maps".
5. Press OK.

To take the velocities from a spectrum, drag a range over the line on the "Collapse" or "Fit" tab
of a Profile viewer of the window, such as a quicklook's spectrum panel (see :ref:`The spectrum
panel <glue_solar_users_guide_iris_spectrum_panel>`), then open the dialog: the velocities reach the
range's ends about a rest wavelength within it.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Map
     - Dataset
     - Attributes
   * - Line moments
     - ``<label> moments <rest>``
     - ``intensity``, the sum over the velocities, in DN / s; ``centroid`` and ``width``, in
       Angstrom; ``velocity`` and ``velocity_width``, in km / s
   * - Doppler image
     - ``<label> Doppler image <rest>``
     - ``red - blue <v> km / s`` at 10, 20, 30, 40 and 50 km / s
   * - Red-blue asymmetry
     - ``<label> red-blue asymmetry <rest>``
     - ``red_blue_asymmetry`` and ``quality``

**Line moments** are irispy's ``calculate_moments`` of the wavelengths within the velocities. With
continuum windows, irispy's ``subtract_background`` first fits each spectrum's background, a
constant to one window or a straight line to more, and subtracts it; without, any continuum adds to
every map. ``width`` is the standard deviation about the centroid, not the full width at half
maximum, which is 2.355 times it for a Gaussian. Mg II h and k and C II are optically thick, so
their centroid and width are proxies for the plasma's motions and broadening, not measurements of
them.

**Error maps** add ``<map> error``: the photon and read noise of each sample, propagated by irispy.
They are statistical only and unreliable below a signal-to-noise ratio of about 5. They are refused
for a rebinned window, as irispy would give each bin the noise of one sample.

**Doppler images**, as CRISPEX makes them, are the red wing less the blue wing, each interpolated at
rest × (1 ± v / c): positive where the red wing is brighter, as for a redshift.

**Red-blue asymmetry** is irispy's ``calculate_red_blue_asymmetry`` of the wavelengths within 1 Å of
the rest wavelength: the mean of the red wing, 30 to 55 km / s above the peak, less that of the blue
wing as far below, over the peak, with the wings and step of SolarSoft's iris_xfiles. It is positive
for excess red emission. ``quality`` is irispy's ``RBAQualityFlag``, 0 where computed and 8 where a
sample is saturated. On Mg II and C II, the peak is the brighter of the two about the central
reversal.

The velocities are on the uncorrected Level 2 wavelength scale, which can be off by 5 to 10 km / s.
To correct them, set a rest wavelength measured on a line at rest (see "Rest wavelength from a
measured line" in :ref:`The spectrum panel <glue_solar_users_guide_iris_spectrum_panel>`).

A pixel is NaN where a sample taken is missing or saturated (see :ref:`Missing and saturated samples
<glue_solar_users_guide_iris_saturation>`); the status bar counts the saturated pixels of the line
moments.

In glue's terminal, ``glue_solar.sources.moments.line_moments(data, center, velocity_range,
continuum, errors)``, ``glue_solar.sources.doppler.doppler_image(data, rest, velocities,
normalized)`` and ``glue_solar.sources.red_blue.red_blue_asymmetry(data, rest, wavelengths,
velocities, step)`` make the same datasets, with other settings.

.. _glue_solar_users_guide_iris_line_fit_maps:

Line fit maps
-------------

To fit a line in every spectrum of a raster window, or of each scan of a stack:

1. On the "Fit" tab of a Profile viewer of the window, such as a quicklook's spectrum panel (see
   :ref:`The spectrum panel <glue_solar_users_guide_iris_spectrum_panel>`), fit one spectrum with
   "Gaussian + constant (IRIS)": drag over the line, with the function "Mean" or "Median" and a
   length, such as ``Angstrom``, as the x unit, and press "Fit". "Settings" builds the model (see
   :ref:`Building the model <glue_solar_users_guide_iris_fit_settings>`).
2. Select the window in the data collection and choose "IRIS: line fit maps".

The window's last such fit, in any of its Profile viewers, is fitted to every spectrum over the
range dragged with astropy's ``parallel_fit_dask``, on all processor cores, while a progress dialog
shows the run; "Cancel" stops it and adds nothing. Where the window and a subset of it are both
shown at the fit, the fit of the layer listed last, usually the subset, is the one taken. Each
spectrum starts at its own background, its 10th percentile, and at each line's peak within two
widths of the fitted center, among the samples nearer it than any other line's; the widths, fixed
values, bounds and ties are as fitted. Missing samples are
left out, and saturated ones, which are only a lower bound. The fit of step 1 leaves a sample out
where all the pixels it combines are saturated (for a Point, where it is), and notes the wavelengths
whose mean includes saturated pixels. A full Si IV 1403 raster, 175,000 spectra, takes about a minute
on 12 cores and 8 GB of memory, the worker processes included.

The result, ``<label> fit <rest>``, holds irispy's ``maps_from_fit`` maps of each line ``i``:
``velocity_i`` and ``fwhm_velocity_i`` in km / s, from the rest wavelength, ``fwhm_i`` in Angstrom
and ``integrated_intensity_i``; then ``quality``, irispy's ``FitQualityFlag``: 0 for a good fit, 1
for none (every sample missing), 2 where the fitter did not converge, 3 where a parameter stopped at
a bound and 4 where the spectrum has missing samples; then each parameter of the model. Each map but
``quality`` has ``<map> error``, from the fit's covariance.

The fits run in Python processes that import the script that started glue: a script of your own
that starts glue needs Python's ``if __name__ == "__main__":`` guard.

.. _glue_solar_users_guide_iris_rest_wavelength:

Rest wavelength
---------------

The line maps, the Profile viewer's :ref:`Doppler velocity <glue_solar_users_guide_iris_velocity>`
and the cursor readout's velocity take a window's rest wavelength:

- the one set with "IRIS: set rest wavelength…" in the window's right-click menu, which lists the
  main IRIS lines within the window and takes a wavelength typed in Å, a blank one removing it. A
  script can set ``meta['rest_wavelength']``, in Å, too;
- else the main IRIS line within the window nearest the wavelength it is named for, within 1 Å, at
  its NIST vacuum wavelength: Mg II k 2796.352 Å in ``Mg II k 2796``, C II 1335.7079 Å in
  ``C II 1336``;
- else none, as for ``2832``.

The window's ``TWAVE`` is never taken: it is not the line's. The tooltip of the line maps' field
says where its wavelength comes from.

.. _glue_solar_users_guide_iris_line_ratio:

Line ratios
-----------

To map the electron density or the temperature from the ratio of two lines, such as O IV 1399.77
and 1401.16 Å:

1. Make the line moments of each line, with a narrow velocity range and continuum windows.
2. Select both maps in the data collection (:kbd:`Ctrl`-click, :kbd:`Cmd`-click on macOS) and
   choose "IRIS: line ratio diagnostic…".
3. Pick the numerator and the denominator, their ``intensity`` unless changed.
4. Give a ratio table, typed or with "Browse…", and the quantity's name: ``log n_e``, ``log T`` or
   one typed. Or tick "O IV 1399.8/1401.2 (CHIANTI, fiasco)" for ``log n_e`` from O IV.

The table is a text file of two columns, separated by spaces or commas, after an optional header
line and ``#`` comments: the quantity, such as log10 of the electron density in cm⁻³, and the
theoretical ratio there, monotonic in it, such as one computed with CHIANTI. irispy's
``map_ratio_to_quantity`` interpolates the maps' ratio on it. The result,
``<numerator> / <denominator> <name>``, holds ``ratio`` and the quantity, NaN where the ratio lies
outside the table's.

The O IV preset uses irispy's ``density_diagnostic`` on CHIANTI's ratio, which fiasco computes at
the densities typed and at the temperature typed, 8 to 13 log cm⁻³ and log T 5.15 unless changed. It
needs fiasco, in the ``density`` extra (see :ref:`Installing glue-solar <glue-solar-index>`);
without it, it is grayed out. On its first use, fiasco downloads and builds the CHIANTI database, a
few GB, in ``~/.fiasco``, while the status bar says so. Keep ``em`` and ``ip`` out of that folder's
path, as in a folder named emily or Temp, or the build finds no ions. If glue quits during the
build, delete the unfinished ``chianti_dbase.h5`` before the next use.

In glue's terminal, ``glue_solar.sources.line_ratio.line_ratio(numerator, denominator, quantity,
ratio, name)`` and ``glue_solar.sources.line_ratio.o_iv_density(numerator, denominator,
log_densities, log_temperature)`` make the same datasets.

.. _glue_solar_users_guide_iris_mg_features:

Mg II features
--------------

1. Select a raster window, or a stack of its scans, covering Mg II k or h, such as "Mg II k 2796",
   and choose "IRIS: Mg II features… (Mg II)".
2. Set the Doppler velocities searched, -40 to 40 km / s from each line unless changed, and tick
   the lines, k and h.
3. Press OK.

irispy's ``calculate_mg_features``, after Pereira et al. (2013) and SolarSoft's
``iris_get_mg_features.pro``, finds each line's center, k3 or h3, at its central reversal, and its
blue and red emission peaks, k2v and k2r or h2v and h2r. The result, ``<label> Mg II features``,
has for each feature:

- ``<feature>_velocity``, in km / s from the line's rest wavelength, on the uncorrected Level 2
  wavelength scale;
- ``<feature>_intensity``, in DN / s.

A feature is NaN where irispy finds none, or where a sample searched is missing or saturated;
``k saturated`` and ``h saturated`` are 1 at those saturated pixels.

irispy measures k from 2796.351 Å and h from 2803.530 Å. A rest wavelength set on the window, such
as Mg II k corrected by a fit of Ni I 2799.474 Å, is taken as k's, and h moves with it. One more
than 1 Å from 2796.351 Å, such as Mg II h's, is refused: clear it first.

In glue's terminal, ``glue_solar.sources.mg_features.mg_features(data, velocities, lines)`` makes
the same dataset.

.. _glue_solar_users_guide_iris_bursts:

UV bursts
---------

1. Select a raster window covering Si IV 1402.77 Å, such as "Si IV 1403", a stack of its scans, or
   a 1400 Å slit-jaw image, and choose "IRIS: detect UV bursts… (Si IV, SJI 1400)".
2. Change irispy's parameters if you need to, and press OK.

Two datasets are added: ``<label> bursts``, a map of the bursts' labels, 0 outside them and 1 to N
for N bursts, which opens in an Image viewer; and ``<label> burst events``, a table with a row a
burst. Drag the table onto a Table viewer: click a column's header to sort by it, and type in the
search box, such as ``T17:2`` for the bursts from 17:20 to 17:29. Or plot it in a Scatter viewer,
such as ``time`` against ``intensity``, or ``coordinate.Tx`` against ``coordinate.Ty``.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * -
     - Raster window
     - Slit-jaw image
   * - irispy
     - ``find_si_iv_bursts``, a port of ``iris_burst_check.pro`` (Young et al. 2018)
     - ``find_sji_bursts``, a port of ``iris_sji_burst_check.pro``
   * - A burst pixel
     - The mean over the velocities, ±50 km / s of Si IV 1402.77 Å, in DN / s, reaches the threshold,
       but stays below 10 times their median, a particle-hit test ("off" turns it off). A threshold
       left blank is irispy's, scaled by the effective area at the observation's date.
     - 10 standard deviations above its frame's median, unless changed.
   * - A burst
     - Pixels that touch, diagonally too; on a sit-and-stare raster, in time too.
     - Pixels that touch within a frame, diagonally too, 2 or more unless changed.
   * - Table columns
     - ``label``, ``raster`` (a stack's scan) and ``npix``; the ``step``, ``y``, ``time``,
       ``coordinate.Tx``, ``coordinate.Ty`` and ``intensity`` of its brightest pixel
     - ``label``, ``frame``, ``npix`` and ``threshold``; the ``y``, ``x``, ``time``,
       ``coordinate.Tx``, ``coordinate.Ty`` and ``intensity`` of its brightest pixel

On a slit-jaw image, 10 standard deviations are a quick look: on active-region data they find bursts
in every frame, and Young et al. (2018) recommend a threshold chosen for each observation. A
slit-jaw image with its :ref:`dust removed <glue_solar_users_guide_iris_calibration>` works too. The
table's coordinates follow :ref:`"IRIS: shift pointing…" <glue_solar_users_guide_iris_pointing>`.

In glue's terminal, ``glue_solar.sources.bursts.si_iv_bursts(data, threshold, velocity_range,
median_factor)`` and ``glue_solar.sources.bursts.sji_bursts(data, sigma_factor, min_pixels)`` make
the same datasets.
