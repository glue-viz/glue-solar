.. _glue_solar_users_guide_iris_calibration:

=================
Dust and radiance
=================

Removing dust
-------------

To remove the dust on a slit-jaw image, select it in the data collection and choose "IRIS: remove
dust" from its right-click menu. irispy's ``SJICube.remove_dust``, after SolarSoft's
``iris_dustbuster``, finds dust where a value lies above -199 and below 0.5 DN, and the pixels next
to it, and replaces each with the median of that pixel over the two frames on either side, scaled by
their exposure times, or else with the median of the 5 by 5 pixels about it. It runs on a worker
thread, a slab of frames at a time, while glue's status bar says "Removing dust from <label>…", and
adds ``<label> dust removed``: the slit-jaw image's values in float32, with its coordinates,
per-frame pointing, ``Time``, ``Exposure time`` and ``<label> dust removed DN/s``, so that the time
sync and the helioprojective links reach it. Missing data stay NaN, and so does dust irispy finds no
replacement for. No viewer opens: drag it onto an Image viewer. The new dataset is held in memory,
its values and their mask: about 310 MiB for the 400 frames of 417 by 388 pixels of OBSID
4000255147's SJI 1400, cleaned in 17 s. ``glue_solar.sources.calibration.remove_dust(data)``
computes the dataset in glue's terminal too.

Radiance
--------

To see a raster window in radiance, select a window, of one scan or a stack of its scans, and
choose "IRIS: radiometric calibration" from its right-click menu. It adds two components to the
window: ``<label> radiance per DN/s``, irispy's factor from DN/s to radiance at each wavelength,
held as one spectrum, and ``<label> radiance``, the window's ``<label> DN/s`` times it, which glue
computes as it reads it, in erg / (Å cm2 s sr). The factor is that of irispy's ``radiometric_calibration``
(``calculate_dn_to_radiance_factor``): the detector's photons per DN, 4 in the FUV and 18 in the
NUV (irispy's ``DN_UNIT``), times the photon energy at each wavelength over the effective area of
irispy's latest response at the window's ``DATE_OBS``, the spectral dispersion and the solid angle
of a pixel, the slit width by a pixel's length along the slit. Unlike SolarSoft's
``iris_calib``, it is per Å, and it is NaN at wavelengths the response does not cover. A stack
holds a spectrum for each scan, as that scan alone gives it, at its own ``DATE_OBS``, and its
``<label> DN/s`` is over each scan's own exposure times, so each scan's radiance is that of the scan
alone. ``glue_solar.sources.calibration.radiometric_calibration(data)`` adds them in glue's terminal
too.

Glue says why, and adds nothing, to remove dust from other data than a slit-jaw image, and to
calibrate other data than a raster window or stack, or a window calibrated already: irispy has no
radiometric calibration of slit-jaw images.
