.. _glue_solar_users_guide_iris_red_blue:

==================
Red-blue asymmetry
==================

To compare the red and blue wings of a line, select a raster window of one scan in the data
collection and choose "IRIS: red-blue asymmetry…" from its right-click menu. Type the rest
wavelength in Å (the window's reference wavelength is never assumed); the wavelengths taken below
and above it, ±1 Å unless changed, are all irispy is given, so a Mg II k window's h line is left
out. irispy's ``calculate_red_blue_asymmetry`` interpolates each profile about its peak every
velocity step and divides the mean of its red wing, from the first to the second wing velocity above
the peak, less the mean of its blue wing, as far below it, by the peak: positive for excess red
emission. The wing velocities, 30 to 55 km/s, and the step, 5 km/s, unless changed, are those of
SolarSoft's iris_xfiles (its double Gaussian fit, ``iris_moment__dgf.pro``). irispy computes the map
on a worker thread from the window's DN/s, a raster step at a time, while glue's status bar says
"Computing red-blue asymmetry of <label>…", and adds ``<label> red-blue asymmetry <rest>`` on the
window's raster steps and slit pixels, with their helioprojective coordinates in arcsec linked with
the other IRIS datasets. No viewer opens: drag it onto an Image viewer and pick a map as its
attribute.

The maps
--------

- ``red_blue_asymmetry``, NaN where irispy does not compute it;
- ``quality``, irispy's ``RBAQualityFlag``: 0 computed, 1 no finite sample, 2 the peak at an end of
  the wavelengths taken, 3 too few samples, 4 the interpolation failed, 5 a peak of 0, 6 a wing not
  covered, 8 saturated: a sample taken at 16182 DN, the Level 2 ceiling saturated samples are
  clipped to (see :ref:`Was it saturated? <glue_solar_users_guide_iris_saturation>`); 7, below a
  minimum intensity, is never set.

Missing (NaN or -Inf) and negative samples are left out. The wings are measured from the peak,
which for the two peaks of Mg II or C II about their central reversal is the brighter one; the rest
wavelength sets the wavelengths taken and their velocities. The new dataset's ``meta`` holds the
observation's ``OBSID`` and ``STARTOBS``, ``red_blue_rest``, ``red_blue_wavelengths``,
``red_blue_velocities`` and ``red_blue_step``.
``glue_solar.sources.red_blue.red_blue_asymmetry(data, rest, wavelengths, velocities, step)``
computes the dataset in glue's terminal too.

Glue says why, and adds nothing, for the data and centres :ref:`line moments
<glue_solar_users_guide_iris_line_moments>` refuse, and for irispy's own errors, such as wing
velocities that do not increase.
