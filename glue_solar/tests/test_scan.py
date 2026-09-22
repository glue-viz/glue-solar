import tarfile
from pathlib import Path

import pytest

from astropy.io import fits

from glue_solar.conftest import MD5, OBS_A, OBS_B, OBS_C, OBS_S, startobs
from glue_solar.sources.loaders.scan import extract_archive, scan_directory, strip_pooch


def test_strip_pooch():
    assert strip_pooch(f"{MD5}iris_l2_x.fits") == "iris_l2_x.fits"
    assert strip_pooch("iris_l2_x.fits") == "iris_l2_x.fits"


def test_groups_by_observation_across_directories(iris_tree):
    obs = {o.obsid: o for o in scan_directory(iris_tree)}
    assert sorted(obs) == sorted([OBS_A[2], OBS_B[2], OBS_C[2], OBS_S])

    a = obs[OBS_A[2]]
    assert a.startobs == startobs(*OBS_A[:2])[:19]
    assert [strip_pooch(p.name)[-11:] for p in a.rasters] == ["r00000.fits", "r00001.fits"]
    assert a.windows == ["C II 1336", "Mg II k 2796"]
    assert list(a.sji) == ["SJI_1400"]
    assert list(a.sdo) == ["171_THIN"]
    assert a.description == "Test raster 1x2 3s"
    assert (a.xcen, a.ycen, a.sat_rot) == (1.5, -2.5, 0.0)
    assert a.nfiles == 4

    b = obs[OBS_B[2]]
    assert b.rasters == []
    assert b.windows == []
    assert list(b.sji) == ["SJI_2832"]


def test_sorted_by_start_time(iris_tree):
    starts = [o.startobs for o in scan_directory(iris_tree)]
    assert starts == sorted(starts)


def test_archive_listed_but_not_loadable(iris_tree):
    c = {o.obsid: o for o in scan_directory(iris_tree)}[OBS_C[2]]
    assert len(c.archives) == 1
    assert c.nfiles == 0
    assert c.startobs == startobs(*OBS_C[:2])[:19]


def test_sparse_header_falls_back_to_obsid_description(iris_tree):
    pytest.importorskip("irispy")
    from irispy.obsid import ObsID

    s = {o.obsid: o for o in scan_directory(iris_tree)}[OBS_S]
    assert s.description == ObsID(int(OBS_S))["raster_fulldesc"]
    assert s.endobs is None
    assert s.xcen is None


def test_non_recursive_only_sees_top_level(iris_tree):
    obs = {o.obsid: o for o in scan_directory(iris_tree, recursive=False)}
    assert obs[OBS_A[2]].rasters == []  # rasters live in a subdirectory
    assert list(obs[OBS_A[2]].sji) == ["SJI_1400"]


def test_filename_time_groups_one_second_header_mismatch_without_merging_repeats(tmp_path):
    obsid = "3683602040"
    for stamp, header_time in (("20211001_060925", "2021-10-01T06:09:24"), ("20211001_070000", "2021-10-01T07:00:00")):
        header = fits.Header(
            {
                "TELESCOP": "IRIS",
                "INSTRUME": "SJI",
                "OBSID": obsid,
                "STARTOBS": header_time,
                "TDESC1": "SJI_1400",
            }
        )
        fits.PrimaryHDU(header=header).writeto(tmp_path / f"iris_l2_{stamp}_{obsid}_SJI_1400_t000.fits")
    archive = tmp_path / f"iris_l2_20211001_060925_{obsid}_raster.tar.gz"
    archive.write_bytes(b"listed without opening")

    observations = scan_directory(tmp_path)
    assert [observation.startobs for observation in observations] == [
        "2021-10-01T06:09:25",
        "2021-10-01T07:00:00",
    ]
    assert all(observation.obsid == obsid for observation in observations)
    assert len(observations[0].archives) == 1
    assert list(observations[0].sji) == ["SJI_1400"]


def test_foreign_fits_files_are_ignored_even_with_iris_metadata(tmp_path):
    for name, instrume in (
        ("iris_l2_20240101_000000_1234567890_raster_t000_r00000.fits", "SPEC"),
        ("foreign_sji.fits", "SJI"),
    ):
        fits.PrimaryHDU(
            header=fits.Header(
                {
                    "TELESCOP": "FOREIGN",
                    "INSTRUME": instrume,
                    "OBSID": "1234567890",
                    "STARTOBS": "2024-01-01T00:00:00",
                }
            )
        ).writeto(tmp_path / name)

    assert scan_directory(tmp_path) == []


def test_invalid_archive_extraction_is_retryable(tmp_path):
    archive = tmp_path / "iris_l2_20140708_114109_3824262996_raster.tar.gz"
    archive.write_bytes(b"not a tar file")
    assert len(scan_directory(tmp_path)[0].archives) == 1

    with pytest.raises(tarfile.ReadError):
        extract_archive(archive)

    assert not archive.with_suffix("").with_suffix("").exists()
    assert len(scan_directory(tmp_path)[0].archives) == 1


def test_partial_archive_extraction_is_retryable(tmp_path, monkeypatch):
    member = tmp_path / "member.txt"
    member.write_text("contents")
    archive = tmp_path / "iris_l2_20140708_114109_3824262996_raster.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(member, arcname=member.name)

    def fail_partway(_tar, path, **_kwargs):
        (Path(path) / "partial.txt").write_text("partial")
        raise OSError("disk full")

    monkeypatch.setattr(tarfile.TarFile, "extractall", fail_partway)
    with pytest.raises(OSError, match="disk full"):
        extract_archive(archive)

    assert not archive.with_suffix("").with_suffix("").exists()
    assert len(scan_directory(tmp_path)[0].archives) == 1


def test_archive_extraction_does_not_overwrite_existing_directory(tmp_path):
    archive = tmp_path / "iris_l2_20140708_114109_3824262996_raster.tar.gz"
    archive.write_bytes(b"contents are irrelevant when the target exists")
    target = archive.with_suffix("").with_suffix("")
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("user data")

    with pytest.raises(FileExistsError, match="already exists"):
        extract_archive(archive)

    assert sentinel.read_text() == "user data"
