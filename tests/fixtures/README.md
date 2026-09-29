# Frozen official-source fixtures

Retrieved on 2026-09-29 from registry-specified official sources. Phase 2A fixture
provenance is recorded in `provenance.json`; Phase 2B originals and sidecars remain in the
immutable raw archive.

The Phase 2A SIAT fixtures reduce metadata to the fields needed by the parser. The Phase 2B
SIAT fixtures are frozen copies of the archived live JSON. `m2_page.html` and `m2.xlsx` are
the official CBU page and its linked DCS workbook; tests parse the exact `Broad money
liabilities` row.

The USD fixture is an original CBU snapshot. Tests create explicitly synthetic mutations
and numerical examples solely for boundary/error cases, never for production ingestion.
