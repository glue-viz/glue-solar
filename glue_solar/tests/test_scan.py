import tarfile
import threading
from pathlib import Path

import pytest

from astropy.io import fits

from glue_solar.conftest import MD5, OBS_A, OBS_B, OBS_C, OBS_S, startobs
from glue_solar.sources.loaders import scan
from glue_solar.sources.loaders.scan import extract_archive, find_observation_files, scan_directory, strip_pooch


def test_strip_pooch():
    assert strip_pooch(f"{MD5}iris_l2_x.fits") == "iris_l2_x.fits"
    assert strip_pooch("iris_l2_x.fits") == "iris_l2_x.fits"


def test_groups_by_observation_across_directories(iris_tree):
    obs = {o.obsid: o for o in scan_directory(iris_tree)}
    assert sorted(obs) == sorted([OBS_A[2], OBS_B[2], OBS_C[2]])

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


def test_derived_raster_file_is_skipped_and_counted(iris_tree):
    skipped = []
    assert OBS_S not in {o.obsid for o in scan_directory(iris_tree, skipped=skipped)}
    assert [strip_pooch(path.name) for path in skipped] == ["iris_l2_20140910_fexxi_rb_steps.fits.gz"]


def test_raster_file_of_another_level_is_skipped(tmp_path):
    header = fits.Header(
        {"TELESCOP": "IRIS", "INSTRUME": "SPEC", "DATA_LEV": 3.0, "OBSID": OBS_S, "STARTOBS": "2014-09-10T11:28:25.590"}
    )
    fits.PrimaryHDU(header=header).writeto(tmp_path / "level3.fits")
    skipped = []
    assert scan_directory(tmp_path, skipped=skipped) == []
    assert skipped == [tmp_path / "level3.fits"]


def test_sparse_header_falls_back_to_obsid_description(tmp_path):
    pytest.importorskip("irispy")
    from irispy.obsid import ObsID

    header = fits.Header(
        {"TELESCOP": "IRIS", "INSTRUME": "SPEC", "DATA_LEV": 2.0, "OBSID": OBS_S, "STARTOBS": "2014-09-10T11:28:25.590"}
    )
    fits.PrimaryHDU(header=header).writeto(tmp_path / "sparse.fits")  # no L2 stem in its name
    [s] = scan_directory(tmp_path)
    assert s.description == ObsID(int(OBS_S))["raster_fulldesc"]
    assert s.endobs is None
    assert s.xcen is None


def test_stop_ends_the_scan_while_it_lists_the_files(iris_tree, monkeypatch):
    stop, listed, is_file = threading.Event(), [], Path.is_file

    def stop_at_the_first(path):
        listed.append(path)
        stop.set()  # Stop, as the first entry is looked at
        return is_file(path)

    monkeypatch.setattr(Path, "is_file", stop_at_the_first)
    assert scan_directory(iris_tree, stop=stop) == []
    assert len(listed) == 1  # and the rest of the tree is not walked


def test_report_reaches_100_only_once_every_file_is_read(iris_tree):
    reports, stop = [], threading.Event()
    scan_directory(iris_tree, report=reports.append)
    assert reports[-1] == 100
    reports.clear()
    stop.set()  # before a file is listed
    assert scan_directory(iris_tree, stop=stop, report=reports.append) == []
    assert reports == []


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


@pytest.fixture
def days_tree(tmp_path):
    """Slit-jaw files stamped 2013-08-31 to 2013-09-03, the second of 2013-09-01 running into 2013-09-02."""
    for name, start, end in (
        ("iris_l2_20130831_120000_4000000001_SJI_1400_t000.fits", "2013-08-31T12:00:00", "2013-08-31T13:00:00"),
        ("iris_l2_20130901_100000_4000000002_SJI_1400_t000.fits", "2013-09-01T10:00:00", "2013-09-01T11:00:00"),
        ("iris_l2_20130901_230000_4000000003_SJI_1400_t000.fits", "2013-09-01T23:00:00", "2013-09-02T01:00:00"),
        ("iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits", "2013-09-02T16:39:35", "2013-09-02T17:58:48"),
        ("iris_l2_20130903_010000_4000000004_SJI_1400_t000.fits", "2013-09-03T01:00:00", "2013-09-03T02:00:00"),
        ("sparse.fits", "2013-08-31T12:00:00", "2013-08-31T13:00:00"),  # no stamp in its name
    ):
        obsid = name[24:34] or "4000000006"
        header = {"TELESCOP": "IRIS", "INSTRUME": "SJI", "OBSID": obsid, "STARTOBS": start, "ENDOBS": end}
        fits.PrimaryHDU(header=fits.Header(header)).writeto(tmp_path / name)
    (tmp_path / "iris_l2_20130901_050000_4000000005_raster.tar.gz").write_bytes(b"listed without opening")
    return tmp_path


def test_time_window_reads_only_the_headers_stamped_from_a_day_before(days_tree, monkeypatch):
    read, primary_header = [], scan._primary_header
    monkeypatch.setattr(scan, "_primary_header", lambda path: read.append(path.name) or primary_header(path))
    observations = scan_directory(days_tree, start="2013-09-02", end="2013-09-02T23:59:59")
    assert sorted(name[:16] for name in read) == [
        "iris_l2_20130901",
        "iris_l2_20130901",
        "iris_l2_20130902",
        "sparse.fits",
    ]
    # the archive's end is not known
    assert [o.startobs for o in observations] == ["2013-09-01T05:00:00", "2013-09-01T23:00:00", "2013-09-02T16:39:35"]


def test_pattern_matches_names_without_pooch_prefix(iris_tree):
    assert [o.obsid for o in scan_directory(iris_tree, pattern="iris_l2_2023*")] == [OBS_B[2]]
    a = {o.obsid: o for o in scan_directory(iris_tree, pattern="*SJI*")}[OBS_A[2]]
    assert (list(a.sji), a.rasters, a.sdo) == (["SJI_1400"], [], {})


def test_find_observation_files(iris_tree, days_tree):
    assert find_observation_files(days_tree, "2013-09-02T17:00", "2013-09-02T17:00") == [
        days_tree / "iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits"
    ]
    rasters = find_observation_files(iris_tree, pattern="*_raster_t*")
    assert [strip_pooch(p.name)[-11:] for p in rasters] == ["r00000.fits", "r00001.fits"]
