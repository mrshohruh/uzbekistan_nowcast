# Collection-only workflow

From the repository root with the pinned virtual environment:

```powershell
.venv/Scripts/python.exe -B -X utf8 -m scripts.collection.run --dry-run
run_collection.bat --check-only --offline
```

Dry/check execution downloads into run-specific receipts and validates isolated candidates. It does not calculate forecasts or modify production inputs. `--offline` replays checksum-verified receipts and labels live sources `LIVE_NOT_TESTED`; missing archived URLs fail visibly.

After verification, the future scheduled command is `run_collection.bat --commit`. It publishes **collection versions only**, under `data/collection/versions`, via an atomic `data/collection/current.json` pointer. Production masters, existing forecast artifacts and accepted runtime seal remain unchanged. `scripts.collection.versions.current_snapshot` is the required hash-verifying reader. Never point existing production readers at partially copied collection files. Integration of collection versions with sealed production orchestration requires an explicit reviewed migration and is not silently enabled here.

`--root` accepts an isolated replica; `--store` selects its evidence/version directory. Both source registry and contracts come from the selected root. `--as-of` requires offline replay. No publication dates are guessed. Nine source families are attempted independently; no inactive indicator is fetched. Nominal canonical industry remains unchanged; approved real SIAT577 observations are versioned in data/recovery and recovery_observations_long. POS comparable recovery remains <=2024-12; later candidates are withheld. New GDP requires the existing documented first-release admission gate.

Exit codes: 0 validated/committed/no information change; 2 degraded source collection (valid independent data may be committed to the collection store); 3 aborted validation; 4 blocked lock/seal/recovery/configuration. Inspect each run_manifest, source_status, observation_decisions, archive_audit and source_receipts alongside collection.log. A degraded run is never reported as clean success. Immutable receipts survive parsing and promotion failures.

The shared `data/staging/operations.lock` excludes concurrent legacy writers. Pending legacy transactions or collection journals block the next run. `--recover-run <run_id>` reconciles a journal only with this lock held: finish a fully published version or mark unpublished candidates abandoned; never automatically publish interrupted candidates. A stale process lock must be reviewed separately; this command does not guess or remove it. Old immutable versions remain readable throughout pointer publication and interruptions.

Use only fixed monthly slots on days **1, 11 and 21, Asia/Tashkent**. No release-calendar scheduler, event triggers or Task Scheduler installation is included. Choose a clock time and verify the unattended account's network/TLS, permissions, pinned environment, lock-recovery procedure and exit monitoring before installation. Current implementation files are additive and outside the accepted production runtime seal; each collection version records existing registry/model hashes. No existing seal was regenerated or accepted.
