.. _glue_solar_users_guide_iris_mg_features:

===============
Mg II features
===============

To map the line centres and emission peaks of Mg II k and h, select a raster window, of one scan or
a stack of its scans, that covers them, such as "Mg II k 2796", in the data collection and choose
"IRIS: Mg II features… (Mg II)" from its right-click menu. Type the Doppler velocities searched, from and
to, in km/s from each line's rest wavelength, -40 to 40 km/s unless changed, and tick the lines
measured, at first those the window covers: k (2796.35 Å) and h (2803.53 Å), irispy's vacuum rest
wavelengths, so no rest wavelength is typed (but see `Rest wavelength`_). irispy's
``calculate_mg_features``, after Pereira et al. (2013) and SolarSoft's ``iris_get_mg_features.pro``,
interpolates each profile within 3 km/s of those velocities, finds the line centre, k3 or h3, at its
central reversal and the blue and red emission peaks, k2v and k2r or h2v and h2r, about it, and
redoes line centres that jump along the slit from their neighbours. It computes the maps on a worker
thread from the window's DN/s, a slab
of raster steps of one scan at a time, while glue's status bar says "Computing Mg II features of
<label>…", and adds ``<label> Mg II features`` on the window's raster steps and slit pixels, with
their helioprojective coordinates in arcsec linked with the other IRIS datasets. No viewer opens:
drag it onto an Image viewer and pick a map as its attribute. A stack's maps are one dataset on its
scans, raster steps and slit pixels, each scan's as that scan alone gives them, at its own
coordinates and exposure times; the scan slider picks the scan.

The maps
--------

For each line measured, ``k2v``, ``k3`` and ``k2r`` or ``h2v``, ``h3`` and ``h2r``, each feature as

- ``<feature>_velocity``, in km/s from the line's rest wavelength, on the uncorrected Level 2
  wavelength scale, which can be off by about 5-10 km/s;
- ``<feature>_intensity``, in the window's unit, DN/s;

NaN where irispy finds no such feature, or a sample within the velocities searched for the line is
missing (NaN or -Inf) or saturated: +Inf, as glue-solar reads 16182 DN, the Level 2 ceiling
saturated samples are clipped to (a sample merely that bright counts too, as Level 2 cannot tell
them apart). Such a sample blanks only its own line's features, at its pixel, which irispy's map of
the line, ``k_saturated`` or ``h_saturated``, marks with 1, else 0 (integers: glue holds irispy's
True and False so), a stack's for each of its scans. The status bar and ``mg_features_saturated`` in
``meta`` say how many pixels of each line the maps mark, over every scan of a stack, and
:ref:`Was it saturated? <glue_solar_users_guide_iris_saturation>` shows where the samples are. A
ticked line the window does not cover over the velocities is left out.
The new dataset's ``meta`` holds the observation's ``OBSID`` and ``STARTOBS``,
``mg_features_velocities`` and ``mg_features_lines``, the lines measured, and with a rest wavelength
set, ``mg_features_rest_wavelength``.
``glue_solar.sources.mg_features.mg_features(data, velocities, lines)`` computes the dataset in
glue's terminal too. :ref:`Exporting derived data <glue_solar_users_guide_exporting_derived_data>`
saves the maps with their coordinates.

The entry is offered only for a raster window or stack that covers Mg II k or h over -40 to 40 km/s.
Glue says why, and adds nothing, for a rest wavelength set more than 1 Å from 2796.351 Å (see
below), velocities that do not increase or that the window does not cover for any line ticked, and
irispy's own errors, such as too few wavelengths within the velocities searched. With no line
ticked, OK adds nothing.

Rest wavelength
---------------

irispy's ``calculate_mg_features`` takes no rest wavelength: it measures k from 2796.351 Å and h
from 2803.530 Å. A rest wavelength set on the window with "IRIS: set rest wavelength…" (see
:ref:`Rest wavelength <glue_solar_users_guide_iris_rest_wavelength>`), such as Mg II k's corrected by
the offset a fit of Ni I 2799.474 Å measures, is taken as k's: irispy is given the window's
wavelengths shorter by the rest wavelength less 2796.351 Å, as irispy advises in place of
SolarSoft's ``wave_comp``. k's velocities are then from the rest wavelength set, and h's from
irispy's h as far off: 0.01 Å redder lowers both by 1.07 km/s. Set to NIST's Mg II k, 2796.352 Å,
the main line the window is named for, it lowers them by 0.11 km/s from irispy's own, which are used
with none set. One more than 1 Å away, such as Mg II h's set for its line moments, is refused:
change or clear it first.
