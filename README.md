# Uzbekistan GDP Nowcasting

The database archives official macroeconomic sources, preserves retrieval and release information, and feeds the current quarterly GDP nowcast. GDP remains quarterly. The target is the published cumulative year-to-date real GDP YoY percent (volume index minus 100).

## Current production model

The active pointer is `results/operations/current_production.json`. Its frozen policy selects **M0 / COMBO_50_50**: 50% DFM and 50% USD/UZS U-MIDAS. At the saved 2026-10-05 information cutoff, the 2026Q3 H3 nowcast is **8.180901340616275%** (DFM 8.301152885464585; U-MIDAS 8.060649795767965).

M0 uses one dynamic factor with AR order 2, estimated with DynamicFactorMQ EM (500 maximum iterations; tolerance 1e-5). The balanced training span begins January 2019. Predictors are industrial production, PPI, USD/UZS, RUB/UZS, gold price, M2, foreign-exchange reserves excluding gold, and POS turnover. Training means and sample standard deviations precede the target quarter; winsorization is disabled. The quarterly bridge uses mean factor aggregation and lagged GDP (bridge B). Missing and release-ineligible observations retain the existing ragged-edge treatment. POS after December 2024 is withheld.

U-MIDAS uses three monthly USD/UZS log changes, an intercept, and lagged GDP, with the existing registry-lag information masks. Combination weights remain 0.5 / 0.5. No model selection, new predictors, or coefficient changes were made during repository consolidation.

`config/production.json` indexes the authoritative policy, frozen specifications, registry and data paths. `scripts.production.config.configuration` resolves settings from these documents rather than duplicating scientific parameters. Transformations remain defined by registry v1.2 and the frozen specification's documented industrial-production/POS recovery exceptions. Unknown release dates remain null; typical registry lags do not constitute observed releases. Historical evaluation has incomplete predictor release vintages and uses documented lag assumptions. Prospective validation remains pending.

## Architecture

- `src/uznowcast/`: registry validation, acquisition/parsers, immutable provenance, transformations, masters, benchmark models and frozen operational utilities.
- `scripts/operations/`: transactional source updates, staging, release checks and snapshot governance. `run_update.py` orchestrates these operations.
- `scripts/production/`: active model fits, diagnostics, dashboard rendering and production orchestration.
- `tests/`: ingestion, transformations, information boundaries, model calculations, rollback/regression and current production tests.
- `scripts/maintenance/`: inventory, consolidation audit and production-freeze validation.

The current seal is `config/production_seal.json`, with an explicit acceptance record. Historical kernels and compatibility namespaces are recovered from Git history. Immutable snapshot receipts retain their original paths; `config/provenance_relocations.json` resolves their archived locations without rewriting evidence.

## Install

Use Python 3.11+; the pinned environment was built on Python 3.12.10 / Windows.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pip install -r requirements-models.txt
.venv/Scripts/python.exe -m pip install -e . --no-deps
```

On Linux/macOS use `.venv/bin/python`. Run commands from the repository root so the `scripts` package is importable. A clean checkout requires the explicitly listed external data in `config/bootstrap_inputs.json`. Keep a source data repository or bundle with that relative file layout; restore only the listed checksum-verified inputs:

```powershell
.venv/Scripts/python.exe -m scripts.operations.bootstrap --source-root C:/path/to/preserved-data
```

This restores intentionally ignored masters, processed observations, metadata and referenced raw evidence. It never copies source code or arbitrary working-tree files. Missing historical source references remain documented as missing. New official downloads use the registry-driven `python -m uznowcast.cli build` pipeline; a fresh download is not a substitute for frozen vintages.

## Update and run

Inspect cached data without fetching new observations or promoting outputs:

```powershell
.venv/Scripts/python.exe -m scripts.production.update --run-nowcast --dry-run --no-network
```

Refresh official sources through the transactional updater and rebuild the active production output:

```powershell
.venv/Scripts/python.exe -m scripts.production.update --run-nowcast
```

Rebuild the latest committed information set in a separate output directory:

```powershell
.venv/Scripts/python.exe -m scripts.production.run --output-dir results/diagnostics/reproduction --no-publish
```

The source update preserves raw receipts, revisions and vintages, validates staged changes, and promotes accepted changes transactionally. Historical `--as-of` requests and dry runs do not append snapshots. H1/H2/H3 retain the existing calendar/release masks. The production builder reuses the committed information cutoff rather than advancing it with the clock. Review each run manifest and warnings; cached runs do not check provider availability. Use `python -m uznowcast.cli build --help` for the registry-driven initial data bootstrap and its offline/refresh options.

## Tests and freeze verification

```powershell
.venv/Scripts/python.exe -X utf8 -m scripts.maintenance.validate_current
```

Tests cover ingestion, transformations, information boundaries, current DFM/U-MIDAS, the accepted seal and transactional operations. The runner uses short Windows temporary paths. Tests prohibit network requests.

## Outputs

`results/current/index.json` locates the authoritative nowcast, policy and dashboard. Scientific diagnostics reside in `results/current/`, and `results/diagnostics/` holds historical validation inputs and optional reproductions. The active dashboard is `dashboard/current/uzbekistan_nowcast.html`; the active nowcast is `results/current/current_nowcast.json`. Operational ledgers, snapshots and receipts reside under `results/operations/`. GDP remains in the quarterly target table.

See `results/repository_cleanup/phase6h1_final_cleanup.md` for the checkpoint, seal migration, exact scientific comparison, removals and clean-checkout validation.
