from __future__ import annotations

import io
import os
import socket
import zipfile
from pathlib import Path

import pytest

from airport_data.config import REPO_ROOT, get_paths
from airport_data.rawstore import RawFile
from airport_data.sources.base import FetchResult, Source, TableSpec, extract_member, load_csv_snake
from airport_data.validation import error, period_match_check, scalar


def make_zip(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, text)
    return buf.getvalue()


class FakeMonthly(Source):
    """Synthetic monthly source: content per period is injected by the test."""
    id = "fake_monthly"
    title = "fake"
    publisher = "test"
    license = "test"
    homepage = ""
    period_kind = "month"
    cadence = "monthly"
    expected_lag_days = 30
    tables = (TableSpec("fake_fact", "test fact", required_columns=("year", "month", "airport", "flights"),
                        not_null=("airport",), non_negative=("flights",), min_rows=1),)

    def __init__(self):
        self.payload: dict[str, bytes] = {}
        self.fail: set[str] = set()

    def available_periods(self, http):
        return sorted(self.payload)

    def fetch(self, period, http):
        if period in self.fail:
            raise ConnectionError("simulated outage")
        return FetchResult([RawFile(f"{period}.zip", self.payload[period])], f"https://example.test/{period}")

    def load(self, con, v, staging, tmp):
        p = extract_member(v, v.files[0]["name"], r"\.csv$", tmp)
        load_csv_snake(con, p, staging["fake_fact"])

    def checks(self, con, v, staging):
        yield period_match_check(con, staging["fake_fact"], v.period)


def csv_for(period: str, rows: list[tuple[str, int]], extra_col: str | None = None) -> bytes:
    y, m = map(int, period.split("-"))
    head = "YEAR,MONTH,AIRPORT,FLIGHTS" + (f",{extra_col}" if extra_col else "")
    body = "\n".join(f"{y},{m},{a},{f}" + (",x" if extra_col else "") for a, f in rows)
    return make_zip("data.csv", head + "\n" + body + "\n")


@pytest.fixture
def tmp_paths(tmp_path):
    return get_paths(tmp_path / "data")


@pytest.fixture
def fake():
    return FakeMonthly()


@pytest.fixture
def no_network(monkeypatch):
    def guard(*a, **k):
        raise RuntimeError("network access attempted during an offline test")
    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


SEED_PATHS = get_paths(REPO_ROOT / "data")


@pytest.fixture(scope="session")
def seed_db(tmp_path_factory):
    """Build the full DB from the committed seed archive into a temp location (offline)."""
    if not (SEED_PATHS.raw / "bts_t100_segment").exists():
        pytest.skip("seed archive not present")
    import shutil
    from airport_data.build import build
    from airport_data.sources import registry
    root = tmp_path_factory.mktemp("seedbuild") / "data"
    root.mkdir()
    # point at the committed raw/curated/reference without copying the archive
    for d in ("raw", "curated", "reference"):
        os.symlink(SEED_PATHS.root / d, root / d)
    shutil.copytree(SEED_PATHS.manifest, root / "manifest", dirs_exist_ok=True)
    paths = get_paths(root)
    sock = socket.socket.connect
    socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network during seed build"))
    try:
        res = build(paths, registry(paths), log=lambda *_: None)
    finally:
        socket.socket.connect = sock
    return paths, res


def network_enabled() -> bool:
    return os.environ.get("AIRPORT_DATA_NETWORK_TESTS") == "1"
