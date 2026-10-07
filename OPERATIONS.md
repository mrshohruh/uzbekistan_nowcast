# Production operations

Install and bootstrap the pinned environment and external data as described in README.md.

- Cached validation: `python -m scripts.production.update --run-nowcast --dry-run --no-network`.
- Update and publish: `python -m scripts.production.update --run-nowcast`.
- Frozen reconstruction: `python -m scripts.production.run --output-dir results/diagnostics/reproduction --no-publish`.
- Tests: `python -X utf8 -m scripts.maintenance.validate_current`.

`run_nowcast.bat` delegates to the current production updater. Review each run manifest before interpreting changes. Source failures remain visible; raw downloads and observed retrieval/release dates are preserved. Historical as-of requests cannot append prospective snapshots. Staged project copies are removed after validation; raw receipts and transaction backups remain available.

The accepted seal protects code, configuration, registry and scientific policy. Intentional code or scientific-policy changes require a new explicit migration and equivalence review; never refresh hashes to hide a failed check. Approved observation updates use transaction manifests and immutable provenance, rather than pretending the initial replay data never change.
