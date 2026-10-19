.. _glue_solar_users_guide_data_actions:

============
Data actions
============

These actions are in a dataset's right-click menu in the data collection. Regridding, rebinning,
north up and dust removal add a new dataset, linked as the original is; only north up opens a
viewer, so drag the others onto one.

.. _glue_solar_users_guide_iris_regrid:

Regridding on time
------------------

glue's axes are index axes, so a sit-and-stare raster's exposures, a stack's scans and the frames of
a slit-jaw image, AIA cutout or SOT cube show evenly spaced, whatever their cadence and gaps. To see
them in time, choose "IRIS: regrid on time". It adds
``<label> regridded``, resampled at the median time step: each pixel holds the exposure, frame or
scan nearest its time within 0.75 steps, and a pixel in a gap is NaN. An Image viewer labels its
axis with the step, such as "Time (2.89 s per pixel)".

A scanning raster's steps are places on the Sun, not times: stack its scans in the observation
browser and regrid the stack, scan by scan. "Quicklook…" shows the original; for a quicklook of the
regridded data, in glue's terminal::

    from glue_solar.quicklook import quicklook

    quicklook(application, [dc["<raster label> regridded"], dc["<slit-jaw label>"]])

.. _glue_solar_users_guide_iris_rebinning:

Rebinning
---------

To trade resolution for signal, choose "IRIS: rebin…" on a raster window, stack, slit-jaw image or
AIA cutout and type the pixels in a bin along each axis, 2 by 2 in space at first. It adds
``<label> rebinned <bins>``, such as ``… rebinned 2x2x1``: each pixel is the mean of its bin, by
ndcube's ``NDCube.rebin``, missing samples left out, and pixels past the last whole bin are dropped.
``Time`` and ``Exposure time`` are the bin's means. A rebinned window's line moments are those of
each bin's mean, without error maps.

.. _glue_solar_users_guide_iris_pointing:

Shifting the pointing
---------------------

IRIS pointing can be off by an arcsecond or two between a slit-jaw image and its raster, or against
AIA. Choose "IRIS: shift pointing…" and type Δx and Δy in arcsec, added to the helioprojective
longitude and latitude; 0, 0 removes the offset. A raster window shifts with the other windows of its
file. Every viewer, readout and link follows, and so do the data made from it; chosen on those, it
shifts the dataset they were made from. Only IRIS data shift: shift them against a map. Draw a
quicklook's region again after shifting its dataset.

To co-align a slit-jaw image with its raster:

1. Click a small, distinct feature on the raster map: the red cross marks where the raster places it
   on the slit-jaw image.
2. Read the feature's position in both with the cursor readout.
3. Shift the slit-jaw image by the raster's position less its own.

Against AIA, drag the map onto the slit-jaw viewer and lower its opacity, or blink the two, and read
the positions the same way. A "Measure" line from the feature in one to the feature in the other
checks the shift: it should be under a pixel long.

North up
--------

A rolled observation (``SAT_ROT``) shows solar north at its roll angle. "IRIS: north up", on a slit-jaw
image, AIA cutout or SOT cube, adds ``<label> north up``, a grid with latitude up, fixed on the sky,
and opens an Image viewer of the image on it. glue resamples each frame onto the grid as it
draws, from the nearest sample, and makes no copy. The image moves across the grid as IRIS follows
the solar rotation. The time sync and the point leave the viewer alone, and "Per-frame limits" and
"Color bar" act on the hidden grid: set the image's limits in its layer's options.

.. _glue_solar_users_guide_iris_calibration:

Removing dust
-------------

"IRIS: remove dust" runs irispy's ``SJICube.remove_dust``, after SolarSoft's
``iris_dustbuster``: each dust pixel of the IRIS pipeline's bad-pixel table, placed in each frame by
the slit's position, and those next to it take the median of that pixel over the two frames on
either side, scaled by their exposure times, or else of the 5 by 5 pixels about it. It adds
``<label> dust removed``, held in memory. A rebinned or regridded image is refused: irispy places
the table in the pixels of the file.

Radiometric calibration
-----------------------

"IRIS: radiometric calibration", on a raster window or stack, rebinned or not, adds two attributes
to it: ``<window> radiance``, in erg / (Angstrom s sr cm2), and ``<window> radiance per DN / s``, the
factor its ``<window> DN / s`` is multiplied by. The factor is irispy's ``radiometric_calibration``,
from the effective area of irispy's latest response at the window's ``DATE_OBS``. Unlike SolarSoft's
``iris_calib``, it is per Angstrom, and it is NaN at wavelengths the response does not cover. irispy
has no calibration of slit-jaw images.

In glue's terminal
------------------

``glue_solar.regrid.regrid_on_time(data)``, ``glue_solar.regrid.rebin(data, bins)``, with a bin per
axis in numpy's order, ``glue_solar.regrid.north_up_iris(data, dc)``,
``glue_solar.sources.calibration.remove_dust(data)`` and
``glue_solar.sources.calibration.radiometric_calibration(data)`` do the same.
