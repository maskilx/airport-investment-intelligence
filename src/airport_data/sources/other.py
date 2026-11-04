"""OurAirports reference data and local (hand-maintained) CSV sources."""
from __future__ import annotations

from pathlib import Path

from ..rawstore import RawFile
from ..validation import error, scalar, warning
from .base import FetchResult, Source, TableSpec, load_csv_snake, today

OA = "https://davidmegginson.github.io/ourairports-data/"


class OurAirports(Source):
    id = "ourairports"
    title = "OurAirports airports & runways (worldwide)"
    publisher = "OurAirports (community; maintained by David Megginson)"
    license = "Public domain (no warranty of accuracy)"
    homepage = "https://ourairports.com/data/"
    period_kind = "snapshot"
    history_mode = "latest"
    cadence = "nightly"
    expected_lag_days = 0
    notes = "Used for coordinates, IATA/ICAO/FAA-LID crosswalk and runway inventory. Community-maintained."
    FILES = ("airports.csv", "runways.csv")
    tables = (
        TableSpec("oa_airport", "One row per airport/heliport/seaplane base worldwide.",
                  required_columns=("id", "ident", "type", "name", "latitude_deg", "longitude_deg", "elevation_ft",
                                    "iso_country", "iso_region", "municipality", "scheduled_service", "iata_code",
                                    "local_code", "gps_code"),
                  not_null=("id", "ident"), unique_key=("id",), unique_key_blocking=True, min_rows=50_000,
                  placeholder_types=(("id", "BIGINT"), ("latitude_deg", "DOUBLE"), ("longitude_deg", "DOUBLE"),
                                     ("elevation_ft", "INTEGER"))),
        TableSpec("oa_runway", "One row per runway.",
                  required_columns=("id", "airport_ref", "airport_ident", "length_ft", "width_ft", "surface",
                                    "lighted", "closed", "le_ident", "he_ident"),
                  not_null=("id", "airport_ref"), unique_key=("id",), unique_key_blocking=True, min_rows=30_000,
                  placeholder_types=(("id", "BIGINT"), ("airport_ref", "BIGINT"), ("length_ft", "INTEGER"),
                                     ("width_ft", "INTEGER"), ("lighted", "BOOLEAN"), ("closed", "BOOLEAN"))),
    )

    def available_periods(self, http) -> list[str]:
        return [today().isoformat()]

    def fetch(self, period, http) -> FetchResult:
        files, hdrs = [], {}
        for name in self.FILES:
            r = http.get(OA + name)
            files.append(RawFile(name, r.body))
            hdrs[name] = {k: r.headers[k] for k in ("last-modified", "etag", "content-length") if k in r.headers}
        return FetchResult(files, OA, {"method": "GET", "files": list(self.FILES)}, {"per_file": hdrs})

    def load(self, con, v, staging, tmp):
        load_csv_snake(con, v.file("airports.csv"), staging["oa_airport"], all_varchar=True)
        con.execute(f'''CREATE OR REPLACE TABLE "{staging["oa_airport"]}" AS SELECT * REPLACE (
            CAST(id AS BIGINT) AS id, TRY_CAST(latitude_deg AS DOUBLE) AS latitude_deg,
            TRY_CAST(longitude_deg AS DOUBLE) AS longitude_deg, TRY_CAST(elevation_ft AS INTEGER) AS elevation_ft)
            FROM "{staging["oa_airport"]}"''')
        load_csv_snake(con, v.file("runways.csv"), staging["oa_runway"], all_varchar=True)
        con.execute(f'''CREATE OR REPLACE TABLE "{staging["oa_runway"]}" AS SELECT * REPLACE (
            CAST(id AS BIGINT) AS id, CAST(airport_ref AS BIGINT) AS airport_ref,
            TRY_CAST(length_ft AS INTEGER) AS length_ft, TRY_CAST(width_ft AS INTEGER) AS width_ft,
            lighted = '1' AS lighted, closed = '1' AS closed) FROM "{staging["oa_runway"]}"''')

    def checks(self, con, v, staging):
        n = scalar(con, f"""SELECT count(*) FROM "{staging['oa_airport']}" WHERE iso_country = 'US'
                           AND type IN ('large_airport','medium_airport') AND coalesce(iata_code,'') <> ''""")
        yield error("us_commercial_airports_present", n >= 300, f"{n} US large/medium airports with IATA", value=n)
        orphan = scalar(con, f"""SELECT count(*) FROM "{staging['oa_runway']}" r
                                LEFT JOIN "{staging['oa_airport']}" a ON a.id = r.airport_ref WHERE a.id IS NULL""")
        yield warning("runway_airport_fk", orphan == 0, f"{orphan} runways with unknown airport_ref", value=orphan)


class LocalCsv(Source):
    """A CSV maintained in the repo (curated facts or static reference lists).

    The file is still ingested through the raw store, so every change becomes a
    new vintage with a checksum, exactly like a downloaded source."""
    publisher = "Project team (curated)"
    period_kind = "version"
    history_mode = "latest"
    cadence = "manual"
    expected_lag_days = 0

    def __init__(self, id: str, title: str, path: Path, table: TableSpec, license: str, homepage: str = "",
                 notes: str = ""):
        self.id, self.title, self.path, self.license, self.homepage, self.notes = id, title, Path(path), license, homepage, notes
        self.tables = (table,)

    def available_periods(self, http=None) -> list[str]:
        return ["current"] if self.path.exists() else []

    def fetch(self, period, http=None) -> FetchResult:
        return FetchResult([RawFile(self.path.name, self.path.read_bytes())], f"file://{self.path.name}",
                           {"method": "local"})

    def load(self, con, v, staging, tmp):
        load_csv_snake(con, v.file(v.files[0]["name"]), staging[self.tables[0].name], all_varchar=True)
