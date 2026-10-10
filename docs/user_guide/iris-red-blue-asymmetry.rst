.. _glue_solar_users_guide_iris_red_blue:

==================
Red-blue asymmetry
==================

To compare the red and blue wings of a line, select a raster window, of one scan or a stack of its
scans, in the data collection and choose "IRIS: red-blue asymmetry…" from its right-click menu. The
rest wavelength, in Å, starts at the window's :ref:`rest wavelength
<glue_solar_users_guide_iris_rest_wavelength>`, or blank for a window without one; type another to
change it. The wavelengths taken below and above it, ±1 Å unless changed, are all irispy is given,
so a Mg II k window's h line is left out. irispy's ``calculate_red_blue_asymmetry`` interpolates
each profile about its peak every velocity step and divides the mean of its red wing, from the first
to the second wing velocity above the peak, less the mean of its blue wing, as far below it, by the
peak: positive for excess red emission. The wing velocities, 30 to 55 km/s, and the step, 5 km/s,
unless changed, are those of SolarSoft's iris_xfiles (its double Gaussian fit,
``iris_moment__dgf.pro``). irispy computes the map on a worker thread from the window's DN/s, a slab
of raster steps of one scan at a time, while glue's status bar says "Computing red-blue asymmetry of
<label>…", and adds ``<label> red-blue asymmetry <rest>`` on the window's raster steps and slit
pixels, with their helioprojective coordinates in arcsec linked with the other IRIS datasets. No
viewer opens: drag it onto an Image viewer and pick a map as its attribute. A stack's maps are one
dataset on its scans, raster steps and slit pixels, each scan's as that scan alone gives them, at
its own coordinates and exposure times; the scan slider picks the scan.

The maps
--------

- ``red_blue_asymmetry``, NaN where irispy does not compute it;
- ``quality``, irispy's ``RBAQualityFlag``: 0 computed, 1 no finite sample, 2 the peak at an end of
  the wavelengths taken, 3 too few samples, 4 the interpolation failed, 5 a peak of 0, 6 a wing not
  covered, 8 saturated: a sample taken is +Inf, as glue-solar reads 16182 DN, the Level 2 ceiling
  saturated samples are clipped to (see :ref:`Was it saturated?
  <glue_solar_users_guide_iris_saturation>`); 7, below a
  minimum intensity, is never set.

Missing (NaN or -Inf) and negative samples are left out. The wings are measured from the peak,
which for the two peaks of Mg II or C II about their central reversal is the brighter one; the rest
wavelength sets the wavelengths taken and their velocities. The new dataset's ``meta`` holds the
observation's ``OBSID`` and ``STARTOBS``, ``red_blue_rest``, ``red_blue_wavelengths``,
``red_blue_velocities`` and ``red_blue_step``.
``glue_solar.sources.red_blue.red_blue_asymmetry(data, rest, wavelengths, velocities, step)``
computes the dataset in glue's terminal too. :ref:`Exporting derived data
<glue_solar_users_guide_exporting_derived_data>` saves the maps with their coordinates.

Glue says why, and adds nothing, for the data and centres :ref:`line moments
<glue_solar_users_guide_iris_line_moments>` refuse, and for irispy's own errors, such as wing
velocities that do not increase.

.. _glue_solar_users_guide_iris_doppler:

Doppler images
--------------

To map a line's red wing less its blue wing at chosen velocities, as CRISPEX's Doppler images do,
select a raster window, of one scan or a stack of its scans, and choose "IRIS: Doppler image…" from
its right-click menu. The rest wavelength starts as above; the velocities, 10, 20, 30, 40, 50 km/s
unless changed, are any positive velocities in km/s, separated by commas or spaces. At each velocity
v, each wing is the window's DN/s interpolated linearly at rest × (1 ± v/c), the optical Doppler
shift, between the two samples about it, and its map, ``red - blue <v> km/s``, is the red wing less
the blue: positive where the red wing is brighter, as for a redshift. "(red - blue) / (red + blue)
too" adds each map over the sum of its wings, ``(red - blue) / (red + blue) <v> km/s``, NaN where a
wing is not positive. glue computes them on a worker thread, while its status bar says "Computing
the Doppler image of <label>…", and adds ``<label> Doppler image <rest>`` on the window's raster
steps and slit pixels, a stack's scans too, each scan at its own wavelengths and coordinates, linked
as above. No viewer opens: drag it onto an Image viewer and pick a map as its attribute.

A map is NaN where either sample about a wing is missing, or saturated: +Inf, as glue-solar reads
16182 DN, the Level 2 ceiling saturated samples are clipped to (see :ref:`Was it saturated?
<glue_solar_users_guide_iris_saturation>`). A line symmetric about the rest wavelength gives 0, to
float precision, where the rest wavelength is a sample's or halfway between two; elsewhere the
interpolation leaves a small difference. Velocities are relative to the uncorrected Level 2
wavelength scale, as the line moments' are (see :ref:`Line moments
<glue_solar_users_guide_iris_line_moments>`). The new dataset's ``meta`` holds the observation's
``OBSID`` and ``STARTOBS``, ``doppler_rest``, ``doppler_velocities`` and ``doppler_sign``,
``"red - blue"``. ``glue_solar.sources.doppler.doppler_image(data, rest, velocities, normalised)``
computes the dataset in glue's terminal too. Glue says why, and adds nothing, for data other than a
raster window or stack, a velocity that is not positive, or a wing outside the window.
