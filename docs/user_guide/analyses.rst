.. _glue_solar_users_guide_analyses:

========
Analyses
========

Each analysis is in the right-click menu of a dataset in the data collection, but for the line fit
maps, which start on a Profile viewer's "Fit" tab. It runs in the background while glue's status bar
says so. Its result is a new dataset, linked with the other IRIS data, which opens in an Image viewer
in the current tab, with the quicklook's point. A stack's result has a scan slider, each scan's as
that scan alone gives it. The result's ``meta`` holds the observation's ``OBSID`` and ``STARTOBS``
and the settings used. To save a map of one scan with its coordinates, see :ref:`Exporting derived
data <glue_solar_users_guide_exporting_derived_data>`.

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
panel <glue_solar_users_guide_iris_spectrum_panel>`). Then open the dialog: the velocities reach the
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

**Line moments** are irispy's line moments of the wavelengths within the velocities. With continuum
windows, each spectrum's background is fitted first, a constant to one window or a straight line to
more, and subtracted. Without them, any continuum adds to every map. ``width`` is the standard
deviation about the centroid, not the full width at half maximum, which is 2.355 times it for a
Gaussian. Mg II h and k and C II are optically thick, so their centroid and width are proxies for
the plasma's motions and broadening, not measurements of them.

**Error maps** add ``<map> error``: the photon and read noise of each sample, propagated by irispy.
They are statistical only and unreliable below a signal-to-noise ratio of about 5. They are refused
for a rebinned window, whose bins would each get the noise of one sample.

**Doppler images**, as CRISPEX makes them, are the red wing less the blue wing, each interpolated at
rest × (1 ± v / c): positive where the red wing is brighter, as for a redshift.

**Red-blue asymmetry** is irispy's red-blue asymmetry of the wavelengths within 1 Å of the rest
wavelength. It is the mean of the red wing, 30 to 55 km / s above the peak, less that of the blue
wing as far below, over the peak. The wings and step are those of SolarSoft's iris_xfiles. It is
positive for excess red emission. ``quality`` is 0 where it is computed and 8 where a sample is
saturated. On Mg II and C II, the peak is the brighter of the two about the central reversal.

The velocities are on the uncorrected Level 2 wavelength scale. To correct them, set a rest
wavelength measured on a line at rest (see "Rest wavelength from a measured line" under
`Line fit maps`_).

A line moments pixel is NaN where every sample within the velocities is missing, or one there is
saturated (see :ref:`Missing and saturated samples <glue_solar_users_guide_iris_saturation>`).
Any other missing sample counts as 0, so lowers its intensity. The red-blue asymmetry leaves missing
samples out, and is NaN where ``quality`` is not 0. A Doppler image pixel is NaN
where either sample it interpolates between is missing or saturated. The status bar counts the
saturated pixels of the line moments.

In glue's terminal, :func:`glue_solar.sources.moments.line_moments`,
:func:`glue_solar.sources.doppler.doppler_image` and
:func:`glue_solar.sources.red_blue.red_blue_asymmetry` make the same datasets, with other settings.

.. _glue_solar_users_guide_iris_line_fit_maps:

Line fit maps
-------------

To fit a line in every spectrum of a raster window, or of each scan of a stack:

1. Open the "Fit" tab of a Profile viewer of the window, such as a quicklook's spectrum panel (see
   :ref:`The spectrum panel <glue_solar_users_guide_iris_spectrum_panel>`).
2. Set the viewer's function to "Mean" or "Median", and its x unit to a length, such as
   ``Angstrom``, or to ``km / s`` from the rest wavelength.
3. Fit one spectrum with "Gaussian + constant": drag over the line and press "Fit". "Settings"
   builds the model (see :ref:`Building the model <glue_solar_users_guide_iris_fit_settings>`).
4. Press "Fit every spectrum", beside "Fit". Its tooltip says why while it is grayed.

The viewer's last such fit is fitted to every spectrum over the range dragged, on all processor
cores. A fit made in ``km / s`` is converted to Angstrom exactly. A progress dialog shows the run;
"Cancel" stops it and adds nothing. Where the window and a subset of it are both shown at the fit,
the fit of the layer listed last, usually the subset, is the one taken. A linear or polynomial
background with a bound or a fixed term needs a fit against a length. Each spectrum starts at its
own background and line peaks; the widths, fixed values, bounds and ties are as fitted. Missing
samples are left out, and saturated ones, which are only a lower bound. A large window takes minutes
and several GB of memory.

The result, ``<label> fit <rest>``, holds for each line ``i`` its ``velocity_i`` and
``fwhm_velocity_i`` in km / s, from the rest wavelength, its ``fwhm_i`` in Angstrom and its
``integrated_intensity_i``. Then comes ``quality``: 0 for a good fit, 1 for none (every sample
missing), 2 where the fitter did not converge, 3 where a parameter stopped at a bound and 4 where
the spectrum has samples left out, missing or saturated. Then comes each parameter of the model.
Each map but ``quality`` has ``<map> error``, from the fit's covariance.

A script of your own that starts glue needs Python's ``if __name__ == "__main__":`` guard, as the
fits run in processes that import it.

.. _glue_solar_users_guide_iris_fit_settings:

**Building the model.** "Settings" on the "Fit" tab lists the components of "Gaussian + constant",
at first a constant background and a Gaussian. Pick a Gaussian, a Lorentzian, or a constant,
linear or polynomial background (with its degree) and press "Add"; "Remove" drops one. Each parameter
has a start (blank: from the data), "Fixed", and a lower and an upper bound, either alone. A line's
parameter can be "Tied to" the same parameter of a line above it. A tied amplitude or width is that
line's times the ratio (blank: the same). A tied center is that line's plus the separation, in the x
unit. A tie to a tied line follows it, its separations adding up and its ratios multiplying. For
C II 1334.53 Å and its 1335.66 and 1335.71 Å blend:

1. Add two Gaussians and give ``mean_1`` the start 1334.53.
2. Tie ``mean_2`` to ``mean_1`` by 1.1305, and ``mean_3`` to ``mean_1`` by 1.1756.
3. Give each amplitude the lower bound 0, press "OK", drag over 1334.1 to 1336.2 Å and press "Fit".

The fit is drawn over the spectrum in a darker shade of its color, with each line on the background
dashed; "Clear" removes them. A line without a start begins at one of the most prominent peaks.
These are emission peaks only where each such line's amplitude has a lower bound of 0 or more, and
absorption peaks only where each has an upper bound of 0 or less. Each line then starts at its peak
among the samples nearer its center than any other line's, so give a blend's lines starts or ties.
The fit can be made with the x unit in Å or ``km / s``, the starts, bounds and separations then in
it.

**Saving a model.** "Save…" in Settings writes the components and every start, "Fixed", bound and
tie to a file, and "Open…" reads one back. Its values are in the x unit it was made in.

**Mg II.** Mg II k and h are each double-peaked. Drag the Fit range over one line's core, about
±40 km / s, and press "Mg II two peaks" in Settings. The model is then two Gaussians on a constant,
one for each emission peak (k2v and k2r, or h2v and h2r), each starting at its peak. Fit the other
line in its own range. For the peaks' and line centers' positions without a fit, use "IRIS: Mg II
features…".

**Rest wavelength from a measured line.** Level 2 wavelengths can be off by 5 to 10 km / s, and the
FUV and NUV drift apart. Measure the offset in a quicklook's spectrum panel, on a line nearly at
rest: O I 1355.5977 Å for the FUV windows (C II, Si IV, O I), or Ni I 2799.474 Å in the Mg II k 2796
window for the NUV.

1. Tick the window's own layer, hidden at first, in glue's "Plot Layers" list: at the function "Mean", as the
   panel opens, it is the whole raster's mean spectrum.
2. On the "Fit" tab, pick "Gaussian + constant" and drag over the line: about 1355.4 to
   1355.8 Å for O I, or 2799.3 to 2799.65 Å for Ni I. Press "Fit".
3. Add the offset, the fitted center less the line's rest wavelength, to the rest wavelength of a
   line on the same detector, and set that with "Set rest wavelength…" on its window.

On OBSID 3824262996, O I fits at 1355.6172 Å (+4.30 km / s), so Si IV 1402.77 Å becomes
1402.789 Å. A saturated sample is only a lower bound. The fit leaves a sample out where all the
pixels it combines are saturated (for a Point, where it is), and says how many. It also notes the
wavelengths whose mean includes saturated pixels, biased low (see :ref:`Missing and saturated samples
<glue_solar_users_guide_iris_saturation>`).

.. _glue_solar_users_guide_iris_rest_wavelength:

Rest wavelength
---------------

The line maps, the Profile viewer's :ref:`Doppler velocity <glue_solar_users_guide_iris_velocity>`
and the cursor readout's velocity take a window's rest wavelength. It is the one set with "Set rest
wavelength…" in the window's right-click menu. The dialog lists the main lines within the window
and takes a wavelength typed in Å; a blank one removes it. A script can set
``meta['rest_wavelength']``, in Å, too. With none set, it is:

- on IRIS data, the main IRIS line of the window's ion nearest the wavelength it is named for,
  within 1 Å. It is at its vacuum wavelength in irispy's line catalog: Mg II k 2796.352 Å in
  ``Mg II k 2796``, O I 1355.59767 Å in ``O I 1356``;
- on DKIST data, the ground-based line within its wavelengths. Of several, it is that of the ion its
  ``WAVEBAND`` names nearest its ``LINEWAV``: He I 10830.25011 Å in ``He I (1083.0 nm)``;
- on an SST cube, the ground-based line, in air, within its wavelengths. Of several, it is the one
  nearest its line core: Ca II K 3933.66 Å in a CHROMIS Ca II H and K cube;
- none without such a line, as for ``2832``.

The window's ``TWAVE`` is never taken: it is not the line's. The tooltip of the line maps' field
says where its wavelength comes from.

.. _glue_solar_users_guide_iris_line_ratio:

Line ratios
-----------

To map the electron density or the temperature from the ratio of two lines, such as O IV 1399.77
and 1401.16 Å:

1. Make the line moments of each line, with a narrow velocity range and continuum windows.
2. Select both maps in the data collection (:kbd:`Ctrl`-click, :kbd:`Cmd`-click on macOS) and
   choose "Line ratio diagnostic…".
3. Pick the numerator and the denominator, their ``intensity`` unless changed.
4. Give a ratio table, typed or with "Browse…", and the quantity's name: ``log n_e``, ``log T`` or
   one typed. Or tick "O IV 1399.8/1401.2 (CHIANTI, fiasco)" for ``log n_e`` from O IV.

The table is a text file of two columns, separated by spaces or commas, after an optional header
line and ``#`` comments. The first column is the quantity, such as log10 of the electron density in
cm⁻³. The second is the theoretical ratio there, monotonic in it, such as one computed with CHIANTI.
The maps' ratio is interpolated on the table. The result,
``<numerator> / <denominator> <name>``, holds ``ratio`` and the quantity, NaN where the ratio lies
outside the table's.

The O IV preset takes CHIANTI's ratio, which fiasco computes at the densities and the temperature
typed: 8 to 13 log cm⁻³ and log T 5.15 unless changed. It needs fiasco, in the ``density`` extra
(see :ref:`Installing glue-solar <glue-solar-index>`);
without it, it is grayed out. On its first use, fiasco downloads and builds the CHIANTI database, a
few GB, in ``~/.fiasco``, while the status bar says so. Keep ``em`` and ``ip`` out of that folder's
path, as in a folder named emily or Temp, or the build finds no ions. If glue quits during the
build, delete the unfinished ``chianti_dbase.h5`` before the next use.

In glue's terminal, :func:`glue_solar.sources.line_ratio.line_ratio` and
:func:`glue_solar.sources.line_ratio.o_iv_density` make the same datasets.

.. _glue_solar_users_guide_iris_mg_features:

Mg II features
--------------

1. Select a raster window, or a stack of its scans, covering Mg II k or h, such as "Mg II k 2796",
   and choose "IRIS: Mg II features…".
2. Set the Doppler velocities searched, -40 to 40 km / s from each line unless changed, and tick
   the lines, k and h.
3. Press OK.

irispy's Mg II feature search, after Pereira et al. (2013), finds each line's center, k3 or h3, at
its central reversal, and its blue and red emission peaks, k2v and k2r or h2v and h2r. The result,
``<label> Mg II features``, has for each feature:

- ``<feature>_velocity``, in km / s from the line's rest wavelength, on the uncorrected Level 2
  wavelength scale;
- ``<feature>_intensity``, in DN / s.

A feature is NaN where none is found, or where a sample searched is missing or saturated;
``k saturated`` and ``h saturated`` are 1 at those saturated pixels.

The velocities are from 2796.351 Å for k and 2803.530 Å for h. A rest wavelength set on the window,
such as Mg II k corrected by a fit of Ni I 2799.474 Å, is taken as k's, and h moves with it. One
more than 1 Å from 2796.351 Å, such as Mg II h's, is refused: clear it first.

In glue's terminal, :func:`glue_solar.sources.mg_features.mg_features` makes the same dataset.

.. _glue_solar_users_guide_iris_bursts:

UV bursts
---------

1. Select a raster window covering Si IV 1402.77 Å, such as "Si IV 1403", a stack of its scans, or
   a 1400 Å slit-jaw image, and choose "IRIS: detect UV bursts…".
2. Change the parameters if you need to, and press OK.

Two datasets are added. ``<label> bursts`` is a map of the bursts' labels, 0 outside them and 1 to N
for N bursts, which opens in an Image viewer. ``<label> burst events`` is a table with a row a
burst. Drag the table onto a Table viewer: click a column's header to sort by it, and type in the
search box, such as ``T17:2`` for the bursts from 17:20 to 17:29. Or plot it in a Scatter viewer,
such as ``time`` against ``intensity``, or ``coordinate.Tx`` against ``coordinate.Ty``.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * -
     - Raster window
     - Slit-jaw image
   * - Method
     - irispy's Si IV burst search, after Young et al. (2018)
     - irispy's search for bright events in an image
   * - A burst pixel
     - The mean over the velocities, ±50 km / s of Si IV 1402.77 Å, in DN / s, reaches the threshold,
       but stays below 10 times their median, a particle-hit test ("off" turns it off). A threshold
       left blank is irispy's default, scaled by the effective area at the observation's date.
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

In glue's terminal, :func:`glue_solar.sources.bursts.si_iv_bursts` and
:func:`glue_solar.sources.bursts.sji_bursts` make the same datasets.
