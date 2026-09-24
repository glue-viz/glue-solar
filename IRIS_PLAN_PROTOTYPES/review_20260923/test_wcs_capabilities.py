"""Real-IRIS WCS autolink evidence; run once with main solar and once with WP1."""
import numpy as np
import pytest
from astropy import units as u
from astropy.wcs.wcsapi import HighLevelWCSWrapper
from glue.core import DataCollection
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink
from glue_solar.sources.loaders.iris import image_data, raster_data, _GlueWCS


def real(files, name):
    return next(path for path in files if path.name == name)


@pytest.fixture
def pair(irispy_test_files):
    sji = image_data(real(irispy_test_files, 'iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits'))
    raster = raster_data([real(irispy_test_files, 'iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits')], ['Si IV 1403'])[0]
    return sji, raster


def test_sji_raster_autolink_geometry_and_limits(pair):
    sji, raster = pair
    dc = DataCollection(list(pair))
    links = wcs_autolink(dc)
    print('SJI/raster links',len(links))
    assert len(links) == 1
    link = links[0]
    dc.add_link(links)
    assert {cid.axis for cid in link.cids1} == {1, 2}
    assert {cid.axis for cid in link.cids2} == {0, 1}
    assert sji.pixel_component_ids[0] not in link.cids1  # time absent
    assert raster.pixel_component_ids[-1] not in link.cids2  # wavelength absent
    incoming = [np.full(10, 25.), np.arange(25., 35.)]
    outgoing = link.forwards(*incoming)
    back = link.backwards(*outgoing)
    valid = np.isfinite(np.asarray(outgoing)).all(axis=0) & np.isfinite(np.asarray(back)).all(axis=0)
    for cid, values in zip(link.cids2, outgoing):
        valid &= (values >= 0) & (values < raster.shape[cid.axis] - 1)
    assert valid.any()  # compare pixels in the actual overlapping footprint
    for actual, expected in zip(back, incoming):
        np.testing.assert_allclose(actual[valid], expected[valid], atol=1e-4)
    incoming = [values[valid] for values in incoming]
    outgoing = [values[valid] for values in outgoing]
    def world(data, cids, pixels, frame=0):
        full = [np.zeros_like(pixels[0]) for _ in data.shape]
        if data is sji:
            full[0] += frame
        for cid, value in zip(cids, pixels):
            full[cid.axis] = value
        values = data.coords.pixel_to_world_values(*full[::-1])
        return {kind: np.asarray(value) * u.Unit(unit) for kind,value,unit in zip(data.coords.world_axis_physical_types, values, data.coords.world_axis_units) if kind and 'helioprojective' in kind}
    initial = world(sji, link.cids1, incoming)
    mapped = world(raster, link.cids2, outgoing)
    later = world(sji, link.cids1, incoming, frame=sji.shape[0]-1)
    for kind in initial:
        np.testing.assert_allclose(initial[kind].to_value(u.arcsec), mapped[kind].to_value(u.arcsec), atol=1e-3)
    drift = max(float(np.max(np.abs((later[kind]-mapped[kind]).to_value(u.arcsec)))) for kind in initial)
    print('Same pixel last-frame sky discrepancy (arcsec)',drift)
    assert drift > 1  # a fixed frame-0 mapping is not time-dependent co-registration
    for source, target, axes in ((sji,raster,(2,1)), (raster,sji,(0,1))):
        x,y=axes
        roi = RoiSubsetState(xatt=source.pixel_component_ids[x], yatt=source.pixel_component_ids[y], roi=RectangularROI(-1, source.shape[x]+1, -1, source.shape[y]+1))
        mask = target.get_mask(roi)
        assert mask.shape == target.shape
        assert mask.any()
        print('ROI propagated',source.shape,'->',target.shape,'selected',mask.sum())

    # Pixel selection already has a linked-coordinate path for profile extraction
    # and image crosshairs, distinct from the generic mask path.
    from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
    x, y = (int(values[0]) for values in incoming)
    point = PixelSubsetState(sji, [slice(None), slice(y, y + 1), slice(x, x + 1)])
    step, slit = point.get_xy(raster, 0, 1)
    spectrum = raster.compute_statistic('mean', raster.main_components[0], axis=(0, 1), subset_state=point)
    np.testing.assert_allclose(spectrum, raster[raster.main_components[0]][step, slit, :], equal_nan=True)
    print('SJI point -> raster spectrum and marker',x,y,'->',step,slit)


def test_raster_pair_and_stack_autolink(irispy_test_files):
    names = [f'iris_l2_20140329_140938_3860258481_raster_t000_r0000{i}.fits' for i in range(3)]
    paths = [real(irispy_test_files,name) for name in names]
    scans = raster_data(paths[:2], ['C II 1336'])
    links = wcs_autolink(DataCollection(scans))
    print('Raster/raster links',len(links))
    stack = raster_data(paths, ['C II 1336'], stack=True)[0]
    scan = raster_data(paths[:1], ['C II 1336'])[0]
    links_stack = wcs_autolink(DataCollection([stack,scan]))
    print('Stack/scan links',len(links_stack))
    expected = int(hasattr(_GlueWCS, '_units'))  # WP1 repairs the high-level units contract
    assert len(links) == len(links_stack) == expected


def test_high_level_coordinate_values_match_declared_units(pair):
    for data in pair:
        pixels = [5.] * data.ndim
        try:
            objects = HighLevelWCSWrapper(data.coords).pixel_to_world(*pixels)
            objects = objects if isinstance(objects, (tuple, list)) else (objects,)
            sky = next(obj for obj in objects if hasattr(obj, 'Tx'))
            values = data.coords.pixel_to_world_values(*pixels)
            axis = list(data.coords.world_axis_physical_types).index('custom:pos.helioprojective.lon')
            discrepancy = float(abs(sky.Tx.to_value(u.arcsec)-values[axis]))
            print('High-level longitude discrepancy',data.label,discrepancy)
            assert discrepancy < 1e-6
        except ValueError as error:
            assert not hasattr(_GlueWCS, '_units')
            assert 'Latitude angle' in str(error)
            print('Known main wrapper error',data.label,type(error).__name__,str(error))


def test_source_map_and_map_map_autolink(pair):
    from astropy.wcs.wcsapi import SlicedLowLevelWCS
    from glue.core import Data
    _, raster = pair
    flux = raster[raster.main_components[0]][:, :, 0]
    def derived(label):
        return Data(label=label, flux=flux, coords=_GlueWCS(SlicedLowLevelWCS(raster.coords._wcs, (slice(None), slice(None), 0))))
    first, second = derived('map one'), derived('map two')
    source_links = wcs_autolink(DataCollection([raster, first]))
    # Use a fresh pair to avoid moving a Data between collections.
    map_links = wcs_autolink(DataCollection([derived('map three'), second]))
    print('Source/map links',len(source_links),'map/map links',len(map_links))
    expected = int(hasattr(_GlueWCS, '_units'))
    assert len(source_links) == len(map_links) == expected
