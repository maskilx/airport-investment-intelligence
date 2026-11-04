"""Airport Investment Intelligence — data foundation layer.

Layers (each depends only on the ones above it):
    sources/     source adapters: metadata, fetch, integrity, load-to-staging
    rawstore     immutable, vintaged archive of original downloaded files
    validation   generic + source-specific checks, results persisted per vintage
    build        reproducible DuckDB build from the raw archive
    coverage     data-coverage assertions (does the DB support the questions?)

Nothing here knows about LLMs, agents, or UIs. Downstream layers read the
DuckDB file (or call `airport_data.db.connect`) and the manifest tables.
"""

__version__ = "0.1.0"
