.. _glue_solar_users_guide_iris_calibration:

=================
Dust and radiance
=================

Removing dust
-------------

To remove the dust on a slit-jaw image, select it in the data collection and choose "IRIS: remove
dust (SJI)" from its right-click menu. irispy's ``SJICube.remove_dust``, after SolarSoft's
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

To see a raster window in radiance, select a window, of one scan or a stack of its scans, rebinned or
not, and choose "IRIS: radiometric calibration" from its right-click menu. It adds two components to the
window: ``<label> radiance per DN/s``, irispy's factor from DN/s to radiance at each wavelength,
held as one spectrum, and ``<label> radiance``, the window's ``<label> DN/s`` times it, which glue
computes as it reads it, in erg / (Å cm2 s sr). The factor is that of irispy's ``radiometric_calibration``
(``calculate_dn_to_radiance_factor``): the detector's photons per DN, 4 in the FUV and 18 in the
NUV (irispy's ``DN_UNIT``), times the photon energy at each wavelength over the effective area of
irispy's latest response at the window's ``DATE_OBS``, the spectral dispersion and the solid angle
of a pixel, the slit width by a pixel's length along the slit. Unlike SolarSoft's
``iris_calib``, it is per Å, and it is NaN at wavelengths the response does not cover. A stack
holds a spectrum for each scan, at the scan's own wavelengths, with its first scan's spectral
dispersion and solid angle, and the response at the stack's ``DATE_OBS``, its first scan's, which
only picks the response: its effective area changes by at most 0.12 % in 10 hours (Si IV 1402.77 Å
on 2014-03-29). Its ``<label> DN/s`` is over each scan's own exposure times, so each scan's radiance
is that of the scan alone within 0.2 %; on the 99 scans of OBSID 3602506433, over 68 minutes, it is
the same, as irispy's response holds the effective area constant from mid-2023 on.
``glue_solar.sources.calibration.radiometric_calibration(data)`` adds them in glue's terminal too.

A window rebinned with "IRIS: rebin…" (see :ref:`Rebinning <glue_solar_users_guide_iris_rebinning>`)
is calibrated too. Each bin is the mean of the window's pixels, so the factor takes their spectral
dispersion and solid angle, from the window's coordinates beneath the rebinned ones, and the
effective area at the bin's wavelength, the mean of its pixels'. The rebinned radiance is then the
window's radiance rebinned within about half the factor's change across a bin, as the bin's samples
share one factor: on OBSID 4000255147's C II 1336 rebinned by 2 along the slit and wavelength,
within 0.036 %, where the factor changes by up to 0.072 % across a bin. A bin along raster steps
adds the rebinned ``<label> DN/s``'s own difference, the bin's mean DN over its mean exposure time
rather than the mean of each step's: up to 0.003 % there.

Removing dust is offered only for a slit-jaw image, and the calibration only for a raster window or
stack that is not calibrated already: irispy has no radiometric calibration of slit-jaw images. Nor
is it offered for a stack with a scan whose ``CDELT1`` to ``CDELT3``, the pixel sizes of its
coordinates, differ from its first scan's, which give every scan's spectral dispersion and solid
angle: ``radiometric_calibration`` refuses one, naming the first scan that differs. The scans of
one observation that the observation browser stacks share them: all 99 of OBSID 3602506433, both of
4000005156 and the X1 flare's rasters r00172-r00174 of 3860258481, in every window.
