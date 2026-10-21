"""Shared bits of the wp10-l-sst-scan-step measurements: page-cache eviction, I/O and memory counters, the cubes."""

import json
import os
import resource
import time
from pathlib import Path

CUBES = {
    "2022": "/home/nabil/DATA/SST/2022-05-12/nb_3950_2022-05-12T08_43_42_08_43_42=0-23_corrected_export2023-01-14T12_41_50_im.fits",
    "2021": "/home/nabil/DATA/SST/2021-08-19/nb_8542_2021-08-19T16_00_12_scans=0,1,3-5,7-27_stokes_corrected_export2022-03-15T10_38_53_im.fits",
    "2024": "/home/nabil/DATA/SST/2024-07-05/nb_3950_2024-07-05T07_32_26_07_32_26=0-332_corrected_export2026-03-10T19_12_28_im.fits",
}


def evict(path, offset=0, length=0):
    """Drop ``path``'s pages (or a range) from the page cache; mapped pages stay, so unmap first."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.posix_fadvise(fd, offset, length, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)


def io():
    """This process's bytes read from disk, major and minor faults."""
    text = dict(line.split(": ") for line in Path("/proc/self/io").read_text().splitlines())
    ru = resource.getrusage(resource.RUSAGE_SELF)
    return int(text["read_bytes"]), ru.ru_majflt, ru.ru_minflt


def memory():
    """RSS and its anonymous part, bytes."""
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    kb = lambda key: int(status[key].split()[0]) * 1024  # noqa: E731
    return kb("VmRSS"), kb("RssAnon")


class Meter:
    """Wall time, disk bytes, faults and memory growth over a ``with`` block."""

    def __enter__(self):
        self.io0, self.mem0 = io(), memory()
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self.t0) * 1e3
        io1, mem1 = io(), memory()
        self.read_mb = (io1[0] - self.io0[0]) / 1e6
        self.majflt, self.minflt = io1[1] - self.io0[1], io1[2] - self.io0[2]
        self.rss_mb, self.anon_mb = (mem1[0] - self.mem0[0]) / 1e6, (mem1[1] - self.mem0[1]) / 1e6

    def dict(self):
        return {"ms": round(self.ms, 2), "read_mb": round(self.read_mb, 1), "majflt": self.majflt,
                "minflt": self.minflt, "rss_mb": round(self.rss_mb, 1), "anon_mb": round(self.anon_mb, 1)}


LOAD_LIMIT = float(os.environ.get("LOAD_LIMIT", 8))  # the coordinator's limit; an override only for tests


def quiet(limit=LOAD_LIMIT, poll=15, timeout=3600):
    """Wait until the 1-minute load average is under ``limit`` (cold timings are taken only then); the load."""
    end = time.time() + timeout
    while os.getloadavg()[0] >= limit and time.time() < end:
        time.sleep(poll)
    return os.getloadavg()


def emit(out, **values):
    values["load"] = [round(v, 2) for v in os.getloadavg()]  # uptime's 1, 5 and 15 minute load averages, at the line
    line = json.dumps(values, default=str)
    print(line, flush=True)
    with open(out, "a") as f:
        f.write(line + "\n")
