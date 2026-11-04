"""Source registry. Adding a source = add an adapter instance here."""
from __future__ import annotations

from ..config import Paths
from .base import Source, TableSpec
from .atads import AtadsAirportOperations
from .bts import BtsLookups, OnTimeReporting, T100SegmentAllCarriers
from .faa import AcaisWorkbook, TerminalAreaForecast
from .faa_investment import FaaGrants, Npias
from .geo_econ import BeaCountyIncome, CensusCbsaDelineation, NasrAirports
from .other import LocalCsv, OurAirports

CONSTRAINT_COLUMNS = ("airport_iata", "category", "item", "value", "unit", "effective_from", "effective_to", "status",
                      "source_title", "source_url", "source_published", "evidence_quote", "retrieved_at",
                      "review_by", "verification")


def registry(paths: Paths) -> dict[str, Source]:
    srcs: list[Source] = [
        T100SegmentAllCarriers(),
        OnTimeReporting(),
        AtadsAirportOperations(),
        BtsLookups(),
        AcaisWorkbook("commercial-service-enplanements"),
        AcaisWorkbook("all-cargo-airports"),
        TerminalAreaForecast(),
        FaaGrants(),
        Npias(),
        OurAirports(),
        NasrAirports(),
        CensusCbsaDelineation(),
        BeaCountyIncome(),
        LocalCsv("ref_us_states", "US states & territories with Census region/division", paths.reference / "us_states.csv",
                 TableSpec("ref_us_state", "State code -> name, FIPS, Census region & division.",
                           required_columns=("state_abr", "state_name", "census_region", "census_division"),
                           not_null=("state_abr",), unique_key=("state_abr",), unique_key_blocking=True, min_rows=50),
                 license="Derived from U.S. Census Bureau regions & divisions (public domain)",
                 homepage="https://www2.census.gov/geo/pdfs/maps-data/maps/reference/us_regdiv.pdf"),
        LocalCsv("ref_county_aliases", "County renames between FAA NASR and BEA/Census", paths.reference / "county_name_aliases.csv",
                 TableSpec("ref_county_name_alias", "NASR county name -> current county FIPS, with reason.",
                           required_columns=("state_abr", "nasr_county_name", "county_fips", "reason"),
                           not_null=("state_abr", "nasr_county_name", "county_fips"),
                           unique_key=("state_abr", "nasr_county_name"), unique_key_blocking=True, min_rows=1),
                 license="Project reference (facts from Census/BEA geography notes)"),
        LocalCsv("ref_airport_geo_overrides", "Airport-level county overrides (e.g. CT planning regions)",
                 paths.reference / "airport_geo_overrides.csv",
                 TableSpec("ref_airport_geo_override", "FAA LID -> current county-equivalent FIPS, legacy FIPS, reason.",
                           required_columns=("faa_lid", "county_fips", "legacy_county_fips", "reason"),
                           not_null=("faa_lid", "county_fips", "reason"), unique_key=("faa_lid",),
                           unique_key_blocking=True, min_rows=1),
                 license="Project reference (Census geography change notes)"),
        LocalCsv("curated_constraints", "Curated airport constraints & capacity projects (cited)",
                 paths.curated / "airport_constraints.csv",
                 TableSpec("curated_constraint",
                           "Facts not available in any dataset (caps, curfews, runway geometry, projects). "
                           "Every row cites a source URL and a verbatim evidence quote.",
                           required_columns=CONSTRAINT_COLUMNS,
                           not_null=("airport_iata", "category", "item", "source_url", "verification"),
                           min_rows=1),
                 license="Mixed — facts cited from public sources; see source_url per row",
                 notes="Hand-maintained. `verification` records who checked the citation and how."),
    ]
    return {s.id: s for s in srcs}


__all__ = ["Source", "TableSpec", "registry"]
