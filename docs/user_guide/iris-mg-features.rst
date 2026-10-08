.. _glue_solar_users_guide_iris_mg_features:

===============
Mg II features
===============

To map the line centres and emission peaks of Mg II k and h, select a raster window of one scan
that covers them, such as "Mg II k 2796", in the data collection and choose "IRIS: Mg II features…"
from its right-click menu. Type the Doppler velocities searched, from and to, in km/s from each
line's rest wavelength, -40 to 40 km/s unless changed, and tick the lines measured, at first those
the window covers: k (2796.35 Å) and h (2803.53 Å), irispy's vacuum rest wavelengths, so no rest
wavelength is typed. irispy's ``calculate_mg_features``, after Pereira et al. (2013) and SolarSoft's
``iris_get_mg_features.pro``, interpolates each profile within 3 km/s of those velocities, finds the
line centre, k3 or h3, at its central reversal and the blue and red emission peaks, k2v and k2r or
h2v and h2r, about it, and redoes line centres that jump along the slit from their neighbours. It
computes the maps on a worker thread from the window's DN/s, a slab of raster steps at a time,
while glue's status bar says "Computing Mg II features of <label>…", and adds ``<label> Mg II
features`` on the window's raster steps and slit pixels, with their helioprojective coordinates in
arcsec linked with the other IRIS datasets. No viewer opens: drag it onto an Image viewer and pick a
map as its attribute.

The maps
--------

For each line measured, ``k2v``, ``k3`` and ``k2r`` or ``h2v``, ``h3`` and ``h2r``, each feature as

- ``<feature>_velocity``, in km/s from the line's rest wavelength, on the uncorrected Level 2
  wavelength scale, which can be off by about 5-10 km/s;
- ``<feature>_intensity``, in the window's unit, DN/s;

NaN where irispy finds no such feature, or a sample within the velocities searched for the line is
missing (NaN or -Inf) or at 16182 DN, the Level 2 ceiling saturated samples are clipped to (a sample
merely that bright counts too, as Level 2 cannot tell them apart). Such a sample blanks only its own
line's features, at its pixel: the status bar and ``mg_features_saturated`` in ``meta`` say how many
pixels of each line, and :ref:`Was it saturated? <glue_solar_users_guide_iris_saturation>` shows
where the samples are. A ticked line the window does not cover over the velocities is left out.
The new dataset's ``meta`` holds the observation's ``OBSID`` and ``STARTOBS``,
``mg_features_velocities`` and ``mg_features_lines``, the lines measured.
``glue_solar.sources.mg_features.mg_features(data, velocities, lines)`` computes the dataset in
glue's terminal too.

Glue says why, and adds nothing, for stacks of scans, slit-jaw images and other data, as for
:ref:`line moments <glue_solar_users_guide_iris_line_moments>`, for a window that covers neither
line over -40 to 40 km/s, before asking, for velocities that do not increase or that the window
does not cover for any line ticked, and for irispy's own errors, such as too few wavelengths
within the velocities searched. With no line ticked, OK adds nothing.
