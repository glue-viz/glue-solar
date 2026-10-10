.. _glue_solar_users_guide_iris_bursts:

=========
UV bursts
=========

To find UV bursts, compact brightenings of the transition region, select a raster window, of one
scan or a stack of its scans, covering Si IV 1402.77 Å, such as "Si IV 1403", or a 1400 Å slit-jaw
image in the data collection and choose "IRIS: detect UV bursts…" from its right-click menu. Type
irispy's parameters, its defaults unless changed; Cancel adds nothing. irispy finds the bursts on a
worker thread, while glue's status bar says "Detecting UV bursts in <label>…", which then says how
many it found, and adds two datasets: ``<label> bursts``, a map of their labels, and
``<label> burst events``, a table of them. No viewer opens: drag the map onto an Image viewer and
the table onto a Table viewer.

In a raster window
------------------

irispy's ``find_si_iv_bursts``, a port of SolarSoft's ``iris_burst_check.pro`` (Young et al. 2018),
averages the wavelengths within the velocities typed, ±50 km/s unless changed, of Si IV 1402.77 Å
in each spectrum, over its raster step's exposure time, and finds a burst pixel where the mean
reaches the threshold and stays below the particle-hit test's factor times their median, 10 unless
changed ("off" switches the test off). The threshold is in DN/s per wavelength bin of data summed
by 2 in wavelength, which irispy scales by the window's summing; left blank, it is irispy's: 500
DN/s times the ratio of the 1402.77 Å effective area at the observation's date to that on
2013-10-22. Pixels that touch, diagonally too, are one burst; in a sit-and-stare window, whose
steps are times, a burst then links in time too. irispy is given the window's scaled DN, missing
samples masked, and only the wavelengths within the velocities.

``<label> bursts`` lies on the window's raster steps and slit pixels, with their helioprojective
coordinates in arcsec linked with the other IRIS datasets. Its ``label`` is 0 outside bursts and 1
to N for the N bursts, and its ``meta`` holds the observation's ``OBSID`` and ``STARTOBS``,
``bursts_threshold``, the threshold irispy applied, in DN/s per wavelength bin of the window,
``bursts_velocity_range`` and ``bursts_median_factor``. ``<label> burst events`` has a row for
each burst, irispy's columns: its ``label``, ``raster``, 0, and ``npix``, its number of pixels,
and the ``step``, ``y`` (the slit pixel), ``time``, ``coordinate.Tx`` and ``coordinate.Ty`` in
arcsec, and ``intensity``, the mean in DN/s, of its brightest pixel; its ``meta`` is the map's.
On the 1600 steps of OBSID 4000255147's Si IV 1403 it takes 0.2 s.

irispy finds a stack's bursts scan by scan, each scan's as that scan alone gives them, at its own
coordinates, times, exposure times and date, so a threshold left blank is each scan's own. The map
lies on the stack's scans, raster steps and slit pixels, the scan slider picking the scan, its
labels numbered on through the scans, 1 to N over all N bursts, as irispy numbers the rasters of a
sequence; ``bursts_threshold`` holds each scan's threshold, and the table's ``raster`` is the scan
of each burst. The status bar counts the bursts of every scan.

In a slit-jaw image
-------------------

irispy's ``find_sji_bursts``, a port of SolarSoft's ``iris_sji_burst_check.pro``, finds a burst
pixel at the threshold typed, 10 standard deviations unless changed, above the median of its frame,
missing pixels left out; pixels that touch within a frame, diagonally too, are one burst, and
bursts with fewer pixels than typed, 2 unless changed, are dropped. The 10 standard deviations are a
quick look: on active-region data they find bursts in every frame, and Young et al. (2018)
recommend a threshold chosen for each observation. A slit-jaw image with its dust removed, by
:ref:`"IRIS: remove dust" <glue_solar_users_guide_iris_calibration>`, works too.

``<label> bursts`` is a cube of their labels, 0 outside bursts and 1 to N through the image, on the
slit-jaw image's coordinates, with its ``Time``, per-frame pointing and ``meta``, so that the time
sync and the helioprojective links reach it, and ``bursts_sigma_factor`` and ``bursts_min_pixels``
in its ``meta``. ``<label> burst events`` has a row for each burst, irispy's columns: its
``label``, ``frame``, ``npix`` and the frame's ``threshold`` in DN, and the ``y``, ``x``, ``time``,
``coordinate.Tx``, ``coordinate.Ty`` and ``intensity`` of its brightest pixel; its ``meta`` holds
the observation's ``OBSID`` and ``STARTOBS`` and the parameters. irispy takes every frame at once:
on the 400 frames of OBSID 4000255147's SJI 1400 it takes 1.3 s and about 1.6 GB more memory at its
peak.

The labels and tables are irispy's own, as its functions give them on the files read in memory,
but for a pointing shifted by :ref:`"Shift pointing…" <glue_solar_users_guide_iris_pointing>`,
which the tables' ``coordinate.Tx`` and ``coordinate.Ty`` include, as the maps' coordinates do.
``glue_solar.sources.bursts.si_iv_bursts(data, threshold, velocity_range, median_factor)`` and
``glue_solar.sources.bursts.sji_bursts(data, sigma_factor, min_pixels)`` return the two datasets in
glue's terminal too.

Glue says why, and adds nothing, for slit-jaw images of other bands, other data, a window with no
wavelength within the velocities of Si IV 1402.77 Å, before asking for ±50 km/s, a threshold that is
not a number, and irispy's own errors.
