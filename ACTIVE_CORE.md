# Active Uzbekistan nowcasting core

Production and prospective research use distinct GDP information policies. Do not
substitute one set of forecasts for the other or retune either frozen model.

| Purpose | Entry point or evidence |
|---|---|
| Registry-driven ingestion | `python -m uznowcast.cli build --scope pilot8 --offline --fx-end 2026-09-29` |
| Frozen production | `src/uznowcast/operational/phase5b1.py`; `results/production/` |
| Production dashboard | `dashboard/current/uzbekistan_nowcast.html` |
| Prospective shadow monitor | `scripts/research/phase6d/monitor.py` |
| Shadow dashboard | `dashboard/phase6d_shadow_monitor.html` |
| Frozen DFM implementation | `scripts/research/phase6c/kernel.py` |
| Verified GDP vintage boundary | `scripts/research/phase6b2/vintages.py` |
| Frozen benchmark adapter | `scripts/research/phase6b2/run.py` |
| Immutable prospective evidence | `results/phase6d/`, including snapshots, ledger, withdrawals and source checks |
| Current registry | `registry/uzbekistan_nowcasting_v1.2_registry.xlsx` |
| Cleanup decisions and verification | `results/cleanup/cleanup_report.md` and `cleanup_manifest.json` |

Run commands from the repository root with `.venv/Scripts/python.exe` on Windows.
Older code and results can remain essential: import graphs, test references and
frozen manifests determine their status, not phase numbers.

## Validate without recording another forecast

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv/Scripts/python.exe scripts/maintenance/cleanup_validate.py shadow
.venv/Scripts/python.exe scripts/maintenance/cleanup_validate.py production
```

These commands write validation reports only under `results/cleanup/`. The shadow
validator reconstructs the saved input snapshot at its original timestamp and
does not call the monitor's operational writer, access the network, append the
prospective ledger, or change Phase 6D manifests.

The saved production release references older master-data hashes than the current
masters. The cleanup report records this pre-existing drift. Preserve the saved
headline and investigate its input vintage separately; do not repair it by
changing the frozen specification or overwriting current data during cleanup.

## What must stay frozen

The DFM uses industrial production, PPI, USD/UZS, RUB/UZS, gold, M2, reserves
excluding gold and verified POS. It has one factor, AR(2), bridge B and quarterly
mean aggregation. POS after December 2024 remains missing.

The combinations retain exact weights: 0.5/0.5 and
0.5438822544881572/0.4561177455118428. The production ensemble retains equal
AR(2)/USD U-MIDAS(3) weights. First-release scoring and withdrawal records remain
separate from the append-only forecast ledger.

Archived paths mirror the originals under `archive/historical_results/` or
`archive/legacy_code/`. Restore individual files using the corresponding entries
in `results/cleanup/archived_files.csv`. Unknown files, user modifications,
official raw evidence and every path pinned by active frozen manifests are kept.
